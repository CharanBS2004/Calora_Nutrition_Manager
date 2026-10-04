import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.entities import User, UserProfile, NutritionGoal
from app.schemas.all_schemas import (
    UserProfileUpdate, UserProfileResponse,
    NutritionGoalUpdate, NutritionGoalResponse
)

router = APIRouter(prefix="/users", tags=["Users & Goals"])

@router.get("/profile", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve profile for the authenticated user."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id, name=current_user.email.split("@")[0])
        db.add(profile)
        db.commit()
        db.refresh(profile)

    allergies = json.loads(profile.allergies) if profile.allergies else []
    food_prefs = json.loads(profile.food_preferences) if profile.food_preferences else []

    return UserProfileResponse(
        user_id=current_user.id,
        name=profile.name,
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        dietary_preference=profile.dietary_preference,
        allergies=allergies,
        food_preferences=food_prefs
    )

@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update profile attributes for authenticated user."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if update.name is not None:
        profile.name = update.name.strip()
    if update.age is not None:
        profile.age = update.age
    if update.gender is not None:
        profile.gender = update.gender
    if update.height_cm is not None:
        profile.height_cm = update.height_cm
    if update.weight_kg is not None:
        profile.weight_kg = update.weight_kg
    if update.activity_level is not None:
        profile.activity_level = update.activity_level
    if update.dietary_preference is not None:
        profile.dietary_preference = update.dietary_preference
    if update.allergies is not None:
        profile.allergies = json.dumps(update.allergies)
    if update.food_preferences is not None:
        profile.food_preferences = json.dumps(update.food_preferences)

    db.commit()
    db.refresh(profile)

    allergies = json.loads(profile.allergies) if profile.allergies else []
    food_prefs = json.loads(profile.food_preferences) if profile.food_preferences else []

    return UserProfileResponse(
        user_id=current_user.id,
        name=profile.name,
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        dietary_preference=profile.dietary_preference,
        allergies=allergies,
        food_preferences=food_prefs
    )

@router.get("/goals", response_model=NutritionGoalResponse)
def get_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve nutrition goals for the authenticated user."""
    goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == current_user.id).first()
    if not goals:
        goals = NutritionGoal(user_id=current_user.id)
        db.add(goals)
        db.commit()
        db.refresh(goals)

    return NutritionGoalResponse(
        user_id=current_user.id,
        calorie_target=goals.calorie_target,
        protein_g=goals.protein_g,
        carb_g=goals.carb_g,
        fat_g=goals.fat_g,
        fiber_g=goals.fiber_g,
        water_ml=goals.water_ml
    )

@router.put("/goals", response_model=NutritionGoalResponse)
def update_goals(
    update: NutritionGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update personalized daily nutrition goals for authenticated user."""
    goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == current_user.id).first()
    if not goals:
        goals = NutritionGoal(user_id=current_user.id)
        db.add(goals)

    if update.calorie_target is not None:
        goals.calorie_target = update.calorie_target
    if update.protein_g is not None:
        goals.protein_g = update.protein_g
    if update.carb_g is not None:
        goals.carb_g = update.carb_g
    if update.fat_g is not None:
        goals.fat_g = update.fat_g
    if update.fiber_g is not None:
        goals.fiber_g = update.fiber_g
    if update.water_ml is not None:
        goals.water_ml = update.water_ml

    db.commit()
    db.refresh(goals)

    return NutritionGoalResponse(
        user_id=current_user.id,
        calorie_target=goals.calorie_target,
        protein_g=goals.protein_g,
        carb_g=goals.carb_g,
        fat_g=goals.fat_g,
        fiber_g=goals.fiber_g,
        water_ml=goals.water_ml
    )
