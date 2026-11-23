import pytest
from starlette.testclient import TestClient
from api.app import app
from services.agent_chat import chat_with_agent, AGENT_META_MAP, AgentChatRequest


def test_agent_chat_meta_map_contains_all_agents():
    expected_agents = {"supervisor", "cfo", "growth", "cto", "customer", "product", "skeptic"}
    assert set(AGENT_META_MAP.keys()) == expected_agents


@pytest.mark.asyncio
async def test_mock_chat_with_all_individual_agents():
    for agent_key in AGENT_META_MAP.keys():
        resp = await chat_with_agent(agent_key=agent_key, message="What is our status and biggest priority?")
        assert resp.agent_key == agent_key
        assert resp.agent_name == AGENT_META_MAP[agent_key]["name"]
        assert resp.role == AGENT_META_MAP[agent_key]["role"]
        assert resp.avatar == AGENT_META_MAP[agent_key]["avatar"]
        assert len(resp.response) > 20
        assert resp.recommendation in ["proceed", "proceed_with_conditions", "caution", "pivot", "investigate", "scale", "challenge"]
        assert isinstance(resp.key_metrics, dict)
        assert len(resp.key_metrics) > 0


@pytest.mark.asyncio
async def test_cfo_specific_telemetry_grounding():
    resp = await chat_with_agent(agent_key="cfo", message="What is our cash runway and burn?")
    assert "runway_months" in resp.key_metrics
    assert "cash_balance" in resp.key_metrics
    assert "Runway" in resp.response or "burn" in resp.response or "Cash" in resp.response or "runway" in resp.response


@pytest.mark.asyncio
async def test_growth_specific_telemetry_grounding():
    resp = await chat_with_agent(agent_key="growth", message="How is our conversion and CAC?")
    assert "trial_to_paid_conversion" in resp.key_metrics
    assert "cac" in resp.key_metrics


@pytest.mark.asyncio
async def test_cto_specific_telemetry_grounding():
    resp = await chat_with_agent(agent_key="cto", message="What is our cloud infrastructure bill?")
    assert "monthly_cloud_cost" in resp.key_metrics
    assert "infra_cost_per_paid_user" in resp.key_metrics


@pytest.mark.asyncio
async def test_customer_specific_telemetry_grounding():
    resp = await chat_with_agent(agent_key="customer", message="What is our churn rate and ticket volume?")
    assert "monthly_churn_rate" in resp.key_metrics
    assert "support_headcount" in resp.key_metrics


@pytest.mark.asyncio
async def test_skeptic_specific_critique():
    resp = await chat_with_agent(agent_key="skeptic", message="What are our primary vulnerabilities?")
    assert "runway_months" in resp.key_metrics
    assert "churn_exposure" in resp.key_metrics
    assert resp.recommendation in ["caution", "challenge", "investigate"]


def test_api_agents_chat_endpoint():
    client = TestClient(app)
    payload = {
        "agent_key": "cfo",
        "message": "Can we afford to hire 2 new engineers?"
    }
    response = client.post("/api/agents/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["agent_key"] == "cfo"
    assert data["agent_name"] == "CFO"
    assert "response" in data
    assert "key_metrics" in data
    assert "runway_months" in data["key_metrics"]


def test_api_agents_chat_unknown_agent_error():
    client = TestClient(app)
    payload = {
        "agent_key": "unknown_ninja_agent",
        "message": "Hello"
    }
    response = client.post("/api/agents/chat", json=payload)
    assert response.status_code == 400
    assert "Unknown agent" in response.json()["detail"]
