"""
Stripe connector for VentureTwin — Financial domain.

Connects to the Stripe Test API to fetch customers, charges, subscriptions
and invoices. Also supports synthetic dataset generation in Stripe Test mode.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from integrations.base import (
    AbstractConnector, ConnectorConfig, ConnectionStatus, ProvenanceType
)

_CONFIG = ConnectorConfig(
    connector_id="stripe",
    display_name="Stripe Payments",
    agent_domain="financial",
    environment="test",
    credential_env_vars=["STRIPE_SECRET_KEY"],
    supports_write=True,
    supports_synthetic_generation=True,
    oauth_required=False,
)


class StripeConnector(AbstractConnector):
    """Stripe Test/Live API connector for financial data."""

    def __init__(self):
        super().__init__(_CONFIG)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> Dict[str, Any]:
        if not self.load_credentials():
            return {"status": self.status.value, "error": self._error}
        self.status = ConnectionStatus.CONNECTING
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.stripe.com/v1/balance",
                    auth=(self._credentials["STRIPE_SECRET_KEY"], ""),
                    timeout=10,
                )
            if resp.status_code == 200:
                self.status = ConnectionStatus.SANDBOX_CONNECTED
                self._error = None
                return {"status": self.status.value, "balance": resp.json()}
            elif resp.status_code in (401, 403):
                self.status = ConnectionStatus.ERROR
                self._error = f"Stripe rejected credentials: HTTP {resp.status_code}"
                return {"status": self.status.value, "error": self._error}
            else:
                self.status = ConnectionStatus.ERROR
                self._error = f"Unexpected Stripe response: HTTP {resp.status_code}"
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

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    async def fetch_data(
        self,
        entity_types: Optional[List[str]] = None,
        since: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._credentials.get("STRIPE_SECRET_KEY"):
            if not self.load_credentials():
                return []
        targets = entity_types or ["customers", "charges", "subscriptions", "invoices"]
        results: List[Dict[str, Any]] = []
        try:
            import httpx
            auth = (self._credentials["STRIPE_SECRET_KEY"], "")
            async with httpx.AsyncClient() as client:
                for entity in targets:
                    params: Dict[str, Any] = {"limit": 100}
                    if since:
                        # Stripe uses Unix timestamps for created[gte]
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                            params["created[gte]"] = int(dt.timestamp())
                        except Exception:
                            pass
                    has_more = True
                    starting_after: Optional[str] = None
                    while has_more:
                        if starting_after:
                            params["starting_after"] = starting_after
                        resp = await client.get(
                            f"https://api.stripe.com/v1/{entity}",
                            auth=auth,
                            params=params,
                            timeout=15,
                        )
                        if resp.status_code != 200:
                            break
                        data = resp.json()
                        items = data.get("data", [])
                        for item in items:
                            item["_entity_type"] = entity.rstrip("s")  # e.g. "customer"
                        results.extend(items)
                        has_more = data.get("has_more", False)
                        if has_more and items:
                            starting_after = items[-1]["id"]
                        else:
                            has_more = False
                        await asyncio.sleep(0.1)
        except Exception as e:
            self._error = str(e)
        return results

    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw:
            entity_type = item.get("_entity_type", "unknown")
            entity_id = item.get("id", "")
            payload: Dict[str, Any] = {}
            if entity_type == "customer":
                payload = {
                    "email": item.get("email"),
                    "name": item.get("name"),
                    "created": item.get("created"),
                    "currency": item.get("currency"),
                    "delinquent": item.get("delinquent"),
                }
            elif entity_type == "charge":
                payload = {
                    "amount": item.get("amount"),
                    "currency": item.get("currency"),
                    "status": item.get("status"),
                    "created": item.get("created"),
                    "customer": item.get("customer"),
                    "paid": item.get("paid"),
                }
            elif entity_type == "subscription":
                payload = {
                    "status": item.get("status"),
                    "current_period_end": item.get("current_period_end"),
                    "customer": item.get("customer"),
                    "plan": (item.get("plan") or {}).get("nickname"),
                    "amount": (item.get("plan") or {}).get("amount"),
                }
            elif entity_type == "invoice":
                payload = {
                    "total": item.get("total"),
                    "amount_due": item.get("amount_due"),
                    "paid": item.get("paid"),
                    "status": item.get("status"),
                    "customer": item.get("customer"),
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

    # ------------------------------------------------------------------
    # Synthetic data generation (Stripe Test mode only)
    # ------------------------------------------------------------------

    async def create_synthetic_customer(
        self, name: str, email: str, plan: str = "starter"
    ) -> Dict[str, Any]:
        """Create a test customer in Stripe Test mode."""
        if not self._credentials.get("STRIPE_SECRET_KEY"):
            self.load_credentials()
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.stripe.com/v1/customers",
                    auth=(self._credentials["STRIPE_SECRET_KEY"], ""),
                    data={"name": name, "email": email, "metadata[plan]": plan},
                    timeout=10,
                )
            if resp.status_code == 200:
                return {"status": "created", "customer": resp.json()}
            return {"status": "error", "code": resp.status_code, "body": resp.text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def create_synthetic_subscription(
        self, customer_id: str, price_id: str
    ) -> Dict[str, Any]:
        """Create a test subscription in Stripe Test mode."""
        if not self._credentials.get("STRIPE_SECRET_KEY"):
            self.load_credentials()
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.stripe.com/v1/subscriptions",
                    auth=(self._credentials["STRIPE_SECRET_KEY"], ""),
                    data={
                        "customer": customer_id,
                        "items[0][price]": price_id,
                    },
                    timeout=10,
                )
            if resp.status_code == 200:
                return {"status": "created", "subscription": resp.json()}
            return {"status": "error", "code": resp.status_code, "body": resp.text}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def generate_synthetic_dataset(self, company_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a plausible set of test customers and subscriptions matching
        the company profile. Uses Stripe Test API (safe — test keys only).
        """
        from integrations.synthetic_generator import SyntheticDataGenerator
        gen = SyntheticDataGenerator(company_profile)
        customers_data = gen.generate_customer_base(count=20)
        created_customers = []
        created_subs = []
        for c in customers_data[:20]:  # limit to 20 for speed
            result = await self.create_synthetic_customer(
                name=c["name"], email=c["email"], plan=c.get("plan", "starter")
            )
            if result.get("status") == "created":
                created_customers.append(result["customer"])
            await asyncio.sleep(0.1)
        return {
            "status": "generated",
            "customers_created": len(created_customers),
            "subscriptions_created": len(created_subs),
            "provenance": ProvenanceType.SYNTHETIC_EXTERNAL.value,
        }
