import json
import re
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, Meal, MealItem, Food, Recipe
from app.schemas.all_schemas import MealCreate, MealResponse, MealItemResponse
from app.services.nutrition_engine import nutrition_engine
from app.services.unit_converter import unit_converter
from app.services.food_lookup import (
    dataset_unit_conversions,
    find_food_matches,
    normalize_unit,
)
from app.services.food_nutrition import calculate_food_portion
from app.services.dietary_preferences import non_vegetarian_components
from app.services.llm_client import LLMConfigurationError, LLMResponseError
from app.services.nutrition_ai import nutrition_ai

router = APIRouter(prefix="/meals", tags=["Meal Logging"])

@router.post("", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def log_meal(
    meal_in: MealCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log a meal with multiple items.
    Calculates nutrition deterministically using INDB and food density converter.
    """
    total_cal = 0.0
    total_prot = 0.0
    total_carb = 0.0
    total_fat = 0.0
    total_fib = 0.0
    conf_scores = []
    dietary_preference = (
        current_user.profile.dietary_preference
        if current_user.profile is not None
        else None
    )

    meal_record = Meal(
        user_id=current_user.id,
        meal_type=meal_in.meal_type.lower(),
        logged_at=meal_in.logged_at or datetime.now(timezone.utc),
        notes=meal_in.notes
    )
    db.add(meal_record)
    db.flush()

    items_to_add = []
    for item in meal_in.items:
        if item.recipe_id:
            recipe = db.query(Recipe).filter(
                Recipe.id == item.recipe_id,
                Recipe.user_id == current_user.id,
            ).first()
            if recipe is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recipe not found or unauthorized.",
                )
            conflicts = non_vegetarian_components(
                dietary_preference,
                _recipe_dietary_components(db, recipe),
            )
            if conflicts and not item.dietary_confirmed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Your profile is {dietary_preference}; "
                        f"'{recipe.name}' contains {', '.join(conflicts)}. "
                        "Explicit dietary confirmation is required before logging."
                    ),
                )
            item_unit = item.unit or recipe.serving_unit
            if normalize_unit(item_unit) not in (
                normalize_unit(recipe.serving_unit), "serving", "servings"
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Recipe quantity must use '{recipe.serving_unit}'.",
                )
            cal = round(recipe.calories_per_serving * item.quantity, 2)
            prot = round(recipe.protein_per_serving * item.quantity, 2)
            carb = round(recipe.carb_per_serving * item.quantity, 2)
            fat = round(recipe.fat_per_serving * item.quantity, 2)
            fib = round(recipe.fiber_per_serving * item.quantity, 2)
            weight_g = round(
                (recipe.total_cooked_weight_g or 0) / max(recipe.servings_count, 1) * item.quantity,
                2,
            )
            food_obj = None
        else:
            food_obj = db.query(Food).filter(Food.id == item.food_id).first() if item.food_id else None
            if item.food_id and food_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Food record not found.",
                )
            if food_obj is None:
                matches = find_food_matches(db, item.item_name)
                if not matches:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"No exact dataset match for '{item.item_name}'.",
                    )
                if len(matches) > 1:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail={
                            "message": f"'{item.item_name}' matches multiple dataset records; select a food_id.",
                            "matches": [food.food_name for food, _ in matches],
                        },
                    )
                food_obj = matches[0][0]
            if food_obj.is_custom:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Nutrition can only be logged from a provided dataset record.",
                )
            conflicts = non_vegetarian_components(
                dietary_preference,
                [food_obj.food_name, food_obj.category or ""],
            )
            if conflicts and not item.dietary_confirmed:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Your profile is {dietary_preference}; "
                        f"'{food_obj.food_name}' is marked as non-vegetarian. "
                        "Explicit dietary confirmation is required before logging."
                    ),
                )

            item_unit = item.unit or food_obj.serving_unit
            cal, prot, carb, fat, fib, weight_g = calculate_food_portion(
                db, food_obj, item.quantity, item_unit
            )
        conf = 1.0

        total_cal += cal or 0
        total_prot += prot or 0
        total_carb += carb or 0
        total_fat += fat or 0
        total_fib += fib or 0
        conf_scores.append(conf or 1.0)

        meal_item = MealItem(
            meal_id=meal_record.id,
            food_id=food_obj.id if food_obj else None,
            recipe_id=item.recipe_id,
            item_name=food_obj.food_name if food_obj else recipe.name,
            quantity=item.quantity,
            unit=item_unit,
            weight_g=weight_g,
            calories=round(cal or 0, 2),
            protein=round(prot or 0, 2),
            carbs=round(carb or 0, 2),
            fat=round(fat or 0, 2),
            fiber=round(fib or 0, 2),
            confidence_score=round(conf or 1.0, 2)
        )
        db.add(meal_item)
        items_to_add.append(meal_item)

    meal_record.total_calories = round(total_cal, 2)
    meal_record.total_protein = round(total_prot, 2)
    meal_record.total_carbs = round(total_carb, 2)
    meal_record.total_fat = round(total_fat, 2)
    meal_record.total_fiber = round(total_fib, 2)
    meal_record.confidence_score = round(sum(conf_scores) / max(len(conf_scores), 1), 2)

    db.commit()
    db.refresh(meal_record)

    return _format_meal(meal_record)

@router.post("/parse-text")
def parse_meal_text(
    text: str = Query(..., description="Natural language meal description (e.g. 'I ate 2 idlis and one bowl of sambar')"),
    meal_type: Optional[str] = "lunch",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    selected_item_name: Optional[str] = None,
    selected_option: Optional[str] = None,
    parsed_items: Optional[str] = None,
    selected_options: Optional[str] = None,
):
    """
    Understand meal text with the configured LLM, then retrieve and calculate only dataset records.
    """
    recognized_items = []
    clarifications = []
    dietary_preference = (
        current_user.profile.dietary_preference
        if current_user is not None and current_user.profile is not None
        else None
    )
    if parsed_items is None:
        try:
            parsed = nutrition_ai.parse_meal(text)
        except LLMConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (LLMResponseError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        try:
            parsed = {
                "meal_type": None,
                "items": nutrition_ai.normalize_meal_items(json.loads(parsed_items)),
            }
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid meal analysis state: {exc}",
            ) from exc
    try:
        selections = json.loads(selected_options) if selected_options else {}
        if not isinstance(selections, dict) or any(
            not isinstance(key, str)
            or not (
                isinstance(value, str)
                or isinstance(value, list)
                and all(isinstance(option, str) for option in value)
            )
            for key, value in selections.items()
        ):
            raise ValueError("Meal clarification selections must map item keys to text options.")
        selections = {
            key: [value] if isinstance(value, str) else value
            for key, value in selections.items()
        }
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid meal analysis state: {exc}") from exc

    if not parsed["items"]:
        clarifications.append({
            "item_name": "",
            "item_key": "0",
            "question": "What food would you like to log?",
            "options": [],
        })

    if parsed["meal_type"]:
        meal_type = parsed["meal_type"]

    if selected_item_name and selected_option:
        selections.setdefault(selected_item_name.strip().casefold(), []).append(selected_option)

    pending_items = []
    for item_index, parsed_item in enumerate(parsed["items"]):
        item_key = str(item_index)
        food_query = parsed_item["food_query"]
        pending_items.append({
            "food_query": food_query,
            "quantity": parsed_item["quantity"],
            "unit": parsed_item["unit"],
        })
        selected_options_for_item = (
            selections.get(item_key)
            or selections.get(food_query.strip().casefold())
            or []
        )
        matches = find_food_matches(db, food_query)
        normalized_query = " ".join(re.findall(r"[a-z0-9]+", food_query.casefold()))
        saved_recipes = (
            db.query(Recipe).filter(
                Recipe.user_id == current_user.id,
                Recipe.is_saved.is_(True),
            ).all()
            if current_user is not None
            else []
        )
        matching_recipes = [
            recipe for recipe in saved_recipes
            if normalized_query
            and normalized_query in " ".join(
                re.findall(r"[a-z0-9]+", recipe.name.casefold())
            )
        ]
        selected_recipe = next(
            (
                recipe for recipe in matching_recipes
                if f"Saved recipe: {recipe.name} "
                f"(serving: 1 {recipe.serving_unit})"
                in selected_options_for_item
            ),
            None,
        )
        if matching_recipes and selected_recipe is None and not any(
            option.startswith("Food dataset: ") for option in selected_options_for_item
        ):
            recipe_options = [
                f"Saved recipe: {recipe.name} "
                f"(serving: 1 {recipe.serving_unit})"
                for recipe in matching_recipes
            ]
            food_options = [
                f"Food dataset: {food.food_name} "
                f"(serving: {food.serving_size:g} {food.serving_unit})"
                for food, _ in matches
            ]
            clarifications.append({
                "item_name": food_query,
                "item_key": item_key,
                "question": (
                    f"Did you mean one of your saved recipes for {food_query}, "
                    "or a food from the nutrition dataset?"
                ),
                "options": recipe_options + food_options,
            })
            continue

        if selected_recipe is not None:
            quantity = parsed_item["quantity"]
            unit = parsed_item["unit"]
            for selected_option_for_item in selected_options_for_item:
                portion = re.fullmatch(
                    r"\s*(\d+(?:\.\d+)?)\s+(.+?)\s*",
                    selected_option_for_item,
                )
                if (
                    quantity is None
                    and portion
                    and normalize_unit(portion.group(2))
                    == normalize_unit(selected_recipe.serving_unit)
                ):
                    quantity = float(portion.group(1))
                    unit = portion.group(2)
            if quantity is None:
                clarifications.append({
                    "item_name": selected_recipe.name,
                    "item_key": item_key,
                    "question": (
                        f"How many {selected_recipe.serving_unit} of your saved "
                        f"{selected_recipe.name} did you have?"
                    ),
                    "options": [
                        f"1 {selected_recipe.serving_unit}",
                        f"2 {selected_recipe.serving_unit}",
                    ],
                })
                continue
            if unit and normalize_unit(unit) not in (
                normalize_unit(selected_recipe.serving_unit),
                "serving",
                "servings",
            ):
                clarifications.append({
                    "item_name": selected_recipe.name,
                    "item_key": item_key,
                    "question": (
                        f"Your saved recipe is measured in "
                        f"{selected_recipe.serving_unit}. How many servings did you have?"
                    ),
                    "options": [
                        f"1 {selected_recipe.serving_unit}",
                        f"2 {selected_recipe.serving_unit}",
                    ],
                })
                continue
            conflicts = non_vegetarian_components(
                dietary_preference,
                _recipe_dietary_components(db, selected_recipe),
            )
            dietary_accept_option = "Yes, include this item"
            dietary_remove_option = "No, remove this item"
            if conflicts and dietary_remove_option in selected_options_for_item:
                continue
            dietary_confirmed = not conflicts or dietary_accept_option in selected_options_for_item
            if conflicts and not dietary_confirmed:
                clarifications.append({
                    "item_name": selected_recipe.name,
                    "item_key": item_key,
                    "question": (
                        f"Your dietary preference is {dietary_preference}. "
                        f"Your saved recipe contains {', '.join(conflicts)}. "
                        "Are you okay including it in this meal?"
                    ),
                    "options": [dietary_accept_option, dietary_remove_option],
                })
                continue
            item_cal = round(selected_recipe.calories_per_serving * quantity, 2)
            item_prot = round(selected_recipe.protein_per_serving * quantity, 2)
            item_carb = round(selected_recipe.carb_per_serving * quantity, 2)
            item_fat = round(selected_recipe.fat_per_serving * quantity, 2)
            item_fib = round(selected_recipe.fiber_per_serving * quantity, 2)
            grams = round(
                (selected_recipe.total_cooked_weight_g or 0)
                / max(selected_recipe.servings_count, 1)
                * quantity,
                2,
            )
            recognized_items.append({
                "food_id": None,
                "recipe_id": selected_recipe.id,
                "item_name": selected_recipe.name,
                "source": "saved_recipe",
                "quantity": quantity,
                "unit": selected_recipe.serving_unit,
                "serving_size": 1,
                "serving_unit": selected_recipe.serving_unit,
                "weight_g": grams,
                "calories": item_cal,
                "protein": item_prot,
                "carbs": item_carb,
                "fat": item_fat,
                "fiber": item_fib,
                "dietary_confirmed": dietary_confirmed,
                "confidence_score": 1.0,
                "is_uncertain": False,
            })
            continue

        selected_dataset_option = next(
            (
                option.removeprefix("Food dataset: ")
                for option in selected_options_for_item
                if option.startswith("Food dataset: ")
            ),
            None,
        )
        if selected_dataset_option is not None:
            matches = [
                (food, score) for food, score in matches
                if selected_dataset_option
                == f"{food.food_name} (serving: {food.serving_size:g} {food.serving_unit})"
            ]
        if not matches:
            clarifications.append({
                "item_name": food_query,
                "item_key": item_key,
                "question": (
                    f"I couldn't find an exact match for '{food_query}' in the available nutrition "
                    "dataset. Could you provide another name or specify the food?"
                ),
                "options": [],
            })
            continue

        selected_food = next(
            (
                food for food, _ in matches
                if (
                    f"{food.food_name} (serving: {food.serving_size:g} {food.serving_unit})"
                    in selected_options_for_item
                    or f"Food dataset: {food.food_name} "
                    f"(serving: {food.serving_size:g} {food.serving_unit})"
                    in selected_options_for_item
                )
            ),
            None,
        )
        if selected_food is not None:
            matches = [(selected_food, 1.0)]

        if len(matches) > 1:
            clarifications.append({
                "item_name": food_query,
                "item_key": item_key,
                "question": f"Which dataset entry do you mean by {food_query}?",
                "options": [
                    f"{food.food_name} (serving: {food.serving_size:g} {food.serving_unit})"
                    for food, _ in matches
                ],
            })
            continue

        food = matches[0][0]
        quantity = parsed_item["quantity"]
        requested_unit = parsed_item["unit"]
        valid_units = list(dict.fromkeys(
            [food.serving_unit] + [
                unit for unit, _ in dataset_unit_conversions(db, food)
                if normalize_unit(unit) != normalize_unit(food.serving_unit)
            ]
        ))
        for selected_option_for_item in selected_options_for_item:
            if quantity is None:
                portion = re.fullmatch(
                    r"\s*(\d+(?:\.\d+)?)\s+(.+?)\s*",
                    selected_option_for_item,
                )
                if portion and any(
                    normalize_unit(portion.group(2)) == normalize_unit(unit)
                    for unit in valid_units
                ):
                    quantity = float(portion.group(1))
                    requested_unit = portion.group(2)
            elif selected_option_for_item:
                selected_unit = next(
                    (
                        unit for unit in valid_units
                        if normalize_unit(selected_option_for_item) == normalize_unit(unit)
                    ),
                    None,
                )
                if selected_unit is not None:
                    requested_unit = selected_unit

        if quantity is None:
            clarifications.append({
                "item_name": food.food_name,
                "item_key": item_key,
                "question": f"How much {food.food_name} did you have? This record is measured in {food.serving_unit}.",
                "options": [f"1 {unit}" for unit in valid_units] + [f"2 {unit}" for unit in valid_units],
            })
            continue

        if requested_unit is None and normalize_unit(food.serving_unit) in ("g", "gram", "grams"):
            clarifications.append({
                "item_name": food.food_name,
                "item_key": item_key,
                "question": f"How many grams of {food.food_name} did you have?",
                "options": [
                    f"{food.serving_size:g} {food.serving_unit}",
                    f"{food.serving_size * 2:g} {food.serving_unit}",
                ],
            })
            continue
        unit = requested_unit or food.serving_unit
        try:
            values = calculate_food_portion(db, food, quantity, unit)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY:
                raise
            valid_units = [food.serving_unit] + [
                unit_name for unit_name, _ in dataset_unit_conversions(db, food)
                if normalize_unit(unit_name) != normalize_unit(food.serving_unit)
            ]
            clarifications.append({
                "item_name": food.food_name,
                "item_key": item_key,
                "question": (
                    f"The dataset does not define '{unit}' for {food.food_name}. "
                    f"Which supported measurement did you use?"
                ),
                "options": list(dict.fromkeys(valid_units)),
            })
            continue

        item_cal, item_prot, item_carb, item_fat, item_fib, grams = values
        conflicts = non_vegetarian_components(
            dietary_preference,
            [food.food_name, food.category or ""],
        )
        dietary_accept_option = "Yes, include this item"
        dietary_remove_option = "No, remove this item"
        if conflicts and dietary_remove_option in selected_options_for_item:
            continue
        dietary_confirmed = not conflicts or dietary_accept_option in selected_options_for_item
        if conflicts and not dietary_confirmed:
            clarifications.append({
                "item_name": food.food_name,
                "item_key": item_key,
                "question": (
                    f"Your dietary preference is {dietary_preference}. "
                    f"{food.food_name} is marked as non-vegetarian. "
                    "Are you okay including it in this meal?"
                ),
                "options": [dietary_accept_option, dietary_remove_option],
            })
            continue
        recognized_items.append({
            "food_id": food.id,
            "food_code": food.food_code,
            "item_name": food.food_name,
            "source": food.source,
            "quantity": quantity,
            "unit": unit,
            "serving_size": food.serving_size,
            "serving_unit": food.serving_unit,
            "weight_g": grams,
            "calories": item_cal,
            "protein": item_prot,
            "carbs": item_carb,
            "fat": item_fat,
            "fiber": item_fib,
            "dietary_confirmed": dietary_confirmed,
            "confidence_score": 1.0,
            "is_uncertain": False,
        })

    total_calories = sum(i["calories"] for i in recognized_items)
    total_protein = sum(i["protein"] for i in recognized_items)
    total_carbs = sum(i["carbs"] for i in recognized_items)
    total_fat = sum(i["fat"] for i in recognized_items)
    total_fiber = sum(i["fiber"] for i in recognized_items)

    return {
        "meal_type": meal_type,
        "pending_items": [
            {"item_key": str(index), **item}
            for index, item in enumerate(pending_items)
        ],
        "recognized_items": recognized_items,
        "total_calories": round(total_calories, 2),
        "total_protein": round(total_protein, 2),
        "total_carbs": round(total_carbs, 2),
        "total_fat": round(total_fat, 2),
        "total_fiber": round(total_fiber, 2),
        "has_uncertainty": len(clarifications) > 0,
        "clarifications": clarifications
    }

@router.get("/today", response_model=List[MealResponse])
def get_today_meals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all meals logged today for the authenticated user."""
    today = date.today()
    meals = db.query(Meal).filter(
        Meal.user_id == current_user.id,
        func.date(Meal.logged_at) == today
    ).order_by(Meal.logged_at.asc()).all()

    return [_format_meal(m) for m in meals]

@router.get("", response_model=List[MealResponse])
def get_meals(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve meal history for a date range with user data isolation."""
    query = db.query(Meal).filter(Meal.user_id == current_user.id)
    if start_date:
        query = query.filter(func.date(Meal.logged_at) >= start_date)
    if end_date:
        query = query.filter(func.date(Meal.logged_at) <= end_date)

    meals = query.order_by(Meal.logged_at.desc()).all()
    return [_format_meal(m) for m in meals]

@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a logged meal with user authorization check."""
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == current_user.id).first()
    if not meal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found or unauthorized.")
    db.delete(meal)
    db.commit()
    return None

def _recipe_dietary_components(db: Session, recipe: Recipe) -> List[str]:
    components = []
    for ingredient in recipe.ingredients:
        components.append(ingredient.ingredient_name)
        if ingredient.food_id is not None:
            food = db.query(Food).filter(Food.id == ingredient.food_id).first()
            if food is not None:
                components.extend([food.food_name, food.category or ""])
    return components


def _format_meal(meal: Meal) -> MealResponse:
    items_out = []
    for it in meal.items:
        items_out.append(
            MealItemResponse(
                id=it.id,
                item_name=it.item_name,
                quantity=it.quantity,
                unit=it.unit,
                weight_g=it.weight_g,
                calories=it.calories,
                protein=it.protein,
                carbs=it.carbs,
                fat=it.fat,
                fiber=it.fiber,
                confidence_score=it.confidence_score
            )
        )
    return MealResponse(
        id=meal.id,
        user_id=meal.user_id,
        meal_type=meal.meal_type,
        logged_at=meal.logged_at,
        total_calories=meal.total_calories,
        total_protein=meal.total_protein,
        total_carbs=meal.total_carbs,
        total_fat=meal.total_fat,
        total_fiber=meal.total_fiber,
        confidence_score=meal.confidence_score,
        notes=meal.notes,
        items=items_out
    )
