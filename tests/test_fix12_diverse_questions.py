import pytest
from orchestrator.parser import parse_decision_query
from orchestrator.supervisor import Supervisor
from verification.verifier import run_all_verification_checks
from data.loader import load_company_data

@pytest.mark.asyncio
async def test_question_selling_company_m_and_a():
    """
    Question: 'Should I sell my company?'
    Expected:
    - Domain: m_and_a_exit
    - All specialist agents advise against selling at early Series A stage (Hold & Scale).
    - Report recommendation: 'Hold & Scale: Do Not Sell Company at Current Stage'
    - Verification checks pass.
    """
    decision = parse_decision_query("Should I sell my company?", allow_all=True)
    assert decision.type == "m_and_a_exit"
    assert "valuation" in decision.objective.lower() or "reserves" in decision.objective.lower()

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    # Agent recommendations
    findings_by_agent = {f.agent.lower(): f for f in state.findings}
    for agent_key in ["cfo", "growth", "cto", "customer", "product"]:
        assert agent_key in findings_by_agent
        f = findings_by_agent[agent_key]
        assert f.recommendation == "reject"
        assert any(term in f.claim.lower() for term in ["hold", "scale", "independent", "early", "discount", "series a"])

    # Final recommendation
    assert "Hold & Scale" in report.recommendation
    assert "Do Not Sell" in report.recommendation

    # Executive summary
    exec_sum = report.sections.get("executive_summary", "")
    assert "advises against selling" in exec_sum or "Hold & Scale" in exec_sum

    # Verification checks
    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Check {c.check_name} failed: {c.detail}"

@pytest.mark.asyncio
async def test_question_hiring_percentage():
    """
    Question: 'how many percent of employees should we hire?'
    Expected:
    - Domain: hiring_headcount
    - Agents recommend calibrated expansion (proceed_with_limits) of 10%-15% headcount.
    - Top strategy is A_calibrated_hiring_12pct.
    - Report recommendation title specifies calibrated 10%-15% headcount expansion.
    - Verification checks pass.
    """
    decision = parse_decision_query("how many percent of employees should we hire?", allow_all=True)
    assert decision.type == "hiring_headcount"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    findings_by_agent = {f.agent.lower(): f for f in state.findings}
    assert findings_by_agent["cfo"].recommendation == "proceed_with_limits"
    assert "10%–15%" in findings_by_agent["cfo"].claim or "10%" in findings_by_agent["cfo"].claim

    # Top strategy ranked
    ranked = report.sections.get("strategies_compared", [])
    assert len(ranked) >= 2
    assert "calibrated_hiring" in ranked[0]["strategy"].lower()
    assert ranked[0]["is_feasible"] is True

    # Final verdict
    assert "10%–15% Headcount Expansion" in report.recommendation or "Calibrated" in report.recommendation

    # Verification checks
    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Check {c.check_name} failed: {c.detail}"

@pytest.mark.asyncio
async def test_question_price_increase_20pct():
    """
    Question: 'Should we raise Starter price by 20%?'
    Expected:
    - Domain: price_increase
    - Final verdict recommends price increase or grandfathering.
    - Verification checks pass.
    """
    decision = parse_decision_query("Should we raise Starter price by 20%?", allow_all=True)
    assert decision.type == "price_increase"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    assert "Proceed with" in report.recommendation

    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Check {c.check_name} failed: {c.detail}"

@pytest.mark.asyncio
async def test_question_freemium_free_plan():
    """
    Question: 'Should we launch a free plan?'
    Expected:
    - Domain: free_plan
    - Top strategy is Strategy B (usage caps) or A.
    - Verification checks pass.
    """
    decision = parse_decision_query("Should we launch a free plan?", allow_all=True)
    assert decision.type == "free_plan"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    assert "Proceed with" in report.recommendation
    assert any(term in report.recommendation for term in ["Usage Caps", "Strategy B", "Feature-Gated"])

    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Check {c.check_name} failed: {c.detail}"

@pytest.mark.asyncio
async def test_question_enterprise_tier():
    """
    Question: 'Can we introduce an enterprise tier with custom SLAs?'
    Expected:
    - Domain: enterprise_tier
    - Verification checks pass.
    """
    decision = parse_decision_query("Can we introduce an enterprise tier with custom SLAs?", allow_all=True)
    assert decision.type == "enterprise_tier"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    assert "Proceed with" in report.recommendation

    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Check {c.check_name} failed: {c.detail}"

@pytest.mark.asyncio
async def test_question_churn_reduction():
    """
    Question: 'How do we reduce customer churn and protect runway?'
    Expected:
    - Domain: churn_reduction
    - Verification checks pass.
    """
    decision = parse_decision_query("How do we reduce customer churn and protect runway?", allow_all=True)
    assert decision.type == "churn_reduction"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    assert "Proceed with" in report.recommendation

    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Check {c.check_name} failed: {c.detail}"

def test_non_business_out_of_domain_queries():
    """
    Non-business queries must be cleanly identified as unsupported with informative guidance:
    - 'What is the capital of Italy?'
    - 'What should I eat for dinner tonight?'
    - 'Tell me a funny joke'
    """
    trivia_queries = [
        "What is the capital of Italy?",
        "What should I eat for dinner tonight?",
        "Tell me a funny joke",
        "Who won the world cup in 2022?"
    ]
    for q in trivia_queries:
        d = parse_decision_query(q, allow_all=True)
        assert d.type == "unsupported"
        assert "Out of Domain" in d.objective
        assert "not a SaaS business strategy decision" in d.objective
