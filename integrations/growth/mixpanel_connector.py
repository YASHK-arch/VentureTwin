"""
Mixpanel connector for VentureTwin — Growth domain.

Tracks user events, conversion funnels, and retention analytics.
Supports proxying via Nango or direct Mixpanel Ingestion / Query API.
Generates realistic multi-stage user journey telemetry for B2B SaaS (Shopify/Nextcloud).
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)
from integrations.nango_service import nango_service
from integrations.store import get_connection

_CONFIG = ConnectorConfig(
    connector_id="mixpanel",
    display_name="Mixpanel",
    agent_domain="growth",
    environment="production",
    credential_env_vars=["MIXPANEL_PROJECT_TOKEN", "MIXPANEL_API_SECRET"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_TRACK_URL = "https://api.mixpanel.com/track"
_QUERY_URL = "https://mixpanel.com/api/2.0/events"


class MixpanelConnector(AbstractConnector):
    """Mixpanel product & growth analytics connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _get_nango_connection_id(self, company_id: str = "default") -> Optional[str]:
        conn = get_connection(company_id=company_id, integration_id=self.config.connector_id)
        if conn and conn.get("nango_connection_id"):
            return conn["nango_connection_id"]
        return None

    async def connect(self) -> Dict[str, Any]:
        # Check Nango connection first
        nango_cid = self._get_nango_connection_id()
        if nango_cid:
            self.status = ConnectionStatus.CONNECTED
            self._error = None
            return {"status": self.status.value, "auth_provider": "nango", "connection_id": nango_cid}

        # Check direct credentials
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}

        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            # Validate secret via Mixpanel API
            secret = self._credentials["MIXPANEL_API_SECRET"]
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://mixpanel.com/api/app/me",
                    auth=(secret, ""),
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Mixpanel auth error: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                # If credentials exist and endpoint returned non-401, allow connected
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value}
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._error = str(e)
            return {"status": self.status.value, "error": self._error}

    async def disconnect(self) -> None:
        self.status = ConnectionStatus.NOT_CONNECTED
        self._credentials = {}

    async def validate_connection(self) -> bool:
        result = await self.connect()
        return result.get("status") == "connected"

    async def fetch_data(
        self,
        entity_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        nango_cid = self._get_nango_connection_id()
        if nango_cid and nango_service.is_configured:
            try:
                res = await nango_service.proxy_request(
                    provider_config_key=self.config.connector_id,
                    connection_id=nango_cid,
                    endpoint="/track",
                    method="GET",
                )
                if isinstance(res.get("data"), list):
                    return res["data"]
            except Exception:
                pass

        if not self._credentials.get("MIXPANEL_API_SECRET"):
            if not self.load_credentials():
                return []

        # Direct API fetch
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            secret = self._credentials["MIXPANEL_API_SECRET"]
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    _QUERY_URL,
                    auth=(secret, ""),
                    params={"event": '["$pageview", "signup", "upgrade"]', "type": "general", "unit": "day"},
                    timeout=15,
                )
            if resp.status_code == 200:
                results.append({"type": "events_aggregate", "raw": resp.json()})
        except Exception:
            pass
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        company_id = "default"
        for item in raw:
            entity_type = item.get("type", "growth_event")
            entity_id = item.get("id") or item.get("distinct_id") or f"mp_{hash(str(item)) & 0xFFFFFF}"
            normalized.append(self.make_normalized_record(
                company_id=company_id,
                entity_type=entity_type,
                entity_id=str(entity_id),
                payload=item,
                provenance_type=ProvenanceType.REAL_API,
            ))
        return normalized

    async def generate_synthetic_dataset(
        self,
        company_profile: Dict[str, Any],
        count: int = 50,
    ) -> Dict[str, Any]:
        """Generates synthetic Mixpanel event batches for user conversion funnels."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        company_name = company_profile.get("company_name", "ShopifyStore")

        events: List[Dict[str, Any]] = []
        funnel_steps = [
            ("landing_page_viewed", 1.0),
            ("pricing_page_viewed", 0.65),
            ("signup_started", 0.42),
            ("free_trial_activated", 0.28),
            ("onboarding_step_completed", 0.22),
            ("starter_plan_purchased", 0.12),
            ("pro_expansion_unlocked", 0.04),
        ]

        for i in range(count):
            user_id = f"user_{company_name.lower()[:4]}_{1000 + i}"
            for step_name, probability in funnel_steps:
                if gen.rng.random() <= probability:
                    event = {
                        "event": step_name,
                        "distinct_id": user_id,
                        "time": int(datetime.now(timezone.utc).timestamp()) - gen.rng.randint(60, 86400 * 30),
                        "properties": {
                            "$source": gen.rng.choice(["google", "direct", "twitter", "linkedin", "github"]),
                            "$browser": gen.rng.choice(["Chrome", "Firefox", "Safari", "Edge"]),
                            "plan_tier": "pro" if "pro" in step_name else "starter",
                            "company": company_name,
                        }
                    }
                    events.append(self.make_normalized_record(
                        company_id="default",
                        entity_type="growth_event",
                        entity_id=f"mp_evt_{10000 + len(events)}",
                        payload=event,
                        provenance_type=ProvenanceType.SYNTHETIC_EXTERNAL,
                    ))

        return {
            "status": "success",
            "records": events,
            "records_created": len(events),
            "message": f"Generated {len(events)} synthetic Mixpanel funnel events for {company_name}",
        }
