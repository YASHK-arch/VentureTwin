"""
GitHub connector for VentureTwin — Engineering domain.

Fetches commits, PRs, issues, and releases from a configured repository.
Supports synthetic dataset generation (labels, issues, test PRs).
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="github",
    display_name="GitHub",
    agent_domain="engineering",
    environment="production",
    credential_env_vars=["GITHUB_TOKEN", "GITHUB_REPO"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)

_BASE = "https://api.github.com"


class GitHubConnector(AbstractConnector):
    """GitHub REST API connector."""

    def __init__(self):
        super().__init__(_CONFIG)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._credentials.get('GITHUB_TOKEN', '')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{_BASE}/user", headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                self.status = ConnectionStatus.CONNECTED
                self._error = None
                return {"status": self.status.value, "user": resp.json().get("login")}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"GitHub auth rejected: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"GitHub unexpected: HTTP {resp.status_code}"
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

    async def _paginate(self, client, url: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        import httpx
        results = []
        page = 1
        while True:
            p = dict(params or {})
            p["per_page"] = 100
            p["page"] = page
            resp = await client.get(url, headers=self._headers(), params=p, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json()
            if not data:
                break
            results.extend(data)
            if len(data) < 100:
                break
            page += 1
            await asyncio.sleep(0.1)
        return results

    async def fetch_data(
        self,
        entity_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._credentials.get("GITHUB_TOKEN"):
            if not self.load_credentials():
                return []
        repo = self._credentials.get("GITHUB_REPO", "")
        if not repo:
            self._error = "GITHUB_REPO env var not set"
            return []
        targets = entity_types or ["commits", "pulls", "issues", "releases"]
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for entity in targets:
                    params: Dict[str, Any] = {"state": "all"}
                    if since:
                        params["since"] = since
                    if entity == "commits":
                        url = f"{_BASE}/repos/{repo}/commits"
                        items = await self._paginate(client, url, params)
                    elif entity == "pulls":
                        url = f"{_BASE}/repos/{repo}/pulls"
                        items = await self._paginate(client, url, {"state": "all"})
                    elif entity == "issues":
                        url = f"{_BASE}/repos/{repo}/issues"
                        items = await self._paginate(client, url, {"state": "all"})
                    elif entity == "releases":
                        url = f"{_BASE}/repos/{repo}/releases"
                        items = await self._paginate(client, url)
                    else:
                        continue
                    for item in items:
                        item["_entity_type"] = entity.rstrip("s")
                    results.extend(items)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("_entity_type", "unknown")
            entity_id = str(item.get("sha") or item.get("id") or item.get("number") or "")
            if entity_type == "commit":
                commit = item.get("commit", {})
                payload = {
                    "sha": item.get("sha"),
                    "message": commit.get("message", "")[:200],
                    "author": (commit.get("author") or {}).get("name"),
                    "date": (commit.get("author") or {}).get("date"),
                }
            elif entity_type in ("pull", "issue"):
                payload = {
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "state": item.get("state"),
                    "user": (item.get("user") or {}).get("login"),
                    "created_at": item.get("created_at"),
                    "closed_at": item.get("closed_at"),
                    "labels": [l.get("name") for l in item.get("labels", [])],
                    "is_pr": "pull_request" in item,
                }
            elif entity_type == "release":
                payload = {
                    "tag_name": item.get("tag_name"),
                    "name": item.get("name"),
                    "published_at": item.get("published_at"),
                    "prerelease": item.get("prerelease"),
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
        """Create labeled issues and test PRs in the configured repo."""
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        activity = gen.generate_engineering_activity(months_back=3)
        repo = self._credentials.get("GITHUB_REPO", "")
        if not repo:
            return {"status": "error", "error": "GITHUB_REPO not set"}
        created = 0
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for item in activity[:20]:
                    if item.get("type") == "issue":
                        body = {
                            "title": item.get("title", "Synthetic issue"),
                            "body": item.get("body", "Generated by VentureTwin synthetic data generator."),
                            "labels": item.get("labels", []),
                        }
                        resp = await client.post(
                            f"{_BASE}/repos/{repo}/issues",
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
            "issues_created": created,
            "provenance": ProvenanceType.SYNTHETIC_EXTERNAL.value,
        }
