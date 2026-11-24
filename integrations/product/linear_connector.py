"""
Linear connector for VentureTwin — Product domain.

Fetches issues, projects, cycles, and initiatives via Linear GraphQL API.
Supports populating synthetic product roadmap and issue velocity.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="linear",
    display_name="Linear",
    agent_domain="product",
    environment="production",
    credential_env_vars=["LINEAR_API_KEY"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"


class LinearConnector(AbstractConnector):
    """Linear product management GraphQL connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _headers(self) -> Dict[str, str]:
        key = self._credentials.get("LINEAR_API_KEY", "")
        return {
            "Authorization": key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        query = "query { viewer { id name email } }"
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(_GRAPHQL_ENDPOINT, headers=self._headers(), json={"query": query}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if "errors" in data and not data.get("data", {}).get("viewer"):
                    self.status = ConnectionStatus.ERROR
                    self._error = f"Linear GraphQL error: {data['errors'][0].get('message')}"
                    return {"status": self.status.value, "error": self._error}
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                viewer = data.get("data", {}).get("viewer", {})
                return {"status": self.status.value, "viewer": viewer.get("name") or viewer.get("id")}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Linear authentication failed: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"Linear unexpected status: HTTP {resp.status_code}"
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
        if not self._credentials.get("LINEAR_API_KEY"):
            if not self.load_credentials():
                return []
        results: List[Dict[str, Any]] = []
        query = """
        query {
          issues(first: 100, orderBy: updatedAt) {
            nodes {
              id
              identifier
              title
              description
              priority
              estimate
              state { name type }
              project { id name }
              cycle { id number name }
              labels { nodes { name } }
              createdAt
              updatedAt
            }
          }
          projects(first: 25) {
            nodes {
              id
              name
              description
              state
              progress
              targetDate
              startDate
              url
            }
          }
          cycles(first: 10) {
            nodes {
              id
              number
              name
              startsAt
              endsAt
              progress
            }
          }
        }
        """
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(_GRAPHQL_ENDPOINT, headers=self._headers(), json={"query": query}, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                for issue in data.get("issues", {}).get("nodes", []):
                    results.append({"entity_type": "issue", "raw": issue})
                for proj in data.get("projects", {}).get("nodes", []):
                    results.append({"entity_type": "project", "raw": proj})
                for cycle in data.get("cycles", {}).get("nodes", []):
                    results.append({"entity_type": "cycle", "raw": cycle})
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("entity_type", "issue")
            raw_data = item.get("raw", {})
            entity_id = str(raw_data.get("id") or hash(str(raw_data)))
            if entity_type == "issue":
                labels = [l.get("name") for l in (raw_data.get("labels") or {}).get("nodes", [])] if isinstance(raw_data.get("labels"), dict) else []
                proj = raw_data.get("project") or {}
                cyc = raw_data.get("cycle") or {}
                cycle_name = cyc.get("name") or (f"Cycle {cyc.get('number')}" if cyc.get("number") else None)
                payload = {
                    "identifier": raw_data.get("identifier"),
                    "title": raw_data.get("title"),
                    "status": (raw_data.get("state") or {}).get("name") if isinstance(raw_data.get("state"), dict) else raw_data.get("state"),
                    "priority": raw_data.get("priority", 0),
                    "estimate": raw_data.get("estimate"),
                    "project": proj.get("name"),
                    "cycle": cycle_name,
                    "labels": labels,
                    "updated_at": raw_data.get("updatedAt") or raw_data.get("createdAt") or datetime.now(timezone.utc).isoformat(),
                }
            elif entity_type == "project":
                payload = {
                    "name": raw_data.get("name"),
                    "description": raw_data.get("description"),
                    "status": raw_data.get("state"),
                    "progress": raw_data.get("progress", 0),
                    "target_date": raw_data.get("targetDate"),
                    "start_date": raw_data.get("startDate"),
                    "url": raw_data.get("url"),
                }
            elif entity_type == "cycle":
                payload = {
                    "name": raw_data.get("name") or f"Cycle {raw_data.get('number')}",
                    "number": raw_data.get("number"),
                    "starts_at": raw_data.get("startsAt"),
                    "ends_at": raw_data.get("endsAt"),
                    "progress": raw_data.get("progress", 0),
                }
            else:
                payload = raw_data

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
        count: int = 25,
    ) -> Dict[str, Any]:
        """Generates realistic synthetic backlog issues, roadmap epics, and velocity milestones."""
        issues = []
        company_name = company_profile.get("company_name", "ShopifyNext")
        titles = [
            f"Optimize checkout conversion funnel for {company_name}",
            "Implement multi-currency invoice rendering",
            "Refactor billing subscription webhook reconciliation",
            "Add SLA alerting for tier 1 enterprise support tickets",
            "Build self-serve plan upgrade modal",
            "Migrate customer telemetry pipeline to Kafka stream",
            "Deprecate legacy v1 pricing plan endpoints",
            "Audit OAuth token refresh loop in third-party integrations"
        ]
        statuses = ["In Progress", "Done", "Todo", "In Review", "Backlog"]

        for i in range(count):
            title = titles[i % len(titles)]
            status = statuses[i % len(statuses)]
            payload = {
                "title": f"[{company_name}] {title} #{i+101}",
                "status": status,
                "priority": 1 if i % 4 == 0 else 2,
                "estimate": 2 + (i * 3) % 8,
                "project": "Core Infrastructure" if i % 2 == 0 else "Growth Experiments",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            issues.append(self.make_normalized_record(
                company_id=str(company_profile.get("id", "default")),
                entity_type="product_issue",
                entity_id=f"linear_syn_{i}",
                payload=payload,
                provenance_type=ProvenanceType.SYNTHETIC_EXTERNAL if self.status == ConnectionStatus.CONNECTED else ProvenanceType.SYNTHETIC_INTERNAL,
            ))

        return {
            "records_created": len(issues),
            "status": "success",
            "records": issues,
            "message": f"Generated {len(issues)} synthetic Linear product issues."
        }
