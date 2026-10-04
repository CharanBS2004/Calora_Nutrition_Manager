# REST API Documentation

## AI-Powered Personal Nutrition & Energy Balance Coach API (v1)

---

## 1. Authentication (`/api/v1/auth`)

### `POST /api/v1/auth/signup`
Creates a new user account and returns a JWT bearer access token.
- **Request Body**:
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "name": "Arjun Sharma"
  }
  ```
- **Response `201 Created`**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user_id": 1,
    "email": "user@example.com",
    "name": "Arjun Sharma"
  }
  ```

### `POST /api/v1/auth/login`
Authenticates existing credentials and returns a JWT bearer access token.

### `GET /api/v1/auth/me`
Returns the currently authenticated user's profile and credentials.

---

## 2. Foods & INDB Search (`/api/v1/foods`)

### `GET /api/v1/foods/search`
Searches INDB foods by keyword with fuzzy matching and category filtering.
- **Query Parameters**:
  - `q` (string, required): e.g. "paneer", "dal", "biryani"
  - `category` (string, optional): e.g. "Curries", "Breads & Rotis"
  - `limit` (int, default: 20)

### `GET /api/v1/foods/{food_id}`
Retrieves detailed micronutrient and macronutrient breakdown for a specific INDB food item.

---

## 3. Meal Logging (`/api/v1/meals`)

### `POST /api/v1/meals`
Logs a meal with multiple items. Computes nutrition deterministically from INDB if not precomputed.
- **Request Body**:
  ```json
  {
    "meal_type": "lunch",
    "logged_at": "2026-09-21T13:30:00Z",
    "items": [
      {
        "item_name": "Roti",
        "quantity": 2.0,
        "unit": "piece",
        "weight_g": 80.0
      },
      {
        "item_name": "Dal Tadka",
        "quantity": 1.0,
        "unit": "cup",
        "weight_g": 240.0
      }
    ],
    "notes": "Home cooked lunch"
  }
  ```

### `POST /api/v1/meals/parse-text`
Parses natural language meal text into recognized INDB food items, extracts quantities/units, calculates nutrition, and returns uncertainty clarification prompts if portions are ambiguous.
- **Query Parameters**:
  - `text` (string): e.g. "I had two parathas with curd and pickle"
  - `meal_type` (string, default: "lunch")

### `GET /api/v1/meals/today`
Returns all meals logged today grouped by meal type with items and nutrient totals.

---

## 4. Recipe Builder & Library (`/api/v1/recipes`)

### `POST /api/v1/recipes/calculate`
Calculates Method C raw-to-cooked yield, total recipe macros, per-serving macros, and per-100g cooked macros.
- **Request Body**:
  ```json
  {
    "recipe_name": "Palak Paneer",
    "ingredients": [
      {"food_name": "Spinach", "quantity": 300, "unit": "g"},
      {"food_name": "Paneer", "quantity": 200, "unit": "g"},
      {"food_name": "Ghee", "quantity": 1, "unit": "tbsp"}
    ],
    "servings_count": 4,
    "total_cooked_weight_g": 600,
    "consumed_quantity": 1,
    "consumed_unit": "serving"
  }
  ```

### `POST /api/v1/recipes`
Saves custom recipe to the user's personal recipe library.

### `POST /api/v1/recipes/{recipe_id}/log`
Quick-logs a saved recipe as a meal with specified servings.

---

## 5. Health Connect & Energy Balance (`/api/v1/health`)

### `POST /api/v1/health/records`
Ingests daily telemetry data from Android Health Connect (total calories burned, active calories, steps).

### `GET /api/v1/health/energy-balance`
Calculates daily Calories In vs Calories Out ($E_{balance} = C_{in} - C_{out}$) and returns balance status (`deficit`, `surplus`, `maintenance`).

---

## 6. Proactive Notifications (`/api/v1/notifications`)

### `GET /api/v1/notifications/settings`
Retrieves quiet hours and meal schedule configuration.

### `PUT /api/v1/notifications/settings`
Updates quiet hours start/end times and individual meal notification toggles.

### `GET /api/v1/notifications/check-missing-meals`
Backend evaluation endpoint called by Android WorkManager. Identifies unlogged meals past their scheduled time, filtering out quiet hours.

---

## 7. Analytics & Reports (`/api/v1/analytics`)

### `GET /api/v1/analytics/daily`
Returns consumed vs target macros, progress percentages, meal distribution, and net energy balance.

### `GET /api/v1/analytics/weekly` & `GET /api/v1/analytics/monthly`
Aggregates period averages, adherence percentage, daily trend series, and top consumed foods.

### `GET /api/v1/analytics/comparison`
Returns period delta comparisons (today vs yesterday, this week vs last week, this month vs last month).

---

## 8. AI Coach & Chat (`/api/v1/coach`)

### `POST /api/v1/coach/chat`
Conversational endpoint orchestrating LangGraph multi-turn agent with 20 deterministic tools, post-action reflection node, and uncertainty clarification.
- **Request Body**:
  ```json
  {
    "message": "Did I get enough protein today?",
    "context": {}
  }
  ```
- **Response**:
  ```json
  {
    "message_id": 42,
    "role": "assistant",
    "reply": "You have consumed 58g of protein today against your target of 75g (77% achieved). You have 17g remaining...",
    "tool_calls": [...],
    "goal_impact": {"remaining_protein_g": 17.0},
    "uncertainty_flag": false,
    "action_buttons": [
      {"label": "Suggest high-protein snack", "action_type": "clarify", "payload": {}}
    ],
    "created_at": "2026-09-21T19:40:00Z"
  }
  ```
