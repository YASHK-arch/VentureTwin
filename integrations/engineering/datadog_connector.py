"""
Datadog connector for VentureTwin — Engineering & Infrastructure domain.

Collects cloud infrastructure metrics, API latencies, error budgets, and service availability.
Supports proxying via Nango or direct Datadog REST API v1/v2.
Generates realistic multi-tier cloud infrastructure telemetry for B2B SaaS (Shopify/Nextcloud).
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
    connector_id="datadog",
    display_name="Datadog",
    agent_domain="engineering",
    environment="developer",
    credential_env_vars=["DATADOG_API_KEY", "DATADOG_APP_KEY"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_BASE_URL = "https://api.datadoghq.com"


class DatadogConnector(AbstractConnector):
    """Datadog observability and infrastructure performance connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _get_nango_connection_id(self, company_id: str = "default") -> Optional[str]:
        conn = get_connection(company_id=company_id, integration_id=self.config.connector_id)
        if conn and conn.get("nango_connection_id"):
            return conn["nango_connection_id"]
        return None

    def _headers(self) -> Dict[str, str]:
        return {
            "DD-API-KEY": self._credentials.get("DATADOG_API_KEY", ""),
            "DD-APPLICATION-KEY": self._credentials.get("DATADOG_APP_KEY", ""),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

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
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_BASE_URL}/api/v1/validate",
                    headers=self._headers(),
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "valid": True}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Datadog authentication rejected: HTTP {resp.status_code}"
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
                    endpoint="/api/v1/events",
                    method="GET",
                )
                if isinstance(res.get("data"), list):
                    return res["data"]
            except Exception:
                pass

        if not self._credentials.get("DATADOG_API_KEY"):
            if not self.load_credentials():
                return []

        results: List[Dict[str, Any]] = []
        try:
            import httpx
            now_ts = int(datetime.now(timezone.utc).timestamp())
            start_ts = now_ts - 86400
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_BASE_URL}/api/v1/events",
                    headers=self._headers(),
                    params={"start": start_ts, "end": now_ts},
                    timeout=15,
                )
            if resp.status_code == 200:
                results.extend(resp.json().get("events", []))
        except Exception:
            pass
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        company_id = "default"
        for item in raw:
            entity_type = "incident" if "alert" in str(item).lower() else "infra_metric"
            entity_id = item.get("id") or f"dd_{hash(str(item)) & 0xFFFFFF}"
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
        """Generates synthetic Datadog infrastructure telemetry."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        company_name = company_profile.get("company_name", "ShopifyPlatform")

        records: List[Dict[str, Any]] = []
        metrics_catalog = [
            ("system.cpu.utilization", 28.5, 4.2, "%"),
            ("system.mem.used_pct", 62.0, 5.0, "%"),
            ("http.api.latency.p95", 138.0, 18.0, "ms"),
            ("http.api.latency.p99", 285.0, 35.0, "ms"),
            ("http.requests.5xx_rate", 0.04, 0.02, "%"),
            ("db.connection_pool.saturation", 41.0, 8.0, "%"),
            ("service.uptime.sla", 99.96, 0.02, "%"),
        ]

        for i in range(count):
            metric_name, base_val, std_dev, unit = gen.rng.choice(metrics_catalog)
            val = round(base_val + gen.rng.uniform(-std_dev, std_dev), 2)
            timestamp = datetime.now(timezone.utc).isoformat()

            metric_entry = {
                "metric": metric_name,
                "value": val,
                "unit": unit,
                "service": f"{company_name.lower()}-backend-api",
                "host": f"node-{gen.rng.randint(1, 12)}.us-east-1",
                "timestamp": timestamp,
                "status": "warning" if (unit == "%" and val > 80.0) else "ok",
            }

            records.append(self.make_normalized_record(
                company_id="default",
                entity_type="infra_metric",
                entity_id=f"dd_met_{10000 + i}",
                payload=metric_entry,
                provenance_type=ProvenanceType.SYNTHETIC_EXTERNAL,
            ))

        return {
            "status": "success",
            "records": records,
            "records_created": len(records),
            "message": f"Generated {len(records)} synthetic Datadog telemetry records for {company_name}",
        }
