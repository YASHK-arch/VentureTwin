"""
Amplitude connector for VentureTwin — Product domain.

Analyzes product feature adoption, daily active users, retention funnels, and user cohorts.
Supports proxying via Nango or direct Amplitude REST API.
Generates realistic multi-tier product analytics telemetry for B2B SaaS (Shopify/Nextcloud).
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
    connector_id="amplitude",
    display_name="Amplitude",
    agent_domain="product",
    environment="cloud",
    credential_env_vars=["AMPLITUDE_API_KEY", "AMPLITUDE_SECRET_KEY"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_BASE_URL = "https://api2.amplitude.com"


class AmplitudeConnector(AbstractConnector):
    """Amplitude product analytics and user engagement connector."""

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
            api_key = self._credentials["AMPLITUDE_API_KEY"]
            secret_key = self._credentials["AMPLITUDE_SECRET_KEY"]
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://amplitude.com/api/2/taxonomy/event-types",
                    auth=(api_key, secret_key),
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "authenticated": True}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Amplitude auth failed: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
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
                    endpoint="/2/events/list",
                    method="GET",
                )
                if isinstance(res.get("data"), list):
                    return res["data"]
            except Exception:
                pass

        if not self._credentials.get("AMPLITUDE_API_KEY"):
            if not self.load_credentials():
                return []

        results: List[Dict[str, Any]] = []
        try:
            import httpx
            api_key = self._credentials["AMPLITUDE_API_KEY"]
            secret_key = self._credentials["AMPLITUDE_SECRET_KEY"]
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://amplitude.com/api/2/events/list",
                    auth=(api_key, secret_key),
                    timeout=15,
                )
            if resp.status_code == 200:
                results.extend(resp.json().get("data", []))
        except Exception:
            pass
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        company_id = "default"
        for item in raw:
            entity_type = "product_analytics"
            entity_id = item.get("id") or item.get("event_type") or f"amp_{hash(str(item)) & 0xFFFFFF}"
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
        """Generates synthetic feature adoption, user session, and retention records."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        company_name = company_profile.get("company_name", "ShopifyApp")

        records: List[Dict[str, Any]] = []
        features = [
            ("checkout_customizer", 0.74, "Checkout & Payment Experience"),
            ("inventory_sync_v2", 0.62, "Supply Chain Automation"),
            ("ai_product_descriptions", 0.45, "Generative Merchandising"),
            ("multi_currency_converter", 0.38, "Global Sales & Tax"),
            ("headless_storefront_api", 0.19, "Developer Ecosystem"),
            ("custom_reports_builder", 0.52, "Business Intelligence"),
        ]

        for i in range(count):
            feat, adoption_rate, cat = gen.rng.choice(features)
            variation = round(adoption_rate + gen.rng.uniform(-0.06, 0.06), 3)

            entry = {
                "feature_name": feat,
                "category": cat,
                "adoption_rate": variation,
                "daily_active_users_using_feature": int(1850 * variation),
                "weekly_stickiness_ratio": round(variation * 0.72, 2),
                "d30_retention_cohort_pct": round(68.5 + gen.rng.uniform(-4.0, 5.0), 1),
                "company": company_name,
                "measured_at": datetime.now(timezone.utc).isoformat(),
            }

            records.append(self.make_normalized_record(
                company_id="default",
                entity_type="product_analytics",
                entity_id=f"amp_feat_{10000 + i}",
                payload=entry,
                provenance_type=ProvenanceType.SYNTHETIC_EXTERNAL,
            ))

        return {
            "status": "success",
            "records": records,
            "records_created": len(records),
            "message": f"Generated {len(records)} synthetic Amplitude feature telemetry records for {company_name}",
        }
