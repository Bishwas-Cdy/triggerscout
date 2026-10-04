import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas import LLMClassification
from app.services.diff import ChangeCandidate


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Small OpenAI-compatible client with a validated structured boundary."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self._settings.openai_api_key)

    async def classify(
        self, company_name: str, candidate: ChangeCandidate
    ) -> LLMClassification | None:
        if not self.enabled:
            return None
        prompt = (
            "Classify this company webpage change as a GTM trigger. Return JSON only with "
            "trigger, confidence (0-1), significance (low|medium|high), why_it_matters, and "
            "recommended_action. Use only evidence shown; do not speculate.\n"
            f"Company: {company_name}\nRemoved: {candidate.before_excerpt}\n"
            f"Added: {candidate.after_excerpt}"
        )
        payload: dict[str, Any] = {
            "model": self._settings.openai_model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a conservative GTM signal classifier."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self._settings.openai_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_timeout_seconds) as client:
                response = await client.post(
                    f"{self._settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise LLMError("LLM content was not text")
            cleaned = content.strip().removeprefix("```json").removesuffix("```").strip()
            return LLMClassification.model_validate(json.loads(cleaned))
        except (
            httpx.HTTPError,
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise LLMError("Invalid LLM response") from exc
