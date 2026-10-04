from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field

# ----------------- Auth Schemas -----------------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=100)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    name: str

class PasswordResetRequest(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=6)

# ----------------- Profile & Goals -----------------
class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=10, le=120)
    gender: Optional[str] = None
    height_cm: Optional[float] = Field(None, ge=50, le=280)
    weight_kg: Optional[float] = Field(None, ge=20, le=300)
    activity_level: Optional[str] = None
    dietary_preference: Optional[str] = None
    allergies: Optional[List[str]] = None
    food_preferences: Optional[List[str]] = None

class UserProfileResponse(BaseModel):
    user_id: int
    name: str
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    activity_level: Optional[str]
    dietary_preference: Optional[str]
    allergies: List[str]
    food_preferences: List[str]

class NutritionGoalUpdate(BaseModel):
    calorie_target: Optional[float] = Field(None, ge=800, le=6000)
    protein_g: Optional[float] = Field(None, ge=10, le=400)
    carb_g: Optional[float] = Field(None, ge=20, le=800)
    fat_g: Optional[float] = Field(None, ge=10, le=300)
    fiber_g: Optional[float] = Field(None, ge=5, le=100)
    water_ml: Optional[float] = Field(None, ge=500, le=8000)

class NutritionGoalResponse(BaseModel):
    user_id: int
    calorie_target: float
    protein_g: float
    carb_g: float
    fat_g: float
    fiber_g: float
    water_ml: float

# ----------------- Food & Nutrition Schemas -----------------
class FoodResponse(BaseModel):
    id: int
    food_code: Optional[str]
    food_name: str
    category: Optional[str]
    source: str
    serving_size: float
    serving_unit: str
    weight_g: float
    energy_kcal: float
    protein_g: float
    carbohydrate_g: float
    fat_g: float
    fiber_g: float
    unit_serving_energy_kcal: Optional[float] = None
    unit_serving_protein_g: Optional[float] = None
    unit_serving_carbohydrate_g: Optional[float] = None
    unit_serving_fat_g: Optional[float] = None
    unit_serving_fiber_g: Optional[float] = None
    is_custom: bool = False

class FoodSearchResponse(BaseModel):
    total: int
    items: List[FoodResponse]

# ----------------- Recipe Schemas -----------------
class IngredientInput(BaseModel):
    food_id: Optional[int] = None
    food_code: Optional[str] = None
    food_name: str
    quantity: float
    unit: str = "g"  # g, ml, cup, katori, tbsp, tsp, piece

class RecipeCalculateRequest(BaseModel):
    name: str = "Custom Recipe"
    ingredients: List[IngredientInput]
    total_cooked_weight_g: Optional[float] = None
    servings_count: float = 1.0
    serving_unit: str = "serving"
    consumed_quantity: Optional[float] = None
    consumed_unit: Optional[str] = "serving"  # "serving" or "g"

class CalculatedNutrients(BaseModel):
    energy_kcal: float
    protein_g: float
    carbohydrate_g: float
    fat_g: float
    fiber_g: float

class RecipeCalculationResult(BaseModel):
    total_recipe: CalculatedNutrients
    per_serving: CalculatedNutrients
    per_100g: CalculatedNutrients
    consumed_portion: Optional[CalculatedNutrients] = None
    confidence_score: float = 1.0
    notes: Optional[str] = None

class RecipeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = "My Recipes"
    ingredients: List[IngredientInput]
    total_cooked_weight_g: Optional[float] = None
    servings_count: float = 1.0
    serving_unit: str = "serving"

class RecipeResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    category: str
    total_cooked_weight_g: Optional[float]
    servings_count: float
    serving_unit: str
    is_saved: bool
    is_system: bool
    calories_per_serving: float
    protein_per_serving: float
    carb_per_serving: float
    fat_per_serving: float
    fiber_per_serving: float
    total_calories: float
    total_protein: float
    total_carb: float
    total_fat: float
    total_fiber: float
    ingredients: List[Dict[str, Any]] = []
    created_at: datetime

# ----------------- Meal Schemas -----------------
class MealItemCreate(BaseModel):
    food_id: Optional[int] = None
    recipe_id: Optional[int] = None
    item_name: str
    quantity: float
    unit: Optional[str] = None
    dietary_confirmed: bool = False
    weight_g: Optional[float] = None
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    confidence_score: float = 1.0

