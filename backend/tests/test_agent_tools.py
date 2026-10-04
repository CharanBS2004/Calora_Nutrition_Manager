import pytest
from app.core.database import (
    SessionLocal,
    Base,
    engine,
    ensure_recipe_ingredient_quantity_column,
)
from app.models.entities import User, Food, NutritionGoal
from app.services.agent.tools import agent_tools

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    ensure_recipe_ingredient_quantity_column()
    db = SessionLocal()
    # Ensure test user exists
    user = db.query(User).filter(User.email == "agent_test_user@example.com").first()
    if not user:
        user = User(email="agent_test_user@example.com", hashed_password="hashed_pw_dummy")
        db.add(user)
        db.flush()
        db.add(NutritionGoal(user_id=user.id, calorie_target=2200.0, protein_g=100.0))
        db.commit()
    yield db, user.id
    db.close()

def test_all_20_agent_tools(db_session):
    db, uid = db_session

    # 1. search_food
    res1 = agent_tools.search_food(query="tea", db=db)
    assert "foods" in res1

    paneer = agent_tools.search_food(query="Paneer", category="dairy", db=db)
    assert paneer["results_count"] > 0
    assert any(
        food["name"] == "Paneer / Cottage cheese, Cow"
        and food["protein_100g"] == 18.3
        and food["source"] == "ICMR_NIN_2017"
        for food in paneer["foods"]
    )

    snacks = agent_tools.search_food(
        query="high-protein Indian snacks",
        db=db,
    )
    assert snacks["results_count"] > 0
    assert "no explicit snack classification" in snacks["selection_note"]
    assert any(
        food["name"] == "Paneer stuffed cheela/chilla"
        and food["source"] == "INDB"
        and food["serving_unit"] == "cheela"
        and food["protein_per_serving"] is not None
        for food in snacks["foods"]
    )

    # 2. get_food_nutrition
    first_food = db.query(Food).first()
    assert first_food is not None
    res2 = agent_tools.get_food_nutrition(food_id=first_food.id, db=db)
    assert "per_100g" in res2

    # 3. calculate_recipe_nutrition
    res3 = agent_tools.calculate_recipe_nutrition(
        ingredients=[{"food_name": "Onion, big, red (Allium cepa)", "quantity": 100, "unit": "g"}],
        servings=2,
        db=db
    )
    assert "total_recipe" in res3

    # 4. log_meal
    res4 = agent_tools.log_meal(
        user_id=uid,
        meal_type="breakfast",
        items=[{"item_name": "Chapati/Roti", "quantity": 2, "unit": "chapati"}],
        db=db
    )
    assert res4["success"] is True
    meal_id = res4["meal_id"]

    # 5. update_meal
    res5 = agent_tools.update_meal(
        meal_id=meal_id,
        user_id=uid,
        items=[{"item_name": "Chapati/Roti", "quantity": 3, "unit": "chapati"}],
        db=db
    )
    assert res5["success"] is True

    # 6. get_today_meals
    res6 = agent_tools.get_today_meals(user_id=uid, db=db)
    assert res6["count"] >= 1

    # 7. get_daily_nutrition
    res7 = agent_tools.get_daily_nutrition(user_id=uid, db=db)
    assert "calories" in res7

    # 8. get_user_goals
    res8 = agent_tools.get_user_goals(user_id=uid, db=db)
    assert "calorie_target" in res8

    # 9. update_user_goals
    res9 = agent_tools.update_user_goals(user_id=uid, calories=2400.0, db=db)
    assert res9["success"] is True

    # 10. save_recipe
    res10 = agent_tools.save_recipe(
        user_id=uid,
        name="Tool Test Recipe",
        ingredients=[{"food_name": "Tomato, ripe, red (Solanum lycopersicum)", "quantity": 100, "unit": "g"}],
        servings=1,
        db=db
    )
    assert res10["success"] is True
    recipe_id = res10["recipe_id"]

    # 11. get_saved_recipes
    res11 = agent_tools.get_saved_recipes(user_id=uid, db=db)
    assert res11["recipes_count"] >= 1

    # 12. get_recipe
    res12 = agent_tools.get_recipe(recipe_id=recipe_id, user_id=uid, db=db)
    assert res12["name"] == "Tool Test Recipe"
    assert res12["ingredients"][0]["quantity"] == 100
    assert res12["ingredients"][0]["quantity_g"] == 100
    assert res12["ingredients"][0]["unit"] == "g"

    # 13. update_recipe
    res13 = agent_tools.update_recipe(recipe_id=recipe_id, user_id=uid, name="Updated Tool Recipe", db=db)
    assert res13["success"] is True

    # 14. get_health_data
    res14 = agent_tools.get_health_data(user_id=uid, db=db)
    assert "records" in res14

    # 15. calculate_energy_balance
    res15 = agent_tools.calculate_energy_balance(user_id=uid, db=db)
    assert "net_balance_kcal" in res15

    # 16. save_user_memory
    res16 = agent_tools.save_user_memory(user_id=uid, fact="Prefers less spicy dal", memory_type="preference", db=db)
    assert res16["success"] is True

    # 17. get_user_memory
    res17 = agent_tools.get_user_memory(user_id=uid, query="spicy", db=db)
    assert len(res17["memories"]) >= 1

    # 18. get_analytics
    res18 = agent_tools.get_analytics(user_id=uid, period="weekly", db=db)
    assert "summary" in res18

    # 19. generate_daily_summary
    res19 = agent_tools.generate_daily_summary(user_id=uid, db=db)
    assert "summary_text" in res19

    # 20. delete_meal
    res20 = agent_tools.delete_meal(meal_id=meal_id, user_id=uid, db=db)
    assert res20["success"] is True
