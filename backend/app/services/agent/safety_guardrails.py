import re
from typing import Tuple, Optional

MEDICAL_DISCLAIMER = (
    "\n\n*Disclaimer: I am an AI nutrition and wellness coach, not a medical professional. "
    "This guidance is educational and does not constitute medical diagnosis, treatment, or clinical prescription. "
    "Please consult a qualified healthcare provider or clinical dietitian for personal medical advice.*"
)

HIGH_RISK_KEYWORDS = [
    r"\bdiagnos(?:e|is)\b",
    r"\bcure\b",
    r"\bprescrib(?:e|tion)\b",
    r"\bmedicat(?:e|ion)\b",
    r"\binsulin\b",
    r"\bdiabet(?:ic|es)\b",
    r"\bhypertension\b",
    r"\bkidney disease\b",
    r"\bheart disease\b",
    r"\bchest pain\b",
    r"\bcancer\b",
    r"\banorexi(?:a|c)\b",
    r"\bbulimi(?:a|c)\b",
    r"\bstarv(?:e|ation)\b"
]

class SafetyGuardrails:
    """
    Nutrition & Medical Safety Guardrails.
    Enforces non-medical boundaries, detects dangerous dietary restrictions,
    and appends required evidence-based disclaimers.
    """

    @classmethod
    def evaluate_query(cls, user_message: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Returns:
          (is_high_risk, requires_disclaimer, refusal_message_or_warning)
        """
        msg_lower = user_message.lower()

        # Check for explicit diagnostic/prescriptive demand
        for pattern in [r"can you diagnose", r"diagnose me", r"what medicine should i take", r"prescribe"]:
            if re.search(pattern, msg_lower):
                return True, True, (
                    "I cannot provide medical diagnoses, clinical assessments, or prescribe medications. "
                    "If you are experiencing symptoms or health concerns, please consult a qualified healthcare professional."
                    + MEDICAL_DISCLAIMER
                )

        # Check for extreme calorie starvation regimes (< 1000 kcal)
        m = re.search(r"eat(?:ing)?\s+(\d+)\s*(?:calories|kcal)", msg_lower)
        if m:
            val = int(m.group(1))
            if val < 900:
                return True, True, (
                    f"Consuming only {val} calories per day is severely below recommended physiological minimums "
                    "and can cause metabolic complications, nutrient deficiencies, and muscle loss. "
                    "Safe, sustainable nutrition generally requires at least 1,200–1,500 kcal/day for adults depending on body composition."
                    + MEDICAL_DISCLAIMER
                )

        # Check general medical terms requiring disclaimer
        requires_disclaimer = False
        for kw in HIGH_RISK_KEYWORDS:
            if re.search(kw, msg_lower):
                requires_disclaimer = True
                break

        return False, requires_disclaimer, None

    @classmethod
    def apply_guardrails_to_response(cls, response_text: str, requires_disclaimer: bool) -> str:
        if requires_disclaimer and MEDICAL_DISCLAIMER.strip() not in response_text:
            return response_text.strip() + MEDICAL_DISCLAIMER
        return response_text

safety_guardrails = SafetyGuardrails()
