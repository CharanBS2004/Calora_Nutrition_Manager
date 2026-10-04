import pytest
from app.core.database import SessionLocal, Base, engine
from app.models.entities import User, UserProfile, NutritionGoal, Recipe
from app.services.agent.agent_orchestrator import agent_orchestrator
from app.services.nutrition_ai import nutrition_ai

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "reflect_test_user@example.com").first()
    if not user:
        user = User(email="reflect_test_user@example.com", hashed_password="pw")
        db.add(user)
        db.flush()
        db.add(NutritionGoal(user_id=user.id, calorie_target=2200.0, protein_g=100.0))
    if user.profile is None:
        user.profile = UserProfile(name="Casey")
    db.commit()
    yield db, user.id
    db.close()

def test_reflection_node_goal_monitoring(db_session, monkeypatch):
    db, uid = db_session
    monkeypatch.setattr(nutrition_ai, "plan_coach_tools", lambda *args: [])
    monkeypatch.setattr(nutrition_ai, "write_coach_response", lambda *args: "Your protein progress is ready.")
    # Query about protein
    res = agent_orchestrator.run(user_id=uid, user_message="How much protein do I still need today?", db=db)
    assert res["reply"] is not None
    assert res["goal_impact"] is not None
    assert "protein_remaining_g" in res["goal_impact"]
    assert len(res["action_buttons"]) > 0

def test_uncertainty_trigger_in_agent(db_session, monkeypatch):
    db, uid = db_session
    monkeypatch.setattr(nutrition_ai, "plan_coach_tools", lambda *args: [])
    monkeypatch.setattr(nutrition_ai, "write_coach_response", lambda *args: "How much did you have?")
    # User message with ambiguous quantity word "some"
    res = agent_orchestrator.run(user_id=uid, user_message="I had some rice and curry for lunch", db=db)
    assert res["uncertainty_flag"] is True
    assert res["clarification_needed"] is not None
    assert len(res["suggested_options"]) > 0

def test_coach_uses_verified_profile_name_over_client_context(db_session, monkeypatch):
    db, uid = db_session
    captured = {}
    monkeypatch.setattr(nutrition_ai, "plan_coach_tools", lambda *args: [])

    def capture_context(message, context, tool_results, reflection):
        captured.update(context)
        return "Hi Casey."

    monkeypatch.setattr(nutrition_ai, "write_coach_response", capture_context)
    agent_orchestrator.run(
        user_id=uid,
        user_message="What is my name?",
        db=db,
        context={"account_name": "Unverified name"},
    )

    assert captured["account_name"] == db.query(User).filter(User.id == uid).one().profile.name
    assert captured["dietary_preference"] == (
        db.query(User).filter(User.id == uid).one().profile.dietary_preference
    )

def test_general_progress_reply_receives_only_high_level_status(db_session, monkeypatch):
    db, uid = db_session
    captured = {}
    monkeypatch.setattr(nutrition_ai, "plan_coach_tools", lambda *args: [])

    def capture_response(message, context, tool_results, reflection):
        captured.update(context=context, tool_results=tool_results, reflection=reflection)
        return "You're making a start with tracking today."

    monkeypatch.setattr(nutrition_ai, "write_coach_response", capture_response)
    agent_orchestrator.run(
        user_id=uid,
        user_message="How am I doing today?",
        db=db,
    )

    assert captured["context"]["response_style"].endswith("Do not include stats.")
    assert captured["tool_results"][0]["tool"] == "daily_tracking_status"
    assert isinstance(captured["tool_results"][0]["result"]["meals_logged_today"], bool)
    assert captured["reflection"] == {}


def test_saved_recipe_mention_prompts_then_retrieves_saved_nutrition(db_session, monkeypatch):
    db, _ = db_session
    user = User(email="saved_recipe_chat_confirmation@example.com", hashed_password="pw")
    db.add(user)
    db.flush()
    recipe = Recipe(
        user_id=user.id,
        name="Casey Special Dosa",
        servings_count=2,
        serving_unit="serving",
        is_saved=True,
        calories_per_serving=245,
        protein_per_serving=12.5,
        carb_per_serving=31,
        fat_per_serving=7.2,
        fiber_per_serving=4.1,
    )
    db.add(recipe)
    db.commit()
    recipe_id = recipe.id
    try:
        def unexpected_plan(*args):
            raise AssertionError("Recipe mention should be handled before generic food search.")

        monkeypatch.setattr(nutrition_ai, "plan_coach_tools", unexpected_plan)
        prompt = agent_orchestrator.run(
            user_id=user.id,
            user_message="I ate Casey Special Dosa",
            db=db,
        )

        assert "saved recipe **Casey Special Dosa**" in prompt["reply"]
        assert prompt["uncertainty_flag"] is True
        assert prompt["suggested_options"] == [
            "Yes, use my saved recipe",
            "No, search the food dataset",
        ]

        result = agent_orchestrator.run(
            user_id=user.id,
            user_message="Yes, use my saved recipe",
            db=db,
        )

        assert "245 kcal" in result["reply"]
        assert "12.5 g protein" in result["reply"]
        assert result["tool_calls"][0]["tool"] == "get_recipe"
        assert result["tool_calls"][0]["result"]["recipe_id"] == recipe_id
    finally:
        db.delete(db.query(User).filter(User.id == user.id).one())
        db.commit()


def test_declining_saved_recipe_continues_with_original_food_query(db_session, monkeypatch):
    db, _ = db_session
    user = User(email="saved_recipe_chat_decline@example.com", hashed_password="pw")
    db.add(user)
    db.flush()
    db.add(Recipe(
        user_id=user.id,
        name="My Lentil Bowl",
        servings_count=1,
        serving_unit="serving",
        is_saved=True,
        calories_per_serving=300,
    ))
    db.commit()
    planned_messages = []

    def planned_tools(message, context, tools):
        planned_messages.append(message)
        return []

    monkeypatch.setattr(nutrition_ai, "plan_coach_tools", planned_tools)
    monkeypatch.setattr(
        nutrition_ai,
        "write_coach_response",
        lambda message, context, tool_results, reflection: "I can search the food dataset instead.",
    )
    try:
        agent_orchestrator.run(
            user_id=user.id,
            user_message="I had My Lentil Bowl",
            db=db,
        )
        response = agent_orchestrator.run(
            user_id=user.id,
            user_message="No, search the food dataset",
            db=db,
        )

        assert response["reply"] == "I can search the food dataset instead."
        assert planned_messages == ["I had My Lentil Bowl"]
    finally:
        db.delete(db.query(User).filter(User.id == user.id).one())
        db.commit()
