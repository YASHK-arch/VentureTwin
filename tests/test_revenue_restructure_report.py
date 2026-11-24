import pytest
from state.schemas import Decision, SimulationRun, Finding, Assumption
from report.report_builder import build_consolidated_report, render_markdown_report

def test_revenue_restructure_report_has_specialist_claims_and_phased_recommendation():
    decision = Decision(
        id="d_shopify_restructure",
        question="How should Shopify restructure its revenue model to reduce dependence on transaction-linked merchant solutions while maintaining growth?",
        type="revenue_restructure",
        objective="Restructure revenue model away from transaction dependency"
    )

    sim_runs = [
        SimulationRun(
            id="sim_A",
            strategy="A_freemium",
            scenario="expected",
            outputs={"net_contribution_12": 298132.5, "runway_months_12": 5.7, "gross_margin_12": 0.68, "mrr_12": 110000.0}
        ),
        SimulationRun(
            id="sim_B",
            strategy="B_usage_caps",
            scenario="expected",
            outputs={"net_contribution_12": 311275.5, "runway_months_12": 6.1, "gross_margin_12": 0.74, "mrr_12": 135000.0}
        ),
        SimulationRun(
            id="sim_C",
            strategy="C_status_quo",
            scenario="expected",
            outputs={"net_contribution_12": 311275.5, "runway_months_12": 6.1, "gross_margin_12": 0.71, "mrr_12": 120000.0}
        )
    ]

    findings = [
        Finding(
            agent="CFO",
            task_id="t_cfo",
            claim="Restructuring Shopify's revenue model to emphasize higher-margin subscription and usage-based pricing—while applying usage caps and conversion incentives—will reduce reliance on transaction-linked merchant solutions and preserve long-term growth within the existing cash runway.",
            recommendation="proceed_with_limits",
            confidence=0.78,
            limitations=["Preserve runway buffer >= 10 months", "Guard gross margin above 70%"]
        ),
        Finding(
            agent="Growth",
            task_id="t_growth",
            claim="Shopify should re-balance its revenue mix by (1) raising the base subscription price and adding tiered premium modules (AI Sidekick, advanced API, dedicated support) to capture more recurring revenue, (2) introducing usage-based caps on low-tier plans that limit free transaction processing and encourage upgrade, and (3) monetising value-added services (POS hardware, B2B wholesale portal, marketplace integrations) while keeping the core commerce engine subscription-first.",
            recommendation="proceed_with_limits",
            confidence=0.76,
            limitations=["Monitor Starter tier churn", "Grandfather established merchants"]
        ),
        Finding(
            agent="Customer Success",
            task_id="t_cs",
            claim="Implement automated dispute resolution and tiered onboarding support to deflect high-touch support overhead and stabilize merchant retention during plan migrations.",
            recommendation="proceed_with_limits",
            confidence=0.78,
            limitations=["Ensure deflection exceeds 25%"]
        ),
        Finding(
            agent="Product",
            task_id="t_prod",
            claim="Shift feature gating between Starter, Grow, Advanced, and Plus to package AI Sidekick and wholesale tools as premium value drivers.",
            recommendation="proceed_with_limits",
            confidence=0.78,
            limitations=["Feature gating adoption tracking"]
        ),
        Finding(
            agent="Skeptic",
            task_id="t_skeptic",
            claim="Audited pricing elasticity and identified transaction fee cap sensitivity; recommend phased rollout across 90-day cohorts with grandfathering.",
            recommendation="proceed_with_limits",
            confidence=0.85,
            limitations=["Cohort sensitivity analysis"]
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
        findings=findings
    )

    # 1. Recommendation must NOT be "Do not proceed"
    assert "Do not proceed" not in report.recommendation
    assert "Proceed with Phased Revenue Restructuring" in report.recommendation
    assert report.confidence in ["Medium", "High"]

    # 2. Executive summary addresses the strategic restructuring blueprint
    exec_sum = report.sections["executive_summary"]
    assert "Phased Revenue Restructuring" in exec_sum
    assert "predictable, recurring SaaS subscriptions" in exec_sum
    assert "AI Sidekick" in exec_sum

    # 3. Dedicated Markdown report contains Executive Specialist Individual Agent Claims section
    md = report.sections.get("markdown_report", "")
    assert "# VentureTwin Decision Stress-Test Report" in md
    assert "## 2. Executive Specialist Individual Agent Claims" in md
    assert "### CFO – Chief Financial Officer" in md
    assert "### Growth – VP Growth & CMO" in md
    assert "### Customer Success – VP Customer Success" in md
    assert "### Product – Chief Product Officer" in md
    assert "### Skeptic – Independent Risk Auditor" in md
    assert "Restructuring Shopify's revenue model" in md
    assert "Shopify should re-balance its revenue mix" in md

    # 4. Phased Execution gates
    assert "execution_plan" in report.sections
    assert len(report.sections["execution_plan"]) == 3
    assert "Phase 1: Tier Packaging & Grandfathering" in report.sections["execution_plan"][0]["phase"]

    # 5. Algorithmic verification checks
    from verification.verifier import run_all_verification_checks
    checks = run_all_verification_checks(report, sim_runs, [])
    for c in checks:
        assert c.status == "passed", f"Verification check {c.check_name} failed: {c.detail}"
