import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc-llm-service" / "rag" / "embeddings.py"


class DummySentenceTransformer:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def encode(self, texts, convert_to_numpy=True):  # pragma: no cover - fallback path
        return [[0.0] * len(texts) for _ in texts]


class DummyEmbeddingFunction:
    pass


dummy_embedding_functions = types.ModuleType("chromadb.utils.embedding_functions")
dummy_embedding_functions.EmbeddingFunction = DummyEmbeddingFunction
dummy_embedding_functions.OllamaEmbeddingFunction = (
    lambda model_name, url=None: (model_name, url)
)
dummy_embedding_functions.SentenceTransformerEmbeddingFunction = (
    lambda model_name: ("sentence", model_name)
)

dummy_utils = types.ModuleType("chromadb.utils")
dummy_utils.embedding_functions = dummy_embedding_functions

dummy_chromadb = types.ModuleType("chromadb")
dummy_chromadb.utils = dummy_utils

sys.modules["chromadb"] = dummy_chromadb
sys.modules["chromadb.utils"] = dummy_utils
sys.modules["chromadb.utils.embedding_functions"] = dummy_embedding_functions
sys.modules["sentence_transformers"] = types.SimpleNamespace(
    SentenceTransformer=DummySentenceTransformer
)


spec = importlib.util.spec_from_file_location("embeddings", MODULE_PATH)
embeddings = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(embeddings)  # type: ignore[arg-type]


def test_fastembed_accepts_namespaced_model(monkeypatch):
    initialized_models = []

    class DummyTextEmbedding:
        def __init__(self, model_name: str):
            initialized_models.append(model_name)

        @staticmethod
        def list_supported_models():
            return ["bge-small-en-v1.5"]

        def embed(self, input):  # noqa: A003
            class Vector:
                def __init__(self, length):
                    self.length = length

                def tolist(self):
                    return [0.1 for _ in range(self.length)]

            return [Vector(len(input)) for _ in input]

    monkeypatch.setattr(embeddings, "embedding_functions", dummy_embedding_functions)
    monkeypatch.setattr(embeddings, "TextEmbedding", DummyTextEmbedding)

    embedding_fn = embeddings.create_embedding_function("BAAI/bge-small-en-v1.5")

    assert initialized_models == ["bge-small-en-v1.5"]
    assert embedding_fn(["one", "two"]) == [[0.1, 0.1], [0.1, 0.1]]
