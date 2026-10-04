import pytest

from app.services.unit_converter import unit_converter


def test_physical_mass_conversions_are_exact():
    grams, is_specific, confidence, _ = unit_converter.convert_to_grams("Any food", 250, "g")
    assert (grams, is_specific, confidence) == (250.0, True, 1.0)

    grams, is_specific, confidence, _ = unit_converter.convert_to_grams("Any food", 0.5, "kg")
    assert (grams, is_specific, confidence) == (500.0, True, 1.0)


def test_unsupported_food_unit_has_no_generic_fallback():
    grams, is_specific, confidence, note = unit_converter.convert_to_grams(
        "Unidentified Unknown Stew", 1.0, "cup"
    )
    assert (grams, is_specific, confidence) == (0.0, False, 0.0)
    assert "has no conversion" in note
