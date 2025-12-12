import asyncio
import logging
from pathlib import Path
from typing import Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from llm_service import LLMService
from mqtt_client import MQTTClient
from rag.retriever import Retriever
from rag_llm import RAGPipeline
from vision_processor import analyze_frame, capture_single

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.yaml"


class AnalyzeRequest(BaseModel):
    device: Optional[str] = None


class DecisionRequest(BaseModel):
    sensors: dict
    last_actions: Optional[list] = None


class SystemStatus(BaseModel):
    camera_ok: bool
    mqtt_connected: bool


class AppContext:
    def __init__(self):
        raw_cfg = yaml.safe_load(CONFIG_PATH.read_text())
        self.cfg = raw_cfg
        llm_cfg = raw_cfg.get("llm", {})
        self.llm = LLMService(llm_cfg.get("endpoint", "http://localhost:11434"), llm_cfg.get("model", "qwen2.5:7b"))
        self.retriever = Retriever(raw_cfg["rag"]["knowledge_path"], raw_cfg["rag"]["vector_db_path"])
        self.rag = RAGPipeline(self.retriever, self.llm)
        mqtt_cfg = raw_cfg.get("mqtt", {})
        self.mqtt = MQTTClient(mqtt_cfg.get("host", "mqtt"), mqtt_cfg.get("port", 1883), mqtt_cfg.get("topic_prefix", "greenhouse"))
        self.mqtt.loop_background()


app = FastAPI(title="PC LLM Coordinator")
ctx = AppContext()


@app.post("/analyze_image")
async def analyze_image(payload: AnalyzeRequest):
    device = payload.device or ctx.cfg["camera"].get("device", "/dev/video0")
    frame = capture_single(device)
    metrics = analyze_frame(frame)
    summary = await ctx.llm.summarize(str(metrics))
    return {"metrics": metrics, "llm_summary": summary}


@app.post("/make_decision")
async def make_decision(payload: DecisionRequest):
    try:
        message = await ctx.rag.ask(f"Сенсори: {payload.sensors}. Останні дії: {payload.last_actions}")
        ctx.mqtt.publish_state("decisions", {"text": message, "sensors": payload.sensors})
        return {"decision": message}
    except Exception as exc:
        logger.exception("Помилка make_decision")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/system_status")
async def system_status():
    mqtt_ok = ctx.mqtt.client.is_connected()
    camera_frame = capture_single(ctx.cfg["camera"].get("device", "/dev/video0"))
    return SystemStatus(camera_ok=camera_frame is not None, mqtt_connected=mqtt_ok)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
