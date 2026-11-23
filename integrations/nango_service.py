"""
Nango Service for VentureTwin.

Provides centralized OAuth authentication, Connect Session Token generation,
connection lifecycle management, and unified API proxying via Nango (https://nango.dev/).
"""

import os
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("venturetwin.nango")

DEFAULT_NANGO_HOST = "https://api.nango.dev"

# Official verified Nango Provider Config Keys
NANGO_PROVIDER_KEYS: Dict[str, str] = {
    "stripe": "stripe",
    "quickbooks": "quickbooks",
    "hubspot": "hubspot",
    "github": "github",
    "intercom": "intercom",
    "zendesk": "zendesk",
    "linear": "linear",
    "datadog": "datadog",
    "amplitude": "amplitude",
    "mixpanel": "mixpanel",
}


class NangoService:
    """Manages server-to-server interactions with Nango API."""

    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None):
        self.api_key = api_key or os.getenv("NANGO_SECRET_KEY") or os.getenv("NANGO_API_KEY") or ""
        self.host = (host or os.getenv("NANGO_HOST") or DEFAULT_NANGO_HOST).rstrip("/")

    @property
    def is_configured(self) -> bool:
        """Returns True if a real Nango secret API key is available."""
        return bool(self.api_key and not self.api_key.startswith("your_"))

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_connect_session(
        self,
        company_id: str = "default",
        allowed_integrations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a short-lived Connect Session Token for the frontend Connect UI.
        If Nango credentials are not configured, returns a mock development session token.
        """
        if not self.is_configured:
            # Standalone / offline developer mode
            return {
                "token": f"dev_session_token_{company_id}",
                "expires_at": None,
                "is_sandbox": True,
                "message": "Running in offline/developer mode without live NANGO_SECRET_KEY."
            }

        payload: Dict[str, Any] = {
            "tags": {"end_user_id": company_id},
        }
        if allowed_integrations:
            # Map connector IDs to Nango provider config keys
            mapped_keys = [NANGO_PROVIDER_KEYS.get(k, k) for k in allowed_integrations]
            payload["allowed_integrations"] = mapped_keys

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.host}/connect/sessions",
                    headers=self._auth_headers(),
                    json=payload,
                    timeout=15,
                )
            if resp.status_code in (200, 201):
                data = resp.json().get("data", resp.json())
                return {
                    "token": data.get("token"),
                    "expires_at": data.get("expires_at"),
                    "is_sandbox": False,
                }
            else:
                logger.warning("Nango createConnectSession failed (%s): %s", resp.status_code, resp.text)
                return {
                    "token": f"dev_session_{company_id}",
                    "is_sandbox": True,
                    "error": f"Nango API returned {resp.status_code}: {resp.text}"
                }
        except Exception as e:
            logger.error("Exception calling Nango createConnectSession: %s", e)
            return {
                "token": f"dev_session_{company_id}",
                "is_sandbox": True,
                "error": str(e)
            }

    async def get_connection(
        self,
        connection_id: str,
        provider_config_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves connection metadata from Nango."""
        if not self.is_configured:
            return None

        p_key = NANGO_PROVIDER_KEYS.get(provider_config_key, provider_config_key)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.host}/connection/{connection_id}",
                    headers=self._auth_headers(),
                    params={"provider_config_key": p_key},
                    timeout=12,
                )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            logger.warning("Failed to fetch Nango connection %s: %s", connection_id, e)
            return None

    async def delete_connection(
        self,
        connection_id: str,
        provider_config_key: str,
    ) -> bool:
        """Deletes a connection from Nango."""
        if not self.is_configured:
            return True

        p_key = NANGO_PROVIDER_KEYS.get(provider_config_key, provider_config_key)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{self.host}/connection/{connection_id}",
                    headers=self._auth_headers(),
                    params={"provider_config_key": p_key},
                    timeout=12,
                )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning("Failed to delete Nango connection %s: %s", connection_id, e)
            return False

    async def proxy_request(
        self,
        provider_config_key: str,
        connection_id: str,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Routes an authenticated HTTP request through Nango's Request Proxy.
        Nango handles OAuth injection and token refreshing automatically.
        """
        if not self.is_configured:
            raise RuntimeError("Nango is not configured with a valid NANGO_SECRET_KEY.")

        p_key = NANGO_PROVIDER_KEYS.get(provider_config_key, provider_config_key)
        clean_endpoint = endpoint.lstrip("/")
        proxy_url = f"{self.host}/proxy/{clean_endpoint}"

        req_headers = self._auth_headers()
        req_headers["Provider-Config-Key"] = p_key
        req_headers["Connection-Id"] = connection_id
        if headers:
            req_headers.update(headers)

        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=method.upper(),
                url=proxy_url,
                headers=req_headers,
                params=params,
                json=data,
                timeout=25,
            )
            return {
                "status_code": resp.status_code,
                "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
            }


# Singleton instance
nango_service = NangoService()
