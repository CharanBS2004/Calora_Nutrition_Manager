from datetime import datetime, date, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    goals = relationship("NutritionGoal", back_populates="user", uselist=False, cascade="all, delete-orphan")
    meals = relationship("Meal", back_populates="user", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="user", cascade="all, delete-orphan")
    health_records = relationship("HealthRecord", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False, default="User")
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    activity_level = Column(String(50), nullable=True, default="moderate")  # sedentary, light, moderate, active, very_active
    dietary_preference = Column(String(50), nullable=True, default="vegetarian")  # vegetarian, vegan, eggetarian, non_vegetarian, jain
    allergies = Column(Text, nullable=True, default="[]")  # JSON array string
    food_preferences = Column(Text, nullable=True, default="[]")  # JSON array string
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="profile")


class NutritionGoal(Base):
    __tablename__ = "nutrition_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    calorie_target = Column(Float, nullable=False, default=2000.0)
    protein_g = Column(Float, nullable=False, default=75.0)
    carb_g = Column(Float, nullable=False, default=250.0)
    fat_g = Column(Float, nullable=False, default=65.0)
    fiber_g = Column(Float, nullable=False, default=30.0)
    water_ml = Column(Float, nullable=False, default=2500.0)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="goals")


class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    food_code = Column(String(50), index=True, nullable=True)
    food_name = Column(String(255), index=True, nullable=False)
    category = Column(String(100), index=True, nullable=True)
    source = Column(String(50), nullable=False, default="INDB")  # INDB, ICMR_NIN, UK_FCT, US_FCT, CUSTOM
    serving_size = Column(Float, nullable=False, default=100.0)
    serving_unit = Column(String(50), nullable=False, default="g")
    weight_g = Column(Float, nullable=False, default=100.0)
    
    # Nutrition per 100g
    energy_kcal = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, nullable=False, default=0.0)
    carbohydrate_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    fiber_g = Column(Float, nullable=False, default=0.0)

    # Unit serving nutrition (if precomputed for recipe/dish)
    unit_serving_energy_kcal = Column(Float, nullable=True)
    unit_serving_protein_g = Column(Float, nullable=True)
    unit_serving_carbohydrate_g = Column(Float, nullable=True)
    unit_serving_fat_g = Column(Float, nullable=True)
    unit_serving_fiber_g = Column(Float, nullable=True)

    micronutrients_json = Column(Text, nullable=True)
    is_custom = Column(Boolean, default=False, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_foods_name_source", "food_name", "source"),
    )


class FoodUnitConversion(Base):
    __tablename__ = "food_unit_conversions"

    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=True)
    food_code = Column(String(50), index=True, nullable=True)
    food_name_pattern = Column(String(255), index=True, nullable=True)
    unit_name = Column(String(100), index=True, nullable=False)  # cup, katori, tbsp, tsp, piece, slice
    grams_equivalent = Column(Float, nullable=False)
    source = Column(String(100), nullable=True, default="Units.xlsx")
    is_density_based = Column(Boolean, default=False, nullable=False)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, default="My Recipes")
    total_cooked_weight_g = Column(Float, nullable=True)
    servings_count = Column(Float, nullable=False, default=1.0)
    serving_unit = Column(String(50), nullable=False, default="serving")
    is_saved = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    
    # Nutrition per serving
    calories_per_serving = Column(Float, nullable=False, default=0.0)
    protein_per_serving = Column(Float, nullable=False, default=0.0)
    carb_per_serving = Column(Float, nullable=False, default=0.0)
    fat_per_serving = Column(Float, nullable=False, default=0.0)
    fiber_per_serving = Column(Float, nullable=False, default=0.0)

    # Nutrition total recipe
    total_calories = Column(Float, nullable=False, default=0.0)
    total_protein = Column(Float, nullable=False, default=0.0)
    total_carb = Column(Float, nullable=False, default=0.0)
    total_fat = Column(Float, nullable=False, default=0.0)
    total_fiber = Column(Float, nullable=False, default=0.0)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="SET NULL"), nullable=True)
    ingredient_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=True)
    quantity_g = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False, default="g")
    
    energy_kcal = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, nullable=False, default=0.0)
    carbohydrate_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    fiber_g = Column(Float, nullable=False, default=0.0)

    recipe = relationship("Recipe", back_populates="ingredients")


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_type = Column(String(50), nullable=False, index=True)  # breakfast, lunch, dinner, snack
    logged_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    
    total_calories = Column(Float, nullable=False, default=0.0)
    total_protein = Column(Float, nullable=False, default=0.0)
    total_carbs = Column(Float, nullable=False, default=0.0)
    total_fat = Column(Float, nullable=False, default=0.0)
    total_fiber = Column(Float, nullable=False, default=0.0)
    
    confidence_score = Column(Float, nullable=False, default=1.0)  # 0.0 to 1.0
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="meals")
    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")


class MealItem(Base):
    __tablename__ = "meal_items"

    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="SET NULL"), nullable=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False, default=1.0)
    unit = Column(String(50), nullable=False, default="serving")
    weight_g = Column(Float, nullable=False, default=100.0)

    calories = Column(Float, nullable=False, default=0.0)
    protein = Column(Float, nullable=False, default=0.0)
    carbs = Column(Float, nullable=False, default=0.0)
    fat = Column(Float, nullable=False, default=0.0)
    fiber = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=1.0)

    meal = relationship("Meal", back_populates="items")


class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recorded_date = Column(Date, nullable=False, index=True)
    
    total_calories_burned = Column(Float, nullable=False, default=0.0)
    active_calories_burned = Column(Float, nullable=False, default=0.0)
    steps = Column(Integer, nullable=False, default=0)
    distance_m = Column(Float, nullable=False, default=0.0)
    active_minutes = Column(Integer, nullable=False, default=0)
    resting_heart_rate = Column(Float, nullable=True)
    source = Column(String(50), nullable=False, default="health_connect")  # health_connect, manual, estimated
    created_at = Column(DateTime, default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_health_user_date", "user_id", "recorded_date", unique=True),
    )

    user = relationship("User", back_populates="health_records")


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_type = Column(String(50), nullable=False, default="preference")  # preference, pattern, routine, fact
    content = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    last_recalled_at = Column(DateTime, default=utcnow, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="memories")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    tool_calls_json = Column(Text, nullable=True)
    contextual_actions_json = Column(Text, nullable=True)
    uncertainty_flag = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="chat_messages")


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    reminders_enabled = Column(Boolean, default=True, nullable=False)
    quiet_hours_start = Column(String(10), nullable=False, default="22:00")
    quiet_hours_end = Column(String(10), nullable=False, default="07:00")
    
    breakfast_time = Column(String(10), nullable=False, default="09:30")
    lunch_time = Column(String(10), nullable=False, default="14:00")
    dinner_time = Column(String(10), nullable=False, default="21:00")
    snack_time = Column(String(10), nullable=False, default="17:00")

    breakfast_enabled = Column(Boolean, default=True, nullable=False)
    lunch_enabled = Column(Boolean, default=True, nullable=False)
    dinner_enabled = Column(Boolean, default=True, nullable=False)
    snack_enabled = Column(Boolean, default=True, nullable=False)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="notification_settings")
