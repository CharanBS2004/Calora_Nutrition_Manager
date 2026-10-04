import json
import re
from typing import Any, Dict, List, Optional

from app.services.llm_client import openrouter_client


MEAL_PARSER_PROMPT = """Extract foods, quantities, explicit units, and meal type from the user's message.
Return only JSON with this shape:
{"meal_type": null, "items": [{"food_query": "food name", "quantity": null, "unit": null}]}
Use null when quantity or an explicitly stated unit is missing. Do not infer a food variant,
serving size, unit, or nutrition value. Return each food mentioned exactly once and do not invent
additional foods or duplicate an item. Keep separate foods as separate items. Use context only to
resolve references such as "that one"; never add facts that are not in the message/context.
Nutrition facts are not your responsibility."""


class NutritionAI:
    def parse_meal(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        parsed = openrouter_client.complete_json(
            MEAL_PARSER_PROMPT,
            json.dumps({"message": message, "context": context or {}}, ensure_ascii=False),
        )
        raw_items = parsed.get("items")
        items = self.normalize_meal_items(raw_items)

        meal_type = parsed.get("meal_type")
        return {
            "meal_type": meal_type.strip().lower() if isinstance(meal_type, str) and meal_type.strip() else None,
            "items": items,
        }

    @staticmethod
    def normalize_meal_items(raw_items: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw_items, list):
            raise ValueError("The language model response did not include a valid item list.")

        items = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            food_query = raw.get("food_query")
            if not isinstance(food_query, str) or not food_query.strip():
                continue
            quantity = raw.get("quantity")
            if quantity is not None:
                try:
                    quantity = float(quantity)
                except (TypeError, ValueError) as exc:
                    raise ValueError("The language model returned an invalid food quantity.") from exc
                if quantity <= 0:
                    raise ValueError("The language model returned a non-positive food quantity.")
            unit = raw.get("unit")
            if unit is not None and not isinstance(unit, str):
                raise ValueError("The language model returned an invalid food unit.")
            items.append({
                "food_query": food_query.strip(),
                "quantity": quantity,
                "unit": unit.strip() if unit and unit.strip() else None,
            })

        return items

    def plan_coach_tools(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        available_tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        parsed = openrouter_client.complete_json(
            """Understand the user's request and choose only the necessary read-only tools from the
supplied list. Return JSON {"tool_calls":[{"name":"tool_name","arguments":{}}]}.
For any question about a named food's nutrition or ingredients, call search_food using the food
name; do not add a category filter unless the user explicitly named a category. For follow-up
questions, use conversation context to resolve which food they mean and search it again if needed.
For broad food recommendations such as high-protein snacks, call search_food with the requested
food class (for example, "high-protein Indian snacks") and use the returned dataset records instead
of treating a phrase search miss as proof that no options exist.
Do not invent IDs, dates, foods, or nutrition facts. Never request write/delete tools or include
user_id/database arguments in tool arguments.""",
            json.dumps({
                "message": message,
                "context": context or {},
                "available_tools": available_tools,
            }, ensure_ascii=False, default=str),
        )
        calls = parsed.get("tool_calls")
        if not isinstance(calls, list):
            raise ValueError("The language model response did not include valid tool calls.")
        return [call for call in calls if isinstance(call, dict)]

    def write_coach_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        reflection: Dict[str, Any],
    ) -> str:
        reply = openrouter_client.complete_text(
            """Reply like a warm, conversational nutrition coach, not a dashboard or report.
Answer the user's actual question directly in one or two short sentences. For broad questions such
as "How am I doing?", give a high-level qualitative summary only: do not include digits, calorie or
macro counts, percentages, meal counts, specific goal progress, missed-meal status, or energy-balance
calculations, or say that the user has eaten more or less than expected. Keep it encouraging and
general, and offer to share details if useful (for example: "You're making a start with tracking
today. I can share a more detailed update if you'd like."). Include exact numbers only when the user
explicitly asks for a quantity, target, count, or calculation. Do not add unsolicited meal
suggestions, warnings, or lists. Use the account name from trusted context if the user asks their
name. Respect any dietary preference in trusted context when suggesting foods: vegetarian excludes
meat, fish, seafood, and eggs; vegan excludes animal-derived foods. Do not override the saved
preference.

Use only facts supported by the supplied tool results, reflection data, or trusted context. For a
food nutrition question, answer from the matching dataset record, state its serving basis (such as
per 100 g or its listed serving), then ask about quantity only if needed. If several preparations
match, briefly distinguish the dataset options or ask which one they mean; do not combine their
values. Never invent or estimate nutrition, meals, goals, or personal details. If the requested data
is absent, say the dataset did not return a match and ask for another name; do not fill the gap with
general nutrition knowledge. For a broad food recommendation, present a few matching records
returned by the search tool and include their recorded protein values with the correct per-100 g or
listed-serving basis; prefer the recorded per-serving value and name its serving unit when present.
When a result includes a selection note about missing category labels, you
must state that limitation before presenting the options and describe them as matching dataset
records, not as records formally tagged with that category. Never turn missing category metadata
into a claim that the dataset has no relevant foods. If ambiguous, ask one relevant follow-up
question.""",
            json.dumps({
                "message": message,
                "context": context or {},
                "tool_results": tool_results,
                "reflection": reflection,
            }, ensure_ascii=False, default=str),
        )
        has_unclassified_snack_results = any(
            "no explicit snack classification" in str(
                result.get("result", {}).get("selection_note", "")
            ).casefold()
            for result in tool_results
            if isinstance(result.get("result"), dict)
        )
        response_mentions_limit = re.search(
            r"dataset.{0,60}(?:does not|doesn't|has no|not).{0,40}(?:label|classif|categor)",
            reply.casefold(),
        )
        if has_unclassified_snack_results and not response_mentions_limit:
            reply = (
                "The dataset does not explicitly label a snack category; these are matching "
                f"prepared-dish records. {reply}"
            )
        return reply


nutrition_ai = NutritionAI()
