import json

import pytest
from fastapi import HTTPException

from app.core.database import SessionLocal, ensure_recipe_ingredient_quantity_column
from app.models.entities import Food, Meal, Recipe, RecipeIngredient, User, UserProfile
from app.services.food_lookup import find_food_matches
from app.services.food_lookup import resolve_recipe_food
from app.services.food_nutrition import calculate_food_portion
from app.services.llm_client import openrouter_client
from app.services.nutrition_ai import nutrition_ai
from app.api.v1.meals import log_meal, parse_meal_text
from app.api.v1.recipes import calculate_recipe, save_recipe
from app.schemas.all_schemas import (
    IngredientInput,
    MealCreate,
    MealItemCreate,
    RecipeCalculateRequest,
    RecipeCreate,
)


@pytest.fixture
def db():
    ensure_recipe_ingredient_quantity_column()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def parse_with_llm(monkeypatch, parsed_response):
    calls = []

    def complete_json(system_prompt, user_prompt):
        calls.append((system_prompt, json.loads(user_prompt)))
        return parsed_response

    monkeypatch.setattr(openrouter_client, "complete_json", complete_json)
    return calls


def test_two_chapathis_use_dataset_serving_nutrition(db, monkeypatch):
    calls = parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "chapathis", "quantity": 2, "unit": None}],
    })

    result = parse_meal_text("I ate 2 chapathis", "lunch", db, None)
    food = db.query(Food).filter(Food.food_name == "Chapati/Roti").one()

    assert len(calls) == 1
    assert calls[0][1]["message"] == "I ate 2 chapathis"
    assert len(result["recognized_items"]) == 1
    item = result["recognized_items"][0]
    assert item["food_id"] == food.id
    assert item["source"] == food.source
    assert item["unit"] == food.serving_unit == "chapati"
    assert item["calories"] == round(food.unit_serving_energy_kcal * 2, 2)
    assert item["calories"] != 50


def test_multiple_meal_foods_are_included_in_analyze_and_confirm_totals(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [
            {"food_query": "chapathi", "quantity": 1, "unit": None},
            {"food_query": "Chicken curry", "quantity": 1, "unit": None},
        ],
    })

    analyzed = parse_meal_text("1 chapathi and 1 chicken curry", "lunch", db, None)
    assert not analyzed["clarifications"]
    assert len(analyzed["recognized_items"]) == 2
    assert analyzed["total_calories"] == pytest.approx(
        sum(item["calories"] for item in analyzed["recognized_items"])
    )
    assert analyzed["total_protein"] == pytest.approx(
        sum(item["protein"] for item in analyzed["recognized_items"])
    )

    user = User(
        email="multi_item_meal_totals@example.com",
        hashed_password="test-hash",
    )
    db.add(user)
    db.commit()
    meal = None
    try:
        meal = log_meal(
            MealCreate(
                meal_type="lunch",
                items=[
                    MealItemCreate(
                        food_id=item["food_id"],
                        item_name=item["item_name"],
                        quantity=item["quantity"],
                        unit=item["unit"],
                    )
                    for item in analyzed["recognized_items"]
                ],
            ),
            user,
            db,
        )
        assert len(meal.items) == 2
        assert meal.total_calories == pytest.approx(
            sum(item.calories for item in meal.items)
        )
        assert meal.total_protein == pytest.approx(
            sum(item.protein for item in meal.items)
        )
    finally:
        if meal is not None:
            saved_meal = db.query(Meal).filter(Meal.id == meal.id).one()
            db.delete(saved_meal)
        db.delete(user)
        db.commit()


def test_generic_curry_keeps_meal_incomplete_until_variant_is_selected(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [
            {"food_query": "chapathi", "quantity": 1, "unit": None},
            {"food_query": "curry", "quantity": 1, "unit": None},
        ],
    })

    result = parse_meal_text("1 chapathi and 1 curry", "lunch", db, None)

    assert result["has_uncertainty"]
    assert len(result["recognized_items"]) == 1
    assert result["recognized_items"][0]["item_name"] == "Chapati/Roti"
    assert result["clarifications"][0]["item_name"] == "curry"
    assert len(result["clarifications"][0]["options"]) > 1
    assert result["total_calories"] == result["recognized_items"][0]["calories"]


