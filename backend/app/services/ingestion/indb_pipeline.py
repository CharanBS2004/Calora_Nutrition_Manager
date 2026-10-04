import os
import json
import logging
from typing import Dict, Any, List, Optional
import openpyxl
from sqlalchemy.orm import Session
from app.models.entities import Food, FoodUnitConversion, Recipe, RecipeIngredient
from app.core.config import settings

logger = logging.getLogger(__name__)

# ICMR-NIN IFCT 2017 official nutrient values per 100g for core Indian raw staple ingredients
ICMR_NIN_STAPLES = {
    "A001": {"name": "Amaranth seed, black (Amaranthus cruentus)", "category": "Cereals and Millets", "kcal": 356.0, "prot": 14.6, "carb": 62.1, "fat": 5.4, "fib": 7.0},
    "A003": {"name": "Bajra / Pearl millet (Pennisetum typhoideum)", "category": "Cereals and Millets", "kcal": 348.0, "prot": 11.0, "carb": 61.8, "fat": 5.4, "fib": 11.5},
    "A005": {"name": "Jowar / Sorghum (Sorghum vulgare)", "category": "Cereals and Millets", "kcal": 334.0, "prot": 10.0, "carb": 67.7, "fat": 1.7, "fib": 10.2},
    "A006": {"name": "Maize, dry (Zea mays)", "category": "Cereals and Millets", "kcal": 334.0, "prot": 11.1, "carb": 66.2, "fat": 3.6, "fib": 12.2},
    "A009": {"name": "Quinoa (Chenopodium quinoa)", "category": "Cereals and Millets", "kcal": 328.0, "prot": 13.1, "carb": 58.5, "fat": 5.6, "fib": 6.8},
    "A010": {"name": "Ragi / Finger millet (Eleusine coracana)", "category": "Cereals and Millets", "kcal": 320.0, "prot": 7.2, "carb": 66.8, "fat": 1.9, "fib": 11.2},
    "A011": {"name": "Rice flakes / Poha (Oryza sativa)", "category": "Cereals and Millets", "kcal": 346.0, "prot": 6.7, "carb": 77.2, "fat": 1.2, "fib": 2.8},
    "A012": {"name": "Rice puffed / Murmura (Oryza sativa)", "category": "Cereals and Millets", "kcal": 325.0, "prot": 7.5, "carb": 73.6, "fat": 0.1, "fib": 15.6},
    "A014": {"name": "Rice, parboiled, milled (Oryza sativa)", "category": "Cereals and Millets", "kcal": 352.0, "prot": 7.8, "carb": 77.2, "fat": 0.5, "fib": 4.1},
    "A018": {"name": "Wheat flour, refined / Maida (Triticum aestivum)", "category": "Cereals and Millets", "kcal": 352.0, "prot": 10.4, "carb": 73.9, "fat": 0.9, "fib": 2.8},
    "A019": {"name": "Wheat flour, whole wheat / Atta (Triticum aestivum)", "category": "Cereals and Millets", "kcal": 320.0, "prot": 10.6, "carb": 64.5, "fat": 1.5, "fib": 11.2},
    "A022": {"name": "Wheat, semolina / Sooji (Triticum aestivum)", "category": "Cereals and Millets", "kcal": 334.0, "prot": 10.4, "carb": 71.8, "fat": 0.8, "fib": 4.2},
    "A024": {"name": "Wheat, vermicelli, roasted (Triticum aestivum)", "category": "Cereals and Millets", "kcal": 332.0, "prot": 10.2, "carb": 71.5, "fat": 0.7, "fib": 3.9},

    # Pulses and Legumes
    "B001": {"name": "Bengal gram, dal / Chana dal (Cicer arietinum)", "category": "Pulses and Legumes", "kcal": 329.0, "prot": 21.6, "carb": 59.8, "fat": 5.3, "fib": 15.3},
    "B002": {"name": "Bengal gram, whole / Kala chana (Cicer arietinum)", "category": "Pulses and Legumes", "kcal": 287.0, "prot": 17.1, "carb": 60.9, "fat": 5.3, "fib": 25.2},
    "B003": {"name": "Black gram, dal / Urad dal (Phaseolus mungo)", "category": "Pulses and Legumes", "kcal": 347.0, "prot": 24.0, "carb": 59.6, "fat": 1.4, "fib": 20.4},
    "B004": {"name": "Black gram, whole / Sabut urad (Phaseolus mungo)", "category": "Pulses and Legumes", "kcal": 291.0, "prot": 22.0, "carb": 58.5, "fat": 1.4, "fib": 24.0},
    "B005": {"name": "Cowpea, brown / Lobia (Vigna catjang)", "category": "Pulses and Legumes", "kcal": 323.0, "prot": 24.1, "carb": 54.5, "fat": 1.0, "fib": 16.0},
    "B010": {"name": "Green gram, dal / Moong dal (Vigna radiata)", "category": "Pulses and Legumes", "kcal": 334.0, "prot": 24.5, "carb": 59.9, "fat": 1.2, "fib": 17.1},
    "B011": {"name": "Green gram, whole / Sabut moong (Vigna radiata)", "category": "Pulses and Legumes", "kcal": 293.0, "prot": 22.5, "carb": 60.0, "fat": 1.2, "fib": 16.8},
    "B012": {"name": "Horse gram, whole / Kulthi (Dolicus biflorus)", "category": "Pulses and Legumes", "kcal": 330.0, "prot": 22.0, "carb": 57.2, "fat": 0.5, "fib": 28.0},
    "B013": {"name": "Lentil dal / Masoor dal (Lens culinaris)", "category": "Pulses and Legumes", "kcal": 343.0, "prot": 25.1, "carb": 60.0, "fat": 0.7, "fib": 11.2},
    "B020": {"name": "Rajmah, red / Kidney beans (Phaseolus vulgaris)", "category": "Pulses and Legumes", "kcal": 299.0, "prot": 22.9, "carb": 60.6, "fat": 1.3, "fib": 24.9},
    "B021": {"name": "Red gram, dal / Toor dal (Cajanus cajan)", "category": "Pulses and Legumes", "kcal": 335.0, "prot": 22.3, "carb": 63.5, "fat": 1.7, "fib": 9.1},
    "B025": {"name": "Soya bean, white (Glycine max)", "category": "Pulses and Legumes", "kcal": 381.0, "prot": 37.8, "carb": 20.9, "fat": 19.8, "fib": 22.5},

    # Leafy and other Vegetables
    "C004": {"name": "Amaranth leaves / Chaulai (Amaranthus gangeticus)", "category": "Leafy Vegetables", "kcal": 36.0, "prot": 4.0, "carb": 5.0, "fat": 0.5, "fib": 6.1},
    "C015": {"name": "Cabbage, green (Brassica oleracea)", "category": "Vegetables", "kcal": 21.0, "prot": 1.4, "carb": 4.3, "fat": 0.1, "fib": 2.8},
    "C020": {"name": "Coriander leaves / Dhania patta", "category": "Leafy Vegetables", "kcal": 31.0, "prot": 3.3, "carb": 4.5, "fat": 0.6, "fib": 4.2},
    "C021": {"name": "Curry leaves / Kadi patta", "category": "Leafy Vegetables", "kcal": 108.0, "prot": 6.1, "carb": 18.7, "fat": 1.0, "fib": 6.4},
    "C024": {"name": "Fenugreek leaves / Methi", "category": "Leafy Vegetables", "kcal": 34.0, "prot": 4.4, "carb": 4.2, "fat": 0.9, "fib": 4.9},
    "C031": {"name": "Spinach / Palak (Spinacia oleracea)", "category": "Leafy Vegetables", "kcal": 24.0, "prot": 2.0, "carb": 2.9, "fat": 0.7, "fib": 2.5},

    "D002": {"name": "Brinjal / Eggplant (Solanum melongena)", "category": "Vegetables", "kcal": 24.0, "prot": 1.4, "carb": 4.0, "fat": 0.3, "fib": 3.4},
    "D006": {"name": "Bottle gourd / Lauki (Lagenaria siceraria)", "category": "Vegetables", "kcal": 11.0, "prot": 0.6, "carb": 2.0, "fat": 0.1, "fib": 1.2},
    "D012": {"name": "Capsicum / Bell pepper, green", "category": "Vegetables", "kcal": 16.0, "prot": 1.2, "carb": 2.6, "fat": 0.2, "fib": 2.4},
    "D015": {"name": "Cauliflower (Brassica oleracea var. botrytis)", "category": "Vegetables", "kcal": 23.0, "prot": 2.5, "carb": 3.9, "fat": 0.4, "fib": 2.8},
    "D024": {"name": "Cucumber (Cucumis sativus)", "category": "Vegetables", "kcal": 13.0, "prot": 0.6, "carb": 2.5, "fat": 0.1, "fib": 1.1},
    "D030": {"name": "Lady's finger / Bhindi (Abelmoschus esculentus)", "category": "Vegetables", "kcal": 27.0, "prot": 1.9, "carb": 6.4, "fat": 0.2, "fib": 3.6},
    "D057": {"name": "Tomato, ripe, red (Solanum lycopersicum)", "category": "Vegetables", "kcal": 21.0, "prot": 0.9, "carb": 3.6, "fat": 0.2, "fib": 1.7},

    # Roots and Tubers
    "F006": {"name": "Carrot (Daucus carota)", "category": "Roots and Tubers", "kcal": 38.0, "prot": 0.9, "carb": 8.0, "fat": 0.2, "fib": 4.4},
    "F014": {"name": "Garlic (Allium sativum)", "category": "Roots and Tubers", "kcal": 125.0, "prot": 6.3, "carb": 24.3, "fat": 0.1, "fib": 2.4},
    "F015": {"name": "Ginger, fresh (Zingiber officinale)", "category": "Roots and Tubers", "kcal": 55.0, "prot": 2.3, "carb": 12.3, "fat": 0.9, "fib": 2.4},
    "F024": {"name": "Onion, big, red (Allium cepa)", "category": "Roots and Tubers", "kcal": 49.0, "prot": 1.2, "carb": 11.1, "fat": 0.1, "fib": 1.8},
    "F027": {"name": "Potato, brown skin (Solanum tuberosum)", "category": "Roots and Tubers", "kcal": 70.0, "prot": 1.6, "carb": 16.0, "fat": 0.1, "fib": 1.7},

    # Condiments and Spices
    "G006": {"name": "Cardamom, green (Elettaria cardamomum)", "category": "Spices and Condiments", "kcal": 255.0, "prot": 10.2, "carb": 42.1, "fat": 2.2, "fib": 20.1},
    "G010": {"name": "Chilli, red (Capsicum annuum)", "category": "Spices and Condiments", "kcal": 236.0, "prot": 15.0, "carb": 31.6, "fat": 6.0, "fib": 30.2},
    "G011": {"name": "Chilli, green (Capsicum annuum)", "category": "Spices and Condiments", "kcal": 45.0, "prot": 2.9, "carb": 6.8, "fat": 0.6, "fib": 6.8},
    "G012": {"name": "Cinnamon (Cinnamomum zeylanicum)", "category": "Spices and Condiments", "kcal": 214.0, "prot": 3.5, "carb": 36.5, "fat": 2.2, "fib": 33.0},
    "G014": {"name": "Cloves (Syzygium aromaticum)", "category": "Spices and Condiments", "kcal": 286.0, "prot": 5.2, "carb": 40.0, "fat": 8.9, "fib": 25.1},
    "G015": {"name": "Coriander seeds (Coriandrum sativum)", "category": "Spices and Condiments", "kcal": 268.0, "prot": 11.5, "carb": 24.2, "fat": 16.1, "fib": 31.2},
    "G016": {"name": "Cumin seeds / Jeera (Cuminum cyminum)", "category": "Spices and Condiments", "kcal": 304.0, "prot": 17.7, "carb": 34.2, "fat": 15.0, "fib": 10.5},
    "G022": {"name": "Mustard seeds / Rai (Brassica nigra)", "category": "Spices and Condiments", "kcal": 508.0, "prot": 20.0, "carb": 23.8, "fat": 39.6, "fib": 8.0},
    "G025": {"name": "Pepper, black (Piper nigrum)", "category": "Spices and Condiments", "kcal": 217.0, "prot": 10.0, "carb": 49.2, "fat": 1.3, "fib": 25.3},
    "G029": {"name": "Turmeric powder / Haldi (Curcuma longa)", "category": "Spices and Condiments", "kcal": 280.0, "prot": 6.3, "carb": 69.9, "fat": 3.6, "fib": 4.5},

    # Nuts and Oilseeds
    "H002": {"name": "Almond / Badam (Prunus dulcis)", "category": "Nuts and Oilseeds", "kcal": 609.0, "prot": 20.8, "carb": 10.5, "fat": 58.9, "fib": 10.5},
    "H006": {"name": "Cashew nut / Kaju (Anacardium occidentale)", "category": "Nuts and Oilseeds", "kcal": 583.0, "prot": 21.2, "carb": 22.3, "fat": 46.9, "fib": 3.7},
    "H008": {"name": "Coconut, dry / Copra (Cocos nucifera)", "category": "Nuts and Oilseeds", "kcal": 624.0, "prot": 6.8, "carb": 18.4, "fat": 62.0, "fib": 14.3},
    "H009": {"name": "Coconut, fresh (Cocos nucifera)", "category": "Nuts and Oilseeds", "kcal": 408.0, "prot": 4.5, "carb": 13.0, "fat": 41.6, "fib": 3.6},
    "H010": {"name": "Groundnut / Peanuts (Arachis hypogaea)", "category": "Nuts and Oilseeds", "kcal": 520.0, "prot": 25.8, "carb": 26.1, "fat": 40.1, "fib": 8.5},
    "H013": {"name": "Sesame seeds / Til (Sesamum indicum)", "category": "Nuts and Oilseeds", "kcal": 520.0, "prot": 18.0, "carb": 25.0, "fat": 43.3, "fib": 14.0},

    # Dairy and Animal Foods
    "L001": {"name": "Milk, Buffalo, whole", "category": "Milk and Milk Products", "kcal": 107.0, "prot": 4.3, "carb": 5.0, "fat": 6.5, "fib": 0.0},
    "L002": {"name": "Milk, Cow, whole", "category": "Milk and Milk Products", "kcal": 67.0, "prot": 3.2, "carb": 4.4, "fat": 4.1, "fib": 0.0},
    "L004": {"name": "Curd / Dahi, Cow", "category": "Milk and Milk Products", "kcal": 60.0, "prot": 3.1, "carb": 4.0, "fat": 4.0, "fib": 0.0},
    "L007": {"name": "Paneer / Cottage cheese, Cow", "category": "Milk and Milk Products", "kcal": 257.0, "prot": 18.3, "carb": 3.4, "fat": 20.8, "fib": 0.0},
    "L008": {"name": "Ghee, Cow", "category": "Milk and Milk Products", "kcal": 900.0, "prot": 0.0, "carb": 0.0, "fat": 100.0, "fib": 0.0},
    "M001": {"name": "Egg, whole, raw, hen", "category": "Eggs and Meat", "kcal": 135.0, "prot": 13.3, "carb": 0.0, "fat": 8.7, "fib": 0.0},
    "N003": {"name": "Chicken, meat with skin, dressed", "category": "Eggs and Meat", "kcal": 168.0, "prot": 21.8, "carb": 0.0, "fat": 9.0, "fib": 0.0},
    "N004": {"name": "Mutton / Goat meat, lean", "category": "Eggs and Meat", "kcal": 118.0, "prot": 21.4, "carb": 0.0, "fat": 3.6, "fib": 0.0},

    # Oils and Fats
    "P001": {"name": "Groundnut oil", "category": "Oils and Fats", "kcal": 900.0, "prot": 0.0, "carb": 0.0, "fat": 100.0, "fib": 0.0},
    "P002": {"name": "Mustard oil", "category": "Oils and Fats", "kcal": 900.0, "prot": 0.0, "carb": 0.0, "fat": 100.0, "fib": 0.0},
    "P003": {"name": "Sunflower oil", "category": "Oils and Fats", "kcal": 900.0, "prot": 0.0, "carb": 0.0, "fat": 100.0, "fib": 0.0},
    "P057": {"name": "Vegetable cooking oil, blended", "category": "Oils and Fats", "kcal": 900.0, "prot": 0.0, "carb": 0.0, "fat": 100.0, "fib": 0.0}
}

