from typing import Dict, Any, List, Optional, Tuple
from app.services.unit_converter import unit_converter

class NutritionEngine:
    """
    Deterministic Nutrition Calculation Engine.
    Executes exact mathematical calculations for:
    - per 100g
    - per portion/quantity
    - recipe totals
    - per serving
    - per cooked gram
    - consumed portions
    - confidence scoring
    """

    @staticmethod
    def calculate_ingredient_nutrients(
        quantity_g: float,
        energy_100g: float,
        protein_100g: float,
        carb_100g: float,
        fat_100g: float,
        fiber_100g: float
    ) -> Dict[str, float]:
        """
        Calculate nutrients for a specific weight in grams:
        nutrient = (quantity_g / 100.0) * nutrient_per_100g
        """
        if quantity_g <= 0:
            return {
                "energy_kcal": 0.0,
                "protein_g": 0.0,
                "carbohydrate_g": 0.0,
                "fat_g": 0.0,
                "fiber_g": 0.0
            }

        factor = quantity_g / 100.0
        return {
            "energy_kcal": round(energy_100g * factor, 2),
            "protein_g": round(protein_100g * factor, 2),
            "carbohydrate_g": round(carb_100g * factor, 2),
            "fat_g": round(fat_100g * factor, 2),
            "fiber_g": round(fiber_100g * factor, 2)
        }

    @classmethod
    def calculate_recipe_totals(
        cls,
        ingredients: List[Dict[str, Any]],
        servings_count: float = 1.0,
        total_cooked_weight_g: Optional[float] = None,
        consumed_quantity: Optional[float] = None,
        consumed_unit: str = "serving",
        db=None,
    ) -> Dict[str, Any]:
        """
        Calculates total recipe nutrition, per-serving, per-100g, and consumed portion.
        Each ingredient dict has:
          quantity, unit, food_name, energy_100g, protein_100g, carb_100g, fat_100g, fiber_100g
        """
        total_energy = 0.0
        total_protein = 0.0
        total_carb = 0.0
        total_fat = 0.0
        total_fiber = 0.0
        total_raw_weight = 0.0
        confidence_scores = []
        ingredient_breakdowns = []

        for ing in ingredients:
            raw_qty = float(ing.get("quantity", 0))
            unit = str(ing.get("unit", "g"))
            food_name = str(ing.get("food_name", ""))
            category = ing.get("category")

            # Convert to grams using food-specific density converter
            grams, is_specific, conf, explanation = unit_converter.convert_to_grams(
                food_name=food_name,
                quantity=raw_qty,
                unit=unit,
                category=category,
                db=db,
            )
            if conf <= 0:
                raise ValueError(explanation)
            confidence_scores.append(conf)
            total_raw_weight += grams

            nutrients = cls.calculate_ingredient_nutrients(
                quantity_g=grams,
                energy_100g=float(ing.get("energy_100g", 0)),
                protein_100g=float(ing.get("protein_100g", 0)),
                carb_100g=float(ing.get("carb_100g", 0)),
                fat_100g=float(ing.get("fat_100g", 0)),
                fiber_100g=float(ing.get("fiber_100g", 0))
            )

            total_energy += nutrients["energy_kcal"]
            total_protein += nutrients["protein_g"]
            total_carb += nutrients["carbohydrate_g"]
            total_fat += nutrients["fat_g"]
            total_fiber += nutrients["fiber_g"]

            ingredient_breakdowns.append({
                "food_id": ing.get("food_id"),
                "food_name": food_name,
                "input_quantity": raw_qty,
                "input_unit": unit,
                "weight_g": grams,
                "nutrients": nutrients,
                "is_density_specific": is_specific,
                "confidence": conf,
                "conversion_note": explanation
            })

        # Overall recipe confidence
        overall_confidence = round(sum(confidence_scores) / max(len(confidence_scores), 1), 2)

        # Servings count sanity check
        effective_servings = max(servings_count, 0.1)

        # Per serving
        per_serving = {
            "energy_kcal": round(total_energy / effective_servings, 2),
            "protein_g": round(total_protein / effective_servings, 2),
            "carbohydrate_g": round(total_carb / effective_servings, 2),
            "fat_g": round(total_fat / effective_servings, 2),
            "fiber_g": round(total_fiber / effective_servings, 2)
        }

        # Per 100g of cooked recipe
        reference_weight = total_cooked_weight_g if (total_cooked_weight_g and total_cooked_weight_g > 0) else total_raw_weight
        reference_weight = max(reference_weight, 1.0)
        per_100g_factor = 100.0 / reference_weight

        per_100g = {
            "energy_kcal": round(total_energy * per_100g_factor, 2),
            "protein_g": round(total_protein * per_100g_factor, 2),
            "carbohydrate_g": round(total_carb * per_100g_factor, 2),
            "fat_g": round(total_fat * per_100g_factor, 2),
            "fiber_g": round(total_fiber * per_100g_factor, 2)
        }

        # Consumed portion calculation if requested
        consumed_portion = None
        if consumed_quantity is not None and consumed_quantity > 0:
            if consumed_unit.lower() in ("g", "gram", "grams"):
                ratio = consumed_quantity / reference_weight
            elif consumed_unit.lower() in ("serving", "servings"):
                ratio = consumed_quantity / effective_servings
            else:
                # convert consumed unit to grams
                consumed_g, _, consumed_confidence, explanation = unit_converter.convert_to_grams(
                    food_name="Recipe",
                    quantity=consumed_quantity,
                    unit=consumed_unit,
                    db=db,
                )
                if consumed_confidence <= 0:
                    raise ValueError(explanation)
                ratio = consumed_g / reference_weight

            consumed_portion = {
                "energy_kcal": round(total_energy * ratio, 2),
                "protein_g": round(total_protein * ratio, 2),
                "carbohydrate_g": round(total_carb * ratio, 2),
                "fat_g": round(total_fat * ratio, 2),
                "fiber_g": round(total_fiber * ratio, 2)
            }

        return {
            "total_recipe": {
                "energy_kcal": round(total_energy, 2),
                "protein_g": round(total_protein, 2),
                "carbohydrate_g": round(total_carb, 2),
                "fat_g": round(total_fat, 2),
                "fiber_g": round(total_fiber, 2)
            },
            "per_serving": per_serving,
            "per_100g": per_100g,
            "consumed_portion": consumed_portion,
            "servings_count": effective_servings,
            "total_cooked_weight_g": total_cooked_weight_g,
            "total_raw_weight_g": round(total_raw_weight, 2),
            "confidence_score": overall_confidence,
            "ingredients": ingredient_breakdowns
        }

    @staticmethod
    def calculate_energy_balance(calories_consumed: float, calories_burned: float) -> Dict[str, Any]:
        """
        Energy Balance = Calories Consumed - Calories Burned.
        Deficit = negative, Surplus = positive, Maintenance = within +/- 100 kcal.
        """
        net = round(calories_consumed - calories_burned, 2)
        if abs(net) <= 100:
            status = "maintenance"
        elif net > 100:
            status = "surplus"
        else:
            status = "deficit"

        return {
            "calories_consumed": round(calories_consumed, 2),
            "calories_burned": round(calories_burned, 2),
            "net_balance_kcal": net,
            "status": status
        }

nutrition_engine = NutritionEngine()
