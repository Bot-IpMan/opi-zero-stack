import json
import logging
import pathlib
from typing import Dict, List

from .embeddings import DEFAULT_EMBEDDING_MODEL
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        kb_path: str,
        vector_path: str,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.kb_path = pathlib.Path(kb_path)
        self.vector_store = VectorStore(vector_path, model_name=model_name)
        self.documents: List[Dict] = []
        self._load_and_index()

    def _load_json(self, path: pathlib.Path) -> List[Dict]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Не вдалося прочитати %s", path)
            return []

    def _load_and_index(self):
        if not self.kb_path.exists():
            logger.warning("Knowledge path %s does not exist", self.kb_path)
            return

        self.documents.clear()
        for json_file in sorted(self.kb_path.glob("*.json")):
            data = self._load_json(json_file)
            for idx, item in enumerate(data):
                text_parts = [item.get("text", "")]
                conditions = item.get("conditions")
                if conditions:
                    text_parts.append(
                        "; ".join(
                            [
                                f"{name}: {value}" for name, value in conditions.items()
                            ]
                        )
                    )
                action = item.get("action")
                if action:
                    text_parts.append(f"Команда: {action}")
                prepared_text = " ".join(filter(None, text_parts))
                self.documents.append(
                    {
                        "id": f"{json_file.stem}-{idx}",
                        "text": prepared_text,
                        "meta": {
                            "topic": item.get("topic", json_file.stem),
                            "file": json_file.name,
                        },
                    }
                )

        if self.documents:
            self.vector_store.reset()
            self.vector_store.add(self.documents)
            logger.info("RAG індекс з %s документів готовий", len(self.documents))
        else:
            logger.warning("Не знайдено жодного RAG документа у %s", self.kb_path)

    def retrieve(self, query: str, top_k: int = 3) -> List[str]:
        return self.vector_store.query(query, top_k=top_k)

    def refresh(self):
        """Reload knowledge base files and rebuild the vector index."""

        self._load_and_index()

    def append_to_knowledge(self, file_name: str, entry: Dict):
        """Append a new knowledge entry to a JSON file and refresh the index."""

        target_file = self.kb_path / file_name
        current = self._load_json(target_file) if target_file.exists() else []
        current.append(entry)
        target_file.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        self._load_and_index()