def test_saved_recipe_is_offered_and_used_in_analyze_meal(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [
            {"food_query": "Chapati/Roti", "quantity": 2, "unit": None},
            {"food_query": "My Brinjal Curry", "quantity": 1, "unit": None},
        ],
    })
    user = User(
        email="saved_recipe_meal_analysis@example.com",
        hashed_password="test-hash",
    )
    db.add(user)
    db.flush()
    recipe = Recipe(
        user_id=user.id,
        name="My Brinjal Curry",
        servings_count=3,
        serving_unit="bowl",
        is_saved=True,
        calories_per_serving=185,
        protein_per_serving=7.5,
        carb_per_serving=20,
        fat_per_serving=8,
        fiber_per_serving=5,
        total_cooked_weight_g=600,
    )
    db.add(recipe)
    db.commit()
    try:
        initial = parse_meal_text(
            "2 chapathis and 1 My Brinjal Curry",
            "lunch",
            db,
            user,
        )
        curry_question = next(
            question for question in initial["clarifications"]
            if question["item_name"] == "My Brinjal Curry"
        )
        assert any(
            option.startswith("Saved recipe: My Brinjal Curry")
            for option in curry_question["options"]
        )
        saved_option = next(
            option for option in curry_question["options"]
            if option.startswith("Saved recipe: My Brinjal Curry")
        )

        resolved = parse_meal_text(
            "2 chapathis and 1 My Brinjal Curry",
            "lunch",
            db,
            user,
            parsed_items=json.dumps(initial["pending_items"]),
            selected_options=json.dumps({"1": [saved_option]}),
        )

        assert not resolved["clarifications"]
        assert len(resolved["recognized_items"]) == 2
        curry_item = resolved["recognized_items"][1]
        assert curry_item["recipe_id"] == recipe.id
        assert curry_item["item_name"] == recipe.name
        assert curry_item["calories"] == 185
        assert resolved["total_calories"] == pytest.approx(
            sum(item["calories"] for item in resolved["recognized_items"])
        )

        meal = log_meal(
            MealCreate(
                meal_type="lunch",
                items=[
                    MealItemCreate(
                        food_id=item.get("food_id"),
                        recipe_id=item.get("recipe_id"),
                        item_name=item["item_name"],
                        quantity=item["quantity"],
                        unit=item["unit"],
                    )
                    for item in resolved["recognized_items"]
                ],
            ),
            user,
            db,
        )
        try:
            saved_recipe_item = next(
                item for item in meal.items if item.item_name == recipe.name
            )
            assert saved_recipe_item.calories == pytest.approx(185)
            assert meal.total_calories == pytest.approx(resolved["total_calories"])
        finally:
            db.delete(db.query(Meal).filter(Meal.id == meal.id).one())
            db.commit()
    finally:
        db.delete(db.query(User).filter(User.id == user.id).one())
        db.commit()


def test_vegetarian_profile_requires_confirmation_for_nonvegetarian_food(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "Chicken curry", "quantity": 1, "unit": None}],
    })
    user = User(
        email="vegetarian_food_warning@example.com",
        hashed_password="test-hash",
        profile=UserProfile(name="Veg User", dietary_preference="vegetarian"),
    )
    db.add(user)
    db.commit()
    try:
        initial = parse_meal_text("1 chicken curry", "lunch", db, user)
        assert initial["has_uncertainty"]
        warning = initial["clarifications"][0]
        assert "vegetarian" in warning["question"]
        assert "Chicken curry" in warning["question"]
        assert warning["options"] == [
            "Yes, include this item",
            "No, remove this item",
        ]
        assert not initial["recognized_items"]

        confirmed = parse_meal_text(
            "1 chicken curry",
            "lunch",
            db,
            user,
            parsed_items=json.dumps(initial["pending_items"]),
            selected_options=json.dumps({"0": ["Yes, include this item"]}),
        )
        assert not confirmed["clarifications"]
        assert confirmed["recognized_items"][0]["dietary_confirmed"] is True

        item = confirmed["recognized_items"][0]
        with pytest.raises(HTTPException) as error:
            log_meal(
                MealCreate(
                    meal_type="lunch",
                    items=[MealItemCreate(
                        food_id=item["food_id"],
                        item_name=item["item_name"],
                        quantity=item["quantity"],
                        unit=item["unit"],
                    )],
                ),
                user,
                db,
            )
        assert error.value.status_code == 409

        meal = log_meal(
            MealCreate(
                meal_type="lunch",
                items=[MealItemCreate(
                    food_id=item["food_id"],
                    item_name=item["item_name"],
                    quantity=item["quantity"],
                    unit=item["unit"],
                    dietary_confirmed=item["dietary_confirmed"],
                )],
            ),
            user,
            db,
        )
        db.delete(db.query(Meal).filter(Meal.id == meal.id).one())
        db.commit()
    finally:
        db.delete(db.query(User).filter(User.id == user.id).one())
        db.commit()


