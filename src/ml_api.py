"""Mercado Livre API Client — async com httpx."""
import httpx
import time
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()


class MLClient:
    BASE = "https://api.mercadolibre.com"
    SITE = "MLB"

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("ML_ACCESS_TOKEN", "")
        self._client = None
        self._last_call = 0

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=20,
            )
        return self._client

    async def _get(self, path: str, params: dict | None = None) -> dict | None:
        elapsed = time.time() - self._last_call
        if elapsed < 0.4:
            await asyncio.sleep(0.4 - elapsed)
        try:
            r = await self._get_client().get(path, params=params)
            self._last_call = time.time()
            if r.status_code == 200:
                return r.json()
            # Auto-refresh on 401
            if r.status_code == 401 and not getattr(self, "_refreshed", False):
                refreshed = self._try_refresh_token()
                if refreshed:
                    self._refreshed = True
                    return await self._get(path, params)
            return {"error": r.status_code, "detail": r.text[:300]}
        except Exception as e:
            return {"error": "exception", "detail": str(e)}

    def _try_refresh_token(self) -> bool:
        """Tenta renovar o token ML via refresh_token."""
        try:
            from src.auth import refresh_ml_token
            ok, msg = refresh_ml_token()
            if ok:
                load_dotenv(override=True)
                self.token = os.getenv("ML_ACCESS_TOKEN", "")
                self._client = None  # força recriação do client
                return True
        except Exception:
            pass
        return False

    # ── BUSCA ──────────────────────────────────────────

    async def search(self, query: str, limit: int = 50, offset: int = 0,
                     status: str = "all") -> dict:
        """
        Busca via /products/search (catálogo ML).
        Para cada produto, enriquece com dados dos anúncios.
        status: "all", "active", "inactive"
        """
        products = await self._get("/products/search", {
            "site_id": self.SITE, "q": query,
            "limit": min(limit, 50), "offset": offset,
        })

        if not products or "error" in products:
            return products or {"error": "no_results", "results": []}

        # Determinar quais status buscar nos items
        if status == "all":
            statuses = ["active", "inactive"]
        else:
            statuses = [status]

        results = []
        for prod in products.get("results", []):
            prod_id = prod.get("id")
            if not prod_id:
                continue

            attrs = {a["id"]: a.get("value_name", "") for a in prod.get("attributes", [])}
            found_items = False

            for st in statuses:
                items_resp = await self._get(f"/products/{prod_id}/items", {"status": st})
                if items_resp and "error" not in items_resp:
                    for item in items_resp.get("results", []):
                        found_items = True
                        results.append({
                            "id": item.get("item_id", ""),
                            "title": prod.get("name", ""),
                            "price": item.get("price", 0),
                            "original_price": item.get("original_price"),
                            "currency_id": item.get("currency_id", "BRL"),
                            "condition": item.get("condition", ""),
                            "status": st,
                            "seller": {"id": item.get("seller_id", ""), "nickname": ""},
                            "shipping": item.get("shipping", {}),
                            "permalink": f"https://www.mercadolivre.com.br/p/{prod_id}",
                            "catalog_product_id": prod_id,
                            "brand": attrs.get("BRAND", ""),
                            "model": attrs.get("MODEL", ""),
                            "capacity": attrs.get("RAM_MEMORY_MODULE_TOTAL_CAPACITY", ""),
                        })

            if not found_items:
                results.append({
                    "id": prod_id,
                    "title": prod.get("name", ""),
                    "price": 0,
                    "condition": "",
                    "status": "catalog_only",
                    "seller": {"id": "", "nickname": "Catálogo ML"},
                    "shipping": {},
                    "permalink": f"https://www.mercadolivre.com.br/p/{prod_id}",
                    "catalog_product_id": prod_id,
                    "brand": attrs.get("BRAND", ""),
                    "model": attrs.get("MODEL", ""),
                    "capacity": attrs.get("RAM_MEMORY_MODULE_TOTAL_CAPACITY", ""),
                })

            if len(results) >= limit:
                break

        return {
            "results": results[:limit],
            "paging": {
                "total": products.get("paging", {}).get("total", len(results)),
                "limit": limit,
                "offset": offset,
            },
            "source": "products/search",
        }

    # ── CONCORRENTES ───────────────────────────────────

    async def search_seller(self, nickname: str = None, seller_id: str = None, limit: int = 50) -> dict:
        """Busca items de um vendedor."""
        # Tenta /sites/MLB/search
        params = {"limit": limit}
        if seller_id:
            params["seller_id"] = seller_id
        elif nickname:
            params["nickname"] = nickname
        result = await self._get(f"/sites/{self.SITE}/search", params)

        if result and "error" not in result:
            return result

        # Fallback: se temos seller_id, usa /users/{id}/items/search
        uid = seller_id
        if uid:
            return await self._seller_items(uid, limit)

        return {"error": "search_blocked", "results": [],
                "detail": "Busca por vendedor bloqueada pela API do ML. Use seller_id."}

    async def _seller_items(self, user_id: str, limit: int) -> dict:
        """Busca items de um vendedor via /users/{id}/items/search."""
        r = await self._get(f"/users/{user_id}/items/search", {"limit": limit})
        if r and "error" not in r:
            item_ids = r.get("results", [])
            if item_ids:
                # Buscar detalhes (só funciona pra items próprios)
                items = []
                for item_id in item_ids[:limit]:
                    detail = await self.get_item(item_id)
                    if detail and "error" not in detail:
                        items.append(detail)
                return {"results": items, "paging": r.get("paging", {})}
        return {"error": "no_items", "results": []}

    # ── DETALHES ───────────────────────────────────────

    async def get_item(self, item_id: str) -> dict:
        return await self._get(f"/items/{item_id}")

    async def get_user(self, user_id: str) -> dict:
        return await self._get(f"/users/{user_id}")

    async def me(self) -> dict:
        return await self._get("/users/me")

    async def close(self):
        await self.client.aclose()
