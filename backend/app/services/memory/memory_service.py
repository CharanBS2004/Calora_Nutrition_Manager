from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.entities import UserMemory, Meal, Recipe, NutritionGoal

class MemoryService:
    """
    User Memory Service managing short-term session context and
    long-term eating habits, preferences, and recurring patterns.
    Strictly isolated per user_id.
    """

    @staticmethod
    def get_short_term_context(user_id: int, db: Session) -> Dict[str, Any]:
        """Fetch today's meals, totals, and remaining goals."""
        today = date.today()
        meals = db.query(Meal).filter(
            Meal.user_id == user_id,
            func.date(Meal.logged_at) == today
        ).all()

        tot_cal = sum(m.total_calories for m in meals)
        tot_prot = sum(m.total_protein for m in meals)
        tot_carb = sum(m.total_carbs for m in meals)
        tot_fat = sum(m.total_fat for m in meals)
        tot_fib = sum(m.total_fiber for m in meals)

        goals = db.query(NutritionGoal).filter(NutritionGoal.user_id == user_id).first()
        target_cal = goals.calorie_target if goals else 2000.0
        target_prot = goals.protein_g if goals else 75.0
        target_carb = goals.carb_g if goals else 250.0
        target_fat = goals.fat_g if goals else 65.0
        target_fib = goals.fiber_g if goals else 30.0

        return {
            "date": today.strftime("%Y-%m-%d"),
            "logged_meals": [
                {
                    "meal_type": m.meal_type,
                    "calories": m.total_calories,
                    "protein": m.total_protein,
                    "items": [it.item_name for it in m.items]
                } for m in meals
            ],
            "totals": {
                "calories": round(tot_cal, 1),
                "protein": round(tot_prot, 1),
                "carbs": round(tot_carb, 1),
                "fat": round(tot_fat, 1),
                "fiber": round(tot_fib, 1)
            },
            "remaining": {
                "calories": round(max(target_cal - tot_cal, 0.0), 1),
                "protein": round(max(target_prot - tot_prot, 0.0), 1),
                "carbs": round(max(target_carb - tot_carb, 0.0), 1),
                "fat": round(max(target_fat - tot_fat, 0.0), 1),
                "fiber": round(max(target_fib - tot_fib, 0.0), 1)
            }
        }

    @staticmethod
    def save_memory(
        user_id: int,
        content: str,
        memory_type: str = "preference",
        context: Optional[str] = None,
        db: Session = None
    ) -> UserMemory:
        """Persist a discovered user eating pattern or preference."""
        # Check if identical memory exists
        existing = db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.content == content
        ).first()

        if existing:
            existing.last_recalled_at = datetime.now(timezone.utc)
            db.commit()
            return existing

        new_mem = UserMemory(
            user_id=user_id,
            content=content,
            memory_type=memory_type,
            context=context,
            confidence=1.0,
            last_recalled_at=datetime.now(timezone.utc)
        )
        db.add(new_mem)
        db.commit()
        db.refresh(new_mem)
        return new_mem

    @staticmethod
    def recall_relevant_memories(user_id: int, query: str, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        """Recall long-term user memories matching query keywords or habits."""
        q_lower = query.lower()
        all_mems = db.query(UserMemory).filter(UserMemory.user_id == user_id).all()

        scored = []
        for m in all_mems:
            words = m.content.lower().split()
            match_count = sum(1 for w in words if w in q_lower)
            if match_count > 0:
                scored.append((match_count, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [
            {"id": m.id, "type": m.memory_type, "content": m.content, "context": m.context}
            for _, m in scored[:limit]
        ]

        # If no specific match, return recent memories
        if not results:
            recent = db.query(UserMemory).filter(
                UserMemory.user_id == user_id
            ).order_by(UserMemory.last_recalled_at.desc()).limit(limit).all()
            results = [
                {"id": m.id, "type": m.memory_type, "content": m.content, "context": m.context}
                for m in recent
            ]

        return results

memory_service = MemoryService()
