import re
from typing import Iterable, Optional


_NON_VEGETARIAN_TERMS = re.compile(
    r"\b(chicken|mutton|lamb|goat|beef|pork|bacon|ham|meat|poultry|"
    r"fish|seafood|prawn|shrimp|crab|lobster|squid|octopus|egg|eggs|"
    r"omelette|omelet|anda)\b",
    re.IGNORECASE,
)


def non_vegetarian_components(
    preference: Optional[str],
    names_and_categories: Iterable[str],
) -> list[str]:
    """Return dataset-backed components conflicting with a vegetarian preference."""
    if (preference or "").strip().casefold() not in {"vegetarian", "vegan", "jain"}:
        return []

    components = []
    has_non_vegetarian_category = False
    for value in names_and_categories:
        text = (value or "").strip()
        if not text:
            continue
        if text.casefold() == "eggs and meat":
            has_non_vegetarian_category = True
            continue
        if _NON_VEGETARIAN_TERMS.search(text):
            components.append(text)
    if has_non_vegetarian_category and not components:
        components.append("non-vegetarian food")
    return list(dict.fromkeys(components))
