import logging
from typing import Iterable, List

from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer

try:  # Prefer the lightweight fastembed backend when available.
    from fastembed import TextEmbedding
except Exception:  # pragma: no cover - fallback handled in code flow.
    TextEmbedding = None

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

    if TextEmbedding:
        try:
            supported_models = TextEmbedding.list_supported_models()
            if isinstance(supported_models, Iterable) and not isinstance(
                supported_models, (str, bytes)
            ):
                supported_models = {
                    model.get("name", model) if hasattr(model, "get") else model
                    for model in supported_models
                }
            else:  # pragma: no cover - defensive guard for unexpected return types
                supported_models = set()

            if model_name not in supported_models:
                logger.info(
                    "FastEmbed model %s not supported, skipping FastEmbed backend.",
                    model_name,
                )
            else:
                logger.info("Using FastEmbed embeddings backend: %s", model_name)

                class FastEmbedEmbeddingFunction(embedding_functions.EmbeddingFunction):
                    def __init__(self, model: TextEmbedding):
                        self._model = model

                    def __call__(self, input: Iterable[str]):
                        return [embedding.tolist() for embedding in self._model.embed(input)]

                return FastEmbedEmbeddingFunction(TextEmbedding(model_name=model_name))
        except Exception:
            logger.warning(
                "FastEmbed unavailable, falling back to SentenceTransformer backend.",
                exc_info=True,
            )

    return SentenceTransformerEmbeddingFunction(model_name=model_name)
