import json
from typing import Any, Dict, List

import httpx

from app.core.config import settings


class LLMConfigurationError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


class OpenRouterClient:
    def _request(self, messages: List[Dict[str, str]], json_response: bool) -> str:
        if settings.LLM_PROVIDER.lower() != "openrouter":
            raise LLMConfigurationError("Set LLM_PROVIDER=openrouter to enable the configured language model.")
        if not settings.LLM_API_KEY:
            raise LLMConfigurationError("Set LLM_API_KEY in backend/.env to enable OpenRouter.")

        payload: Dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
        }
        if json_response:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = httpx.post(
                settings.LLM_API_BASE_URL.rstrip("/") + "/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/",
                    "X-Title": "CALORA Nutrition Coach",
                },
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMResponseError("OpenRouter did not return a usable response.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMResponseError("OpenRouter returned an empty response.")
        return content.strip()

    def complete_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        content = self._request([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], json_response=True)
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseError("OpenRouter returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise LLMResponseError("OpenRouter JSON response must be an object.")
        return result

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        return self._request([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ], json_response=False)


openrouter_client = OpenRouterClient()
