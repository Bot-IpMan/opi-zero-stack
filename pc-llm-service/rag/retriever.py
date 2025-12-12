import json
import logging
import pathlib
from typing import List

from .embeddings import Embedder
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, kb_path: str, vector_path: str):
        self.kb_path = pathlib.Path(kb_path)
        self.vector_store = VectorStore(vector_path)
        self.embedder = Embedder()
        self._ensure_index()

    def _ensure_index(self):
        if not self.kb_path.exists():
            logger.warning("Knowledge path %s does not exist", self.kb_path)
            return

        docs = []
        for json_file in self.kb_path.glob("*.json"):
            data = json.loads(json_file.read_text())
            for idx, item in enumerate(data):
                docs.append(
                    {
                        "id": f"{json_file.stem}-{idx}",
                        "text": item.get("text", ""),
                        "meta": {"topic": item.get("topic", json_file.stem)},
                    }
                )
        if docs:
            self.vector_store.add(docs)
            logger.info("RAG індекс з %s документів готовий", len(docs))
        else:
            logger.warning("Не знайдено жодного RAG документа у %s", self.kb_path)

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        return self.vector_store.query(self.embedder.encode, query, top_k=top_k)
