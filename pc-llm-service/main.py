import asyncio
import logging
import os
import re
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
import yaml
from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, Field

from llm_service import LLMService
from mqtt_client import MQTTClient
from rag import DEFAULT_EMBEDDING_MODEL, Retriever
from rag_llm import RAGPipeline
from vision_processor import CameraError, analyze_frame, capture_single

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "config.yaml"


LLM_DECISIONS_PENDING = Counter(
    "llm_decisions_pending_total",
    "Number of LLM decisions waiting for approval",
)
LLM_DECISIONS_APPROVED = Counter(
    "llm_decisions_approved_total",
    "Number of LLM decisions approved by operator",
)
LLM_DECISIONS_REJECTED = Counter(
    "llm_decisions_rejected_total",
    "Number of LLM decisions rejected by operator",
)


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


class DecisionRecord(BaseModel):
    id: str
    text: str
    sensors: Dict[str, Any]
    status: str
    created_at: float


class AppContext:
    def __init__(self):
        raw_cfg = load_config()
        self.cfg = raw_cfg
        llm_cfg = raw_cfg.get("llm", {})
        self.llm = LLMService(
            llm_cfg.get("endpoint", "http://localhost:11434"),
            llm_cfg.get("model", "qwen2.5:7b"),
        )
        self.retriever = Retriever(
            raw_cfg["rag"]["knowledge_path"],
            raw_cfg["rag"]["vector_db_path"],
            raw_cfg["rag"].get("embedding_model", DEFAULT_EMBEDDING_MODEL),
        )
        self.rag = RAGPipeline(self.retriever, self.llm)
        mqtt_cfg = raw_cfg.get("mqtt", {})
        self.mqtt = MQTTClient(
            mqtt_cfg.get("host", "mqtt"),
            mqtt_cfg.get("port", 1883),
            mqtt_cfg.get("topic_prefix", "greenhouse"),
            mqtt_cfg.get("enabled", True),
        )
        self.mqtt.loop_background()
        self.decisions: dict[str, DecisionRecord] = {}
        logger.info("AppContext initialized")

    async def store_decision(self, message: str, sensors: Dict[str, Any]) -> DecisionRecord:
        decision_id = str(uuid.uuid4())
        record = DecisionRecord(
            id=decision_id,
            text=message,
            sensors=sensors,
            status="pending",
            created_at=asyncio.get_event_loop().time(),
        )
        self.decisions[decision_id] = record
        LLM_DECISIONS_PENDING.inc()
        payload = {
            "id": decision_id,
            "text": message,
            "status": "pending",
            "sensors": sensors,
        }
        self.mqtt.publish_state("decisions", payload)
        return record

    async def update_decision_status(self, decision_id: str, status: str) -> DecisionRecord:
        if decision_id not in self.decisions:
            raise KeyError(f"Decision {decision_id} not found")

        record = self.decisions[decision_id]
        record.status = status
        if status == "approved":
            LLM_DECISIONS_APPROVED.inc()
        elif status == "rejected":
            LLM_DECISIONS_REJECTED.inc()

        self.decisions[decision_id] = record
        self.mqtt.publish_state("approvals", {"id": decision_id, "status": status})
        return record

    def list_decisions(self) -> list[DecisionRecord]:
        return sorted(self.decisions.values(), key=lambda d: d.created_at, reverse=True)


@lru_cache(maxsize=1)
def get_ctx() -> AppContext:
    return AppContext()


app = FastAPI(title="PC LLM Coordinator")


def resolve_camera_device(cfg: dict, override: Optional[str]) -> str:
    if override:
        return override

    camera_cfg = cfg.get("camera", {})
    device = camera_cfg.get("device")
    if device:
        return device

    opi_cfg = cfg.get("opi", {})
    host = opi_cfg.get("host")
    port = opi_cfg.get("port", 8000)
    if host:
        return f"http://{host}:{port}/camera/snapshot"

    return "/dev/video0"


@app.post("/analyze_image")
async def analyze_image(payload: AnalyzeRequest):
    ctx = get_ctx()
    device = resolve_camera_device(ctx.cfg, payload.device)
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
        message = await ctx.rag.ask(
            f"Сенсори: {payload.sensors}. Останні дії: {payload.last_actions}"
        )
        record = await ctx.store_decision(message, payload.sensors)
        return {"decision": record.text, "id": record.id, "status": record.status}
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


@app.get("/decisions")
async def list_decisions():
    ctx = get_ctx()
    return {"items": [record.model_dump() for record in ctx.list_decisions()]}


def _render_approvals_html(ctx: AppContext) -> str:
    rows = []
    for record in ctx.list_decisions():
        buttons = "" if record.status != "pending" else (
            f"<form style='display:inline' method='post' action='/decisions/{record.id}/approve'>"
            f"<button type='submit'>Approve</button></form>"
            f"<form style='display:inline;margin-left:8px' method='post' action='/decisions/{record.id}/reject'>"
            f"<button type='submit'>Reject</button></form>"
        )
        rows.append(
            f"<tr><td>{record.id}</td><td>{record.status}</td><td>{record.text}</td><td>{buttons}</td></tr>"
        )

    table_rows = "".join(rows) or "<tr><td colspan='4'>No decisions yet</td></tr>"
    return f"""
    <html>
      <head>
        <title>Decision Approvals</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 20px; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; }}
          th {{ background: #f4f4f4; text-align: left; }}
          button {{ padding: 6px 12px; }}
        </style>
      </head>
      <body>
        <h2>Pending LLM decisions</h2>
        <table>
          <thead><tr><th>ID</th><th>Status</th><th>Text</th><th>Actions</th></tr></thead>
          <tbody>{table_rows}</tbody>
        </table>
      </body>
    </html>
    """


@app.get("/approvals")
async def approvals_html():
    ctx = get_ctx()
    return Response(content=_render_approvals_html(ctx), media_type="text/html")


@app.post("/decisions/{decision_id}/{action}")
async def update_decision(decision_id: str, action: str, request: Request):
    ctx = get_ctx()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Unsupported action")

    status = "approved" if action == "approve" else "rejected"
    try:
        record = await ctx.update_decision_status(decision_id, status)
    except KeyError:
        raise HTTPException(status_code=404, detail="Decision not found")
    except Exception as exc:
        logger.exception("Не вдалося оновити статус рішення")
        raise HTTPException(status_code=500, detail=str(exc))

    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/approvals", status_code=303)

    return {"status": record.status, "id": record.id}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.api_route("/system_status", methods=["GET", "POST"])
async def system_status(payload: Optional[RobotStatus] = Body(default=None)):
    ctx = get_ctx()
    mqtt_ok = bool(getattr(ctx.mqtt, "connected", False))
    if payload:
        logger.debug("Отримано статус від робота: %s", payload.model_dump())
    try:
        capture_single(resolve_camera_device(ctx.cfg, None))
        camera_ok = True
    except CameraError:
        camera_ok = False
    return SystemStatus(camera_ok=camera_ok, mqtt_connected=mqtt_ok)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False, loop="asyncio")
