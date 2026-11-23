"""
ConnectorRegistry and IntegrationManager for VentureTwin integration connectors.
"""

from typing import Dict, List, Any, Optional
from integrations.base import AbstractConnector, ConnectionStatus


class ConnectorRegistry:
    """Holds all registered integration connectors."""

    def __init__(self):
        self._connectors: Dict[str, AbstractConnector] = {}

    def register(self, connector: AbstractConnector) -> None:
        """Register a connector instance by its connector_id."""
        self._connectors[connector.config.connector_id] = connector

    def get_connector(self, connector_id: str) -> Optional[AbstractConnector]:
        """Return a single connector by ID, or None if not found."""
        return self._connectors.get(connector_id)

    def get_by_domain(self, domain: str) -> List[AbstractConnector]:
        """Return all connectors for a given agent domain."""
        return [c for c in self._connectors.values() if c.config.agent_domain == domain]

    def get_all_statuses(self) -> List[Dict[str, Any]]:
        """Return sync status for all registered connectors."""
        return [c.get_sync_status() for c in self._connectors.values()]

    def all_connector_ids(self) -> List[str]:
        return list(self._connectors.keys())


class IntegrationManager:
    """High-level orchestration over all registered connectors."""

    def __init__(self, registry: ConnectorRegistry):
        self.registry = registry

    async def connect_all(self) -> Dict[str, Any]:
        """Attempt to connect all registered connectors."""
        results: Dict[str, Any] = {}
        for connector_id, connector in self.registry._connectors.items():
            try:
                result = await connector.connect()
                results[connector_id] = result
            except Exception as e:
                results[connector_id] = {"status": "error", "error": str(e)}
        return results

    async def sync_all(self, since: Optional[str] = None) -> Dict[str, Any]:
        """Trigger sync on all connected connectors."""
        results: Dict[str, Any] = {}
        for connector_id, connector in self.registry._connectors.items():
            if connector.status in (ConnectionStatus.CONNECTED, ConnectionStatus.SANDBOX_CONNECTED):
                try:
                    record = await connector.sync_history(since=since)
                    results[connector_id] = {
                        "status": record.status,
                        "records_fetched": record.records_fetched,
                        "records_created": record.records_created,
                        "sync_end": record.sync_end,
                        "error": record.error_message,
                    }
                except Exception as e:
                    results[connector_id] = {"status": "error", "error": str(e)}
            else:
                results[connector_id] = {
                    "status": "skipped",
                    "reason": connector.status.value
                }
        return results

    def get_status_summary(self) -> Dict[str, Any]:
        """Return a summary of all connector statuses grouped by domain."""
        all_statuses = self.registry.get_all_statuses()
        domains: Dict[str, List[Dict[str, Any]]] = {}
        for s in all_statuses:
            domain = s["agent_domain"]
            domains.setdefault(domain, []).append(s)
        connected = sum(1 for s in all_statuses if s["status"] in ("connected", "sandbox_connected"))
        awaiting = sum(1 for s in all_statuses if s["status"] == "awaiting_credentials")
        errored = sum(1 for s in all_statuses if s["status"] == "error")
        return {
            "total": len(all_statuses),
            "connected": connected,
            "awaiting_credentials": awaiting,
            "error": errored,
            "by_domain": domains,
        }

    async def get_agent_data(self, agent_domain: str, since: Optional[str] = None) -> Dict[str, Any]:
        """Merge data from all connectors in a given agent domain."""
        connectors = self.registry.get_by_domain(agent_domain)
        merged: Dict[str, Any] = {
            "agent_domain": agent_domain,
            "connectors": [],
            "records": [],
        }
        for connector in connectors:
            connector_info: Dict[str, Any] = {
                "connector_id": connector.config.connector_id,
                "display_name": connector.config.display_name,
                "status": connector.status.value,
                "records": [],
            }
            if connector.status in (ConnectionStatus.CONNECTED, ConnectionStatus.SANDBOX_CONNECTED):
                try:
                    raw = await connector.fetch_data(since=since)
                    normalized = connector.normalize_data(raw)
                    connector_info["records"] = normalized
                    merged["records"].extend(normalized)
                except Exception as e:
                    connector_info["error"] = str(e)
            merged["connectors"].append(connector_info)
        return merged


# ---------------------------------------------------------------------------
# Module-level singletons — built lazily to avoid import-time side effects
# ---------------------------------------------------------------------------

def _build_registry() -> ConnectorRegistry:
    """Instantiate and register all connectors (Nango managed and direct APIs)."""
    from integrations.financial.stripe_connector import StripeConnector
    from integrations.financial.quickbooks_connector import QuickBooksConnector
    from integrations.growth.hubspot_connector import HubSpotConnector
    from integrations.growth.mixpanel_connector import MixpanelConnector
    from integrations.growth.ga4_connector import GA4Connector
    from integrations.engineering.github_connector import GitHubConnector
    from integrations.engineering.datadog_connector import DatadogConnector
    from integrations.engineering.cloudwatch_connector import CloudWatchConnector
    from integrations.customer.intercom_connector import IntercomConnector
    from integrations.customer.zendesk_connector import ZendeskConnector
    from integrations.product.amplitude_connector import AmplitudeConnector
    from integrations.product.posthog_connector import PostHogConnector
    from integrations.product.linear_connector import LinearConnector
    from integrations.intelligence.firecrawl_connector import FirecrawlConnector
    from integrations.intelligence.brave_search_connector import BraveSearchConnector
    from integrations.intelligence.tavily_connector import TavilyConnector

    reg = ConnectorRegistry()
    for cls in [
        StripeConnector, QuickBooksConnector,
        HubSpotConnector, MixpanelConnector, GA4Connector,
        GitHubConnector, DatadogConnector, CloudWatchConnector,
        IntercomConnector, ZendeskConnector,
        AmplitudeConnector, PostHogConnector, LinearConnector,
        FirecrawlConnector, BraveSearchConnector, TavilyConnector,
    ]:
        reg.register(cls())
    return reg


registry: ConnectorRegistry = _build_registry()
manager: IntegrationManager = IntegrationManager(registry)
