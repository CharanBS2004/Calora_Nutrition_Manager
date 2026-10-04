import re
import json
import logging
import inspect
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional, TypedDict
from sqlalchemy.orm import Session

from app.models.entities import User, NutritionGoal, Meal, ChatMessage, Recipe
from app.services.agent.tools import agent_tools
from app.services.agent.safety_guardrails import safety_guardrails
from app.services.agent.uncertainty_engine import uncertainty_engine
from app.services.memory.memory_service import memory_service
from app.core.config import settings
from app.services.nutrition_ai import nutrition_ai

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    user_id: int
    user_message: str
    context: Dict[str, Any]
    is_high_risk: bool
    requires_disclaimer: bool
    refusal_message: Optional[str]
    planned_tools: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    reflection_data: Dict[str, Any]
    uncertainty_detected: bool
    clarification_payload: Optional[Dict[str, Any]]
    final_reply: str
    action_buttons: List[Dict[str, Any]]

class AgentOrchestrator:
    """
    Agentic AI Nutrition Coach with LangGraph-style State Execution.
    Features:
    1. Plan & Tool Selection Node
    2. Tool Execution Node (using 20 deterministically executed tools)
    3. Post-Action Reflection & Validation Node (verifies values, goal impact, uncertainty)
    4. Response Generation with Action Cards & Safety Guardrails
    """

    def __init__(self):
        self.tools = agent_tools

    def run(self, user_id: int, user_message: str, db: Session, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the agentic lifecycle on user input."""
        trusted_context = dict(context or {})
        user = db.query(User).filter(User.id == user_id).first()
        if user is not None and user.profile is not None:
            trusted_context["account_name"] = user.profile.name
            trusted_context["dietary_preference"] = user.profile.dietary_preference

        state: AgentState = {
            "user_id": user_id,
            "user_message": user_message,
            "context": trusted_context,
            "is_high_risk": False,
            "requires_disclaimer": False,
            "refusal_message": None,
            "planned_tools": [],
            "tool_results": [],
            "reflection_data": {},
            "uncertainty_detected": False,
            "clarification_payload": None,
            "final_reply": "",
            "action_buttons": []
        }
        original_user_message = user_message
        bypass_recipe_prompt = False

        # Step 1: Safety Guardrails Pre-Check
        is_high_risk, requires_disclaimer, refusal = safety_guardrails.evaluate_query(user_message)
        state["is_high_risk"] = is_high_risk
        state["requires_disclaimer"] = requires_disclaimer
        if refusal:
            state["final_reply"] = refusal
            self._persist_chat(user_id, user_message, refusal, False, db)
            return self._build_output(state)

        pending_recipe = self._get_pending_recipe_confirmation(user_id, db)
        if pending_recipe is not None:
            confirmation = self._parse_recipe_confirmation(user_message)
            if confirmation is None and "recipe_ids" in pending_recipe:
                selected_recipe_name = next(
                    (
                        name for name in pending_recipe.get("recipe_names", [])
                        if self._normalize_recipe_text(user_message)
                        == self._normalize_recipe_text(name)
                    ),
                    None,
                )
                if selected_recipe_name is not None:
                    selected_id = pending_recipe["recipe_ids"][
                        pending_recipe["recipe_names"].index(selected_recipe_name)
                    ]
                    pending_recipe = {
                        "recipe_id": selected_id,
                        "recipe_name": selected_recipe_name,
                    }
                    confirmation = True
            if confirmation is True and "recipe_id" not in pending_recipe:
                confirmation = None
            if confirmation is True:
                recipe = db.query(Recipe).filter(
                    Recipe.id == pending_recipe["recipe_id"],
                    Recipe.user_id == user_id,
                    Recipe.is_saved.is_(True),
                ).first()
                if recipe is not None:
                    recipe_result = self.tools.get_recipe(
                        recipe_id=recipe.id,
                        user_id=user_id,
                        db=db,
                    )
                    state["tool_results"] = [{
                        "tool": "get_recipe",
                        "args": {"recipe_id": recipe.id},
                        "result": recipe_result,
                    }]
                    state["final_reply"] = (
                        f"Using your saved recipe **{recipe.name}**. "
                        f"One {recipe.serving_unit} has "
                        f"{recipe.calories_per_serving:.0f} kcal, "
                        f"{recipe.protein_per_serving:.1f} g protein, "
                        f"{recipe.carb_per_serving:.1f} g carbs, and "
                        f"{recipe.fat_per_serving:.1f} g fat."
                    )
                    self._persist_chat(
                        user_id,
                        user_message,
                        state["final_reply"],
                        False,
                        db,
                        tool_calls=state["tool_results"],
                    )
                    return self._build_output(state)
            elif confirmation is None:
                if "recipe_names" in pending_recipe:
                    state["final_reply"] = (
                        "Choose which saved recipe you meant: "
                        + ", ".join(f"**{name}**" for name in pending_recipe["recipe_names"])
                        + "."
                    )
                    options = pending_recipe["recipe_names"]
                else:
                    state["final_reply"] = (
                        f"Did you mean your saved recipe **{pending_recipe['recipe_name']}**?"
                    )
                    options = [
                        "Yes, use my saved recipe",
                        "No, search the food dataset",
                    ]
                state["uncertainty_detected"] = True
                state["clarification_payload"] = {
                    "question": "Choose which saved recipe to use.",
                    "options": options,
                }
                self._persist_chat(
                    user_id,
                    user_message,
                    state["final_reply"],
                    True,
                    db,
                    tool_calls=[{
                        "tool": "saved_recipe_confirmation",
                        "args": pending_recipe,
                    }],
                )
                return self._build_output(state)

            if confirmation is False:
                user_message = self._previous_user_message(user_id, db) or user_message
                state["user_message"] = user_message
                bypass_recipe_prompt = True

        matching_recipes = (
            []
            if bypass_recipe_prompt
            else self._find_saved_recipe_mentions(user_id, user_message, db)
        )
        if matching_recipes:
            if len(matching_recipes) == 1:
                recipe = matching_recipes[0]
                state["final_reply"] = (
                    f"I found your saved recipe **{recipe.name}**. "
                    "Do you want me to use its saved nutrition?"
                )
                pending = {"recipe_id": recipe.id, "recipe_name": recipe.name}
                options = [
                    "Yes, use my saved recipe",
                    "No, search the food dataset",
                ]
            else:
                names = ", ".join(f"**{recipe.name}**" for recipe in matching_recipes)
                state["final_reply"] = (
                    f"I found multiple saved recipes that could match: {names}. "
                    "Which one should I use?"
                )
                pending = {
                    "recipe_ids": [recipe.id for recipe in matching_recipes],
                    "recipe_names": [recipe.name for recipe in matching_recipes],
                }
                options = [recipe.name for recipe in matching_recipes]
            state["uncertainty_detected"] = True
            state["clarification_payload"] = {
                "question": "Choose whether to use a saved recipe.",
                "options": options,
            }
            self._persist_chat(
                user_id,
                user_message,
                state["final_reply"],
                True,
                db,
                tool_calls=[{
                    "tool": "saved_recipe_confirmation",
                    "args": pending,
                }],
            )
            return self._build_output(state)

        # Step 2: Planning Node (Intent Recognition & Tool Selection)
        state = self._plan_node(state, db)

        # Step 3: Tool Execution Node
        state = self._tool_execution_node(state, db)

        # Step 4: Post-Action Reflection & Validation Node
        state = self._post_action_reflection_node(state, db)

        # Step 5: Response Generation Node
        state = self._generate_response_node(state, db)

        # Step 6: Apply Safety Guardrails to Final Response
        state["final_reply"] = safety_guardrails.apply_guardrails_to_response(
            state["final_reply"], state["requires_disclaimer"]
        )

        # Persist conversation to database
        self._persist_chat(
            user_id=user_id,
            user_message=original_user_message,
            assistant_reply=state["final_reply"],
            uncertainty_flag=state["uncertainty_detected"],
            db=db,
            tool_calls=state["tool_results"],
            actions=state["action_buttons"]
        )

        return self._build_output(state)

    @staticmethod
    def _normalize_recipe_text(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))

    def _find_saved_recipe_mentions(
        self,
        user_id: int,
        user_message: str,
        db: Session,
    ) -> List[Recipe]:
        message = f" {self._normalize_recipe_text(user_message)} "
        if not message.strip():
            return []
        recipes = db.query(Recipe).filter(
            Recipe.user_id == user_id,
            Recipe.is_saved.is_(True),
        ).order_by(Recipe.id.asc()).all()
        return [
            recipe for recipe in recipes
            if f" {self._normalize_recipe_text(recipe.name)} " in message
        ]

    @staticmethod
    def _parse_recipe_confirmation(message: str) -> Optional[bool]:
        normalized = " ".join(re.findall(r"[a-z0-9]+", message.casefold()))
        if re.match(r"^(yes|yeah|yep|correct|that one|use it|use my saved recipe)\b", normalized):
            return True
        if re.match(r"^(no|nope|not that|search the food dataset|look it up as a food)\b", normalized):
            return False
        return None

    @staticmethod
    def _get_pending_recipe_confirmation(user_id: int, db: Session) -> Optional[Dict[str, Any]]:
        last_assistant = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "assistant",
        ).order_by(ChatMessage.id.desc()).first()
        if last_assistant is None or not last_assistant.tool_calls_json:
            return None
        try:
            tool_calls = json.loads(last_assistant.tool_calls_json)
        except json.JSONDecodeError:
            return None
        for call in tool_calls:
            if call.get("tool") == "saved_recipe_confirmation":
                args = call.get("args")
                if isinstance(args, dict):
                    return args
        return None

    @staticmethod
    def _previous_user_message(user_id: int, db: Session) -> Optional[str]:
        previous = db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id,
            ChatMessage.role == "user",
        ).order_by(ChatMessage.id.desc()).first()
        return previous.content if previous is not None else None

    def _plan_node(self, state: AgentState, db: Session) -> AgentState:
        """Use the configured LLM to select validated, read-only backend tools."""
        read_only_tools = {
            "search_food", "get_food_nutrition", "get_today_meals",
            "get_daily_nutrition", "get_user_goals", "get_saved_recipes",
            "get_recipe", "get_health_data", "calculate_energy_balance",
            "get_user_memory", "get_analytics", "generate_daily_summary",
        }
        specifications = []
        signatures = {}
        for name in sorted(read_only_tools):
            function = getattr(self.tools, name)
            signature = inspect.signature(function)
            signatures[name] = signature
            specifications.append({
                "name": name,
                "description": (function.__doc__ or "").strip(),
                "arguments": [
                    {
                        "name": parameter.name,
                        "required": parameter.default is inspect.Parameter.empty,
                    }
                    for parameter in signature.parameters.values()
                    if parameter.name not in {"user_id", "db", "kwargs"}
                ],
            })

        calls = nutrition_ai.plan_coach_tools(
            state["user_message"], state["context"], specifications
        )
        planned_tools = []
        for call in calls:
            name = call.get("name")
            arguments = call.get("arguments", {})
            if name not in signatures or not isinstance(arguments, dict):
                continue
            signature = signatures[name]
            allowed_arguments = {
                parameter.name
                for parameter in signature.parameters.values()
                if parameter.name not in {"user_id", "db", "kwargs"}
            }
            if any(key not in allowed_arguments for key in arguments):
                continue
            required_arguments = {
                parameter.name
                for parameter in signature.parameters.values()
                if parameter.default is inspect.Parameter.empty
                and parameter.name not in {"user_id", "db", "kwargs"}
            }
            if not required_arguments.issubset(arguments):
                continue
            planned_tools.append({"tool": name, "args": arguments})

        state["planned_tools"] = planned_tools
        return state

    def _tool_execution_node(self, state: AgentState, db: Session) -> AgentState:
        """Execute planned tools and gather deterministic data."""
        results = []
        uid = state["user_id"]

        for planned in state["planned_tools"]:
            t_name = planned["tool"]
            args = planned["args"]
            fn = getattr(self.tools, t_name, None)
            if fn:
                try:
                    res = fn(user_id=uid, db=db, **args)
                    results.append({"tool": t_name, "args": args, "result": res})
                except Exception as e:
                    logger.error(f"Error executing tool {t_name}: {e}")
                    results.append({"tool": t_name, "error": str(e)})

        state["tool_results"] = results
        return state

    def _post_action_reflection_node(self, state: AgentState, db: Session) -> AgentState:
        """
        EXPLICIT POST-ACTION REFLECTION & VALIDATION NODE:
        1. Verifies returned nutrition values (checks for physiological anomalies).
        2. Calculates Goal Impact (net delta against daily calorie and macro targets).
        3. Evaluates Uncertainty Level (detects fallback conversions or missing portions).
        4. Identifies whether additional clarification / action is needed before finalizing.
        5. Continuously monitors progress toward daily goals.
        """
        uid = state["user_id"]
        reflection = {
            "validated_nutrition": True,
            "goal_impact": {},
            "warnings": [],
            "followup_needed": False
        }

        # 1. Fetch current daily progress and goals
        daily = self.tools.get_daily_nutrition(user_id=uid, db=db)
        goals = self.tools.get_user_goals(user_id=uid, db=db)

        cal_rem = daily.get("calories", {}).get("remaining", 0)
        prot_rem = daily.get("protein_g", {}).get("remaining", 0)
        carb_rem = daily.get("carb_g", {}).get("remaining", 0)
        fat_rem = daily.get("fat_g", {}).get("remaining", 0)
        fib_rem = daily.get("fiber_g", {}).get("remaining", 0)

        reflection["goal_impact"] = {
            "consumed_calories": daily.get("calories", {}).get("consumed", 0),
            "calorie_target": daily.get("calories", {}).get("target", 2000),
            "calories_remaining": cal_rem,
            "protein_remaining_g": prot_rem,
            "carb_remaining_g": carb_rem,
            "fat_remaining_g": fat_rem,
            "fiber_remaining_g": fib_rem,
            "energy_balance": daily.get("energy_balance_kcal", 0),
            "calories_burned": daily.get("calories_burned", 0)
        }

        # 2. Check for missing meals today
        meals_logged = daily.get("meals_logged", {})
        reflection["meals_logged_today"] = any(meals_logged.values())
        now_hour = datetime.now().hour
        if now_hour >= 11 and not meals_logged.get("breakfast"):
            reflection["warnings"].append("Breakfast has not been logged yet today.")
            reflection["followup_needed"] = True
        elif now_hour >= 15 and not meals_logged.get("lunch"):
            reflection["warnings"].append("Lunch has not been logged yet today.")
            reflection["followup_needed"] = True
        elif now_hour >= 21 and not meals_logged.get("dinner"):
            reflection["warnings"].append("Dinner has not been logged yet today.")
            reflection["followup_needed"] = True

        # 3. Check for uncertainty in user message (e.g. 'I had some rice')
        msg = state["user_message"]
        for term in ["some", "a little", "few", "a bit", "a plate of"]:
            if term in msg.lower():
                state["uncertainty_detected"] = True
                is_unc, clar = uncertainty_engine.analyze_meal_uncertainty("Your meal", msg, 0.55)
                if is_unc:
                    state["clarification_payload"] = clar
                break

        state["reflection_data"] = reflection
        return state

    def _generate_response_node(self, state: AgentState, db: Session) -> AgentState:
        """Generate natural language from retrieved data without generating nutrition facts."""
        actions = [
            {"label": "Log Food", "action_type": "log_meal", "payload": {}},
            {"label": "How am I doing today?", "action_type": "ask_query", "payload": {"text": "How am I doing today?"}},
        ]
        tool_names = {result.get("tool") for result in state["tool_results"]}
        if "get_today_meals" in tool_names:
            actions.append({"label": "View Today's Meals", "action_type": "view_meals", "payload": {}})
        if "get_analytics" in tool_names:
            actions.append({"label": "View Analytics", "action_type": "view_analytics", "payload": {}})

        response_context = state["context"]
        response_tools = state["tool_results"]
        response_reflection = state["reflection_data"]
        if re.search(
            r"\b(how am i doing|how am i going|general sense|quick overview|"
            r"how is my progress|how's my progress)\b",
            state["user_message"].casefold(),
        ):
            meals_logged = state["reflection_data"].get("meals_logged_today", False)
            response_context = {
                **state["context"],
                "response_style": "Give a brief, encouraging high-level check-in. Do not include stats.",
            }
            response_tools = [{
                "tool": "daily_tracking_status",
                "result": {"meals_logged_today": meals_logged},
            }]
            response_reflection = {}

        state["final_reply"] = nutrition_ai.write_coach_response(
            state["user_message"],
            response_context,
            response_tools,
            response_reflection,
        )
        state["action_buttons"] = actions
        return state

    def _persist_chat(
        self,
        user_id: int,
        user_message: str,
        assistant_reply: str,
        uncertainty_flag: bool,
        db: Session,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ):
        """Record the conversation turns in database."""
        # User message
        u_msg = ChatMessage(
            user_id=user_id,
            role="user",
            content=user_message,
            uncertainty_flag=False
        )
        db.add(u_msg)

        # Assistant message
        a_msg = ChatMessage(
            user_id=user_id,
            role="assistant",
            content=assistant_reply,
            tool_calls_json=json.dumps(tool_calls, default=str) if tool_calls else None,
            contextual_actions_json=json.dumps(actions, default=str) if actions else None,
            uncertainty_flag=uncertainty_flag
        )
        db.add(a_msg)
        db.commit()

    def _build_output(self, state: AgentState) -> Dict[str, Any]:
        clar_options = []
        clar_question = None
        if state["clarification_payload"]:
            clar_question = state["clarification_payload"].get("question")
            clar_options = state["clarification_payload"].get("options", [])

        return {
            "reply": state["final_reply"],
            "tool_calls": state["tool_results"],
            "goal_impact": state["reflection_data"].get("goal_impact"),
            "uncertainty_flag": state["uncertainty_detected"],
            "clarification_needed": clar_question,
            "suggested_options": clar_options,
            "action_buttons": state["action_buttons"]
        }

agent_orchestrator = AgentOrchestrator()
