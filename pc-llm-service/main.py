import asyncio
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
import yaml
from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel, Field

from llm_service import LLMService
from mqtt_client import MQTTClient
from rag.retriever import Retriever
from rag_llm import RAGPipeline
from vision_processor import CameraError, analyze_frame, capture_single

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _expand_env(text: str) -> str:
    pattern = re.compile(r"\$\{([^:}]+)(:-([^}]+))?}")

    def repl(match: re.Match) -> str:
        var_name = match.group(1)
        default = match.group(3) or ""
        return os.environ.get(var_name, default)

    return pattern.sub(repl, text)


def load_config() -> dict:
    """Load YAML config with environment variable expansion."""
    raw_text = _expand_env(CONFIG_PATH.read_text())
    return yaml.safe_load(raw_text)


class AnalyzeRequest(BaseModel):
    device: Optional[str] = Field(None, description="Path to camera device")


class DecisionRequest(BaseModel):
    sensors: dict = Field(..., description="Latest sensor readings")
    last_actions: Optional[list] = Field(None, description="Recent actuator actions")


class ManualOverrideRequest(BaseModel):
    action: str = Field(..., description="Назва ручної дії для виконання")
    payload: dict = Field(default_factory=dict, description="Додаткові параметри для дії")


class SystemStatus(BaseModel):
    camera_ok: bool
    mqtt_connected: bool


class RobotStatus(BaseModel):
    sensors: Dict[str, Any]
    actuators: Dict[str, Any]


class AppContext:
    def __init__(self):
        raw_cfg = load_config()
        self.cfg = raw_cfg
        llm_cfg = raw_cfg.get("llm", {})
        self.llm = LLMService(
            llm_cfg.get("endpoint", "http://localhost:11434"),
            llm_cfg.get("model", "qwen2.5:7b"),
        )
        self.retriever = Retriever(raw_cfg["rag"]["knowledge_path"], raw_cfg["rag"]["vector_db_path"])
        self.rag = RAGPipeline(self.retriever, self.llm)
        mqtt_cfg = raw_cfg.get("mqtt", {})
        self.mqtt = MQTTClient(
            mqtt_cfg.get("host", "mqtt"),
            mqtt_cfg.get("port", 1883),
            mqtt_cfg.get("topic_prefix", "greenhouse"),
        )
        self.mqtt.loop_background()
        logger.info("AppContext initialized")


@lru_cache(maxsize=1)
def get_ctx() -> AppContext:
    return AppContext()


app = FastAPI(title="PC LLM Coordinator")


@app.post("/analyze_image")
async def analyze_image(payload: AnalyzeRequest):
    ctx = get_ctx()
    device = payload.device or ctx.cfg["camera"].get(
        "device", "http://opi-zero:8000/camera/snapshot"
    )
    try:
        frame = capture_single(device)
        metrics = analyze_frame(frame)
        summary = await ctx.llm.summarize(str(metrics))
    except CameraError as exc:
        logger.exception("Помилка доступу до камери")
        raise HTTPException(status_code=503, detail=str(exc))
    return {"metrics": metrics, "llm_summary": summary}


@app.post("/make_decision")
async def make_decision(payload: DecisionRequest):
    ctx = get_ctx()
    try:
        message = await ctx.rag.ask(f"Сенсори: {payload.sensors}. Останні дії: {payload.last_actions}")
        ctx.mqtt.publish_state("decisions", {"text": message, "sensors": payload.sensors})
        return {"decision": message}
    except Exception as exc:
        logger.exception("Помилка make_decision")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/override_decision")
async def override_decision(payload: ManualOverrideRequest):
    ctx = get_ctx()
    override_message = {"action": payload.action, "payload": payload.payload, "source": "human"}
    try:
        ctx.mqtt.publish_state("manual_overrides", override_message)
        return {"status": "ok", "override": override_message}
    except Exception as exc:
        logger.exception("Помилка override_decision")
        raise HTTPException(status_code=500, detail=str(exc))


@app.api_route("/system_status", methods=["GET", "POST"])
async def system_status(payload: Optional[RobotStatus] = Body(default=None)):
    ctx = get_ctx()
    mqtt_ok = ctx.mqtt.client.is_connected()
    if payload:
        logger.debug("Отримано статус від робота: %s", payload.model_dump())
    try:
        capture_single(ctx.cfg["camera"].get("device", "http://opi-zero:8000/camera/snapshot"))
        camera_ok = True
    except CameraError:
        camera_ok = False
    return SystemStatus(camera_ok=camera_ok, mqtt_connected=mqtt_ok)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False, loop="asyncio")