def test_vegetarian_profile_warns_when_saved_recipe_contains_meat(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "My Chicken Curry", "quantity": 1, "unit": None}],
    })
    user = User(
        email="vegetarian_recipe_warning@example.com",
        hashed_password="test-hash",
        profile=UserProfile(name="Veg User", dietary_preference="vegetarian"),
    )
    db.add(user)
    db.flush()
    chicken = db.query(Food).filter(Food.food_name == "Chicken curry").one()
    recipe = Recipe(
        user_id=user.id,
        name="My Chicken Curry",
        servings_count=1,
        serving_unit="serving",
        is_saved=True,
        calories_per_serving=200,
    )
    db.add(recipe)
    db.flush()
    db.add(RecipeIngredient(
        recipe_id=recipe.id,
        food_id=chicken.id,
        ingredient_name=chicken.food_name,
        quantity=100,
        quantity_g=100,
        unit="g",
    ))
    db.commit()
    try:
        initial = parse_meal_text("1 My Chicken Curry", "lunch", db, user)
        saved_option = next(
            option for option in initial["clarifications"][0]["options"]
            if option.startswith("Saved recipe: My Chicken Curry")
        )
        result = parse_meal_text(
            "1 My Chicken Curry",
            "lunch",
            db,
            user,
            parsed_items=json.dumps(initial["pending_items"]),
            selected_options=json.dumps({"0": [saved_option]}),
        )
        assert result["has_uncertainty"]
        assert any(
            "contains Chicken curry" in clarification["question"]
            for clarification in result["clarifications"]
        )
        assert result["clarifications"][0]["options"] == [
            "Yes, include this item",
            "No, remove this item",
        ]
    finally:
        db.delete(db.query(User).filter(User.id == user.id).one())
        db.commit()


def test_missing_quantity_requests_dataset_serving(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "chapathi", "quantity": None, "unit": None}],
    })

    result = parse_meal_text("I ate chapathi", "lunch", db, None)

    assert not result["recognized_items"]
    assert result["has_uncertainty"]
    assert "How much" in result["clarifications"][0]["question"]
    assert any("chapati" in option for option in result["clarifications"][0]["options"])


def test_quantity_chip_resolves_without_reparsing_or_losing_original_food(db, monkeypatch):
    calls = parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [
            {"food_query": "chapathi", "quantity": None, "unit": None},
            {"food_query": "Chicken curry", "quantity": 1, "unit": None},
        ],
    })
    original_text = "chapathi and one chicken curry"
    initial = parse_meal_text(original_text, "lunch", db, None)

    resolved = parse_meal_text(
        original_text,
        "lunch",
        db,
        None,
        parsed_items=json.dumps(initial["pending_items"]),
        selected_options=json.dumps({"0": "2 chapati"}),
    )

    assert len(calls) == 1
    assert not resolved["clarifications"]
    assert [item["item_name"] for item in resolved["recognized_items"]] == [
        "Chapati/Roti",
        "Chicken curry",
    ]
    assert resolved["recognized_items"][0]["quantity"] == 2
    assert resolved["total_calories"] == pytest.approx(
        sum(item["calories"] for item in resolved["recognized_items"])
    )


