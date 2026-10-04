import re
import unicodedata
from functools import lru_cache
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Tuple

import openpyxl
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Food


_IGNORED_TOKENS = {
    "a", "an", "and", "ate", "eaten", "for", "had", "have", "i", "of",
    "some", "the", "with", "food", "please", "log", "meal", "my",
}
_FOOD_DESCRIPTORS = {
    "big", "small", "large", "red", "green", "ripe", "hybrid", "brown",
    "skin", "raw", "fresh", "whole", "cow", "buffalo", "spice", "spices",
}


def _tokens(value: str) -> List[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", normalized)
    result = []
    for word in words:
        if word in _IGNORED_TOKENS or word.isdigit():
            continue
        if word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("s") and not word.endswith(("ss", "us")) and len(word) > 3:
            word = word[:-1]
        result.append(word)
    return result


def _token_score(query_token: str, food_tokens: List[str]) -> float:
    if query_token in food_tokens:
        return 1.0
    return max((SequenceMatcher(None, query_token, token).ratio() for token in food_tokens), default=0.0)


def _label_key(value: str) -> str:
    without_parenthetical = re.sub(r"\([^)]*\)", "", value)
    return " ".join(sorted(_tokens(without_parenthetical)))


def _scientific_name(value: str) -> str:
    match = re.search(r"\(([A-Z][a-z]+ [a-z]+)\)", value)
    return match.group(1).casefold() if match else ""


def _ingredient_labels_match(reference: str, food_name: str) -> bool:
    if _scientific_name(reference) and _scientific_name(reference) == _scientific_name(food_name):
        return True

    reference_key = _label_key(reference)
    if not reference_key:
        return False
    food_parts = re.split(r"\s*/\s*", food_name)
    if any(reference_key == _label_key(part) for part in food_parts):
        return True

    reference_tokens = set(_tokens(re.sub(r"\([^)]*\)", "", reference)))
    food_tokens = set(_tokens(re.sub(r"\([^)]*\)", "", food_name)))
    if reference_tokens == food_tokens:
        return True
    return (
        reference_tokens - _FOOD_DESCRIPTORS
        == food_tokens - _FOOD_DESCRIPTORS
        and (reference_tokens | food_tokens) - (reference_tokens & food_tokens)
        <= _FOOD_DESCRIPTORS
    )


def _equivalent_food_key(food: Food) -> tuple:
    return (
        food.food_name.strip().casefold(),
        food.serving_size,
        food.serving_unit.strip().casefold(),
        food.weight_g,
        food.energy_kcal,
        food.protein_g,
        food.carbohydrate_g,
        food.fat_g,
        food.fiber_g,
        food.unit_serving_energy_kcal,
        food.unit_serving_protein_g,
        food.unit_serving_carbohydrate_g,
        food.unit_serving_fat_g,
        food.unit_serving_fiber_g,
        food.micronutrients_json,
    )


def _deduplicate_equivalent_foods(foods: List[Food]) -> List[Food]:
    source_priority = {
        "icmr_nin_2017": 0,
        "indb": 1,
        "uk_fct": 2,
        "us_fct": 3,
    }
    unique = {}
    for food in sorted(
        foods,
        key=lambda candidate: (
            source_priority.get((candidate.source or "").casefold(), 4),
            (candidate.food_code or "").casefold(),
            candidate.id or 0,
        ),
    ):
        unique.setdefault(_equivalent_food_key(food), food)
    return list(unique.values())


@lru_cache(maxsize=4)
def _recipe_ingredient_references(dataset_dir: str) -> dict:
    path = Path(dataset_dir) / "recipes.xlsx"
    if not path.is_file():
        return {}

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        rows = worksheet.iter_rows(values_only=True)
        headers = next(rows, ())
        columns = {str(name).strip(): index for index, name in enumerate(headers) if name}
        required = {"ingredient_name_org", "food_name", "food_code"}
        if not required.issubset(columns):
            raise ValueError(f"{path} is missing recipe ingredient columns: {sorted(required - columns)}")

        references = {}
        for row in rows:
            ingredient = row[columns["ingredient_name_org"]]
            food_name = row[columns["food_name"]]
            food_code = row[columns["food_code"]]
            if not ingredient or not food_name:
                continue
            entry = (str(food_name).strip(), str(food_code).strip() if food_code else None)
            references.setdefault(_label_key(str(food_name)), set()).add(entry)
            if _ingredient_labels_match(str(ingredient), str(food_name)):
                references.setdefault(_label_key(str(ingredient)), set()).add(entry)
        return {key: sorted(entries) for key, entries in references.items()}
    finally:
        workbook.close()


def resolve_recipe_food(
    db: Session,
    food_name: str,
    food_id: int = None,
    food_code: str = None,
) -> Food:
    """Resolve an ingredient through explicit IDs/codes, then dataset recipe names."""
    if food_id is not None:
        food = db.query(Food).filter(Food.id == food_id).first()
        if food is None or food.is_custom:
            raise ValueError(f"Food record {food_id} is not present in the nutrition dataset.")
        return food

    clean_name = food_name.strip()
    references = [clean_name]
    codes = [food_code] if food_code else []
    alias_entries = _recipe_ingredient_references(settings.INDB_DATASET_DIR).get(
        _label_key(clean_name), []
    )
    for reference_name, reference_code in alias_entries:
        if reference_name not in references:
            references.append(reference_name)
        if reference_code and reference_code not in codes:
            codes.append(reference_code)

    dataset_foods = db.query(Food).filter(Food.is_custom.is_(False)).all()
    by_code = [
        food for code in codes
        for food in dataset_foods
        if food.food_code == code
        and any(_ingredient_labels_match(reference, food.food_name) for reference in references)
    ]
    by_code = list({food.id: food for food in by_code}.values())
    by_code = _deduplicate_equivalent_foods(by_code)
    if len(by_code) == 1:
        return by_code[0]
    if len(by_code) > 1:
        candidates = by_code
    else:
        candidates = [
            food for food in dataset_foods
            if any(_ingredient_labels_match(reference, food.food_name) for reference in references)
        ]
        candidates = list({food.id: food for food in candidates}.values())
    candidates = _deduplicate_equivalent_foods(candidates)

    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        names = ", ".join(
            f"{food.food_name} [source={food.source}, code={food.food_code or 'n/a'}]"
            for food in sorted(candidates, key=lambda candidate: candidate.food_name.casefold())
        )
        raise ValueError(
            f"Could not reliably map '{clean_name}' to one nutrition dataset record. "
            f"Matching records: {names}."
        )
    raise ValueError(
        f"Could not reliably map '{clean_name}' to a nutrition dataset record; "
        "no compatible record or dataset recipe reference was found."
    )


def find_food_matches(db: Session, query: str) -> List[Tuple[Food, float]]:
    """Find dataset records matching every meaningful token in a food name."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    matches = []
    foods = db.query(Food).filter(Food.is_custom.is_(False)).all()
    for food in foods:
        food_tokens = _tokens(food.food_name)
        scores = [_token_score(token, food_tokens) for token in query_tokens]
        if scores and all(score >= 0.82 for score in scores):
            matches.append((food, sum(scores) / len(scores)))

    matches.sort(key=lambda result: (
        -result[1],
        len(_tokens(result[0].food_name)),
        result[0].food_name.casefold(),
    ))
    return matches


def normalize_unit(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().strip()
    normalized = re.sub(r"^\s*\d+(?:\.\d+)?\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def dataset_unit_conversions(db: Session, food: Food) -> List[Tuple[str, float]]:
    """Return only household-unit conversions explicitly imported from Units.xlsx."""
    from app.models.entities import FoodUnitConversion

    food_tokens = _tokens(food.food_name)
    conversions = db.query(FoodUnitConversion).filter(
        FoodUnitConversion.food_name_pattern.isnot(None)
    ).all()
    ranked = []
    for conversion in conversions:
        pattern_tokens = _tokens(conversion.food_name_pattern or "")
        if not pattern_tokens:
            continue
        score = sum(_token_score(token, food_tokens) for token in pattern_tokens) / len(pattern_tokens)
        if all(_token_score(token, food_tokens) >= 0.82 for token in pattern_tokens):
            ranked.append((score, conversion))

    if not ranked:
        return []

    best_score = max(score for score, _ in ranked)
    best = [conversion for score, conversion in ranked if score == best_score]
    units = {}
    for conversion in best:
        unit = normalize_unit(conversion.unit_name)
        grams = float(conversion.grams_equivalent)
        if unit:
            units.setdefault(unit, set()).add(grams)
    return [
        (unit, next(iter(gram_values)))
        for unit, gram_values in units.items()
        if len(gram_values) == 1
    ]
