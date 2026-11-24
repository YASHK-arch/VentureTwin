"""
Zendesk connector for VentureTwin — Customer domain.

Uses Basic auth (email + API token) to fetch tickets, users, and ticket metrics.
Supports synthetic ticket generation for sandbox subdomains.
"""

import asyncio
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="zendesk",
    display_name="Zendesk",
    agent_domain="customer",
    environment="sandbox",
    credential_env_vars=["ZENDESK_SUBDOMAIN", "ZENDESK_EMAIL", "ZENDESK_API_TOKEN"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)


class ZendeskConnector(AbstractConnector):
    """Zendesk Support API connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _base_url(self) -> str:
        subdomain = self._credentials.get("ZENDESK_SUBDOMAIN", "")
        return f"https://{subdomain}.zendesk.com/api/v2"

    def _auth_header(self) -> str:
        email = self._credentials.get("ZENDESK_EMAIL", "")
        token = self._credentials.get("ZENDESK_API_TOKEN", "")
        encoded = base64.b64encode(f"{email}/token:{token}".encode()).decode()
        return f"Basic {encoded}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url()}/users/me.json",
                    headers=self._headers(),
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.SANDBOX_CONNECTED
                self._error = None
                return {"status": self.status.value, "user": resp.json().get("user", {}).get("email")}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Zendesk auth rejected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"Zendesk unexpected: HTTP {resp.status_code}"
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
        if not self._credentials.get("ZENDESK_SUBDOMAIN"):
            if not self.load_credentials():
                return []
        targets = entity_types or ["tickets", "users"]
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for entity in targets:
                    url = f"{self._base_url()}/{entity}.json"
                    next_url: Optional[str] = url
                    while next_url:
                        params: Dict[str, Any] = {}
                        if since and entity == "tickets":
                            params["start_time"] = since
                            # Use incremental export for tickets
                            resp = await client.get(
                                f"{self._base_url()}/incremental/tickets.json",
                                headers=self._headers(),
                                params={"start_time": "0"},
                                timeout=15,
                            )
                        else:
                            resp = await client.get(next_url, headers=self._headers(), params=params, timeout=15)
                        if resp.status_code != 200:
                            break
                        data = resp.json()
                        items = data.get(entity, data.get("results", []))
                        for item in items:
                            item["_entity_type"] = entity.rstrip("s")
                        results.extend(items)
                        next_url = data.get("next_page")
                        await asyncio.sleep(0.1)
                        if since:
                            break  # incremental mode; don't follow next_page here
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("_entity_type", "unknown")
            entity_id = str(item.get("id", ""))
            if entity_type == "ticket":
                payload = {
                    "subject": item.get("subject"),
                    "status": item.get("status"),
                    "priority": item.get("priority"),
                    "type": item.get("type"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "requester_id": item.get("requester_id"),
                    "assignee_id": item.get("assignee_id"),
                    "satisfaction_rating": (item.get("satisfaction_rating") or {}).get("score"),
                }
            elif entity_type == "user":
                payload = {
                    "name": item.get("name"),
                    "email": item.get("email"),
                    "role": item.get("role"),
                    "created_at": item.get("created_at"),
                    "time_zone": item.get("time_zone"),
                }
            else:
                payload = {k: v for k, v in item.items() if not k.startswith("_")}
            normalized.append(
                self.make_normalized_record(
                    company_id="default",
                    entity_type=entity_type,
                    entity_id=entity_id,
                    payload=payload,
                    provenance_type=ProvenanceType.REAL_API,
                )
            )
        return normalized

    async def generate_synthetic_dataset(self, company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create tickets with statuses/comments in Zendesk sandbox."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        tickets = gen.generate_support_tickets(customers=gen.generate_customer_base(10), count=20)
        created = 0
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for t in tickets[:20]:
                    body = {
                        "ticket": {
                            "subject": t.get("subject", "Support request"),
                            "comment": {"body": t.get("description", "Generated by VentureTwin.")},
                            "priority": t.get("priority", "normal"),
                            "status": t.get("status", "open"),
                        }
                    }
                    resp = await client.post(
                        f"{self._base_url()}/tickets.json",
                        headers=self._headers(),
                        json=body,
                        timeout=10,
                    )
                    if resp.status_code in (200, 201):
                        created += 1
                    await asyncio.sleep(0.2)
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {
            "status": "generated",
            "tickets_created": created,
            "provenance": ProvenanceType.SYNTHETIC_EXTERNAL.value,
        }
