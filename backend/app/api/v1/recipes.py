from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, Recipe, RecipeIngredient, Meal, MealItem
from app.schemas.all_schemas import (
    RecipeCreate, RecipeResponse, RecipeCalculateRequest,
    RecipeCalculationResult, MealResponse, MealItemResponse
)
from app.services.nutrition_engine import nutrition_engine
from app.services.food_lookup import resolve_recipe_food

router = APIRouter(prefix="/recipes", tags=["Recipe Builder & Library"])

@router.post("/calculate", response_model=RecipeCalculationResult)
def calculate_recipe(
    request: RecipeCalculateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """
    Deterministically calculate nutrition for a custom recipe before saving or logging.
    Supports total cooked weight, servings count, and consumed portion calculations.
    """
    ingredients_data = []
    for ing in request.ingredients:
        try:
            food = resolve_recipe_food(db, ing.food_name, ing.food_id, ing.food_code)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        ingredients_data.append({
            "food_id": food.id,
            "food_name": food.food_name,
            "quantity": ing.quantity,
            "unit": ing.unit,
            "energy_100g": food.energy_kcal,
            "protein_100g": food.protein_g,
            "carb_100g": food.carbohydrate_g,
            "fat_100g": food.fat_g,
            "fiber_100g": food.fiber_g,
            "serving_unit": food.serving_unit,
        })

    try:
        calc = nutrition_engine.calculate_recipe_totals(
            ingredients=ingredients_data,
            servings_count=request.servings_count,
            total_cooked_weight_g=request.total_cooked_weight_g,
            consumed_quantity=request.consumed_quantity,
            consumed_unit=request.consumed_unit or "serving",
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RecipeCalculationResult(
        total_recipe=calc["total_recipe"],
        per_serving=calc["per_serving"],
        per_100g=calc["per_100g"],
        consumed_portion=calc["consumed_portion"],
        confidence_score=calc["confidence_score"],
        notes=f"Total raw weight: {calc['total_raw_weight_g']}g"
    )

@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def save_recipe(
    request: RecipeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a custom recipe to the user's personal recipe library."""
    ingredients_data = []
    for ing in request.ingredients:
        try:
            food_obj = resolve_recipe_food(db, ing.food_name, ing.food_id, ing.food_code)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        ingredients_data.append({
            "food_id": food_obj.id,
            "food_name": food_obj.food_name,
            "quantity": ing.quantity,
            "unit": ing.unit,
            "energy_100g": food_obj.energy_kcal,
            "protein_100g": food_obj.protein_g,
            "carb_100g": food_obj.carbohydrate_g,
            "fat_100g": food_obj.fat_g,
            "fiber_100g": food_obj.fiber_g,
            "serving_unit": food_obj.serving_unit,
        })

    try:
        calc = nutrition_engine.calculate_recipe_totals(
            ingredients=ingredients_data,
            servings_count=request.servings_count,
            total_cooked_weight_g=request.total_cooked_weight_g,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    new_recipe = Recipe(
        user_id=current_user.id,
        name=request.name.strip(),
        description=request.description,
        category=request.category or "My Recipes",
        total_cooked_weight_g=request.total_cooked_weight_g,
        servings_count=request.servings_count,
        serving_unit=request.serving_unit,
        is_saved=True,
        is_system=False,
        calories_per_serving=calc["per_serving"]["energy_kcal"],
        protein_per_serving=calc["per_serving"]["protein_g"],
        carb_per_serving=calc["per_serving"]["carbohydrate_g"],
        fat_per_serving=calc["per_serving"]["fat_g"],
        fiber_per_serving=calc["per_serving"]["fiber_g"],
        total_calories=calc["total_recipe"]["energy_kcal"],
        total_protein=calc["total_recipe"]["protein_g"],
        total_carb=calc["total_recipe"]["carbohydrate_g"],
        total_fat=calc["total_recipe"]["fat_g"],
        total_fiber=calc["total_recipe"]["fiber_g"]
    )
    db.add(new_recipe)
    db.flush()

    for item in calc["ingredients"]:
        ing_model = RecipeIngredient(
            recipe_id=new_recipe.id,
            food_id=item["food_id"],
            ingredient_name=item["food_name"],
            quantity=item["input_quantity"],
            quantity_g=item["weight_g"],
            unit=item["input_unit"],
            energy_kcal=item["nutrients"]["energy_kcal"],
            protein_g=item["nutrients"]["protein_g"],
            carbohydrate_g=item["nutrients"]["carbohydrate_g"],
            fat_g=item["nutrients"]["fat_g"],
            fiber_g=item["nutrients"]["fiber_g"]
        )
        db.add(ing_model)

    db.commit()
    db.refresh(new_recipe)

    return _format_recipe_response(new_recipe)

@router.get("", response_model=List[RecipeResponse])
def list_recipes(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all saved recipes belonging to the current user (and system recipes)."""
    query = db.query(Recipe).filter(
        (Recipe.user_id == current_user.id) | (Recipe.is_system == True)
    )
    if category:
        query = query.filter(Recipe.category == category)

    recipes = query.order_by(Recipe.created_at.desc()).all()
    return [_format_recipe_response(r) for r in recipes]

@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve recipe details with strict ownership verification."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe or (recipe.user_id != current_user.id and not recipe.is_system):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")
    return _format_recipe_response(recipe)

@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user recipe with ownership authorization."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.user_id == current_user.id).first()
    if not recipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found or unauthorized.")
    db.delete(recipe)
    db.commit()
    return None

@router.post("/{recipe_id}/log", response_model=MealResponse)
def log_recipe_meal(
    recipe_id: int,
    servings: float = 1.0,
    meal_type: str = "lunch",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Quick-log a saved recipe directly into a meal."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe or (recipe.user_id != current_user.id and not recipe.is_system):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")

    cal = round(recipe.calories_per_serving * servings, 2)
    prot = round(recipe.protein_per_serving * servings, 2)
    carb = round(recipe.carb_per_serving * servings, 2)
    fat = round(recipe.fat_per_serving * servings, 2)
    fib = round(recipe.fiber_per_serving * servings, 2)

    new_meal = Meal(
        user_id=current_user.id,
        meal_type=meal_type,
        total_calories=cal,
        total_protein=prot,
        total_carbs=carb,
        total_fat=fat,
        total_fiber=fib,
        confidence_score=1.0,
        notes=f"Logged from saved recipe: {recipe.name}"
    )
    db.add(new_meal)
    db.flush()

    item = MealItem(
        meal_id=new_meal.id,
        recipe_id=recipe.id,
        item_name=recipe.name,
        quantity=servings,
        unit="serving",
        weight_g=round((recipe.total_cooked_weight_g or 100.0) / max(recipe.servings_count, 1) * servings, 1),
        calories=cal,
        protein=prot,
        carbs=carb,
        fat=fat,
        fiber=fib,
        confidence_score=1.0
    )
    db.add(item)
    db.commit()
    db.refresh(new_meal)

    return MealResponse(
        id=new_meal.id,
        user_id=new_meal.user_id,
        meal_type=new_meal.meal_type,
        logged_at=new_meal.logged_at,
        total_calories=new_meal.total_calories,
        total_protein=new_meal.total_protein,
        total_carbs=new_meal.total_carbs,
        total_fat=new_meal.total_fat,
        total_fiber=new_meal.total_fiber,
        confidence_score=new_meal.confidence_score,
        notes=new_meal.notes,
        items=[
            MealItemResponse(
                id=item.id,
                item_name=item.item_name,
                quantity=item.quantity,
                unit=item.unit,
                weight_g=item.weight_g,
                calories=item.calories,
                protein=item.protein,
                carbs=item.carbs,
                fat=item.fat,
                fiber=item.fiber,
                confidence_score=item.confidence_score
            )
        ]
    )

def _format_recipe_response(recipe: Recipe) -> RecipeResponse:
    ingredients_list = []
    for ing in recipe.ingredients:
        ingredients_list.append({
            "id": ing.id,
            "food_id": ing.food_id,
            "ingredient_name": ing.ingredient_name,
            "quantity": ing.quantity if ing.quantity is not None else ing.quantity_g,
            "quantity_g": ing.quantity_g,
            "unit": ing.unit,
            "unit": ing.unit,
            "energy_kcal": ing.energy_kcal,
            "protein_g": ing.protein_g,
            "carbohydrate_g": ing.carbohydrate_g,
            "fat_g": ing.fat_g,
            "fiber_g": ing.fiber_g
        })

    return RecipeResponse(
        id=recipe.id,
        user_id=recipe.user_id,
        name=recipe.name,
        description=recipe.description,
        category=recipe.category,
        total_cooked_weight_g=recipe.total_cooked_weight_g,
        servings_count=recipe.servings_count,
        serving_unit=recipe.serving_unit,
        is_saved=recipe.is_saved,
        is_system=recipe.is_system,
        calories_per_serving=recipe.calories_per_serving,
        protein_per_serving=recipe.protein_per_serving,
        carb_per_serving=recipe.carb_per_serving,
        fat_per_serving=recipe.fat_per_serving,
        fiber_per_serving=recipe.fiber_per_serving,
        total_calories=recipe.total_calories,
        total_protein=recipe.total_protein,
        total_carb=recipe.total_carb,
        total_fat=recipe.total_fat,
        total_fiber=recipe.total_fiber,
        ingredients=ingredients_list,
        created_at=recipe.created_at
    )
