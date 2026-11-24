import pytest
from starlette.testclient import TestClient
from api.app import app
from state.schemas import Decision
from orchestrator.decomposer import decompose_decision
from services.supervisor_groq import (
    deterministic_supervisor_routing,
    SupervisorRoutingDecision,
    route_decision_specialists
)

@pytest.fixture
def client():
    return TestClient(app)

def test_deterministic_routing_free_plan():
    res = deterministic_supervisor_routing("Should we launch a free plan?")
    assert isinstance(res, SupervisorRoutingDecision)
    assert set(res.selected_specialists) == {"cfo", "growth", "cto", "customer", "product"}
    assert len(res.specialist_directives) == 5
    assert "cfo" in res.specialist_directives
    assert "cto" in res.specialist_directives
    assert res.source == "deterministic_router"

def test_deterministic_routing_infra():
    res = deterministic_supervisor_routing("Can we cut our AWS cloud infra bill by 30%?")
    assert set(res.selected_specialists) == {"cto", "cfo"}
    assert "cto" in res.specialist_directives
    assert "cfo" in res.specialist_directives
    assert "customer" not in res.selected_specialists

def test_deterministic_routing_price_raise():
    res = deterministic_supervisor_routing("Should we raise Starter price by 20%?")
    assert set(res.selected_specialists) == {"cfo", "growth", "product"}
    assert "growth" in res.specialist_directives

def test_deterministic_routing_churn():
    res = deterministic_supervisor_routing("How can we reduce churn on our Pro plan?")
    assert set(res.selected_specialists) == {"customer", "product", "cfo"}
    assert "customer" in res.specialist_directives

def test_decomposer_dynamic_specialists_two_nodes():
    dec = Decision(
        id="dec_test_infra",
        question="Can we cut our AWS bill?",
        objective="Cut AWS bill by 30%"
    )
    # 2 specialists: CTO + CFO
    dag = decompose_decision(dec, selected_specialists=["cto", "cfo"])
    
    # Analysis tasks should only be cto and cfo
    analysis_tasks = [t for t in dag.tasks.values() if t.kind == "agent_analysis"]
    assert len(analysis_tasks) == 2
    owner_agents = {t.owner_agent for t in analysis_tasks}
    assert owner_agents == {"cto", "cfo"}
    
    # Skeptic audit should only depend on task_cto_analysis and task_cfo_analysis
    skeptic_task = dag.tasks["task_skeptic_audit"]
    assert set(skeptic_task.depends_on) == {"task_cto_analysis", "task_cfo_analysis"}
    
    # Total tasks = 2 specialists + 7 downstream = 9 tasks
    assert len(dag.tasks) == 9

def test_decomposer_dynamic_specialists_three_nodes():
    dec = Decision(
        id="dec_test_price",
        question="Should we raise Starter price by 20%?",
        objective="Raise price by 20%"
    )
    dag = decompose_decision(dec, selected_specialists=["cfo", "growth", "product"])
    analysis_tasks = [t for t in dag.tasks.values() if t.kind == "agent_analysis"]
    assert len(analysis_tasks) == 3
    # Total tasks = 3 specialists + 7 downstream = 10 tasks
    assert len(dag.tasks) == 10

def test_decomposer_default_all_five_nodes():
    dec = Decision(
        id="dec_test_free",
        question="Should we launch a free plan?",
        objective="Freemium model packaging"
    )
    dag = decompose_decision(dec)
    assert len(dag.tasks) == 12
    analysis_tasks = [t for t in dag.tasks.values() if t.kind == "agent_analysis"]
    assert len(analysis_tasks) == 5

def test_route_endpoint_and_async_routing(client):
    res = client.post("/api/orchestration/route", json={"query": "Should we migrate from AWS to GCP?"})
    assert res.status_code == 200
    data = res.json()
    assert "selected_specialists" in data
    assert "cto" in data["selected_specialists"]
    assert "specialist_directives" in data
    assert "context_summary" in data

def test_submit_decision_dynamic_routing(client):
    res = client.post("/api/decisions", json={"query": "Can we cut our cloud infrastructure cost?"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    assert "selected_specialists" in data
    assert "cto" in data["selected_specialists"]
    assert "routing" in data
