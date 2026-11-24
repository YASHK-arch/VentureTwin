"""
Agent Tooling and Data Retrieval Layer.

Provides executive agents with scoped business telemetry from foundational data loaders
and normalized external SaaS integrations.
"""

from typing import Dict, Any, List, Optional
from data.loader import load_company_data


def get_company_data_source() -> Dict[str, Any]:
    return load_company_data()


def lookup_financials() -> Dict[str, Any]:
    data = get_company_data_source()
    return data["financials"]


def lookup_funnel() -> Dict[str, Any]:
    data = get_company_data_source()
    return data["funnel"]


def lookup_customers() -> Dict[str, Any]:
    data = get_company_data_source()
    return data["customers"]


def lookup_infra_costs() -> Dict[str, Any]:
    data = get_company_data_source()
    return data["infrastructure"]


def lookup_support_metrics() -> Dict[str, Any]:
    data = get_company_data_source()
    return data["support"]


def lookup_unit_economics() -> Dict[str, Any]:
    data = get_company_data_source()
    return data["unit_economics"]


# ---------------------------------------------------------------------------
# Integration-scoped tools (Stripe, QuickBooks, HubSpot, GA4, GitHub, etc.)
# ---------------------------------------------------------------------------

def lookup_integration_telemetry(agent_domain: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves normalized records ingested from external SaaS platforms for a domain."""
    try:
        from integrations.normalized_store import get_records_by_domain
        return get_records_by_domain(agent_domain, limit=limit)
    except Exception:
        return []


def lookup_competitor_research(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves evidence-backed web intelligence and pricing benchmarks (Firecrawl/Tavily)."""
    try:
        from integrations.normalized_store import get_records_by_domain
        return get_records_by_domain("intelligence", limit=limit)
    except Exception:
        return []


def lookup_product_roadmap(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves issue velocity, feature engagement, and roadmap epics (Linear/PostHog)."""
    try:
        from integrations.normalized_store import get_records_by_domain
        return get_records_by_domain("product", limit=limit)
    except Exception:
        return []
