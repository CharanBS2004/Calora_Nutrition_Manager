from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Food
from app.services.food_lookup import normalize_unit
from app.services.nutrition_engine import nutrition_engine
from app.services.unit_converter import unit_converter


def calculate_food_portion(db: Session, food: Food, quantity: float, unit: str):
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Food quantity must be greater than zero.",
        )

    if (
        normalize_unit(unit) == normalize_unit(food.serving_unit)
        and food.unit_serving_energy_kcal is not None
    ):
        return (
            round(food.unit_serving_energy_kcal * quantity, 2),
            round((food.unit_serving_protein_g or 0) * quantity, 2),
            round((food.unit_serving_carbohydrate_g or 0) * quantity, 2),
            round((food.unit_serving_fat_g or 0) * quantity, 2),
            round((food.unit_serving_fiber_g or 0) * quantity, 2),
            round((food.weight_g or 0) * quantity, 2),
        )

    grams, _, confidence, note = unit_converter.convert_to_grams(
        food_name=food.food_name,
        quantity=quantity,
        unit=unit,
        db=db,
        serving_unit=food.serving_unit,
    )
    if confidence <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=note,
        )

    nutrients = nutrition_engine.calculate_ingredient_nutrients(
        quantity_g=grams,
        energy_100g=food.energy_kcal,
        protein_100g=food.protein_g,
        carb_100g=food.carbohydrate_g,
        fat_100g=food.fat_g,
        fiber_100g=food.fiber_g,
    )
    return (
        nutrients["energy_kcal"],
        nutrients["protein_g"],
        nutrients["carbohydrate_g"],
        nutrients["fat_g"],
        nutrients["fiber_g"],
        grams,
    )
