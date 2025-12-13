import logging
from typing import Iterable, List

from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        return self.model.encode(list(texts), convert_to_numpy=True).tolist()


def create_embedding_function(model_name: str = "all-MiniLM-L6-v2") -> embedding_functions.EmbeddingFunction:
    """Factory for a Chroma-ready embedding function.

    Prefers the lightweight FastEmbed backend to avoid PyTorch crashes on
    constrained hosts. Falls back to the original SentenceTransformer-based
    embeddings if FastEmbed is unavailable.
    """

    try:
        logger.info("Using FastEmbed embeddings backend: %s", model_name)
        return embedding_functions.FastEmbedEmbeddingFunction(model_name=model_name)
    except Exception:
        logger.warning(
            "FastEmbed unavailable, falling back to SentenceTransformer backend.",
            exc_info=True,
        )
        return SentenceTransformerEmbeddingFunction(model_name=model_name)
