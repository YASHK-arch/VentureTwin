"""
Brave Search connector for VentureTwin — Skeptic / Market Intelligence domain.

Queries Brave Search REST API for evidence-backed market intelligence, competitor benchmarking,
pricing developments, and industry macro trends.
NOTE: Returns real external web search results, NOT synthetic data.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="brave_search",
    display_name="Brave Search",
    agent_domain="intelligence",
    environment="production",
    credential_env_vars=["BRAVE_SEARCH_API_KEY"],
    supports_write=False,
    supports_synthetic_generation=False,
    oauth_required=False,
)

_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchConnector(AbstractConnector):
    """Brave Search API connector for real-world competitive intelligence."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _headers(self) -> Dict[str, str]:
        key = self._credentials.get("BRAVE_SEARCH_API_KEY", "")
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": key,
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    _SEARCH_URL,
                    headers=self._headers(),
                    params={"q": "B2B SaaS benchmark metrics 2026", "count": 1},
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "provider": "Brave Search Web API"}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Brave Search API key rejected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "provider": "Brave Search Web API"}
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._error = str(e)
            return {"status": self.status.value, "error": self._error}

    async def disconnect(self) -> None:
        self.status = ConnectionStatus.NOT_CONNECTED
        self._credentials = {}

    async def validate_connection(self) -> bool:
        res = await self.connect()
        return res.get("status") == "connected"

    async def fetch_data(
        self,
        entity_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Queries Brave Search for market intelligence, competitor pricing, and industry benchmarks."""
        if not self._credentials.get("BRAVE_SEARCH_API_KEY"):
            if not self.load_credentials():
                return []
        queries = entity_types or [
            "B2B SaaS freemium churn rates 2026",
            "Shopify merchant churn rate vs gross merchandise value",
            "Nextcloud enterprise support pricing SLA"
        ]
        results: List[Dict[str, Any]] = []

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for q in queries:
                    resp = await client.get(
                        _SEARCH_URL,
                        headers=self._headers(),
                        params={"q": q, "count": 3},
                        timeout=12,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        web_results = data.get("web", {}).get("results", [])
                        for item in web_results:
                            results.append({
                                "query": q,
                                "title": item.get("title"),
                                "url": item.get("url"),
                                "description": item.get("description"),
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                            })
        except Exception:
            pass
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalizes web search intelligence with strict external research provenance."""
        normalized: List[Dict[str, Any]] = []
        company_id = "default"
        for idx, item in enumerate(raw):
            url = item.get("url", f"brave_search_{idx}")
            title = item.get("title", "Market Intelligence Research")
            description = item.get("description", "")
            query = item.get("query", "B2B SaaS benchmark")

            payload = {
                "source_title": title,
                "source_url": url,
                "summary": description,
                "query": query,
                "retrieved_at": item.get("fetched_at", datetime.now(timezone.utc).isoformat()),
                "source": "brave_search_web_api",
            }

            rec = self.make_normalized_record(
                company_id=company_id,
                entity_type="market_research",
                entity_id=f"bs_{hash(url) & 0xFFFFFF}",
                payload=payload,
                provenance_type=ProvenanceType.EXTERNAL_RESEARCH,
            )
            normalized.append(rec)
        return normalized
