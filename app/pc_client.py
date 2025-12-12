import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PCClient:
    """HTTP клієнт для зв'язку з ПК координатором."""

    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"

    async def send_status(self, sensors: Dict[str, Any], actuators: Dict[str, Any]):
        import httpx

        payload = {"sensors": sensors, "actuators": actuators}
        url = f"{self.base_url}/system_status"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, json=payload)
        except Exception:
            logger.exception("Не вдалося відправити статус на ПК")

    async def request_decision(self, sensors: Dict[str, Any]):
        import httpx

        url = f"{self.base_url}/make_decision"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(url, json={"sensors": sensors})
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.exception("Помилка запиту рішення на ПК")
            return {"error": "pc_unreachable"}
