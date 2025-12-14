import logging
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)


class LLMService:
    """Простий клієнт до Ollama для чат-запитів із вбудованою підказкою."""

    def __init__(self, base_url: str, model: str, client_factory=httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client_factory = client_factory
        logger.info("LLMService ініціалізовано із моделлю %s", model)

    async def chat(self, prompt: str, context: Optional[List[str]] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": self._build_prompt(prompt, context),
            "options": {"temperature": 0.2},
        }

        url = f"{self.base_url}/api/generate"
        try:
            async with self.client_factory(timeout=60) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception:
            logger.exception("Не вдалося отримати відповідь від LLM")
            return "LLM тимчасово недоступна."

    async def summarize(self, text: str) -> str:
        prompt = (
            "Стисло підсумуй дані з теплиці. Виділи ризики та наступні кроки.\n"
            f"Дані:\n{text}"
        )
        return await self.chat(prompt)

    def _build_prompt(self, prompt: str, context: Optional[List[str]] = None) -> str:
        """Додати контекст до підказки у вигляді маркованого списку."""

        if not context:
            return prompt

        context_block = "\n- ".join(context)
        return f"{prompt}\n\nКонтекст:\n- {context_block}"
