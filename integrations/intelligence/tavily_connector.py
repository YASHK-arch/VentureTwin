"""
Tavily connector for VentureTwin — Skeptic / Market Intelligence domain.

Queries Tavily Search API for evidence-backed market research, competitor benchmarking,
and macroeconomic industry trends.
NOTE: Returns real external web search results, NOT synthetic data.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="tavily",
    display_name="Tavily",
    agent_domain="intelligence",
    environment="production",
    credential_env_vars=["TAVILY_API_KEY"],
    supports_write=False,
    supports_synthetic_generation=False,
    oauth_required=False,
)

_TAVILY_API_URL = "https://api.tavily.com/search"


class TavilyConnector(AbstractConnector):
    """Tavily search API connector for evidence-backed competitive intelligence."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        key = self._credentials.get("TAVILY_API_KEY", "")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    _TAVILY_API_URL,
                    headers=self._headers(),
                    json={"api_key": key, "query": "B2B SaaS benchmark churn 2026", "max_results": 1},
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "provider": "Tavily Search API"}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Tavily authentication failed: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"Tavily unexpected status: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
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
        """Queries Tavily with market/competitor research queries."""
        if not self._credentials.get("TAVILY_API_KEY"):
            if not self.load_credentials():
                return []
        queries = entity_types or [
            "B2B SaaS freemium to paid conversion benchmarks",
            "Shopify merchant churn rate vs gross merchandise value",
            "Nextcloud enterprise support pricing SLA"
        ]
        results: List[Dict[str, Any]] = []
        key = self._credentials.get("TAVILY_API_KEY", "")

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for q in queries:
                    resp = await client.post(
                        _TAVILY_API_URL,
                        headers=self._headers(),
                        json={
                            "api_key": key,
                            "query": q,
                            "search_depth": "basic",
                            "include_answer": True,
                            "max_results": 3,
                        },
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer")
                        for item in data.get("results", []):
                            results.append({
                                "entity_type": "market_research",
                                "raw": {
                                    "query": q,
                                    "answer": answer,
                                    "title": item.get("title"),
                                    "url": item.get("url"),
                                    "content": item.get("content"),
                                    "score": item.get("score"),
                                }
                            })
                    await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for idx, item in enumerate(raw):
            raw_data = item.get("raw", {})
            url = raw_data.get("url", f"tavily_search_{idx}")
            payload = {
                "query": raw_data.get("query"),
                "headline": raw_data.get("title"),
                "source_url": url,
                "summary": raw_data.get("content", "")[:1200],
                "ai_synthesis": raw_data.get("answer"),
                "relevance_score": raw_data.get("score", 0.85),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            rec = self.make_normalized_record(
                company_id="default",
                entity_type="external_market_fact",
                entity_id=f"tavily_{idx}_{hash(url) % 100000}",
                payload=payload,
                provenance_type=ProvenanceType.EXTERNAL_RESEARCH,
            )
            normalized.append(rec)
        return normalized
