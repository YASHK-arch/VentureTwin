"""
Intercom connector for VentureTwin — Customer domain.

Fetches contacts, conversations, and stats from the Intercom API.
Supports synthetic dataset generation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="intercom",
    display_name="Intercom",
    agent_domain="customer",
    environment="developer",
    credential_env_vars=["INTERCOM_ACCESS_TOKEN"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_BASE = "https://api.intercom.io"


class IntercomConnector(AbstractConnector):
    """Intercom API connector for customer success data."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._credentials.get('INTERCOM_ACCESS_TOKEN', '')}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{_BASE}/me", headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "app": resp.json().get("app", {}).get("id_code")}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Intercom auth rejected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"Intercom unexpected: HTTP {resp.status_code}"
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
        if not self._credentials.get("INTERCOM_ACCESS_TOKEN"):
            if not self.load_credentials():
                return []
        targets = entity_types or ["contacts", "conversations"]
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for entity in targets:
                    page = 1
                    while True:
                        params: Dict[str, Any] = {"per_page": 50, "page": page}
                        resp = await client.get(
                            f"{_BASE}/{entity}",
                            headers=self._headers(),
                            params=params,
                            timeout=15,
                        )
                        if resp.status_code != 200:
                            break
                        data = resp.json()
                        items = data.get("data", data.get("conversations", []))
                        for item in items:
                            item["_entity_type"] = entity.rstrip("s")
                        results.extend(items)
                        pages = data.get("pages", {})
                        total_pages = pages.get("total_pages", 1)
                        if page >= total_pages:
                            break
                        page += 1
                        await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("_entity_type", "unknown")
            entity_id = str(item.get("id", ""))
            if entity_type == "contact":
                payload = {
                    "email": item.get("email"),
                    "name": item.get("name"),
                    "role": item.get("role"),
                    "created_at": item.get("created_at"),
                    "last_seen_at": item.get("last_seen_at"),
                    "signed_up_at": item.get("signed_up_at"),
                }
            elif entity_type == "conversation":
                payload = {
                    "state": item.get("state"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                    "read": item.get("read"),
                    "assignee_type": (item.get("assignee") or {}).get("type"),
                    "first_contact_reply": (item.get("first_contact_reply") or {}).get("created_at"),
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
        """Create test contacts and conversations in Intercom developer mode."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        customers = gen.generate_customer_base(count=20)
        created = 0
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for c in customers[:20]:
                    body = {
                        "role": "user",
                        "email": c["email"],
                        "name": c["name"],
                    }
                    resp = await client.post(
                        f"{_BASE}/contacts",
                        headers=self._headers(),
                        json=body,
                        timeout=10,
                    )
                    if resp.status_code in (200, 201):
                        created += 1
                    await asyncio.sleep(0.1)
        except Exception as e:
            return {"status": "error", "error": str(e)}
        return {
            "status": "generated",
            "contacts_created": created,
            "provenance": ProvenanceType.SYNTHETIC_EXTERNAL.value,
        }
