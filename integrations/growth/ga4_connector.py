"""
Google Analytics 4 connector for VentureTwin — Growth domain.

Validates via Measurement Protocol and queries the GA4 Data API.
Supports synthetic event generation via the GA4 Measurement Protocol.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="ga4",
    display_name="Google Analytics 4",
    agent_domain="growth",
    environment="test",
    credential_env_vars=[
        "GA4_MEASUREMENT_ID",
        "GA4_API_SECRET",
        "GA4_PROPERTY_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_MP_URL = "https://www.google-analytics.com/mp/collect"
_DATA_API_BASE = "https://analyticsdata.googleapis.com/v1beta"


class GA4Connector(AbstractConnector):
    """Google Analytics 4 connector (Measurement Protocol + Data API)."""

    def __init__(self):
        super().__init__(_CONFIG)

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            measurement_id = self._credentials["GA4_MEASUREMENT_ID"]
            api_secret = self._credentials["GA4_API_SECRET"]
            test_payload = {
                "client_id": "venturetwin_connection_test",
                "events": [{"name": "connection_test", "params": {"test": True}}],
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    _MP_URL,
                    params={"measurement_id": measurement_id, "api_secret": api_secret},
                    json=test_payload,
                    timeout=10,
                )
            # GA4 MP returns 204 on success (no content)
            if resp.status_code in (200, 204):
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"GA4 auth error: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"GA4 unexpected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
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
        """Query GA4 Data API for sessions, page views, conversions."""
        if not self._credentials.get("GA4_PROPERTY_ID"):
            if not self.load_credentials():
                return []
        property_id = self._credentials["GA4_PROPERTY_ID"]
        # We need a service account token from GOOGLE_APPLICATION_CREDENTIALS
        token = await self._get_service_account_token()
        if not token:
            return []
        end_date = "today"
        start_date = since[:10] if since else "30daysAgo"
        reports = [
            {
                "_report": "sessions",
                "dimensions": [{"name": "date"}],
                "metrics": [
                    {"name": "sessions"},
                    {"name": "totalUsers"},
                    {"name": "newUsers"},
                    {"name": "bounceRate"},
                ],
            },
            {
                "_report": "page_views",
                "dimensions": [{"name": "pagePath"}],
                "metrics": [{"name": "screenPageViews"}, {"name": "averageSessionDuration"}],
            },
            {
                "_report": "conversions",
                "dimensions": [{"name": "eventName"}],
                "metrics": [{"name": "eventCount"}, {"name": "conversions"}],
            },
        ]
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            url = f"{_DATA_API_BASE}/properties/{property_id}:runReport"
            async with httpx.AsyncClient() as client:
                for report in reports:
                    report_name = report.pop("_report")
                    body = {
                        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
                        "dimensions": report["dimensions"],
                        "metrics": report["metrics"],
                    }
                    resp = await client.post(url, headers=headers, json=body, timeout=15)
                    if resp.status_code == 200:
                        data = resp.json()
                        data["_entity_type"] = "ga4_report"
                        data["_report_name"] = report_name
                        results.append(data)
                    await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    async def _get_service_account_token(self) -> Optional[str]:
        """Obtain a Google API Bearer token from the service account JSON file."""
        import os, json, time
        import hashlib, hmac
        cred_path = self._credentials.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if not cred_path or not os.path.exists(cred_path):
            self._error = "GOOGLE_APPLICATION_CREDENTIALS file not found"
            return None
        try:
            with open(cred_path, "r") as f:
                sa = json.load(f)
            # Build a JWT manually using RSA — requires cryptography package
            # We gracefully fail if unavailable
            try:
                from cryptography.hazmat.primitives import serialization, hashes
                from cryptography.hazmat.primitives.asymmetric import padding
                from cryptography.hazmat.backends import default_backend
                import base64 as b64
                import json as _json
                now = int(time.time())
                header = b64.urlsafe_b64encode(_json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=")
                claims = {
                    "iss": sa["client_email"],
                    "scope": "https://www.googleapis.com/auth/analytics.readonly",
                    "aud": "https://oauth2.googleapis.com/token",
                    "exp": now + 3600,
                    "iat": now,
                }
                payload_b64 = b64.urlsafe_b64encode(_json.dumps(claims).encode()).rstrip(b"=")
                signing_input = header + b"." + payload_b64
                private_key = serialization.load_pem_private_key(
                    sa["private_key"].encode(), password=None, backend=default_backend()
                )
                signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
                sig_b64 = b64.urlsafe_b64encode(signature).rstrip(b"=")
                jwt = (signing_input + b"." + sig_b64).decode()
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt},
                        timeout=10,
                    )
                if resp.status_code == 200:
                    return resp.json().get("access_token")
                return None
            except ImportError:
                self._error = "cryptography package not installed; GA4 Data API unavailable"
                return None
        except Exception as e:
            self._error = str(e)
            return None

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            report_name = item.get("_report_name", "unknown")
            rows = item.get("rows", [])
            for i, row in enumerate(rows):
                dim_headers = [d.get("name") for d in item.get("dimensionHeaders", [])]
                met_headers = [m.get("name") for m in item.get("metricHeaders", [])]
                dim_values = [v.get("value") for v in row.get("dimensionValues", [])]
                met_values = [v.get("value") for v in row.get("metricValues", [])]
                payload = dict(zip(dim_headers, dim_values))
                payload.update(dict(zip(met_headers, met_values)))
                payload["report"] = report_name
                normalized.append(
                    self.make_normalized_record(
                        company_id="default",
                        entity_type="ga4_report_row",
                        entity_id=f"{report_name}_{i}",
                        payload=payload,
                        provenance_type=ProvenanceType.REAL_API,
                    )
                )
        return normalized

    async def generate_synthetic_dataset(self, company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Send batched synthetic events via GA4 Measurement Protocol."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        events_data = gen.generate_analytics_events(days_back=30)
        if not self._credentials.get("GA4_MEASUREMENT_ID"):
            self.load_credentials()
        measurement_id = self._credentials.get("GA4_MEASUREMENT_ID", "")
        api_secret = self._credentials.get("GA4_API_SECRET", "")
        sent = 0
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                # GA4 MP accepts up to 25 events per request
                batch = []
                for ev in events_data:
                    batch.append({"name": ev.get("event_name", "page_view"), "params": ev.get("params", {})})
                    if len(batch) >= 25:
                        payload = {"client_id": ev.get("client_id", "synthetic_user"), "events": batch}
                        await client.post(
                            _MP_URL,
                            params={"measurement_id": measurement_id, "api_secret": api_secret},
                            json=payload,
                            timeout=10,
                        )
                        sent += len(batch)
                        batch = []
                        await asyncio.sleep(0.1)
                if batch:
                    payload = {"client_id": "synthetic_user_last", "events": batch}
                    await client.post(
                        _MP_URL,
                        params={"measurement_id": measurement_id, "api_secret": api_secret},
                        json=payload,
                        timeout=10,
                    )
                    sent += len(batch)
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {
            "status": "generated",
            "events_sent": sent,
            "provenance": ProvenanceType.SYNTHETIC_EXTERNAL.value,
        }
