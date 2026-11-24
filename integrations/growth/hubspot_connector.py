"""
HubSpot CRM connector for VentureTwin — Growth domain.

Fetches contacts, companies, and deals via HubSpot CRM API v3.
Supports synthetic dataset generation using the HubSpot Test portal.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="hubspot",
    display_name="HubSpot CRM",
    agent_domain="growth",
    environment="developer",
    credential_env_vars=["HUBSPOT_ACCESS_TOKEN"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_BASE = "https://api.hubapi.com"


class HubSpotConnector(AbstractConnector):
    """HubSpot CRM API v3 connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self._credentials['HUBSPOT_ACCESS_TOKEN']}"}
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{_BASE}/crm/v3/objects/contacts",
                    headers=headers,
                    params={"limit": 1},
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"HubSpot auth rejected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"Unexpected response: HTTP {resp.status_code}"
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
        if not self._credentials.get("HUBSPOT_ACCESS_TOKEN"):
            if not self.load_credentials():
                return []
        targets = entity_types or ["contacts", "companies", "deals"]
        headers = {"Authorization": f"Bearer {self._credentials['HUBSPOT_ACCESS_TOKEN']}"}
        results: List[Dict[str, Any]] = []
        props_map = {
            "contacts": "email,firstname,lastname,jobtitle,phone,company,lifecyclestage,createdate",
            "companies": "name,domain,industry,numberofemployees,annualrevenue,city,state,country,createdate",
            "deals": "dealname,amount,dealstage,pipeline,closedate,createdate",
        }
        type_map = {
            "contacts": "contact",
            "companies": "company",
            "deals": "deal",
        }
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for obj_type in targets:
                    after: Optional[str] = None
                    while True:
                        params: Dict[str, Any] = {"limit": 100}
                        if obj_type in props_map:
                            params["properties"] = props_map[obj_type]
                        if after:
                            params["after"] = after
                        resp = await client.get(
                            f"{_BASE}/crm/v3/objects/{obj_type}",
                            headers=headers,
                            params=params,
                            timeout=15,
                        )
                        if resp.status_code != 200:
                            break
                        data = resp.json()
                        for item in data.get("results", []):
                            item["_entity_type"] = type_map.get(obj_type, obj_type.rstrip("s"))
                        results.extend(data.get("results", []))
                        paging = data.get("paging", {})
                        next_page = paging.get("next", {}).get("after")
                        if next_page:
                            after = next_page
                        else:
                            break
                        await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("_entity_type", "unknown")
            entity_id = item.get("id", "")
            props = item.get("properties", {})
            if entity_type == "contact":
                payload = {
                    "email": props.get("email"),
                    "firstname": props.get("firstname"),
                    "lastname": props.get("lastname"),
                    "jobtitle": props.get("jobtitle"),
                    "phone": props.get("phone"),
                    "company": props.get("company"),
                    "lifecyclestage": props.get("lifecyclestage"),
                    "createdate": props.get("createdate"),
                }
            elif entity_type in ("company", "companies", "companie", "compan"):
                payload = {
                    "name": props.get("name"),
                    "domain": props.get("domain"),
                    "industry": props.get("industry"),
                    "numberofemployees": props.get("numberofemployees"),
                    "annualrevenue": props.get("annualrevenue"),
                    "city": props.get("city"),
                    "state": props.get("state"),
                    "country": props.get("country"),
                }
            elif entity_type == "deal":
                payload = {
                    "dealname": props.get("dealname"),
                    "amount": props.get("amount"),
                    "dealstage": props.get("dealstage"),
                    "closedate": props.get("closedate"),
                    "pipeline": props.get("pipeline"),
                }
            else:
                payload = props
            normalized.append(
                self.make_normalized_record(
                    company_id="default",
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    payload=payload,
                    provenance_type=ProvenanceType.REAL_API,
                )
            )
        return normalized

    async def generate_synthetic_dataset(self, company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create realistic CRM leads/deals via HubSpot API (developer test portal)."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        leads = gen.generate_marketing_leads(count=30)
        headers = {
            "Authorization": f"Bearer {self._credentials.get('HUBSPOT_ACCESS_TOKEN', '')}",
            "Content-Type": "application/json",
        }
        created = 0
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for lead in leads[:30]:
                    body = {
                        "properties": {
                            "email": lead.get("email"),
                            "firstname": lead.get("firstname"),
                            "lastname": lead.get("lastname"),
                            "company": lead.get("company"),
                            "phone": lead.get("phone", ""),
                            "lifecyclestage": "lead",
                        }
                    }
                    resp = await client.post(
                        f"{_BASE}/crm/v3/objects/contacts",
                        headers=headers,
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
