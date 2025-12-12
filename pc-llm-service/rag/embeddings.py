from typing import Iterable, List

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        return self.model.encode(list(texts), convert_to_numpy=True).tolist()


def create_embedding_function(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformerEmbeddingFunction:
    """Factory for a Chroma-ready embedding function."""

    return SentenceTransformerEmbeddingFunction(model_name=model_name)
