import pytest
from datetime import date, datetime
from sqlalchemy import func
from app.core.database import SessionLocal, Base, engine
from app.models.entities import User, NutritionGoal, Meal, MealItem
from app.services.analytics_service import analytics_service

@pytest.fixture(scope="module")
def setup_user():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "analytics_test@example.com").first()
    if not user:
        user = User(email="analytics_test@example.com", hashed_password="pw")
        db.add(user)
        db.flush()
        db.add(NutritionGoal(user_id=user.id, calorie_target=2000.0, protein_g=80.0))
        db.commit()
    
    # Always ensure a meal logged for today
    today_meal = db.query(Meal).filter(Meal.user_id == user.id, func.date(Meal.logged_at) == date.today()).first()
    if not today_meal:
        m = Meal(user_id=user.id, meal_type="breakfast", logged_at=datetime.now(), total_calories=450.0, total_protein=18.0, total_carbs=60.0, total_fat=12.0, total_fiber=5.0)
        db.add(m)
        db.flush()
        db.add(MealItem(meal_id=m.id, item_name="Idli", quantity=2, unit="piece", calories=160.0, protein=6.0, carbs=32.0, fat=1.0, fiber=2.0))
        db.commit()
    yield user.id
    db.close()

def test_daily_analytics(setup_user):
    db = SessionLocal()
    uid = setup_user
    daily = analytics_service.get_daily_analytics(uid, date.today(), db)
    assert daily["calories"]["consumed"] >= 450.0
    assert daily["calories"]["target"] == 2000.0
    assert daily["protein_g"]["consumed"] >= 18.0
    assert daily["meals_logged"]["breakfast"] is True
    assert daily["meals_count"] >= 1
    db.close()

def test_period_reports(setup_user):
    db = SessionLocal()
    uid = setup_user
    weekly = analytics_service.get_period_report(uid, "weekly", date.today(), db)
    assert weekly["period"] == "weekly"
    assert "avg_calories" in weekly["summary"]
    assert "daily_breakdown" in weekly
    assert len(weekly["daily_breakdown"]) == 7
    assert len(weekly["top_foods"]) >= 1
    db.close()
