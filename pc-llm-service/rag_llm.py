import logging
from typing import List

from rag.retriever import Retriever
from llm_service import LLMService

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Проста RAG-обгортка навколо LLM."""

    def __init__(self, retriever: Retriever, llm: LLMService):
        self.retriever = retriever
        self.llm = llm

    async def ask(self, query: str) -> str:
        support_docs: List[str] = self.retriever.retrieve(query, top_k=3)
        logger.debug("RAG контекст: %s", support_docs)
        prompt = (
            "Ти — агроном та оператор теплиці. Використай надані нотатки, щоб відповісти.\n"
            f"Джерела:\n- " + "\n- ".join(support_docs) + "\n"
            f"Запит: {query}\n"
            "Дай стисле рішення українською."
        )
        return await self.llm.chat(prompt, context=support_docs)
