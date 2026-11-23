"""
Firecrawl connector for VentureTwin — Skeptic / Market Intelligence domain.

Scrapes real-time competitor websites, pricing pages, and product announcements.
Preserves source URLs, retrieval timestamps, and markdown payloads.
NOTE: Returns real external web intelligence, NOT synthetic data.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="firecrawl",
    display_name="Firecrawl",
    agent_domain="intelligence",
    environment="production",
    credential_env_vars=["FIRECRAWL_API_KEY"],
    supports_write=False,
    supports_synthetic_generation=False,
    oauth_required=False,
)

_BASE_URL = "https://api.firecrawl.dev/v1"


class FirecrawlConnector(AbstractConnector):
    """Firecrawl web scraping connector for competitor intelligence."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _headers(self) -> Dict[str, str]:
        key = self._credentials.get("FIRECRAWL_API_KEY", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        # Test key validity with a lightweight scrape or ping
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{_BASE_URL}/scrape",
                    headers=self._headers(),
                    json={"url": "https://example.com", "pageOptions": {"onlyMainContent": True}},
                    timeout=15,
                )
            if resp.status_code in (200, 201):
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "provider": "Firecrawl v1 API"}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Firecrawl API key rejected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                # If key is valid but scrape had an issue or quota, still treat as configured if not 401
                if resp.status_code == 402:
                    self.status = ConnectionStatus.ERROR
                    self._error = "Firecrawl credits exhausted"
                    return {"status": self.status.value, "error": self._error}
                self.status = ConnectionStatus.CONNECTED
                return {"status": self.status.value, "provider": "Firecrawl v1 API"}
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
        """Scrapes default competitor URLs or provided entity targets."""
        if not self._credentials.get("FIRECRAWL_API_KEY"):
            if not self.load_credentials():
                return []
        urls_to_scrape = entity_types or [
            "https://stripe.com/pricing",
            "https://www.shopify.com/pricing",
            "https://linear.app/pricing"
        ]
        results: List[Dict[str, Any]] = []

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for target_url in urls_to_scrape:
                    if not target_url.startswith("http"):
                        continue
                    try:
                        resp = await client.post(
                            f"{_BASE_URL}/scrape",
                            headers=self._headers(),
                            json={"url": target_url, "formats": ["markdown"]},
                            timeout=25,
                        )
                        if resp.status_code in (200, 201):
                            data = resp.json()
                            results.append({
                                "entity_type": "competitor_scrape",
                                "raw": {
                                    "url": target_url,
                                    "markdown": data.get("data", {}).get("markdown", "")[:4000],
                                    "title": data.get("data", {}).get("metadata", {}).get("title"),
                                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                                }
                            })
                    except Exception as scrape_err:
                        results.append({
                            "entity_type": "competitor_scrape_error",
                            "raw": {"url": target_url, "error": str(scrape_err)}
                        })
                    await asyncio.sleep(0.2)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            raw_data = item.get("raw", {})
            url = raw_data.get("url", "unknown")
            entity_id = f"scrape_{hash(url) % 1000000}"
            payload = {
                "source_url": url,
                "title": raw_data.get("title", "Competitor Pricing / Architecture"),
                "summary": raw_data.get("markdown", "")[:1000],
                "retrieved_at": raw_data.get("scraped_at", datetime.now(timezone.utc).isoformat()),
            }
            rec = self.make_normalized_record(
                company_id="default",
                entity_type="market_scrape",
                entity_id=entity_id,
                payload=payload,
                provenance_type=ProvenanceType.EXTERNAL_RESEARCH,
            )
            normalized.append(rec)
        return normalized
