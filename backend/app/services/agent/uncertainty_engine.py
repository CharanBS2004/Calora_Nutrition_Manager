import re
from typing import Dict, Any, List, Optional, Tuple

class UncertaintyEngine:
    """
    Nutrition Uncertainty Engine.
    Detects underspecified meal descriptions (e.g., 'some rice and curry'),
    evaluates confidence levels, and formats structured clarification questions.
    """

    AMBIGUOUS_QUANTITY_TERMS = ["some", "a little", "few", "a bit", "a bowl", "a plate", "lots of", "much"]

    @classmethod
    def analyze_meal_uncertainty(cls, food_name: str, raw_input: str, confidence_score: float) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Determine whether an item has significant uncertainty requiring clarification.
        Returns (is_uncertain, clarification_payload)
        """
        is_uncertain = False
        reason = None

        lower_input = raw_input.lower()
        for term in cls.AMBIGUOUS_QUANTITY_TERMS:
            if re.search(rf"\b{term}\b", lower_input):
                is_uncertain = True
                reason = f"Portion specified with ambiguous term '{term}'"
                break

        if confidence_score < 0.70:
            is_uncertain = True
            if not reason:
                reason = "Generic volume conversion without exact food density factor"

        if not is_uncertain:
            return False, None

        # Build structured options tailored to Indian culinary portion measures
        clean_name = food_name.split("(")[0].strip()
        options = [
            f"Small portion (1 katori / ~100g)",
            f"Medium portion (1 cup / 1.5 katori / ~150g)",
            f"Large portion (2 cups / ~250g)",
            f"Custom weight in grams"
        ]

        # Customize for specific foods
        if any(term in clean_name.lower() for term in ["roti", "chapati", "idli", "dosa", "egg"]):
            options = ["1 piece / serving", "2 pieces / servings", "3 pieces / servings", "4 pieces / servings"]
        elif any(term in clean_name.lower() for term in ["chai", "tea", "coffee", "milk"]):
            options = ["1 small tea cup (~100ml)", "1 standard cup (~150ml)", "1 tall mug / glass (~250ml)"]

        return True, {
            "item_name": clean_name,
            "reason": reason,
            "question": f"Approximately how much {clean_name} did you have?",
            "options": options
        }

uncertainty_engine = UncertaintyEngine()