class MealCreate(BaseModel):
    meal_type: str = "lunch"  # breakfast, lunch, dinner, snack
    logged_at: Optional[datetime] = None
    items: List[MealItemCreate]
    notes: Optional[str] = None

class MealItemResponse(BaseModel):
    id: int
    item_name: str
    quantity: float
    unit: str
    weight_g: float
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    confidence_score: float

class MealResponse(BaseModel):
    id: int
    user_id: int
    meal_type: str
    logged_at: datetime
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    total_fiber: float
    confidence_score: float
    notes: Optional[str]
    items: List[MealItemResponse]

# ----------------- Health & Energy Balance -----------------
class HealthRecordCreate(BaseModel):
    recorded_date: date
    total_calories_burned: float
    active_calories_burned: float = 0.0
    steps: int = 0
    distance_m: float = 0.0
    active_minutes: int = 0
    resting_heart_rate: Optional[float] = None
    source: str = "health_connect"

class HealthRecordResponse(BaseModel):
    user_id: int
    recorded_date: date
    total_calories_burned: float
    active_calories_burned: float
    steps: int
    distance_m: float
    active_minutes: int
    resting_heart_rate: Optional[float]
    source: str

class EnergyBalanceResponse(BaseModel):
    target_date: date
    calories_consumed: float
    calories_burned: float
    net_balance_kcal: float  # consumed - burned
    burned_source: str
    status: str  # surplus, deficit, maintenance

# ----------------- Notifications & Quiet Hours -----------------
class NotificationSettingsUpdate(BaseModel):
    reminders_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    breakfast_time: Optional[str] = None
    lunch_time: Optional[str] = None
    dinner_time: Optional[str] = None
    snack_time: Optional[str] = None
    breakfast_enabled: Optional[bool] = None
    lunch_enabled: Optional[bool] = None
    dinner_enabled: Optional[bool] = None
    snack_enabled: Optional[bool] = None

class NotificationSettingsResponse(BaseModel):
    user_id: int
    reminders_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    breakfast_time: str
    lunch_time: str
    dinner_time: str
    snack_time: str
    breakfast_enabled: bool
    lunch_enabled: bool
    dinner_enabled: bool
    snack_enabled: bool

class MissingMealAlert(BaseModel):
    meal_type: str
    scheduled_time: str
    message: str
    is_quiet_hours: bool

# ----------------- AI Coach & LangGraph Agent -----------------
class ActionButton(BaseModel):
    label: str
    action_type: str  # log_meal, view_meals, ask_why, clarify
    payload: Dict[str, Any] = {}

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message_id: int
    role: str = "assistant"
    reply: str
    tool_calls: List[Dict[str, Any]] = []
    goal_impact: Optional[Dict[str, Any]] = None
    uncertainty_flag: bool = False
    clarification_needed: Optional[str] = None
    suggested_options: List[str] = []
    action_buttons: List[ActionButton] = []
    created_at: datetime

# ----------------- Analytics -----------------
class NutrientProgress(BaseModel):
    consumed: float
    target: float
    percentage: float
    remaining: float

class DailyAnalytics(BaseModel):
    date: date
    calories: NutrientProgress
    protein_g: NutrientProgress
    carb_g: NutrientProgress
    fat_g: NutrientProgress
    fiber_g: NutrientProgress
    calories_burned: Optional[float]
    active_calories_burned: float
    burned_source: str
    energy_balance_kcal: Optional[float]
    steps: int
    meals_count: int
    meals_logged: Dict[str, bool]  # breakfast: true, lunch: true, etc.
    meal_calories: Dict[str, float]

class PeriodAverages(BaseModel):
    avg_calories: float
    avg_protein: float
    avg_carb: float
    avg_fat: float
    avg_fiber: float
    avg_calories_burned: float
    avg_energy_balance: float
    avg_steps: int
    goal_adherence_percent: float
    total_meals_logged: int
    missed_meals_count: int

class TrendPoint(BaseModel):
    date: str
    consumed_kcal: float
    burned_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    fiber_g: float

class AnalyticsReport(BaseModel):
    period: str  # "daily", "weekly", "monthly"
    start_date: str
    end_date: str
    summary: PeriodAverages
    daily_breakdown: List[TrendPoint] = []
    top_foods: List[Dict[str, Any]] = []
    top_recipes: List[Dict[str, Any]] = []
    comparison_previous_period: Optional[Dict[str, float]] = None
