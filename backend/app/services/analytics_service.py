from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entities import Meal, MealItem, HealthRecord, NutritionGoal, Recipe

class AnalyticsService:
    """
    Comprehensive Analytics Service for daily, weekly, monthly aggregation,
    trend calculations, macro progress, and comparison deltas.
    """

    @staticmethod
    def get_daily_analytics(user_id: int, target_date: date, db: Session) -> Dict[str, Any]:
        """Generate full day analytics including macros, goals, meals, and health expenditure."""
        # 1. User goals
        goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == user_id).first()
        target_cal = goals.calorie_target if goals else 2000.0
        target_prot = goals.protein_g if goals else 75.0
        target_carb = goals.carb_g if goals else 250.0
        target_fat = goals.fat_g if goals else 65.0
        target_fib = goals.fiber_g if goals else 30.0

        # 2. Logged meals
        meals = db.query(Meal).filter(
            Meal.user_id == user_id,
            func.date(Meal.logged_at) == target_date
        ).all()

        tot_cal = sum(m.total_calories for m in meals)
        tot_prot = sum(m.total_protein for m in meals)
        tot_carb = sum(m.total_carbs for m in meals)
        tot_fat = sum(m.total_fat for m in meals)
        tot_fib = sum(m.total_fiber for m in meals)

        # Meal distribution
        meal_logged = {"breakfast": False, "lunch": False, "dinner": False, "snack": False}
        meal_cal = {"breakfast": 0.0, "lunch": 0.0, "dinner": 0.0, "snack": 0.0}

        for m in meals:
            mtype = m.meal_type.lower()
            if mtype in meal_logged:
                meal_logged[mtype] = True
                meal_cal[mtype] = round(meal_cal[mtype] + m.total_calories, 1)

        # 3. Health connect records
        health = db.query(HealthRecord).filter(
            HealthRecord.user_id == user_id,
            HealthRecord.recorded_date == target_date
        ).first()

        has_total_calorie_data = bool(
            health and health.total_calories_burned > 0
        )
        cal_burned = health.total_calories_burned if has_total_calorie_data else None
        active_calories_burned = health.active_calories_burned if health else 0.0
        steps = health.steps if health else 0
        net_balance = round(tot_cal - cal_burned, 1) if cal_burned is not None else None
        if health is None:
            burned_source = "No Health Connect data synced"
        elif has_total_calorie_data:
            burned_source = "Health Connect (actual total calories)"
        else:
            burned_source = "Health Connect: total calories unavailable"

        def make_prog(consumed: float, target: float) -> Dict[str, float]:
            pct = round((consumed / max(target, 1.0)) * 100.0, 1)
            rem = round(max(target - consumed, 0.0), 1)
            return {
                "consumed": round(consumed, 1),
                "target": round(target, 1),
                "percentage": pct,
                "remaining": rem
            }

        return {
            "date": target_date,
            "calories": make_prog(tot_cal, target_cal),
            "protein_g": make_prog(tot_prot, target_prot),
            "carb_g": make_prog(tot_carb, target_carb),
            "fat_g": make_prog(tot_fat, target_fat),
            "fiber_g": make_prog(tot_fib, target_fib),
            "calories_burned": round(cal_burned, 1) if cal_burned is not None else None,
            "active_calories_burned": round(active_calories_burned, 1),
            "burned_source": burned_source,
            "energy_balance_kcal": net_balance,
            "steps": steps,
            "meals_count": len(meals),
            "meals_logged": meal_logged,
            "meal_calories": meal_cal
        }

    @classmethod
    def get_period_report(
        cls,
        user_id: int,
        period: str,  # "weekly" or "monthly"
        end_date: Optional[date],
        db: Session
    ) -> Dict[str, Any]:
        """Calculate period averages, daily trend series, top consumed foods, and comparison deltas."""
        e_date = end_date or date.today()
        days = 7 if period == "weekly" else 30
        s_date = e_date - timedelta(days=days - 1)

        # Fetch meals in range
        meals = db.query(Meal).filter(
            Meal.user_id == user_id,
            func.date(Meal.logged_at) >= s_date,
            func.date(Meal.logged_at) <= e_date
        ).all()

        # Fetch health records in range
        health_records = db.query(HealthRecord).filter(
            HealthRecord.user_id == user_id,
            HealthRecord.recorded_date >= s_date,
            HealthRecord.recorded_date <= e_date
        ).all()
        health_map = {h.recorded_date: h for h in health_records}

        # Daily breakdown series
        daily_trends = []
        meals_by_date = {}
        for m in meals:
            m_date = m.logged_at.date()
            if m_date not in meals_by_date:
                meals_by_date[m_date] = []
            meals_by_date[m_date].append(m)

        all_cals = []
        all_prots = []
        all_carbs = []
        all_fats = []
        all_fibs = []
        all_burns = []
        all_balances = []
        all_steps = []

        curr = s_date
        logged_days_count = 0

        while curr <= e_date:
            day_meals = meals_by_date.get(curr, [])
            if day_meals:
                logged_days_count += 1

            d_cal = sum(m.total_calories for m in day_meals)
            d_prot = sum(m.total_protein for m in day_meals)
            d_carb = sum(m.total_carbs for m in day_meals)
            d_fat = sum(m.total_fat for m in day_meals)
            d_fib = sum(m.total_fiber for m in day_meals)

            h_rec = health_map.get(curr)
            d_burn = (
                h_rec.total_calories_burned
                if h_rec and h_rec.total_calories_burned > 0
                else 0.0
            )
            d_steps = h_rec.steps if h_rec else 0
            d_balance = round(d_cal - d_burn, 1)

            all_cals.append(d_cal)
            all_prots.append(d_prot)
            all_carbs.append(d_carb)
            all_fats.append(d_fat)
            all_fibs.append(d_fib)
            all_burns.append(d_burn)
            all_balances.append(d_balance)
            all_steps.append(d_steps)

            daily_trends.append({
                "date": curr.strftime("%Y-%m-%d"),
                "consumed_kcal": round(d_cal, 1),
                "burned_kcal": round(d_burn, 1),
                "protein_g": round(d_prot, 1),
                "carb_g": round(d_carb, 1),
                "fat_g": round(d_fat, 1),
                "fiber_g": round(d_fib, 1)
            })
            curr += timedelta(days=1)

        # Averages
        avg_cal = round(sum(all_cals) / max(len(all_cals), 1), 1)
        avg_prot = round(sum(all_prots) / max(len(all_prots), 1), 1)
        avg_carb = round(sum(all_carbs) / max(len(all_carbs), 1), 1)
        avg_fat = round(sum(all_fats) / max(len(all_fats), 1), 1)
        avg_fib = round(sum(all_fibs) / max(len(all_fibs), 1), 1)
        avg_burn = round(sum(all_burns) / max(len(all_burns), 1), 1)
        avg_bal = round(sum(all_balances) / max(len(all_balances), 1), 1)
        avg_steps = int(sum(all_steps) / max(len(all_steps), 1))

        # Goal adherence
        goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == user_id).first()
        target_cal = goals.calorie_target if goals else 2000.0
        adherence_days = sum(1 for c in all_cals if abs(c - target_cal) <= (target_cal * 0.15))
        goal_adherence_pct = round((adherence_days / max(days, 1)) * 100.0, 1)

        # Top consumed foods
        meal_ids = [m.id for m in meals]
        items = db.query(MealItem).filter(MealItem.meal_id.in_(meal_ids)).all() if meal_ids else []
        food_counter = Counter(it.item_name for it in items)
        top_foods = [{"name": name, "count": count} for name, count in food_counter.most_common(5)]

        # Top recipes used
        recipe_ids = [it.recipe_id for it in items if it.recipe_id is not None]
        recipe_counter = Counter(recipe_ids)
        top_recipes = []
        for rid, count in recipe_counter.most_common(5):
            rec = db.query(Recipe).filter(Recipe.id == rid).first()
            if rec:
                top_recipes.append({"id": rec.id, "name": rec.name, "count": count})

        # Calculate previous period for comparison
        prev_end = s_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days - 1)
        prev_meals = db.query(Meal).filter(
            Meal.user_id == user_id,
            func.date(Meal.logged_at) >= prev_start,
            func.date(Meal.logged_at) <= prev_end
        ).all()

        prev_cal_tot = sum(m.total_calories for m in prev_meals)
        prev_avg_cal = round(prev_cal_tot / max(days, 1), 1)
        prev_prot_tot = sum(m.total_protein for m in prev_meals)
        prev_avg_prot = round(prev_prot_tot / max(days, 1), 1)

        cal_delta_pct = round(((avg_cal - prev_avg_cal) / max(prev_avg_cal, 1.0)) * 100.0, 1) if prev_avg_cal > 0 else 0.0
        prot_delta_pct = round(((avg_prot - prev_avg_prot) / max(prev_avg_prot, 1.0)) * 100.0, 1) if prev_avg_prot > 0 else 0.0

        return {
            "period": period,
            "start_date": s_date.strftime("%Y-%m-%d"),
            "end_date": e_date.strftime("%Y-%m-%d"),
            "summary": {
                "avg_calories": avg_cal,
                "avg_protein": avg_prot,
                "avg_carb": avg_carb,
                "avg_fat": avg_fat,
                "avg_fiber": avg_fib,
                "avg_calories_burned": avg_burn,
                "avg_energy_balance": avg_bal,
                "avg_steps": avg_steps,
                "goal_adherence_percent": goal_adherence_pct,
                "total_meals_logged": len(meals),
                "missed_meals_count": max((days * 3) - len(meals), 0)
            },
            "daily_breakdown": daily_trends,
            "top_foods": top_foods,
            "top_recipes": top_recipes,
            "comparison_previous_period": {
                "calories_delta_percent": cal_delta_pct,
                "protein_delta_percent": prot_delta_pct
            }
        }

analytics_service = AnalyticsService()
