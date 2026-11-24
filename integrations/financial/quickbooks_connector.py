"""
QuickBooks Online connector for VentureTwin — Financial domain.

OAuth 2.0 based connector that exchanges a refresh token for an access token
to query P&L, Balance Sheet, Accounts, Invoices and Expenses via the
QuickBooks Reports API.

OAuth Setup Instructions:
--------------------------
1. Create an app at https://developer.intuit.com/
2. Add redirect URI: https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl
3. Use the OAuth 2.0 Playground to obtain an initial refresh token.
4. Set env vars: QUICKBOOKS_CLIENT_ID, QUICKBOOKS_CLIENT_SECRET,
   QUICKBOOKS_REFRESH_TOKEN, QUICKBOOKS_COMPANY_ID
5. Tokens auto-refresh on each connect() call.
"""

import asyncio
import base64
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="quickbooks",
    display_name="QuickBooks Online",
    agent_domain="financial",
    environment="sandbox",
    credential_env_vars=[
        "QUICKBOOKS_CLIENT_ID",
        "QUICKBOOKS_CLIENT_SECRET",
        "QUICKBOOKS_REFRESH_TOKEN",
        "QUICKBOOKS_COMPANY_ID",
    ],
    supports_write=False,
    supports_synthetic_generation=False,
    oauth_required=True,
)

_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
_SANDBOX_BASE = "https://sandbox-quickbooks.api.intuit.com/v3/company"


class QuickBooksConnector(AbstractConnector):
    """QuickBooks Online sandbox/production connector."""

    def __init__(self):
        super().__init__(_CONFIG)
        self._access_token: Optional[str] = None

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            self._access_token = await self._refresh_access_token()
            if self._access_token:
                self.status = ConnectionStatus.SANDBOX_CONNECTED
                self._error = None
                return {"status": self.status.value}
            self.status = ConnectionStatus.ERROR
            self._error = "Failed to obtain access token from QuickBooks"
            return {"status": self.status.value, "error": self._error}
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._error = str(e)
            return {"status": self.status.value, "error": self._error}

    async def disconnect(self) -> None:
        self.status = ConnectionStatus.NOT_CONNECTED
        self._access_token = None
        self._credentials = {}

    async def validate_connection(self) -> bool:
        if not self._access_token:
            await self.connect()
        return bool(self._access_token) and self.status in (
            ConnectionStatus.CONNECTED, ConnectionStatus.SANDBOX_CONNECTED
        )

    async def _refresh_access_token(self) -> Optional[str]:
        import httpx
        client_id = self._credentials["QUICKBOOKS_CLIENT_ID"]
        client_secret = self._credentials["QUICKBOOKS_CLIENT_SECRET"]
        refresh_token = self._credentials["QUICKBOOKS_REFRESH_TOKEN"]
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(_TOKEN_URL, headers=headers, data=data, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        self._error = f"Token refresh failed: HTTP {resp.status_code} — {resp.text[:200]}"
        return None

    async def fetch_data(
        self,
        entity_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._access_token:
            await self.connect()
        if not self._access_token:
            return []
        company_id = self._credentials.get("QUICKBOOKS_COMPANY_ID", "")
        base = f"{_SANDBOX_BASE}/{company_id}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }
        targets = entity_types or ["ProfitAndLoss", "BalanceSheet", "Invoice", "Purchase"]
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                for report in targets:
                    if report in ("ProfitAndLoss", "BalanceSheet"):
                        url = f"{base}/reports/{report}"
                        resp = await client.get(url, headers=headers, params={"minorversion": 65}, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            data["_entity_type"] = "report"
                            data["_report_name"] = report
                            results.append(data)
                    else:
                        query = f"SELECT * FROM {report} MAXRESULTS 100"
                        resp = await client.get(
                            f"{base}/query",
                            headers=headers,
                            params={"query": query, "minorversion": 65},
                            timeout=15,
                        )
                        if resp.status_code == 200:
                            body = resp.json()
                            entities = body.get("QueryResponse", {}).get(report, [])
                            for e in entities:
                                e["_entity_type"] = report.lower()
                            results.extend(entities)
                    await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("_entity_type", "unknown")
            entity_id = item.get("Id", item.get("_report_name", "unknown"))
            if entity_type == "report":
                payload = {
                    "report_name": item.get("_report_name"),
                    "header": item.get("Header", {}),
                    "rows_summary": str(item.get("Rows", {}))[:500],
                }
            elif entity_type == "invoice":
                payload = {
                    "total_amount": item.get("TotalAmt"),
                    "balance": item.get("Balance"),
                    "due_date": item.get("DueDate"),
                    "customer_ref": item.get("CustomerRef", {}).get("name"),
                    "doc_number": item.get("DocNumber"),
                }
            elif entity_type == "purchase":
                payload = {
                    "total_amount": item.get("TotalAmt"),
                    "account_ref": (item.get("AccountRef") or {}).get("name"),
                    "txn_date": item.get("TxnDate"),
                    "payment_type": item.get("PaymentType"),
                }
            else:
                payload = {k: v for k, v in item.items() if not k.startswith("_")}
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
