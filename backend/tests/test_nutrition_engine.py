import pytest
from app.services.nutrition_engine import nutrition_engine

def test_ingredient_nutrients_calculation():
    # Test 150g of a food with 100 kcal, 10g prot, 20g carb, 2g fat, 5g fib per 100g
    res = nutrition_engine.calculate_ingredient_nutrients(
        quantity_g=150.0,
        energy_100g=100.0,
        protein_100g=10.0,
        carb_100g=20.0,
        fat_100g=2.0,
        fiber_100g=5.0
    )
    assert res["energy_kcal"] == 150.0
    assert res["protein_g"] == 15.0
    assert res["carbohydrate_g"] == 30.0
    assert res["fat_g"] == 3.0
    assert res["fiber_g"] == 7.5

def test_custom_recipe_method_c():
    """
    Test Method C from user prompt:
    Onion 150g, Tomato 200g, Potato 250g, Carrot 100g, Oil 20g
    Total cooked recipe = 900g, User ate = 250g
    """
    ingredients = [
        {"food_name": "Onion", "quantity": 150, "unit": "g", "energy_100g": 49.0, "protein_100g": 1.2, "carb_100g": 11.1, "fat_100g": 0.1, "fiber_100g": 1.8},
        {"food_name": "Tomato", "quantity": 200, "unit": "g", "energy_100g": 21.0, "protein_100g": 0.9, "carb_100g": 3.6, "fat_100g": 0.2, "fiber_100g": 1.7},
        {"food_name": "Potato", "quantity": 250, "unit": "g", "energy_100g": 70.0, "protein_100g": 1.6, "carb_100g": 16.0, "fat_100g": 0.1, "fiber_100g": 1.7},
        {"food_name": "Carrot", "quantity": 100, "unit": "g", "energy_100g": 38.0, "protein_100g": 0.9, "carb_100g": 8.0, "fat_100g": 0.2, "fiber_100g": 4.4},
        {"food_name": "Oil", "quantity": 20, "unit": "g", "energy_100g": 900.0, "protein_100g": 0.0, "carb_100g": 0.0, "fat_100g": 100.0, "fiber_100g": 0.0}
    ]

    calc = nutrition_engine.calculate_recipe_totals(
        ingredients=ingredients,
        servings_count=3.0,
        total_cooked_weight_g=900.0,
        consumed_quantity=250.0,
        consumed_unit="g"
    )

    # Expected Total Energy:
    # Onion: 1.5 * 49 = 73.5
    # Tomato: 2.0 * 21 = 42.0
    # Potato: 2.5 * 70 = 175.0
    # Carrot: 1.0 * 38 = 38.0
    # Oil: 0.2 * 900 = 180.0
    # Total = 508.5 kcal
    assert round(calc["total_recipe"]["energy_kcal"], 1) == 508.5
    assert calc["servings_count"] == 3.0

    # Per serving: 508.5 / 3 = 169.5 kcal
    assert round(calc["per_serving"]["energy_kcal"], 1) == 169.5

    # Consumed portion: 250g of 900g cooked = 508.5 * (250 / 900) = 141.25 kcal
    assert round(calc["consumed_portion"]["energy_kcal"], 1) == 141.2
    assert calc["confidence_score"] == 1.0

def test_energy_balance_calculation():
    # 1850 consumed, 2300 burned -> -450 deficit
    balance = nutrition_engine.calculate_energy_balance(1850.0, 2300.0)
    assert balance["calories_consumed"] == 1850.0
    assert balance["calories_burned"] == 2300.0
    assert balance["net_balance_kcal"] == -450.0
    assert balance["status"] == "deficit"

    # Maintenance check within +/- 100 kcal
    maint = nutrition_engine.calculate_energy_balance(2050.0, 2000.0)
    assert maint["status"] == "maintenance"
