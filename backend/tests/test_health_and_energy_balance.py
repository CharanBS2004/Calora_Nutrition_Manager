import uuid
import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.entities import User, Food

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_headers():
    Base.metadata.create_all(bind=engine)
    unique_email = f"health_test_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/api/v1/auth/signup", json={
        "email": unique_email,
        "password": "Password123!",
        "name": "Health User"
    })
    token = client.post("/api/v1/auth/login", json={
        "email": unique_email,
        "password": "Password123!"
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_sync_health_record_and_energy_balance(auth_headers):
    today_str = date.today().strftime("%Y-%m-%d")

    # 1. Sync simulated Health Connect data
    sync_resp = client.post("/api/v1/health/records", headers=auth_headers, json={
        "recorded_date": today_str,
        "total_calories_burned": 2300.0,
        "active_calories_burned": 550.0,
        "steps": 8420,
        "distance_m": 6200.0,
        "active_minutes": 45,
        "source": "health_connect"
    })
    assert sync_resp.status_code == 200
    assert sync_resp.json()["steps"] == 8420

    with SessionLocal() as db:
        food = db.query(Food).filter(Food.food_name == "Chapati/Roti").one()
        food_id = food.id
        food_name = food.food_name
        expected_calories = round(food.unit_serving_energy_kcal * 2, 2)

    # 2. Log a meal using the dataset's chapati serving
    meal_resp = client.post("/api/v1/meals", headers=auth_headers, json={
        "meal_type": "lunch",
        "items": [
            {
                "food_id": food_id,
                "item_name": food_name,
                "quantity": 2,
            }
        ]
    })
    assert meal_resp.status_code == 201

    # 3. Check Energy Balance using logged dataset nutrition
    balance_resp = client.get("/api/v1/health/energy-balance", headers=auth_headers)
    assert balance_resp.status_code == 200
    data = balance_resp.json()
    assert data["calories_consumed"] == expected_calories
    assert data["calories_burned"] == 2300.0
    assert data["net_balance_kcal"] == expected_calories - 2300.0
    assert data["status"] == "deficit"
    assert "Health Connect" in data["burned_source"]
