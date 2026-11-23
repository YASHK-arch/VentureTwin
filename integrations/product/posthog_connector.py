"""
PostHog connector for VentureTwin — Product domain.

Fetches events, persons, feature flags, and insights from PostHog Cloud or self-hosted API.
Supports synthetic product analytics dataset ingestion.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="posthog",
    display_name="PostHog",
    agent_domain="product",
    environment="cloud",
    credential_env_vars=["POSTHOG_API_KEY", "POSTHOG_PROJECT_ID"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)


class PostHogConnector(AbstractConnector):
    """PostHog product analytics connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _host(self) -> str:
        return os.getenv("POSTHOG_HOST", "app.posthog.com").strip()

    def _base_url(self) -> str:
        host = self._host()
        if not host.startswith("http"):
            host = f"https://{host}"
        return host

    def _headers(self) -> Dict[str, str]:
        key = self._credentials.get("POSTHOG_API_KEY", "")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        project_id = self._credentials.get("POSTHOG_PROJECT_ID", "")
        url = f"{self._base_url()}/api/projects/{project_id}/"
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self._headers(), timeout=12)
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "project_id": project_id, "name": resp.json().get("name")}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"PostHog authentication failed: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"PostHog unexpected status: HTTP {resp.status_code}"
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
        if not self._credentials.get("POSTHOG_API_KEY"):
            if not self.load_credentials():
                return []
        project_id = self._credentials.get("POSTHOG_PROJECT_ID", "")
        base = self._base_url()
        targets = entity_types or ["events", "feature_flags", "insights"]
        results: List[Dict[str, Any]] = []

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for target in targets:
                    url = f"{base}/api/projects/{project_id}/{target}/"
                    resp = await client.get(url, headers=self._headers(), params={"limit": 100}, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("results", data if isinstance(data, list) else [])
                        for item in items:
                            results.append({
                                "entity_type": target.rstrip("s"),
                                "raw": item,
                            })
                    await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("entity_type", "event")
            raw_data = item.get("raw", {})
            entity_id = str(raw_data.get("id") or raw_data.get("uuid") or raw_data.get("key") or hash(str(raw_data)))
            payload = {
                "event_name": raw_data.get("event"),
                "distinct_id": raw_data.get("distinct_id"),
                "properties": raw_data.get("properties", {}),
                "timestamp": raw_data.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            }
            rec = self.make_normalized_record(
                company_id="default",
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
                provenance_type=ProvenanceType.REAL_API,
            )
            normalized.append(rec)
        return normalized

    async def generate_synthetic_dataset(
        self,
        company_profile: Dict[str, Any],
        count: int = 50,
    ) -> Dict[str, Any]:
        """Ingests or outputs synthetic product activity events (feature adoption, signups, onboarding)."""
        events = []
        now = datetime.now(timezone.utc).isoformat()
        company_name = company_profile.get("company_name", "ShopifyMerchant")
        sample_events = [
            "dashboard_viewed", "checkout_completed", "feature_exported",
            "report_generated", "integration_connected", "plan_upgraded"
        ]

        for i in range(count):
            user_id = f"user_{hash(company_name) % 1000 + i}"
            event_name = sample_events[i % len(sample_events)]
            payload = {
                "event": event_name,
                "distinct_id": user_id,
                "properties": {
                    "company": company_name,
                    "plan": "Pro" if i % 2 == 0 else "Enterprise",
                    "source": "venturetwin_synthetic_generator",
                    "duration_sec": 45 + (i * 7) % 300,
                },
                "timestamp": now,
            }
            events.append(self.make_normalized_record(
                company_id=str(company_profile.get("id", "default")),
                entity_type="product_event",
                entity_id=f"posthog_syn_{i}",
                payload=payload,
                provenance_type=ProvenanceType.SYNTHETIC_EXTERNAL if self.status == ConnectionStatus.CONNECTED else ProvenanceType.SYNTHETIC_INTERNAL,
            ))

        # If connected to live PostHog API, batch capture
        if self.status == ConnectionStatus.CONNECTED:
            try:
                import httpx
                capture_url = f"{self._base_url()}/capture/"
                batch = [{
                    "event": e["payload"]["event"],
                    "distinct_id": e["payload"]["distinct_id"],
                    "properties": e["payload"]["properties"],
                    "timestamp": e["payload"]["timestamp"],
                } for e in events[:25]]
                async with httpx.AsyncClient() as client:
                    await client.post(capture_url, json={"api_key": self._credentials.get("POSTHOG_API_KEY"), "batch": batch}, timeout=10)
            except Exception:
                pass

        return {
            "records_created": len(events),
            "status": "success",
            "records": events,
            "message": f"Generated {len(events)} synthetic PostHog product analytics events."
        }
