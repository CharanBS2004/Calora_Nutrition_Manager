from datetime import date, datetime, timedelta, timezone
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entities import Food, Recipe, RecipeIngredient, Meal, MealItem, HealthRecord, NutritionGoal, UserMemory
from app.services.nutrition_engine import nutrition_engine
from app.services.unit_converter import unit_converter
from app.services.analytics_service import analytics_service
from app.services.memory.memory_service import memory_service
from app.services.food_lookup import find_food_matches, resolve_recipe_food
from app.services.food_nutrition import calculate_food_portion

class AgentTools:
    """
    Complete implementation of all 20 tools required for the Agentic AI Nutrition Coach.
    Every tool enforces user isolation through user_id scoping.
    """

    @staticmethod
    def search_food(query: str, category: Optional[str] = None, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 1: search_food(query, category)"""
        matches = find_food_matches(db, query)
        foods = [
            (food, score) for food, score in matches
            if not category or (food.category and category.casefold() in food.category.casefold())
        ]
        selection_note = None
        if not foods and re.search(r"\bsnacks?\b", query, re.IGNORECASE):
            snack_markers = (
                "sandwich", "samosa", "dhokla", "chilla", "cheela", "cutlet",
                "kebab", "tikki", "pakora", "pakoda", "vada", "chaat", "bonda",
                "toast",
            )
            foods = [
                (food, 1.0)
                for food in db.query(Food).filter(
                    Food.is_custom.is_(False),
                    Food.category == "Indian Prepared Dish",
                ).all()
                if any(marker in food.food_name.casefold() for marker in snack_markers)
            ]
            selection_note = (
                "The dataset has no explicit snack classification. These are prepared-dish "
                "records selected by their dataset names; use only their recorded nutrition "
                "and serving data."
            )
        if not foods and category:
            foods = matches
        foods.sort(key=lambda result: (
            -(
                result[0].unit_serving_protein_g
                if result[0].unit_serving_protein_g is not None
                else result[0].protein_g
            ) if selection_note else 0,
            result[0].category != "Milk and Milk Products",
            result[0].category == "Indian Prepared Dish",
            -result[1],
            result[0].food_name.casefold(),
        ))
        result = {
            "query": query,
            "results_count": len(foods),
            "foods": [
                {
                    "food_id": f.id,
                    "name": f.food_name,
                    "food_code": f.food_code,
                    "source": f.source,
                    "category": f.category,
                    "calories_100g": f.energy_kcal,
                    "protein_100g": f.protein_g,
                    "source": f.source,
                    "carbs_100g": f.carbohydrate_g,
                    "fat_100g": f.fat_g,
                    "serving_size": f.serving_size,
                    "serving_unit": f.serving_unit,
                    "calories_per_serving": f.unit_serving_energy_kcal,
                    "protein_per_serving": f.unit_serving_protein_g,
                } for f, _ in foods[:12]
            ]
        }
        if selection_note:
            result["selection_note"] = selection_note
        return result

    @staticmethod
    def get_food_nutrition(food_id: int, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 2: get_food_nutrition(food_id)"""
        food = db.query(Food).filter(Food.id == food_id).first()
        if not food:
            return {"error": f"Food with id {food_id} not found"}
        return {
            "food_id": food.id,
            "name": food.food_name,
            "category": food.category,
            "per_100g": {
                "calories": food.energy_kcal,
                "protein_g": food.protein_g,
                "carbs_g": food.carbohydrate_g,
                "fat_g": food.fat_g,
                "fiber_g": food.fiber_g
            },
            "standard_serving": {
                "unit": food.serving_unit,
                "calories": food.unit_serving_energy_kcal,
                "protein_g": food.unit_serving_protein_g,
                "carbs_g": food.unit_serving_carbohydrate_g,
                "fat_g": food.unit_serving_fat_g,
                "fiber_g": food.unit_serving_fiber_g
            }
        }

    @staticmethod
    def calculate_recipe_nutrition(
        ingredients: List[Dict[str, Any]],
        servings: float = 1.0,
        cooked_weight: Optional[float] = None,
        db: Session = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Tool 3: calculate_recipe_nutrition(ingredients, servings, cooked_weight)"""
        ing_data = []
        for ing in ingredients:
            fname = ing.get("food_name", "")
            fid = ing.get("food_id")
            food = resolve_recipe_food(
                db,
                fname,
                fid,
                ing.get("food_code"),
            )

            ing_data.append({
                "food_id": food.id,
                "food_name": food.food_name,
                "quantity": float(ing.get("quantity", 100)),
                "unit": ing.get("unit", "g"),
                "energy_100g": food.energy_kcal,
                "protein_100g": food.protein_g,
                "carb_100g": food.carbohydrate_g,
                "fat_100g": food.fat_g,
                "fiber_100g": food.fiber_g,
            })

        return nutrition_engine.calculate_recipe_totals(
            ingredients=ing_data,
            servings_count=servings,
            total_cooked_weight_g=cooked_weight,
            db=db,
        )

    @staticmethod
    def log_meal(
        user_id: int,
        meal_type: str,
        items: List[Dict[str, Any]],
        logged_at: Optional[str] = None,
        notes: Optional[str] = None,
        db: Session = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Tool 4: log_meal(meal_type, items, logged_at)"""
        tot_cal, tot_prot, tot_carb, tot_fat, tot_fib = 0.0, 0.0, 0.0, 0.0, 0.0
        prepared_items = []
        saved_items = []
        for it in items:
            name = it.get("item_name", "")
            if it.get("quantity") is None:
                raise ValueError(f"Food '{name}' needs a quantity before it can be logged.")
            qty = float(it["quantity"])
            matches = find_food_matches(db, name)
            if len(matches) != 1:
                raise ValueError(f"Food '{name}' is not an exact, unique dataset match.")
            food = matches[0][0]
            if food.is_custom:
                raise ValueError(f"Food '{name}' is not present in the nutrition dataset.")
            unit = it.get("unit") or food.serving_unit
            values = calculate_food_portion(db, food, qty, unit)
            nutr = {
                "energy_kcal": values[0],
                "protein_g": values[1],
                "carbohydrate_g": values[2],
                "fat_g": values[3],
                "fiber_g": values[4],
            }
            prepared_items.append((food, qty, unit, values[5], nutr))
            saved_items.append({"name": food.food_name, "calories": nutr["energy_kcal"], "protein": nutr["protein_g"]})
            tot_cal += nutr["energy_kcal"]
            tot_prot += nutr["protein_g"]
            tot_carb += nutr["carbohydrate_g"]
            tot_fat += nutr["fat_g"]
            tot_fib += nutr["fiber_g"]

        meal = Meal(
            user_id=user_id,
            meal_type=meal_type.lower(),
            logged_at=datetime.now(timezone.utc),
            notes=notes
        )
        db.add(meal)
        db.flush()

        for food, qty, unit, grams, nutr in prepared_items:
            m_item = MealItem(
                meal_id=meal.id,
                food_id=food.id,
                item_name=food.food_name,
                quantity=qty,
                unit=unit,
                weight_g=grams,
                calories=nutr["energy_kcal"],
                protein=nutr["protein_g"],
                carbs=nutr["carbohydrate_g"],
                fat=nutr["fat_g"],
                fiber=nutr["fiber_g"],
                confidence_score=1.0
            )
            db.add(m_item)

        meal.total_calories = round(tot_cal, 2)
        meal.total_protein = round(tot_prot, 2)
        meal.total_carbs = round(tot_carb, 2)
        meal.total_fat = round(tot_fat, 2)
        meal.total_fiber = round(tot_fib, 2)
        meal.confidence_score = 1.0
        db.commit()
        db.refresh(meal)

        return {
            "success": True,
            "meal_id": meal.id,
            "meal_type": meal.meal_type,
            "total_calories": meal.total_calories,
            "total_protein": meal.total_protein,
            "items": saved_items
        }

    @staticmethod
    def update_meal(meal_id: int, user_id: int, items: List[Dict[str, Any]], db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 5: update_meal(meal_id, items)"""
        meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user_id).first()
        if not meal:
            return {"error": "Meal not found or unauthorized"}
        tot_cal, tot_prot, tot_carb, tot_fat, tot_fib = 0.0, 0.0, 0.0, 0.0, 0.0
        prepared_items = []
        for it in items:
            name = it.get("item_name", "")
            if it.get("quantity") is None:
                raise ValueError(f"Food '{name}' needs a quantity before it can be logged.")
            qty = float(it["quantity"])
            matches = find_food_matches(db, name)
            if len(matches) != 1:
                raise ValueError(f"Food '{name}' is not an exact, unique dataset match.")
            food = matches[0][0]
            if food.is_custom:
                raise ValueError(f"Food '{name}' is not present in the nutrition dataset.")
            unit = it.get("unit") or food.serving_unit
            values = calculate_food_portion(db, food, qty, unit)
            g = values[5]
            n = {
                "energy_kcal": values[0],
                "protein_g": values[1],
                "carbohydrate_g": values[2],
                "fat_g": values[3],
                "fiber_g": values[4],
            }
            prepared_items.append((food, name, qty, unit, g, n))
            tot_cal += n["energy_kcal"]
            tot_prot += n["protein_g"]
            tot_carb += n["carbohydrate_g"]
            tot_fat += n["fat_g"]
            tot_fib += n["fiber_g"]

        db.query(MealItem).filter(MealItem.meal_id == meal.id).delete()
        for food, name, qty, unit, g, n in prepared_items:
            m_item = MealItem(
                meal_id=meal.id,
                food_id=food.id,
                item_name=food.food_name,
                quantity=qty,
                unit=unit,
                weight_g=g,
                calories=n["energy_kcal"],
                protein=n["protein_g"],
                carbs=n["carbohydrate_g"],
                fat=n["fat_g"],
                fiber=n["fiber_g"]
            )
            db.add(m_item)

        meal.total_calories = round(tot_cal, 2)
        meal.total_protein = round(tot_prot, 2)
        meal.total_carbs = round(tot_carb, 2)
        meal.total_fat = round(tot_fat, 2)
        meal.total_fiber = round(tot_fib, 2)
        db.commit()
        return {"success": True, "meal_id": meal.id, "total_calories": meal.total_calories}

    @staticmethod
    def delete_meal(meal_id: int, user_id: int, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 6: delete_meal(meal_id)"""
        meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user_id).first()
        if not meal:
            return {"error": "Meal not found or unauthorized"}
        db.delete(meal)
        db.commit()
        return {"success": True, "deleted_meal_id": meal_id}

    @staticmethod
    def get_today_meals(user_id: int, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 7: get_today_meals()"""
        today = date.today()
        meals = db.query(Meal).filter(
            Meal.user_id == user_id,
            func.date(Meal.logged_at) == today
        ).all()
        return {
            "date": today.strftime("%Y-%m-%d"),
            "count": len(meals),
            "meals": [
                {
                    "meal_id": m.id,
                    "type": m.meal_type,
                    "calories": m.total_calories,
                    "protein": m.total_protein,
                    "items": [{"name": it.item_name, "quantity": it.quantity, "unit": it.unit, "calories": it.calories} for it in m.items]
                } for m in meals
            ]
        }

    @staticmethod
    def get_daily_nutrition(user_id: int, date_str: Optional[str] = None, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 8: get_daily_nutrition(date)"""
        t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        return analytics_service.get_daily_analytics(user_id, t_date, db)

    @staticmethod
    def get_user_goals(user_id: int, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 9: get_user_goals()"""
        goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == user_id).first()
        if not goals:
            return {"calorie_target": 2000.0, "protein_g": 75.0, "carb_g": 250.0, "fat_g": 65.0, "fiber_g": 30.0}
        return {
            "calorie_target": goals.calorie_target,
            "protein_g": goals.protein_g,
            "carb_g": goals.carb_g,
            "fat_g": goals.fat_g,
            "fiber_g": goals.fiber_g,
            "water_ml": goals.water_ml
        }

    @staticmethod
    def update_user_goals(
        user_id: int,
        calories: Optional[float] = None,
        protein: Optional[float] = None,
        carbs: Optional[float] = None,
        fat: Optional[float] = None,
        fiber: Optional[float] = None,
        db: Session = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Tool 10: update_user_goals(calories, protein, carbs, fat, fiber)"""
        goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == user_id).first()
        if not goals:
            goals = NutritionGoal(user_id=user_id)
            db.add(goals)
        if calories: goals.calorie_target = calories
        if protein: goals.protein_g = protein
        if carbs: goals.carb_g = carbs
        if fat: goals.fat_g = fat
        if fiber: goals.fiber_g = fiber
        db.commit()
        db.refresh(goals)
        return {"success": True, "updated_goals": {"calories": goals.calorie_target, "protein": goals.protein_g, "carbs": goals.carb_g, "fat": goals.fat_g}}

    @staticmethod
    def get_saved_recipes(user_id: int, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 11: get_saved_recipes()"""
        recipes = db.query(Recipe).filter((Recipe.user_id == user_id) | (Recipe.is_system == True)).all()
        return {
            "recipes_count": len(recipes),
            "recipes": [
                {
                    "recipe_id": r.id,
                    "name": r.name,
                    "category": r.category,
                    "calories_per_serving": r.calories_per_serving,
                    "protein_per_serving": r.protein_per_serving,
                    "servings": r.servings_count
                } for r in recipes
            ]
        }

    @staticmethod
    def get_recipe(recipe_id: int, user_id: int, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 12: get_recipe(recipe_id)"""
        r = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not r or (r.user_id != user_id and not r.is_system):
            return {"error": "Recipe not found"}
        return {
            "recipe_id": r.id,
            "name": r.name,
            "servings": r.servings_count,
            "calories_per_serving": r.calories_per_serving,
            "protein_per_serving": r.protein_per_serving,
            "carb_per_serving": r.carb_per_serving,
            "fat_per_serving": r.fat_per_serving,
            "ingredients": [
                {
                    "name": i.ingredient_name,
                    "quantity": i.quantity if i.quantity is not None else i.quantity_g,
                    "quantity_g": i.quantity_g,
                    "unit": i.unit,
                    "calories": i.energy_kcal,
                }
                for i in r.ingredients
            ]
        }

    @staticmethod
    def save_recipe(
        user_id: int,
        name: str,
        ingredients: List[Dict[str, Any]],
        servings: float = 1.0,
        cooked_weight: Optional[float] = None,
        db: Session = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Tool 13: save_recipe(name, ingredients, servings, cooked_weight)"""
        calc = AgentTools.calculate_recipe_nutrition(ingredients, servings, cooked_weight, db)
        rec = Recipe(
            user_id=user_id,
            name=name,
            servings_count=servings,
            total_cooked_weight_g=cooked_weight,
            calories_per_serving=calc["per_serving"]["energy_kcal"],
            protein_per_serving=calc["per_serving"]["protein_g"],
            carb_per_serving=calc["per_serving"]["carbohydrate_g"],
            fat_per_serving=calc["per_serving"]["fat_g"],
            fiber_per_serving=calc["per_serving"]["fiber_g"],
            total_calories=calc["total_recipe"]["energy_kcal"],
            total_protein=calc["total_recipe"]["protein_g"],
            total_carb=calc["total_recipe"]["carbohydrate_g"],
            total_fat=calc["total_recipe"]["fat_g"],
            total_fiber=calc["total_recipe"]["fiber_g"]
        )
        db.add(rec)
        db.flush()
        for i in calc["ingredients"]:
            db.add(RecipeIngredient(
                recipe_id=rec.id,
                food_id=i["food_id"],
                ingredient_name=i["food_name"],
                quantity=i["input_quantity"],
                quantity_g=i["weight_g"],
                unit=i["input_unit"],
                energy_kcal=i["nutrients"]["energy_kcal"],
                protein_g=i["nutrients"]["protein_g"],
                carbohydrate_g=i["nutrients"]["carbohydrate_g"],
                fat_g=i["nutrients"]["fat_g"],
                fiber_g=i["nutrients"]["fiber_g"]
            ))
        db.commit()
        return {"success": True, "recipe_id": rec.id, "name": rec.name, "calories_per_serving": rec.calories_per_serving}

    @staticmethod
    def update_recipe(recipe_id: int, user_id: int, name: Optional[str] = None, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 14: update_recipe(recipe_id, ...)"""
        r = db.query(Recipe).filter(Recipe.id == recipe_id, Recipe.user_id == user_id).first()
        if not r: return {"error": "Recipe not found"}
        if name: r.name = name
        db.commit()
        return {"success": True, "recipe_id": r.id, "name": r.name}

    @staticmethod
    def get_health_data(user_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 15: get_health_data(start_date, end_date)"""
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else (date.today() - timedelta(days=6))
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
        records = db.query(HealthRecord).filter(
            HealthRecord.user_id == user_id,
            HealthRecord.recorded_date >= s_date,
            HealthRecord.recorded_date <= e_date
        ).all()
        return {
            "count": len(records),
            "records": [
                {
                    "date": r.recorded_date.strftime("%Y-%m-%d"),
                    "calories_burned": r.total_calories_burned,
                    "steps": r.steps,
                    "source": r.source
                } for r in records
            ]
        }

    @staticmethod
    def calculate_energy_balance(user_id: int, date_str: Optional[str] = None, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 16: calculate_energy_balance(date)"""
        t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        meals = db.query(Meal).filter(Meal.user_id == user_id, func.date(Meal.logged_at) == t_date).all()
        consumed = sum(m.total_calories for m in meals)
        health = db.query(HealthRecord).filter(HealthRecord.user_id == user_id, HealthRecord.recorded_date == t_date).first()
        burned = health.total_calories_burned if health else 2000.0
        return nutrition_engine.calculate_energy_balance(consumed, burned)

    @staticmethod
    def get_user_memory(user_id: int, query: str = "", db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 17: get_user_memory(query)"""
        mems = memory_service.recall_relevant_memories(user_id, query, db)
        return {"memories": mems}

    @staticmethod
    def save_user_memory(user_id: int, fact: str, memory_type: str = "preference", db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 18: save_user_memory(fact, memory_type)"""
        m = memory_service.save_memory(user_id, fact, memory_type=memory_type, db=db)
        return {"success": True, "memory_id": m.id, "content": m.content}

    @staticmethod
    def get_analytics(user_id: int, period: str = "weekly", db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 19: get_analytics(period, metric)"""
        return analytics_service.get_period_report(user_id, period, date.today(), db)

    @staticmethod
    def generate_daily_summary(user_id: int, date_str: Optional[str] = None, db: Session = None, **kwargs) -> Dict[str, Any]:
        """Tool 20: generate_daily_summary(date)"""
        t_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        data = analytics_service.get_daily_analytics(user_id, t_date, db)
        return {
            "date": t_date.strftime("%Y-%m-%d"),
            "summary_text": (
                f"On {t_date}, you consumed {data['calories']['consumed']} kcal ({data['calories']['percentage']}% of goal). "
                f"Protein: {data['protein_g']['consumed']}g / {data['protein_g']['target']}g. "
                f"Calories burned: {data['calories_burned']} kcal, resulting in a net balance of {data['energy_balance_kcal']} kcal."
            ),
            "data": data
        }

agent_tools = AgentTools()