def test_ambiguous_coffee_lists_only_dataset_records(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "coffee", "quantity": None, "unit": None}],
    })

    result = parse_meal_text("I had coffee", "lunch", db, None)

    assert not result["recognized_items"]
    options = result["clarifications"][0]["options"]
    assert len(options) > 1
    assert any("Instant coffee" in option for option in options)
    assert any("Steeped hot coffee" in option for option in options)
    assert all("50 kcal" not in option for option in options)


def test_multiple_variant_selections_persist_until_all_foods_resolve(db, monkeypatch):
    calls = parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [
            {"food_query": "curry", "quantity": 1, "unit": None},
            {"food_query": "coffee", "quantity": 1, "unit": None},
        ],
    })
    original_text = "one curry and one coffee"
    initial = parse_meal_text(original_text, "lunch", db, None)
    assert len(initial["clarifications"]) == 2

    paneer_curry = db.query(Food).filter(Food.food_name == "Paneer curry").one()
    curry_option = (
        f"{paneer_curry.food_name} "
        f"(serving: {paneer_curry.serving_size:g} {paneer_curry.serving_unit})"
    )
    first_resolution = parse_meal_text(
        original_text,
        "lunch",
        db,
        None,
        parsed_items=json.dumps(initial["pending_items"]),
        selected_options=json.dumps({"0": curry_option}),
    )
    assert [item["item_key"] for item in first_resolution["clarifications"]] == ["1"]

    coffee = db.query(Food).filter(Food.food_name == "Instant coffee").one()
    coffee_option = (
        f"{coffee.food_name} (serving: {coffee.serving_size:g} {coffee.serving_unit})"
    )
    resolved = parse_meal_text(
        original_text,
        "lunch",
        db,
        None,
        parsed_items=json.dumps(initial["pending_items"]),
        selected_options=json.dumps({
            "0": curry_option,
            "1": coffee_option,
        }),
    )

    assert len(calls) == 1
    assert not resolved["clarifications"]
    assert [item["item_name"] for item in resolved["recognized_items"]] == [
        "Paneer curry",
        "Instant coffee",
    ]


def test_variant_and_quantity_answers_both_persist_for_one_food(db, monkeypatch):
    calls = parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "curry", "quantity": None, "unit": None}],
    })
    original_text = "curry"
    initial = parse_meal_text(original_text, "lunch", db, None)
    paneer_curry = db.query(Food).filter(Food.food_name == "Paneer curry").one()
    curry_option = (
        f"{paneer_curry.food_name} "
        f"(serving: {paneer_curry.serving_size:g} {paneer_curry.serving_unit})"
    )

    selected_variant = parse_meal_text(
        original_text,
        "lunch",
        db,
        None,
        parsed_items=json.dumps(initial["pending_items"]),
        selected_options=json.dumps({"0": [curry_option]}),
    )
    assert selected_variant["clarifications"][0]["item_key"] == "0"
    quantity_option = next(
        option
        for option in selected_variant["clarifications"][0]["options"]
        if option.startswith("1 ")
    )

    resolved = parse_meal_text(
        original_text,
        "lunch",
        db,
        None,
        parsed_items=json.dumps(initial["pending_items"]),
        selected_options=json.dumps({"0": [curry_option, quantity_option]}),
    )

    assert len(calls) == 1
    assert not resolved["clarifications"]
    assert len(resolved["recognized_items"]) == 1
    assert resolved["recognized_items"][0]["item_name"] == "Paneer curry"
    assert resolved["recognized_items"][0]["quantity"] == 1


def test_selected_dataset_option_resolves_ambiguous_food(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "roti", "quantity": 2, "unit": None}],
    })
    selected_food = db.query(Food).filter(Food.food_name == "Chapati/Roti").one()
    selected_option = (
        f"{selected_food.food_name} "
        f"(serving: {selected_food.serving_size:g} {selected_food.serving_unit})"
    )

    result = parse_meal_text(
        "I ate 2 rotis",
        "lunch",
        db,
        None,
        selected_item_name="Roti",
        selected_option=selected_option,
    )

    assert not result["clarifications"]
    assert len(result["recognized_items"]) == 1
    item = result["recognized_items"][0]
    assert item["food_id"] == selected_food.id
    assert item["source"] == selected_food.source
    assert item["quantity"] == 2
    assert item["unit"] == selected_food.serving_unit
    assert item["calories"] == round(selected_food.unit_serving_energy_kcal * 2, 2)


