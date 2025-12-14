import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "pc-llm-service" / "main.py"
sys.path.append(str(MODULE_PATH.parent))

spec = importlib.util.spec_from_file_location("pc_llm_main", MODULE_PATH)
pc_llm_main = importlib.util.module_from_spec(spec)
assert spec and spec.loader

fastapi_mock = MagicMock()
fastapi_mock.FastAPI.return_value = MagicMock()
fastapi_mock.Body = MagicMock
fastapi_mock.HTTPException = type("HTTPException", (Exception,), {})
fastapi_mock.Request = MagicMock
fastapi_mock.Response = MagicMock

prometheus_mock = MagicMock()
prometheus_mock.Counter.return_value = MagicMock()
prometheus_mock.generate_latest = MagicMock(return_value=b"")
prometheus_mock.CONTENT_TYPE_LATEST = "text/plain"

sys.modules.setdefault("uvicorn", types.SimpleNamespace())
sys.modules.setdefault("yaml", MagicMock(safe_load=lambda text: text))
sys.modules.setdefault("httpx", MagicMock())
sys.modules.setdefault("fastapi", fastapi_mock)
sys.modules.setdefault("fastapi.responses", MagicMock(RedirectResponse=MagicMock))
sys.modules.setdefault("prometheus_client", prometheus_mock)
sys.modules.setdefault("pydantic", MagicMock(BaseModel=object, Field=lambda default=None, **_: default))
sys.modules.setdefault("mqtt_client", MagicMock(MQTTClient=MagicMock()))
sys.modules.setdefault("rag", MagicMock(DEFAULT_EMBEDDING_MODEL="model", Retriever=MagicMock()))
sys.modules.setdefault("rag_llm", MagicMock(RAGPipeline=MagicMock()))
sys.modules.setdefault(
    "vision_processor",
    MagicMock(CameraError=Exception, analyze_frame=MagicMock(), capture_single=MagicMock()),
)

spec.loader.exec_module(pc_llm_main)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text,env_value,expected",
    [
        ("device: ${CAMERA_DEVICE:-}", None, "device: "),
        ("device: ${CAMERA_DEVICE:-/dev/video0}", None, "device: /dev/video0"),
        ("device: ${CAMERA_DEVICE:-/dev/video0}", "/dev/video2", "device: /dev/video2"),
    ],
)
def test_expand_env_supports_empty_default(monkeypatch, text, env_value, expected):
    if env_value is None:
        monkeypatch.delenv("CAMERA_DEVICE", raising=False)
    else:
        monkeypatch.setenv("CAMERA_DEVICE", env_value)

    expanded = pc_llm_main._expand_env(text)
    assert expanded == expected

    monkeypatch.delenv("CAMERA_DEVICE", raising=False)
