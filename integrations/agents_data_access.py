"""
Scoped Agent Data Access Layer for VentureTwin.

Provides role-based, permissioned access to normalized integration telemetry.
Agents do not hold direct API credentials; they access domain-specific normalized views
governed by AGENT_DATA_DOMAINS policies.
"""

from typing import Dict, Any, List, Optional
from integrations.registry import registry
from integrations.normalized_store import (
    get_records_by_domain,
    get_latest_records,
)

AGENT_DATA_DOMAINS: Dict[str, List[str]] = {
    "cfo": ["financial", "growth"],
    "growth": ["growth", "financial"],
    "cto": ["engineering"],
    "customer": ["customer"],
    "product": ["product", "growth"],
    "skeptic": ["intelligence"],
    "supervisor": ["financial", "growth", "engineering", "customer", "product", "intelligence"]
}


async def get_agent_integration_data(
    agent_key: str,
    company_id: str = "default",
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Returns normalized integration data scoped to the agent's permissioned domains.
    Includes both real API records and synthetic test records with explicit provenance.
    """
    clean_key = agent_key.lower().strip()
    permitted_domains = AGENT_DATA_DOMAINS.get(clean_key, ["financial", "growth"])

    records_by_domain: Dict[str, List[Dict[str, Any]]] = {}
    total_records = 0

    for domain in permitted_domains:
        recs = get_records_by_domain(domain, company_id=company_id, limit=limit)
        records_by_domain[domain] = recs
        total_records += len(recs)

    return {
        "agent_key": clean_key,
        "permitted_domains": permitted_domains,
        "company_id": company_id,
        "total_records": total_records,
        "data": records_by_domain,
    }


async def get_integration_summary_for_agent(agent_key: str) -> Dict[str, Any]:
    """Returns connection statuses, environment, and last sync timestamp for agent's domains."""
    clean_key = agent_key.lower().strip()
    permitted_domains = AGENT_DATA_DOMAINS.get(clean_key, [])

    connector_summaries: List[Dict[str, Any]] = []
    all_statuses = registry.get_all_statuses()

    for s in all_statuses:
        if s["agent_domain"] in permitted_domains:
            connector_summaries.append(s)

    active_count = sum(1 for c in connector_summaries if c["status"] in ("connected", "sandbox_connected"))

    return {
        "agent_key": clean_key,
        "permitted_domains": permitted_domains,
        "total_connectors": len(connector_summaries),
        "active_connectors": active_count,
        "connectors": connector_summaries,
    }
