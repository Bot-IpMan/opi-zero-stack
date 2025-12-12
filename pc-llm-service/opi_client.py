import httpx


class OPIClient:
    """HTTP клієнт для доступу до сервісів Orange Pi Zero."""

    def __init__(self, host: str, port: int, camera_path: str = "/camera/frame"):
        self.base_url = f"http://{host}:{port}"
        self.camera_path = camera_path

    async def fetch_camera_frame(self) -> bytes:
        url = f"{self.base_url}{self.camera_path}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