def test_selected_curry_variant_is_counted_once_with_the_other_meal_food(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [
            {"food_query": "chapathi", "quantity": 1, "unit": None},
            {"food_query": "curry", "quantity": 1, "unit": None},
        ],
    })
    selected_food = db.query(Food).filter(Food.food_name == "Paneer curry").one()
    selected_option = (
        f"{selected_food.food_name} "
        f"(serving: {selected_food.serving_size:g} {selected_food.serving_unit})"
    )

    result = parse_meal_text(
        "1 chapathi and 1 curry",
        "lunch",
        db,
        None,
        selected_item_name="curry",
        selected_option=selected_option,
    )

    assert not result["clarifications"]
    assert [item["item_name"] for item in result["recognized_items"]].count(
        "Paneer curry"
    ) == 1
    assert len(result["recognized_items"]) == 2
    assert result["total_calories"] == pytest.approx(
        sum(item["calories"] for item in result["recognized_items"])
    )


def test_unsupported_cup_unit_is_not_assumed_for_coffee(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "Steeped hot coffee", "quantity": 2, "unit": "cup"}],
    })

    result = parse_meal_text("I had 2 cups of steeped hot coffee", "lunch", db, None)

    assert not result["recognized_items"]
    assert "does not define 'cup'" in result["clarifications"][0]["question"]
    assert "tea cup" in result["clarifications"][0]["options"]


def test_unknown_food_has_no_fabricated_nutrition(db, monkeypatch):
    parse_with_llm(monkeypatch, {
        "meal_type": None,
        "items": [{"food_query": "imaginary mooncake", "quantity": 1, "unit": "piece"}],
    })

    result = parse_meal_text("I ate an imaginary mooncake", "lunch", db, None)

    assert not result["recognized_items"]
    assert "couldn't find an exact match" in result["clarifications"][0]["question"]
    assert result["total_calories"] == 0
    assert find_food_matches(db, "imaginary mooncake") == []


def test_dataset_household_conversion_is_food_specific(db):
    food = db.query(Food).filter(Food.food_name == "Boiled rice (Uble chawal)").one()

    calories, *_ = calculate_food_portion(db, food, 1, "cup")

    assert calories == round(food.energy_kcal * 1.6, 2)


def test_unknown_unit_is_rejected_without_generic_conversion(db):
    food = db.query(Food).filter(Food.food_name == "Steeped hot coffee").one()

    with pytest.raises(HTTPException) as error:
        calculate_food_portion(db, food, 2, "cup")

    assert error.value.status_code == 422


def test_recipe_ingredients_resolve_through_dataset_recipe_crosswalk(db):
    expected = {
        "Onion": ("Onion, big, red (Allium cepa)", "F024", "ICMR_NIN_2017"),
        "Tomato": ("Tomato, ripe, red (Solanum lycopersicum)", "D057", "ICMR_NIN_2017"),
        "Mustard oil": ("Oil, mustard", "T510", "US_FCT"),
        "Potato": ("Potato, brown skin (Solanum tuberosum)", "F027", "ICMR_NIN_2017"),
        "Paneer": ("Paneer / Cottage cheese, Cow", "L007", "ICMR_NIN_2017"),
    }

    for ingredient, (food_name, food_code, source) in expected.items():
        food = resolve_recipe_food(db, ingredient)
        assert (food.food_name, food.food_code, food.source) == (
            food_name,
            food_code,
            source,
        )


def test_recipe_mapping_rejects_stale_code_when_food_name_disagrees(db):
    food = resolve_recipe_food(db, "Potato", food_code="F006")

    assert food.food_name == "Potato, brown skin (Solanum tuberosum)"
    assert food.food_code == "F027"
    assert food.food_name != "Carrot (Daucus carota)"


