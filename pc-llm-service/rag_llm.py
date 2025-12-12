import logging
from typing import Dict, List

from rag.retriever import Retriever
from llm_service import LLMService

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Проста RAG-обгортка навколо LLM."""

    def __init__(self, retriever: Retriever, llm: LLMService):
        self.retriever = retriever
        self.llm = llm

    async def ask(self, query: str, top_k: int = 3) -> str:
        support_docs: List[str] = self.retriever.retrieve(query, top_k=top_k)
        logger.debug("RAG контекст: %s", support_docs)
        prompt = (
            "Ти — агроном та оператор теплиці. Використай нотатки, щоб дати чітку пораду.\n"
            f"Джерела:\n- " + "\n- ".join(support_docs) + "\n"
            f"Запит: {query}\n"
            "Дай стисле рішення українською із конкретними кроками. Якщо джерела порожні — скажи, що знань не вистачає."
        )
        return await self.llm.chat(prompt, context=support_docs)

    def refresh_knowledge(self):
        """Перечитати JSON-файли та перебудувати індекс."""

        self.retriever.refresh()

    def add_knowledge(self, file_name: str, entry: Dict):
        """Додати новий елемент до бази знань і одразу переіндексувати."""

        self.retriever.append_to_knowledge(file_name, entry)
