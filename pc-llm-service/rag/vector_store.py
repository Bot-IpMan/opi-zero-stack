import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(self, path: str):
        self.client = chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection("knowledge")

    def add(self, docs):
        ids = [doc["id"] for doc in docs]
        texts = [doc["text"] for doc in docs]
        metadatas = [doc.get("meta", {}) for doc in docs]
        self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    def query(self, embedding_fn, query: str, top_k: int = 3):
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [f"{m.get('topic','')}: {d}" for d, m in zip(docs, metas)]
