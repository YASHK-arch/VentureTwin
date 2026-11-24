import pytest
from orchestrator.parser import parse_decision_query
from orchestrator.supervisor import Supervisor
from verification.verifier import run_all_verification_checks
from report.report_builder import build_consolidated_report
from state.schemas import Decision, SimulationRun, Finding
from data.loader import load_company_data


def test_user_growth_query_classification():
    """Verify that queries with 'increase' for users/growth are NOT misclassified as price_increase."""
    d1 = parse_decision_query("What strategy should we execute to increase number of users?", allow_all=True)
    assert d1.type == "user_growth"
    assert d1.classification.subtype == "user_growth"

    d2 = parse_decision_query("How do we scale user acquisition and customer growth?", allow_all=True)
    assert d2.type == "user_growth"

    d3 = parse_decision_query("Should we raise Starter price by 20%?", allow_all=True)
    assert d3.type == "price_increase"


@pytest.mark.asyncio
async def test_workflow_user_growth_dynamic_report():
    """
    Test full end-to-end execution for user growth query:
    1. Query classified as user_growth.
    2. Supervisor runs appropriate simulation strategies.
    3. Consolidated report recommendation and executive summary dynamically reflect
       the user growth initiative and synthesize individual agent findings.
    4. All verification checks pass.
    """
    query = "What strategy should we execute to increase number of users?"
    decision = parse_decision_query(query, allow_all=True)
    assert decision.type == "user_growth"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)

    assert state.status in ["completed", "degraded"]
    assert state.report is not None

    report = state.report
    # Recommendation title must be about user growth/acquisition, NOT price increase
    assert "Price Increase" not in report.recommendation
    assert any(term in report.recommendation.lower() for term in ["freemium", "acquisition", "user", "growth"])

    # Executive summary must synthesize the individual agents
    exec_summary = report.sections.get("executive_summary", "")
    assert "Price Increase" not in exec_summary
    assert "CFO" in exec_summary or "Growth" in exec_summary
    assert "runway" in exec_summary.lower()

    # Agent findings must be present
    agent_findings = report.sections.get("agent_findings", [])
    assert len(agent_findings) > 0
    cfo_found = any(f["agent"] == "CFO" for f in agent_findings)
    growth_found = any(f["agent"] == "Growth" for f in agent_findings)
    assert cfo_found or growth_found

    # Verification checks
    checks = run_all_verification_checks(report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Verification check {c.check_name} failed: {c.detail}"


def test_consolidated_report_dynamic_specialist_synthesis():
    """Verify build_consolidated_report dynamically weaves agent findings into executive summary."""
    data = load_company_data()
    decision = Decision(
        id="dec_custom_growth",
        type="user_growth",
        question="What strategy should we execute to increase number of users?",
        objective="Evaluate user growth channels",
        metadata={"selected_specialists": ["cfo", "growth"]}
    )

    findings = [
        Finding(
            agent="CFO",
            task_id="t1",
            claim="Increasing user count via a freemium expansion strategy is viable only if incremental infrastructure cost per free user is strictly capped.",
            recommendation="proceed_with_limits",
            confidence=0.85,
            limitations=["infra_cost_per_free_user capped at $0.80"]
        ),
        Finding(
            agent="Growth",
            task_id="t2",
            claim="Implement a freemium tier with usage caps and feature gating to boost free-to-paid conversion.",
            recommendation="proceed_with_limits",
            confidence=0.78,
            limitations=["organic SEO acquisition priority"]
        ),
        Finding(
            agent="Skeptic",
            task_id="t3",
            claim="Downside conversion risk must be monitored with 60-day review gates.",
            recommendation="proceed_with_limits",
            confidence=0.85
        )
    ]

    sim_runs = [
        SimulationRun(
            id="sim_fg",
            strategy="A_freemium_acquisition_expansion",
            scenario="expected",
            parameters={},
            outputs={
                "mrr_12": 210000.0,
                "net_contribution_12": 605760.60,
                "runway_months_12": 14.5,
                "gross_margin_12": 0.74,
                "support_headcount_12": 3
            }
        )
    ]

    report = build_consolidated_report(
        decision=decision,
        sim_runs=sim_runs,
        assumptions=[],
        conflicts=[],
        verification_results=[],
        tornado_data=[],
        flip_point_info={"has_flip_point": False},
        company_data=data,
        findings=findings
    )

    # 1. Recommendation title
    assert "Price Increase" not in report.recommendation
    assert "Freemium" in report.recommendation or "Acquisition" in report.recommendation

    # 2. Executive summary has quantitative numbers and specialist claims
    exec_summary = report.sections["executive_summary"]
    assert "605,760.60" in exec_summary
    assert "14.5" in exec_summary
    assert "CFO" in exec_summary
    assert "Growth" in exec_summary
    assert "freemium expansion strategy" in exec_summary.lower()

    # 3. Verification checks pass
    checks = run_all_verification_checks(report, sim_runs, [], company_data=data)
    for c in checks:
        assert c.status == "passed", f"Verification check {c.check_name} failed: {c.detail}"


def test_broad_strategic_and_platform_queries_in_domain():
    """Verify that broad strategic, platform, and ecosystem questions are correctly classified as in-domain."""
    queries = [
        "How should Shopify evolve from a commerce platform into a broader business operating system for merchants?",
        "How should Shopify restructure its financial services ecosystem to become a more comprehensive financial partner for merchants?",
        "Should we expand our developer platform and monetize third-party integrations?",
        "How do we improve merchant solution adoption across enterprise clients?"
    ]
    for q in queries:
        d = parse_decision_query(q, allow_all=True)
        assert d.type != "unsupported", f"Query '{q}' should be supported, got: {d.type}"
        assert d.classification.category != "out_of_domain", f"Query '{q}' should not be out_of_domain"
        assert d.type in ["strategic_decision", "enterprise_tier"]


@pytest.mark.asyncio
async def test_workflow_platform_evolution_strategy():
    """Test full workflow execution for strategic platform initiative."""
    q = "How should Shopify evolve from a commerce platform into a broader business operating system for merchants?"
    d = parse_decision_query(q, allow_all=True)
    assert d.type == "strategic_decision"

    sup = Supervisor()
    state = await sup.execute_workflow(d)
    assert state.status in ["completed", "degraded"]
    assert state.report is not None
    assert "Proceed with" in state.report.recommendation
    assert "Adopt Proposal" not in state.report.recommendation
    assert state.report.sections.get("executive_summary") is not None
    assert "A adopt proposal" not in state.report.sections.get("executive_summary", "")

    checks = run_all_verification_checks(state.report, state.simulation_runs, state.assumptions)
    for c in checks:
        assert c.status == "passed", f"Verification check {c.check_name} failed: {c.detail}"


def test_customer_success_redesign_dynamic_report():
    """
    Directly tests the customer success redesign query shown in the user's uploaded image.
    Verifies that the consolidated report does NOT produce 'Adopt Proposal' or raw quote concatenation.
    """
    data = load_company_data()
    q = "Redesigning the customer success organization to support millions of merchants while maintaining personalization"
    decision = parse_decision_query(q, allow_all=True)

    findings = [
        Finding(
            agent="CFO",
            task_id="t_cfo",
            claim="To support millions of merchants while maintaining personalized support, adopt a tiered customer-success model leveraging AI-driven self-service.",
            recommendation="proceed_with_limits",
            confidence=0.85,
            limitations=["Preserve runway >= 10 months"]
        ),
        Finding(
            agent="CTO",
            task_id="t_cto",
            claim="Must be coupled with infrastructure cost controls and usage ceilings to prevent compute bloat.",
            recommendation="proceed_with_limits",
            confidence=0.80,
            limitations=["Enforce API rate limits"]
        ),
        Finding(
            agent="Customer",
            task_id="t_cs",
            claim="Redesign Customer Success into a 3-tier model with dedicated Enterprise CSMs and an AI-augmented self-service hub.",
            recommendation="proceed_with_limits",
            confidence=0.88,
            limitations=["Monitor ticket volume per rep"]
        ),
        Finding(
            agent="Product",
            task_id="t_prod",
            claim="This initiative represents operational staffing and workflow routing rather than product packaging.",
            recommendation="reject",
            confidence=0.70
        ),
        Finding(
            agent="Skeptic",
            task_id="t_skep",
            claim="Detailed headcount and cost per support rep data must be validated against actual merchant mix.",
            recommendation="proceed_with_limits",
            confidence=0.85
        )
    ]

    sim_runs = [
        SimulationRun(
            id="sim_cs",
            strategy="A_adopt_proposal",
            scenario="expected",
            parameters={},
            outputs={
                "mrr_12": 195000.0,
                "net_contribution_12": 476258.55,
                "runway_months_12": 10.6,
                "gross_margin_12": 0.72,
                "support_headcount_12": 4
            }
        )
    ]

    report = build_consolidated_report(
        decision=decision,
        sim_runs=sim_runs,
        assumptions=[],
        conflicts=[],
        verification_results=[],
        tornado_data=[],
        flip_point_info={"has_flip_point": False},
        company_data=data,
        findings=findings
    )

    # 1. Recommendation title must be tailored to Customer Success, NOT generic 'Adopt Proposal'
    assert "Adopt Proposal" not in report.recommendation
    assert "Customer Success" in report.recommendation or "Support" in report.recommendation
    assert report.recommendation.startswith("Proceed with Limits:")

    # 2. Executive summary must synthesize specialists smoothly without raw 'A adopt proposal'
    exec_sum = report.sections["executive_summary"]
    assert "A adopt proposal" not in exec_sum
    assert "476,258.55" in exec_sum
    assert "10.6" in exec_sum
    assert "CFO" in exec_sum
    assert "CTO" in exec_sum
    assert "Customer Success" in exec_sum or "Customer" in exec_sum

    # 3. Verification checks pass
    checks = run_all_verification_checks(report, sim_runs, [], company_data=data)
    for c in checks:
        assert c.status == "passed", f"Verification check {c.check_name} failed: {c.detail}"


def test_dynamic_report_with_explicit_llm_synthesis():
    """Verify that when an LLM synthesis is supplied, the report honors it cleanly."""
    data = load_company_data()
    decision = parse_decision_query("How should Shopify evolve from a commerce platform into a broader business operating system?", allow_all=True)

    sim_runs = [
        SimulationRun(
            id="sim_llm",
            strategy="A_adopt_proposal",
            scenario="expected",
            parameters={},
            outputs={
                "mrr_12": 220000.0,
                "net_contribution_12": 520000.0,
                "runway_months_12": 12.0,
                "gross_margin_12": 0.75
            }
        )
    ]

    custom_synthesis = {
        "recommendation_title": "Proceed with Limits: Merchant OS Platform Expansion",
        "executive_summary": (
            "Recommendation: Proceed with Limits: Merchant OS Platform Expansion (Confidence: High). "
            "Under expected operating parameters, expanding platform architecture delivers an estimated "
            "$520,000.00 in cumulative 12-month net contribution while maintaining 12.0 months of runway. "
            "Executive leadership aligns on phased rollout with strict API governance."
        ),
        "key_actions": ["Deploy API partner sandbox", "Enforce compute isolation"]
    }

    report = build_consolidated_report(
        decision=decision,
        sim_runs=sim_runs,
        assumptions=[],
        conflicts=[],
        verification_results=[],
        tornado_data=[],
        flip_point_info={"has_flip_point": False},
        company_data=data,
        findings=[],
        llm_synthesis=custom_synthesis
    )

    assert report.recommendation == "Proceed with Limits: Merchant OS Platform Expansion"
    assert report.sections["executive_summary"] == custom_synthesis["executive_summary"]

    checks = run_all_verification_checks(report, sim_runs, [], company_data=data)
    for c in checks:
        assert c.status == "passed", f"Verification check {c.check_name} failed: {c.detail}"
