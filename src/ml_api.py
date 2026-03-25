"""Mercado Livre API Client — async com httpx."""
import httpx
import time
import os
from dotenv import load_dotenv

load_dotenv()

class MLClient:
    BASE = "https://api.mercadolibre.com"
    SITE = "MLB"

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("ML_ACCESS_TOKEN", "")
        self.client = httpx.AsyncClient(
            base_url=self.BASE,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=20,
        )
        self._last_call = 0

    async def _get(self, path: str, params: dict | None = None) -> dict | None:
        elapsed = time.time() - self._last_call
        if elapsed < 0.4:
            import asyncio
            await asyncio.sleep(0.4 - elapsed)
        try:
            r = await self.client.get(path, params=params)
            self._last_call = time.time()
            if r.status_code == 200:
                return r.json()
            return {"error": r.status_code, "detail": r.text[:300]}
        except Exception as e:
            return {"error": "exception", "detail": str(e)}

    async def search(self, query: str, limit: int = 50, offset: int = 0) -> dict:
        return await self._get(f"/sites/{self.SITE}/search", {
            "q": query, "limit": min(limit, 50), "offset": offset,
        })

    async def search_seller(self, nickname: str = None, seller_id: str = None, limit: int = 50) -> dict:
        params = {"limit": limit}
        if seller_id:
            params["seller_id"] = seller_id
        elif nickname:
            params["nickname"] = nickname
        return await self._get(f"/sites/{self.SITE}/search", params)

    async def get_item(self, item_id: str) -> dict:
        return await self._get(f"/items/{item_id}")

    async def get_user(self, user_id: str) -> dict:
        return await self._get(f"/users/{user_id}")

    async def me(self) -> dict:
        return await self._get("/users/me")

    async def close(self):
        await self.client.aclose()
