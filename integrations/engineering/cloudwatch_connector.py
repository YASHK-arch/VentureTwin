"""
AWS CloudWatch connector for VentureTwin — Engineering domain.

Uses httpx with manually implemented AWS SigV4 signing (no boto3 dependency).
Fetches metric statistics and supports synthetic metric data injection.
"""

import asyncio
import hashlib
import hmac
import json
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="cloudwatch",
    display_name="AWS CloudWatch",
    agent_domain="engineering",
    environment="sandbox",
    credential_env_vars=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)


class CloudWatchConnector(AbstractConnector):
    """AWS CloudWatch connector with manual SigV4 signing."""

    def __init__(self):
        super().__init__(_CONFIG)

    # ------------------------------------------------------------------
    # AWS SigV4 helpers
    # ------------------------------------------------------------------

    def _sign(self, key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    def _get_signature_key(self, key: str, date_stamp: str, region: str, service: str) -> bytes:
        k_date = self._sign(("AWS4" + key).encode("utf-8"), date_stamp)
        k_region = self._sign(k_date, region)
        k_service = self._sign(k_region, service)
        k_signing = self._sign(k_service, "aws4_request")
        return k_signing

    def _sigv4_headers(
        self,
        method: str,
        host: str,
        uri: str,
        query: str,
        body: str,
        region: str,
        service: str,
        access_key: str,
        secret_key: str,
    ) -> Dict[str, str]:
        now = datetime.now(timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        canonical_headers = f"content-type:application/x-www-form-urlencoded\nhost:{host}\nx-amz-date:{amz_date}\n"
        signed_headers = "content-type;host;x-amz-date"
        canonical_request = "\n".join([method, uri, query, canonical_headers, signed_headers, payload_hash])

        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])

        signing_key = self._get_signature_key(secret_key, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return {
            "Authorization": authorization,
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Amz-Date": amz_date,
        }

    async def _cw_post(self, body_params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """POST a CloudWatch API call and return parsed JSON."""
        import httpx
        region = self._credentials.get("AWS_REGION", "us-east-1")
        access_key = self._credentials.get("AWS_ACCESS_KEY_ID", "")
        secret_key = self._credentials.get("AWS_SECRET_ACCESS_KEY", "")
        host = f"monitoring.{region}.amazonaws.com"
        body = urllib.parse.urlencode(body_params)
        headers = self._sigv4_headers(
            method="POST",
            host=host,
            uri="/",
            query="",
            body=body,
            region=region,
            service="monitoring",
            access_key=access_key,
            secret_key=secret_key,
        )
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://{host}/",
                    headers=headers,
                    content=body.encode("utf-8"),
                    timeout=15,
                )
            if resp.status_code == 200:
                # CloudWatch returns XML; parse it simply
                return {"raw_xml": resp.text, "status_code": 200}
            return {"status_code": resp.status_code, "error": resp.text[:300]}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            result = await self._cw_post({"Action": "ListMetrics", "Version": "2010-08-01"})
            if result and result.get("status_code") == 200:
                self.status = ConnectionStatus.SANDBOX_CONNECTED
                self._error = None
                return {"status": self.status.value}
            sc = result.get("status_code") if result else None
            if sc in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"CloudWatch auth rejected: HTTP {sc}"
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"CloudWatch error: {result}"
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
        return result.get("status") in ("connected", "sandbox_connected")

    async def fetch_data(
        self,
        entity_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._credentials.get("AWS_ACCESS_KEY_ID"):
            if not self.load_credentials():
                return []
        metrics_to_fetch = entity_types or ["CPUUtilization", "MemoryUtilization", "RequestCount", "Latency"]
        end_time = datetime.now(timezone.utc)
        if since:
            try:
                start_time = datetime.fromisoformat(since.replace("Z", "+00:00"))
            except Exception:
                start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(days=7)
        results: List[Dict[str, Any]] = []
        for metric_name in metrics_to_fetch:
            params = {
                "Action": "GetMetricStatistics",
                "Version": "2010-08-01",
                "Namespace": "VentureTwin/Application",
                "MetricName": metric_name,
                "StartTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "EndTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Period": "3600",
                "Statistics.member.1": "Average",
                "Statistics.member.2": "Maximum",
            }
            result = await self._cw_post(params)
            if result:
                result["_entity_type"] = "metric"
                result["_metric_name"] = metric_name
                results.append(result)
            await asyncio.sleep(0.1)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            metric_name = item.get("_metric_name", "unknown")
            payload = {
                "metric_name": metric_name,
                "namespace": "VentureTwin/Application",
                "raw_response": item.get("raw_xml", "")[:500],
                "status_code": item.get("status_code"),
            }
            normalized.append(
                self.make_normalized_record(
                    company_id="default",
                    entity_type="cloudwatch_metric",
                    entity_id=metric_name,
                    payload=payload,
                    provenance_type=ProvenanceType.REAL_API,
                )
            )
        return normalized

    async def generate_synthetic_dataset(self, company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """PutMetricData for CPU/memory/latency/request counts."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        metrics_data = gen.generate_infrastructure_metrics(days_back=7)
        sent = 0
        for metric in metrics_data[:50]:
            params: Dict[str, str] = {
                "Action": "PutMetricData",
                "Version": "2010-08-01",
                "Namespace": "VentureTwin/Application",
                "MetricData.member.1.MetricName": metric.get("metric_name", "CPUUtilization"),
                "MetricData.member.1.Value": str(metric.get("value", 0)),
                "MetricData.member.1.Unit": metric.get("unit", "Percent"),
                "MetricData.member.1.Timestamp": metric.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")),
            }
            result = await self._cw_post(params)
            if result and result.get("status_code") == 200:
                sent += 1
            await asyncio.sleep(0.1)
        return {
            "status": "generated",
            "metrics_sent": sent,
            "provenance": ProvenanceType.SYNTHETIC_EXTERNAL.value,
        }
