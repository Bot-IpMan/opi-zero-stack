from typing import List, Optional

import chromadb
from chromadb.config import Settings

from .embeddings import create_embedding_function


class VectorStore:
    def __init__(self, path: str, model_name: str = "all-MiniLM-L6-v2"):
        self.path = path
        self.embedding_function = create_embedding_function(model_name)
        self.client = chromadb.PersistentClient(
            path=path, settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self._init_collection()

    def _init_collection(self):
        return self.client.get_or_create_collection(
            "knowledge",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self):
        try:
            self.client.delete_collection("knowledge")
        finally:
            self.collection = self._init_collection()

    def add(self, docs: List[dict]):
        ids = [doc["id"] for doc in docs]
        texts = [doc["text"] for doc in docs]
        metadatas = [doc.get("meta", {}) for doc in docs]
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    def query(self, query: str, top_k: int = 3) -> List[str]:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        combined = []
        for text, meta in zip(docs, metas):
            topic = meta.get("topic") or meta.get("file") or ""  # pragma: no cover
            combined.append(f"{topic}: {text}" if topic else text)
        return combined

    def count(self) -> Optional[int]:
        if not self.collection:
            return None
        return self.collection.count()