def test_recipe_mapping_reports_multiple_compatible_food_records(db):
    duplicate = Food(
        food_code="TEST-PANEER",
        food_name="Paneer",
        category="Milk and Milk Products",
        source="TEST",
        serving_size=100,
        serving_unit="g",
        weight_g=100,
        energy_kcal=250,
        protein_g=18,
        carbohydrate_g=3,
        fat_g=20,
        fiber_g=0,
        is_custom=False,
    )
    db.add(duplicate)
    db.flush()
    try:
        with pytest.raises(ValueError, match="Could not reliably map 'Paneer'.*Matching records"):
            resolve_recipe_food(db, "Paneer")
    finally:
        db.rollback()


def test_recipe_mapping_collapses_duplicate_records_with_identical_nutrition(db, monkeypatch, tmp_path):
    import app.services.food_lookup as food_lookup

    original = db.query(Food).filter(
        Food.food_name == "Onion, big, red (Allium cepa)"
    ).one()
    duplicate = Food(
        food_code="DUPLICATE-ONION",
        food_name=original.food_name,
        category=original.category,
        source="TEST",
        serving_size=original.serving_size,
        serving_unit=original.serving_unit,
        weight_g=original.weight_g,
        energy_kcal=original.energy_kcal,
        protein_g=original.protein_g,
        carbohydrate_g=original.carbohydrate_g,
        fat_g=original.fat_g,
        fiber_g=original.fiber_g,
        is_custom=False,
    )
    db.add(duplicate)
    db.flush()
    monkeypatch.setattr(food_lookup.settings, "INDB_DATASET_DIR", str(tmp_path / "empty"))

    resolved = resolve_recipe_food(db, "Onion")

    assert resolved.id == original.id


def test_recipe_mapping_keeps_same_name_foods_with_different_nutrition_ambiguous(
    db, monkeypatch, tmp_path
):
    import app.services.food_lookup as food_lookup

    original = db.query(Food).filter(Food.food_name == "Paneer").one_or_none()
    if original is None:
        original = Food(
            food_code="TEST-PANEER-BASE",
            food_name="Paneer",
            category="Milk and Milk Products",
            source="TEST",
            serving_size=100,
            serving_unit="g",
            weight_g=100,
            energy_kcal=250,
            protein_g=18,
            carbohydrate_g=3,
            fat_g=20,
            fiber_g=0,
            is_custom=False,
        )
        db.add(original)
        db.flush()
    duplicate = Food(
        food_code="TEST-PANEER-DIFFERENT",
        food_name=original.food_name,
        category=original.category,
        source="TEST",
        serving_size=original.serving_size,
        serving_unit=original.serving_unit,
        weight_g=original.weight_g,
        energy_kcal=original.energy_kcal + 10,
        protein_g=original.protein_g,
        carbohydrate_g=original.carbohydrate_g,
        fat_g=original.fat_g,
        fiber_g=original.fiber_g,
        is_custom=False,
    )
    db.add(duplicate)
    db.flush()
    monkeypatch.setattr(food_lookup.settings, "INDB_DATASET_DIR", str(tmp_path / "empty"))

    with pytest.raises(ValueError, match=r"source=TEST, code=TEST-PANEER"):
        resolve_recipe_food(db, "Paneer")


def test_current_recipe_ingredients_save_with_dataset_food_ids(db):
    user = User(
        email="recipe_mapping_regression@example.com",
        hashed_password="test-hash",
    )
    db.add(user)
    db.commit()
    ingredients = [
        IngredientInput(food_name="Onion", quantity=100, unit="g"),
        IngredientInput(food_name="Tomato", quantity=150, unit="g"),
        IngredientInput(food_name="Mustard oil", quantity=1, unit="g"),
        IngredientInput(food_name="Potato", quantity=200, unit="g"),
        IngredientInput(food_name="Paneer", quantity=100, unit="g"),
    ]
    recipe = None
    try:
        response = save_recipe(
            RecipeCreate(
                name="Dataset Mapping Regression",
                ingredients=ingredients,
                servings_count=4,
                total_cooked_weight_g=551,
            ),
            user,
            db,
        )
        recipe = db.query(Recipe).filter(Recipe.id == response.id).one()
        linked_codes = {
            db.query(Food).filter(Food.id == ingredient.food_id).one().food_code
            for ingredient in recipe.ingredients
        }
        assert len(recipe.ingredients) == 5
        assert all(ingredient.food_id is not None for ingredient in recipe.ingredients)
        assert linked_codes == {"F024", "D057", "T510", "F027", "L007"}
        assert [ingredient.unit for ingredient in recipe.ingredients] == ["g"] * 5
        assert [ingredient.quantity for ingredient in recipe.ingredients] == [
            100,
            150,
            1,
            200,
            100,
        ]
    finally:
        if recipe is not None:
            db.delete(recipe)
        db.delete(user)
        db.commit()


