import pytest
from starlette.testclient import TestClient
from api.app import app
from integrations.registry import registry, manager
from integrations.base import ConnectionStatus, ProvenanceType
from integrations.synthetic_generator import SyntheticDataGenerator
from integrations.agents_data_access import AGENT_DATA_DOMAINS, get_agent_integration_data, get_integration_summary_for_agent
from integrations.normalized_store import upsert_records, get_records_by_domain


def test_registry_has_all_twelve_connectors():
    expected_twelve = {
        "stripe", "quickbooks",
        "hubspot", "mixpanel",
        "github", "datadog",
        "intercom", "zendesk",
        "amplitude", "linear",
        "firecrawl", "brave_search"
    }
    registered = set(registry.all_connector_ids())
    assert expected_twelve.issubset(registered), f"Missing connectors: {expected_twelve - registered}"


def test_connectors_await_credentials_when_env_vars_missing(monkeypatch):
    monkeypatch.setattr("integrations.store.get_connection_state", lambda *args, **kwargs: None)
    # Ensure env vars are cleared for testing credential gating
    for cid in registry.all_connector_ids():
        conn = registry.get_connector(cid)
        assert conn is not None
        monkeypatch.setattr(conn, "get_nango_connection", lambda *args, **kwargs: None)
        conn.status = ConnectionStatus.NOT_CONNECTED
        for env_var in conn.config.credential_env_vars:
            monkeypatch.delenv(env_var, raising=False)
            monkeypatch.setenv(env_var, "")
        
        status = conn.get_sync_status()
        assert status["status"] in ("not_connected", "awaiting_credentials")
        assert len(status["missing_env_vars"]) > 0


def test_provenance_record_structure():
    stripe = registry.get_connector("stripe")
    rec = stripe.make_normalized_record(
        company_id="company_test",
        entity_type="payment",
        entity_id="pay_999",
        payload={"amount": 249, "currency": "usd"},
        provenance_type=ProvenanceType.SYNTHETIC_EXTERNAL
    )
    assert rec["company_id"] == "company_test"
    assert rec["integration"] == "stripe"
    assert rec["agent_domain"] == "financial"
    assert rec["entity_type"] == "payment"
    assert rec["entity_id"] == "pay_999"
    assert rec["provenance"]["type"] == "synthetic_external"
    assert "timestamp" in rec


def test_synthetic_data_generator_cohesion():
    gen = SyntheticDataGenerator({"company_name": "ShopifyMerchant"})
    dataset = gen.generate_full_company_dataset()

    assert dataset["company_name"] == "ShopifyMerchant"
    assert dataset["provenance"]["type"] == "synthetic_internal"
    assert len(dataset["customers"]) >= 50
    assert len(dataset["financials"]["charges"]) > 0
    assert len(dataset["growth"]["deals"]) > 0
    assert len(dataset["engineering"]["commits"]) > 0
    assert len(dataset["support"]) > 0

    # Cross-domain consistency: charges and tickets must link to valid customer ids
    valid_cids = {c["customer_id"] for c in dataset["customers"]}
    for ch in dataset["financials"]["charges"]:
        assert ch["customer_id"] in valid_cids
    for tk in dataset["support"]:
        assert tk["customer_id"] in valid_cids


@pytest.mark.asyncio
async def test_scoped_agent_data_access():
    # Insert test normalized records
    test_recs = [
        {
            "company_id": "test_corp",
            "integration": "stripe",
            "agent_domain": "financial",
            "entity_type": "payment",
            "entity_id": "pay_test_1",
            "timestamp": "2026-11-24T00:00:00Z",
            "provenance": {"type": "synthetic_internal", "source": "test"},
            "payload": {"amount": 500}
        },
        {
            "company_id": "test_corp",
            "integration": "hubspot",
            "agent_domain": "growth",
            "entity_type": "deal",
            "entity_id": "deal_test_1",
            "timestamp": "2026-11-24T00:00:00Z",
            "provenance": {"type": "synthetic_internal", "source": "test"},
            "payload": {"amount": 1000}
        }
    ]
    upsert_records(test_recs)

    # CFO can access financial and growth
    cfo_data = await get_agent_integration_data("cfo", company_id="test_corp")
    assert "financial" in cfo_data["permitted_domains"]
    assert "growth" in cfo_data["permitted_domains"]
    assert "engineering" not in cfo_data["permitted_domains"]

    # CTO cannot access financial
    cto_data = await get_agent_integration_data("cto", company_id="test_corp")
    assert "engineering" in cto_data["permitted_domains"]
    assert "financial" not in cto_data["permitted_domains"]


def test_api_integrations_endpoints():
    client = TestClient(app)

    # 1. Get all statuses
    res = client.get("/api/integrations/status")
    assert res.status_code == 200
    statuses = res.json()
    assert len(statuses) >= 12
    ids = [s["connector_id"] for s in statuses]
    assert "stripe" in ids
    assert "linear" in ids
    assert "firecrawl" in ids
    assert "mixpanel" in ids
    assert "datadog" in ids
    assert "amplitude" in ids
    assert "brave_search" in ids

    # 2. Get single status
    res = client.get("/api/integrations/status/stripe")
    assert res.status_code == 200
    assert res.json()["connector_id"] == "stripe"
    assert res.json()["agent_domain"] == "financial"

    # 3. Generate synthetic data for Stripe
    res = client.post("/api/integrations/generate/stripe", json={
        "company_profile": {"company_name": "NextcloudHub"},
        "count": 20
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["records_created"] > 0

    # 4. Agent summary endpoint
    res = client.get("/api/integrations/agent/cfo/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["agent_key"] == "cfo"
    assert "financial" in summary["permitted_domains"]
    assert summary["total_connectors"] >= 4

    # 5. Nango connect session token endpoint
    res = client.post("/api/integrations/nango/session-token", json={
        "company_id": "test_company",
        "allowed_integrations": ["stripe", "linear"]
    })
    assert res.status_code == 200
    sess_data = res.json()
    assert "token" in sess_data
    assert sess_data["token"] is not None

    # 6. Nango callback endpoint
    res = client.post("/api/integrations/nango/callback", json={
        "connection_id": "nango_test_conn_123",
        "provider_config_key": "stripe",
        "company_id": "test_company"
    })
    assert res.status_code == 200
    cb_data = res.json()
    assert cb_data["status"] == "success"
    assert cb_data["connector_id"] == "stripe"
