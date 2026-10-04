import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.entities import User, Meal, Recipe, Food

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_signup_and_login():
    # User 1 Signup
    resp = client.post("/api/v1/auth/signup", json={
        "email": "user1@example.com",
        "password": "Password123!",
        "name": "User One"
    })
    assert resp.status_code in (201, 400)

    # User 1 Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "user1@example.com",
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["email"] == "user1@example.com"
    token1 = data["access_token"]

    # Verify /me endpoint
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "user1@example.com"

def test_user_data_isolation():
    # Register User A
    client.post("/api/v1/auth/signup", json={
        "email": "usera@example.com",
        "password": "Password123!",
        "name": "User A"
    })
    login_a = client.post("/api/v1/auth/login", json={
        "email": "usera@example.com",
        "password": "Password123!"
    }).json()
    token_a = login_a["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B
    client.post("/api/v1/auth/signup", json={
        "email": "userb@example.com",
        "password": "Password123!",
        "name": "User B"
    })
    login_b = client.post("/api/v1/auth/login", json={
        "email": "userb@example.com",
        "password": "Password123!"
    }).json()
    token_b = login_b["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    with SessionLocal() as db:
        onion = db.query(Food).filter(
            Food.food_name == "Onion, big, red (Allium cepa)"
        ).one()
        onion_id = onion.id
        onion_name = onion.food_name

    # User A creates a custom recipe
    recipe_a_resp = client.post("/api/v1/recipes", headers=headers_a, json={
        "name": "User A Private Sambar",
        "ingredients": [{"food_id": onion_id, "food_name": onion_name, "quantity": 100, "unit": "g"}],
        "servings_count": 2
    })
    assert recipe_a_resp.status_code == 201
    recipe_a_id = recipe_a_resp.json()["id"]

    with SessionLocal() as db:
        chapati = db.query(Food).filter(Food.food_name == "Chapati/Roti").one()
        chapati_id = chapati.id
        chapati_name = chapati.food_name

    # User A logs a meal
    meal_a_resp = client.post("/api/v1/meals", headers=headers_a, json={
        "meal_type": "breakfast",
        "items": [{"food_id": chapati_id, "item_name": chapati_name, "quantity": 2, "unit": "chapati"}]
    })
    assert meal_a_resp.status_code == 201
    meal_a_id = meal_a_resp.json()["id"]

    # User B tries to view User A's private recipe directly -> Must be 404
    forbidden_recipe = client.get(f"/api/v1/recipes/{recipe_a_id}", headers=headers_b)
    assert forbidden_recipe.status_code == 404

    # User B tries to delete User A's recipe -> Must be 404 / Unauthorized
    del_forbidden_recipe = client.delete(f"/api/v1/recipes/{recipe_a_id}", headers=headers_b)
    assert del_forbidden_recipe.status_code == 404

    # User B tries to delete User A's meal -> Must be 404 / Unauthorized
    del_forbidden_meal = client.delete(f"/api/v1/meals/{meal_a_id}", headers=headers_b)
    assert del_forbidden_meal.status_code == 404

    # User B gets their own today meals -> User A's meal must NOT appear
    b_meals = client.get("/api/v1/meals/today", headers=headers_b).json()
    assert not any(m["id"] == meal_a_id for m in b_meals)
