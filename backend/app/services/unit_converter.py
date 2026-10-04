import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import openpyxl

from app.core.config import PROJECT_ROOT
from app.services.food_lookup import dataset_unit_conversions, normalize_unit


class UnitConverter:
    """Convert quantities only when the unit is physical mass or present in Units.xlsx."""

    def __init__(self, indb_dir: Optional[str] = None):
        self.indb_dir = indb_dir or os.environ.get(
            "INDB_DATASET_DIR", str(PROJECT_ROOT / "DATASET" / "INDB")
        )
        self.specific_conversions: Dict[str, Dict[str, float]] = {}
        self._load_units_xlsx()

    @staticmethod
    def _food_key(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]", "", value).lower()

    @staticmethod
    def _extract_grams(text: str) -> Optional[float]:
        match = re.search(r"([\d.]+)\s*(?:g|gm|grams?)\b", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    def _load_units_xlsx(self) -> None:
        units_path = Path(self.indb_dir) / "Units.xlsx"
        if not units_path.is_file():
            return

        workbook = openpyxl.load_workbook(units_path, read_only=True, data_only=True)
        try:
            sheet = workbook.active
            current_food = None
            for row in sheet.iter_rows(min_row=2, values_only=True):
                food_cell = row[0] if row else None
                unit_cell = row[1] if len(row) > 1 else None
                equivalent_cell = row[2] if len(row) > 2 else None
                if food_cell:
                    current_food = str(food_cell).strip()
                if not current_food or not unit_cell or not equivalent_cell:
                    continue

                grams = self._extract_grams(str(equivalent_cell))
                unit = normalize_unit(str(unit_cell))
                if grams is None or grams <= 0 or not unit:
                    continue
                key = self._food_key(current_food)
                self.specific_conversions.setdefault(key, {})[unit] = grams
        finally:
            workbook.close()

    def convert_to_grams(
        self,
        food_name: str,
        quantity: float,
        unit: str,
        category: Optional[str] = None,
        db=None,
        serving_unit: Optional[str] = None,
        serving_weight_g: Optional[float] = None,
    ) -> Tuple[float, bool, float, str]:
        if quantity <= 0:
            return 0.0, True, 1.0, "Zero quantity"

        normalized_unit = normalize_unit(unit)
        if normalized_unit in ("g", "gram", "grams"):
            return float(quantity), True, 1.0, "Exact mass in grams"
        if normalized_unit in ("kg", "kilogram", "kilograms"):
            return float(quantity * 1000.0), True, 1.0, "Exact mass in kilograms"

        if db is not None:
            from app.models.entities import Food

            candidates = db.query(Food).filter(Food.food_name == food_name).all()
            for food in candidates:
                for dataset_unit, grams_per_unit in dataset_unit_conversions(db, food):
                    if normalized_unit == normalize_unit(dataset_unit):
                        return (
                            round(quantity * grams_per_unit, 2),
                            True,
                            1.0,
                            f"Units.xlsx conversion: 1 {dataset_unit} = {grams_per_unit}g",
                        )

        food_key = self._food_key(food_name)
        for dataset_food, conversions in self.specific_conversions.items():
            if dataset_food and dataset_food == food_key:
                grams_per_unit = conversions.get(normalized_unit)
                if grams_per_unit is not None:
                    return (
                        round(quantity * grams_per_unit, 2),
                        True,
                        1.0,
                        f"Units.xlsx conversion: 1 {unit} = {grams_per_unit}g",
                    )

        return 0.0, False, 0.0, f"Unit '{unit}' has no conversion for '{food_name}' in the dataset."


unit_converter = UnitConverter()