def test_recipe_does_not_guess_missing_mustard_oil_tablespoon_conversion(db):
    request = RecipeCalculateRequest(
        ingredients=[IngredientInput(food_name="Mustard oil", quantity=1, unit="tbsp")],
    )

    with pytest.raises(HTTPException) as error:
        calculate_recipe(request, db, None)

    assert error.value.status_code == 422
    assert "has no conversion" in error.value.detail


def test_natural_language_parser_uses_configured_llm_client(monkeypatch):
    from app.core.config import settings
    import httpx

    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": '{"items": []}'}}]}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, payload=json, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(httpx, "post", fake_post)

    result = nutrition_ai.parse_meal("I ate lunch")

    assert result["items"] == []
    assert seen["url"].endswith("/chat/completions")
    assert seen["headers"]["Authorization"] == "Bearer test-key"
    assert seen["payload"]["response_format"] == {"type": "json_object"}
    assert "do not invent" in seen["payload"]["messages"][0]["content"]


def test_coach_response_prompt_is_conversational_and_grounded(monkeypatch):
    from app.services.nutrition_ai import nutrition_ai

    seen = {}

    def fake_complete_text(system_prompt, user_prompt):
        seen["system_prompt"] = system_prompt
        return "You're making steady progress."

    monkeypatch.setattr(openrouter_client, "complete_text", fake_complete_text)
    reply = nutrition_ai.write_coach_response(
        "How am I doing today?",
        {"account_name": "Casey"},
        [{"tool": "get_daily_nutrition", "result": {"calories": {"consumed": 500}}}],
        {},
    )

    assert reply == "You're making steady progress."
    assert "warm, conversational nutrition coach" in seen["system_prompt"]
    assert "do not include digits, calorie or\nmacro counts" in seen["system_prompt"]
    assert "For a\nfood nutrition question, answer from the matching dataset record" in seen["system_prompt"]
    assert "Include exact numbers only when the user" in seen["system_prompt"]
    assert "Never" in seen["system_prompt"]
    assert "nutrition, meals, goals, or personal details" in seen["system_prompt"]


def test_coach_prompt_retrieves_broad_food_recommendations_from_dataset(monkeypatch):
    seen = {}

    def fake_complete_json(system_prompt, user_prompt):
        seen["prompt"] = system_prompt
        return {
            "tool_calls": [{
                "name": "search_food",
                "arguments": {"query": "high-protein Indian snacks"},
            }]
        }

    monkeypatch.setattr(openrouter_client, "complete_json", fake_complete_json)
    calls = nutrition_ai.plan_coach_tools(
        "Can you suggest high-protein Indian snacks?",
        None,
        [{"name": "search_food", "arguments": ["query", "category"]}],
    )

    assert calls[0]["name"] == "search_food"
    assert "For broad food recommendations" in seen["prompt"]
    assert "phrase search miss as proof" in seen["prompt"]


def test_coach_preserves_dataset_food_category_limitation(monkeypatch):
    monkeypatch.setattr(
        openrouter_client,
        "complete_text",
        lambda *args: "Here are a few options from the dataset.",
    )

    reply = nutrition_ai.write_coach_response(
        "Can you suggest high-protein Indian snacks?",
        {},
        [{
            "tool": "search_food",
            "result": {
                "selection_note": (
                    "The dataset has no explicit snack classification. These are prepared dishes."
                )
            },
        }],
        {},
    )

    assert reply.startswith(
        "The dataset does not explicitly label a snack category; these are matching "
        "prepared-dish records."
    )
