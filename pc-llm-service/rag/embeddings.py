import logging
import os
from typing import Iterable, List

from chromadb.utils import embedding_functions
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from sentence_transformers import SentenceTransformer

try:  # Prefer the lightweight fastembed backend when available.
    from fastembed import TextEmbedding
except Exception:  # pragma: no cover - fallback handled in code flow.
    TextEmbedding = None

logger = logging.getLogger(__name__)


# Default embedding model chosen for compatibility with the FastEmbed backend.
# Using FastEmbed keeps the service away from PyTorch wheels that may crash on
# CPUs without AVX/AVX2 support (those typically exit with code 136).
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class Embedder:
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        return self.model.encode(list(texts), convert_to_numpy=True).tolist()


def create_embedding_function(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> embedding_functions.EmbeddingFunction:
    """Factory for a Chroma-ready embedding function.

    Prefers the lightweight FastEmbed backend to avoid PyTorch crashes on
    constrained hosts. Falls back to the original SentenceTransformer-based
    embeddings if FastEmbed is unavailable.
    """

    if ":" in model_name:
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        logger.info(
            "Using Ollama embeddings backend: model=%s, url=%s",
            model_name,
            base_url,
        )
        return embedding_functions.OllamaEmbeddingFunction(
            model_name=model_name, url=base_url
        )

    if TextEmbedding:
        try:
            supported_models_raw = TextEmbedding.list_supported_models()
            if isinstance(supported_models_raw, Iterable) and not isinstance(
                supported_models_raw, (str, bytes)
            ):
                normalized_models = []
                for model in supported_models_raw:
                    if isinstance(model, dict):
                        normalized_models.append(model.get("name"))
                    else:
                        normalized_models.append(model)

                supported_models = {
                    candidate
                    for candidate in normalized_models
                    if isinstance(candidate, (str, bytes))
                }
            else:  # pragma: no cover - defensive guard for unexpected return types
                supported_models = set()

            # FastEmbed often publishes model IDs without namespaces. Try both the
            # requested name and a variant without the leading namespace so that
            # `BAAI/bge-small-en-v1.5` maps to the supported `bge-small-en-v1.5`.
            candidates = [model_name]
            if "/" in model_name:
                candidates.append(model_name.split("/", 1)[1])

            for candidate in candidates:
                if supported_models and candidate not in supported_models:
                    continue

                try:
                    chosen_model = TextEmbedding(model_name=candidate)
                    logger.info(
                        "Using FastEmbed embeddings backend: %s (requested %s)",
                        candidate,
                        model_name,
                    )

                    class FastEmbedEmbeddingFunction(
                        embedding_functions.EmbeddingFunction
                    ):
                        def __init__(self, model: TextEmbedding):
                            self._model = model

                        def __call__(self, input: Iterable[str]):
                            return [
                                embedding.tolist()
                                for embedding in self._model.embed(input)
                            ]

                    return FastEmbedEmbeddingFunction(chosen_model)
                except Exception:
                    logger.warning(
                        "FastEmbed model %s failed to initialize, trying next candidate.",
                        candidate,
                        exc_info=True,
                    )
        except Exception:
            logger.warning(
                "FastEmbed unavailable, falling back to SentenceTransformer backend.",
                exc_info=True,
            )

    return SentenceTransformerEmbeddingFunction(model_name=model_name)