class INDBIngestionPipeline:
    """
    ETL Ingestion Pipeline for Indian Nutrient Databank (INDB)
    Loads:
      - INDB.xlsx (1,014 Indian dishes)
      - UK_fct.xlsx (144 foods)
      - US_fct.xlsx (54 foods)
      - ICMR-NIN 2017 baseline staples (A001-P057)
      - Units.xlsx (346 food density and volume unit conversions)
    """

    def __init__(self, indb_dir: Optional[str] = None):
        self.indb_dir = indb_dir or settings.INDB_DATASET_DIR

    def run_ingestion(self, db: Session, force: bool = False) -> Dict[str, int]:
        existing_foods = db.query(Food).count()
        if existing_foods > 100 and not force:
            logger.info(f"Database already populated with {existing_foods} foods. Skipping ingestion.")
            return {"foods_loaded": existing_foods, "conversions_loaded": db.query(FoodUnitConversion).count()}

        logger.info("Starting INDB dataset ingestion...")
        counts = {"indb_recipes": 0, "uk_fct": 0, "us_fct": 0, "icmr_nin": 0, "conversions": 0}
        existing_food_keys = {
            self._food_key(source, food_code, food_name)
            for source, food_code, food_name in db.query(
                Food.source, Food.food_code, Food.food_name
            ).all()
        }
        existing_conversion_keys = {
            self._conversion_key(pattern, unit, source)
            for pattern, unit, source in db.query(
                FoodUnitConversion.food_name_pattern,
                FoodUnitConversion.unit_name,
                FoodUnitConversion.source,
            ).all()
        }

        # 1. Ingest ICMR-NIN Staples
        for code, data in ICMR_NIN_STAPLES.items():
            key = self._food_key("ICMR_NIN_2017", code, data["name"])
            if key in existing_food_keys:
                continue
            food = Food(
                food_code=code,
                food_name=data["name"],
                category=data["category"],
                source="ICMR_NIN_2017",
                serving_size=100.0,
                serving_unit="g",
                weight_g=100.0,
                energy_kcal=float(data["kcal"]),
                protein_g=float(data["prot"]),
                carbohydrate_g=float(data["carb"]),
                fat_g=float(data["fat"]),
                fiber_g=float(data["fib"]),
                is_custom=False
            )
            db.add(food)
            existing_food_keys.add(key)
            counts["icmr_nin"] += 1

        db.flush()

        # 2. Ingest UK_fct.xlsx
        uk_path = os.path.join(self.indb_dir, "UK_fct.xlsx")
        if os.path.exists(uk_path):
            wb = openpyxl.load_workbook(uk_path, read_only=True, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            for r in rows[1:]:
                if not r or len(r) < 12:
                    continue
                code = str(r[2] or r[1] or "")
                name = str(r[3] or "").strip()
                if not name:
                    continue
                kcal = self._to_float(r[6])
                carb = self._to_float(r[7])
                prot = self._to_float(r[8])
                fat = self._to_float(r[9])
                fib = self._to_float(r[11])

                key = self._food_key("UK_FCT", code, name)
                if key in existing_food_keys:
                    continue
                food = Food(
                    food_code=code,
                    food_name=name,
                    category="Supplementary UK FCT",
                    source="UK_FCT",
                    serving_size=100.0,
                    serving_unit="g",
                    weight_g=100.0,
                    energy_kcal=kcal,
                    protein_g=prot,
                    carbohydrate_g=carb,
                    fat_g=fat,
                    fiber_g=fib,
                    is_custom=False
                )
                db.add(food)
                existing_food_keys.add(key)
                counts["uk_fct"] += 1
            db.flush()

        # 3. Ingest US_fct.xlsx
        us_path = os.path.join(self.indb_dir, "US_fct.xlsx")
        if os.path.exists(us_path):
            wb = openpyxl.load_workbook(us_path, read_only=True, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            for r in rows[1:]:
                if not r or len(r) < 12:
                    continue
                code = str(r[2] or r[1] or "")
                name = str(r[3] or "").strip()
                if not name:
                    continue
                kcal = self._to_float(r[6])
                carb = self._to_float(r[7])
                prot = self._to_float(r[8])
                fat = self._to_float(r[9])
                fib = self._to_float(r[11])

                key = self._food_key("US_FCT", code, name)
                if key in existing_food_keys:
                    continue
                food = Food(
                    food_code=code,
                    food_name=name,
                    category="Supplementary US FCT",
                    source="US_FCT",
                    serving_size=100.0,
                    serving_unit="g",
                    weight_g=100.0,
                    energy_kcal=kcal,
                    protein_g=prot,
                    carbohydrate_g=carb,
                    fat_g=fat,
                    fiber_g=fib,
                    is_custom=False
                )
                db.add(food)
                existing_food_keys.add(key)
                counts["us_fct"] += 1
            db.flush()

        # 4. Ingest INDB.xlsx (1,014 Prepared Dishes)
        indb_path = os.path.join(self.indb_dir, "INDB.xlsx")
        if os.path.exists(indb_path):
            wb = openpyxl.load_workbook(indb_path, read_only=True, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            for r in rows[1:]:
                if not r or len(r) < 10:
                    continue
                code = str(r[0] or "")
                name = str(r[1] or "").strip()
                if not name:
                    continue

                kcal_100g = self._to_float(r[4])
                carb_100g = self._to_float(r[5])
                prot_100g = self._to_float(r[6])
                fat_100g = self._to_float(r[7])
                fib_100g = self._to_float(r[9])

                serv_unit = str(r[42] or "serving").strip() if len(r) > 42 else "serving"
                serv_kcal = self._to_float(r[44]) if len(r) > 44 else None
                serv_carb = self._to_float(r[45]) if len(r) > 45 else None
                serv_prot = self._to_float(r[46]) if len(r) > 46 else None
                serv_fat = self._to_float(r[47]) if len(r) > 47 else None
                serv_fib = self._to_float(r[49]) if len(r) > 49 else None

                # Compute estimated serving weight in grams
                serving_weight_g = 100.0
                if serv_kcal and kcal_100g > 0:
                    serving_weight_g = round((serv_kcal / kcal_100g) * 100.0, 1)

                key = self._food_key("INDB", code, name)
                if key in existing_food_keys:
                    continue
                food = Food(
                    food_code=code,
                    food_name=name,
                    category="Indian Prepared Dish",
                    source="INDB",
                    serving_size=1.0,
                    serving_unit=serv_unit,
                    weight_g=serving_weight_g,
                    energy_kcal=kcal_100g,
                    protein_g=prot_100g,
                    carbohydrate_g=carb_100g,
                    fat_g=fat_100g,
                    fiber_g=fib_100g,
                    unit_serving_energy_kcal=serv_kcal,
                    unit_serving_protein_g=serv_prot,
                    unit_serving_carbohydrate_g=serv_carb,
                    unit_serving_fat_g=serv_fat,
                    unit_serving_fiber_g=serv_fib,
                    is_custom=False
                )
                db.add(food)
                existing_food_keys.add(key)
                counts["indb_recipes"] += 1

            db.flush()

        # 5. Ingest Units.xlsx Conversions
        units_path = os.path.join(self.indb_dir, "Units.xlsx")
        if os.path.exists(units_path):
            wb = openpyxl.load_workbook(units_path, read_only=True, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            current_food = None
            for r in rows[1:]:
                if r[0]:
                    current_food = str(r[0]).strip()
                unit_str = str(r[1]).strip() if r[1] else ""
                equiv_str = str(r[2]).strip() if len(r) > 2 and r[2] else ""
                if not current_food or not unit_str:
                    continue

                # parse grams
                grams = self._extract_grams_val(equiv_str or unit_str)
                if grams:
                    key = self._conversion_key(current_food, unit_str, "Units.xlsx")
                    if key in existing_conversion_keys:
                        continue
                    conv = FoodUnitConversion(
                        food_name_pattern=current_food,
                        unit_name=unit_str,
                        grams_equivalent=grams,
                        source="Units.xlsx",
                        is_density_based=True
                    )
                    db.add(conv)
                    existing_conversion_keys.add(key)
                    counts["conversions"] += 1

            db.flush()

        db.commit()
        total_foods = counts["icmr_nin"] + counts["uk_fct"] + counts["us_fct"] + counts["indb_recipes"]
        logger.info(f"Ingestion completed: {total_foods} foods and {counts['conversions']} conversions loaded.")
        return {"foods_loaded": total_foods, "conversions_loaded": counts["conversions"], "details": counts}

    @staticmethod
    def _food_key(source: str, food_code: Optional[str], food_name: str) -> tuple[str, str]:
        code_or_name = str(food_code or "").strip() or food_name.strip().casefold()
        return source, code_or_name

    @staticmethod
    def _conversion_key(
        food_name_pattern: Optional[str],
        unit_name: Optional[str],
        source: Optional[str],
    ) -> tuple[str, str, str]:
        return (
            (food_name_pattern or "").strip().casefold(),
            (unit_name or "").strip().casefold(),
            (source or "").strip().casefold(),
        )

    @staticmethod
    def _to_float(val: Any) -> float:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip().lower()
        if val_str in ("tr", "trace", "n", "na", "", "none"):
            return 0.0
        try:
            return float(val_str)
        except ValueError:
            return 0.0

    @staticmethod
    def _extract_grams_val(text: str) -> Optional[float]:
        import re
        m = re.search(r"([\d\.]+)\s*(?:g|gm|grams?|ml)\b", text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
        return None

indb_pipeline = INDBIngestionPipeline()
