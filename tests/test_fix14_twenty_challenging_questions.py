"""
VentureTwin — Fix 14 Test Suite: Twenty Challenging Strategic Test Questions.

Tests all 19 challenging questions grouped by their testing domains:
1. Financial reasoning and constraint conflicts (Tests 1, 2, 3)
2. Conflicting agent recommendations (Tests 4, 5, 6)
3. Ambiguous and incomplete decisions (Tests 7, 8, 9)
4. Sensitivity analysis and uncertainty (Tests 10, 11, 12)
5. Complex multi-department decisions (Tests 13, 14, 15)
6. Adversarial and edge-case tests (Tests 16, 17, 18, 19)

Strict invariant:
All test questions use the EXACT wording provided by the CEO / user.
"""
import pytest
import os
import asyncio
from typing import Dict, Any

from orchestrator.parser import parse_decision
from orchestrator.supervisor import Supervisor
from agents.llm_client import LLMClient
from orchestrator.decomposer import decompose_decision, DAGValidationError
from simulation.finance import (
    calculate_multi_expenditures,
    calculate_free_plan_costs,
    calculate_growth_vs_cto,
    reconcile_runway_figures,
    calculate_marketing_scenarios,
    calculate_churn_vs_acq_impact,
    calculate_competing_investments_simultaneous,
    calculate_acquisition_vs_organic_growth,
    calculate_layoffs_vs_automation,
    calculate_spend_buffer_risk,
    calculate_injected_false_runway,
    calculate_adversarial_contradiction,
    calculate_zero_negative_burn_model
)

@pytest.fixture(autouse=True)
def set_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")


# =============================================================================
# GROUP 1: Financial reasoning and constraint conflicts
# =============================================================================

@pytest.mark.asyncio
async def test_question_1_revenue_growth_vs_runway():
    """
    Test 1 — Revenue growth vs. runway
    Expected behavior:
    - Calculate runway as approximately 10.31 months.
    - Recognize that the proposal technically satisfies the 10-month constraint.
    - Avoid treating the projected 25% acquisition increase as guaranteed revenue.
    - Recommend conditions or staged spending.
    """
    query = (
        "NimbusDesk is considering spending an additional $35,000/month on sales and marketing. "
        "The expected outcome is a 25% increase in new customer acquisition, but there is no guarantee of improved conversion or retention. "
        "Current net burn is $125,000/month, cash balance is $1.65M, and minimum required runway is 10 months. "
        "Should we approve this investment? Calculate the maximum affordable spend, quantify the runway impact, and explain what evidence would justify the investment."
    )
    decision = parse_decision(query)
    assert decision.type == "spend_budget"
    assert decision.classification.subtype == "revenue_vs_runway"

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None

    assert "proceed with limits" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "10.31" in exec_summary
    assert "$40,000" in exec_summary
    assert "$35,000" in exec_summary

    # Ensure all verifications passed
    for v in report.sections.get("verification_summary", []):
        assert v["status"] == "passed", f"Verification {v['check_name']} failed: {v.get('detail')}"


@pytest.mark.asyncio
async def test_question_2_multiple_simultaneous_expenditures():
    """
    Test 2 — Multiple simultaneous expenditures
    Expected behavior:
    - Total additional spend = $42,000/month.
    - Maximum additional spend = $40,000/month.
    - All three together violate the constraint.
    - Evaluate combinations rather than simply rejecting everything.
    - Do not assume marketing, hiring, and infrastructure have equal strategic value.
    """
    query = (
        "We are considering three investments: $20,000/month in marketing, $14,000/month for two support specialists, "
        "and $8,000/month in cloud infrastructure upgrades. Can NimbusDesk approve all three while maintaining at least 10 months of runway? "
        "If not, identify which combinations are financially feasible and recommend the best combination."
    )
    decision = parse_decision(query)
    assert decision.type == "multi_expenditure"
    assert decision.classification.subtype == "multiple_expenditures"

    # Math engine check
    multi = calculate_multi_expenditures()
    assert multi["total_spend"] == 42000.0
    assert multi["max_allowable_spend"] == 40000.0
    assert multi["all_together_runway"] == 9.88
    assert multi["all_together_feasible"] is False

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "proceed with limits" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "$42,000" in exec_summary
    assert "9.88" in exec_summary
    assert "$40,000" in exec_summary

    # Combinations evaluated in trade_off_analysis
    trade_offs = report.sections.get("trade_off_analysis", [])
    assert len(trade_offs) >= 2


@pytest.mark.asyncio
async def test_question_3_revenue_growth_with_increasing_costs():
    """
    Test 3 — Revenue growth with increasing costs
    Expected behavior:
    - Infrastructure cost = $2,300/month.
    - Expected tickets = 240/month.
    - Support cost = approximately $5,599.20/month.
    - Total incremental cost = approximately $7,899.20/month.
    - New burn = approximately $132,899.20/month.
    - Runway ≈ 12.42 months.
    - Explicitly state that acquisition, conversion, and revenue benefits are not included.
    """
    query = (
        "NimbusDesk wants to launch a free plan. The company expects 2,000 free users within three months. "
        "Each free user costs $1.15/month in infrastructure, and 12% of free users are estimated to generate support tickets. "
        "Current support cost is $23.33 per ticket. Assume the 12% ticket rate means 0.12 tickets per user per month. "
        "What is the monthly cost of acquiring and serving these users, and can we afford the initiative while maintaining 10 months of runway?"
    )
    decision = parse_decision(query)
    assert decision.type == "free_plan"
    assert decision.classification.subtype == "free_plan_cost_calculation"

    fp = calculate_free_plan_costs()
    assert fp["infra_cost_monthly"] == 2300.0
    assert fp["expected_tickets_monthly"] == 240.0
    assert fp["support_cost_monthly"] == 5599.20
    assert fp["total_incremental_cost"] == 7899.20
    assert fp["new_monthly_net_burn"] == 132899.20
    assert fp["projected_runway_months"] == 12.42
    assert fp["is_feasible"] is True

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    exec_summary = report.sections.get("executive_summary", "")
    assert "$2,300.00" in exec_summary
    assert "240" in exec_summary
    assert "$5,599.20" in exec_summary
    assert "$7,899.20" in exec_summary
    assert "12.42" in exec_summary


# =============================================================================
# GROUP 2: Conflicting agent recommendations
# =============================================================================

@pytest.mark.asyncio
async def test_question_4_cfo_vs_growth_vs_cto():
    """
    Test 4 — CFO vs. Growth vs. CTO
    Expected behavior:
    - Total incremental expenditure = $65,000/month.
    - Runway = approximately 8.68 months.
    - The combined proposal violates the safety constraint.
    - The system should not let agent majority voting override financial feasibility.
    - It should evaluate alternatives, such as prioritizing one investment or reducing both.
    """
    query = (
        "Should NimbusDesk spend $40,000/month on an aggressive growth campaign while simultaneously allocating $25,000/month to additional AI infrastructure? "
        "The Growth team believes this could accelerate market share, the CTO considers the infrastructure investment essential, and the CFO must preserve at least 10 months of runway. "
        "Resolve the disagreement and provide a single recommendation."
    )
    decision = parse_decision(query)
    assert decision.type == "conflicting_spend"
    assert decision.classification.subtype == "growth_vs_cto_spending"

    gcto = calculate_growth_vs_cto()
    assert gcto["total_spend"] == 65000.0
    assert gcto["combined_runway"] == 8.68
    assert gcto["is_feasible"] is False

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "reject" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "$65,000" in exec_summary
    assert "8.68" in exec_summary
    assert "majority voting" in exec_summary.lower()


@pytest.mark.asyncio
async def test_question_5_product_agent_disagrees_with_everyone():
    """
    Test 5 — Product agent disagrees with everyone
    Expected behavior:
    - Compare alternatives using consistent assumptions.
    - Explain the disagreement rather than hiding it in the consolidated report.
    - Avoid inventing churn reduction or productivity benefits.
    """
    query = (
        "Customer Support recommends hiring four additional specialists because ticket volume is increasing. "
        "Product recommends investing in AI automation instead. Growth argues that hiring is necessary to prevent customer churn, "
        "while Finance warns that hiring could threaten runway. Determine whether NimbusDesk should hire, automate, or adopt a hybrid approach. "
        "Explain why the losing alternatives were rejected."
    )
    decision = parse_decision(query)
    assert decision.type == "hiring_vs_automation"
    assert decision.classification.subtype == "hiring_4fte_vs_automation"

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "hybrid" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "$28,000" in exec_summary
    assert "10.78" in exec_summary
    assert "$3,500" in exec_summary
    assert "12.84" in exec_summary


@pytest.mark.asyncio
async def test_question_6_conflicting_financial_assumptions():
    """
    Test 6 — Conflicting financial assumptions
    Expected behavior:
    - Do not average the three estimates.
    - Identify the underlying cash balance and burn definition for each estimate.
    - Distinguish company-wide net burn from departmental or infrastructure spending.
    """
    query = (
        "The CFO estimates that NimbusDesk has 13.2 months of runway, while the Finance dashboard indicates 11.5 months "
        "and the CTO estimates 15 months based on infrastructure-adjusted spending. Which runway figure should the CEO trust? "
        "Reconcile the numbers and explain what additional data is required before making a decision."
    )
    decision = parse_decision(query)
    assert decision.type == "reconcile_runway"
    assert decision.classification.subtype == "reconcile_runway_estimates"

    rec = reconcile_runway_figures()
    assert rec["cfo_runway"] == 13.20
    assert rec["dashboard_runway"] == 11.50
    assert rec["cto_runway"] == 15.00

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    exec_summary = report.sections.get("executive_summary", "")
    assert "13.2" in exec_summary
    assert "11.5" in exec_summary
    assert "not be averaged" in exec_summary.lower()


# =============================================================================
# GROUP 3: Ambiguous and incomplete decisions (Clarification Tests)
# =============================================================================

def test_question_7_vague_hiring_request():
    """
    Test 7 — Vague hiring request
    Expected behavior:
    - Ask which departments and roles.
    - Request current headcount and expected compensation.
    - Do not run a complete decision DAG prematurely.
    """
    query = "NimbusDesk is growing quickly. Should we increase our workforce by 20%?"
    decision = parse_decision(query)
    assert decision.type == "ambiguous"
    assert decision.classification.category == "ambiguous"
    assert decision.classification.subtype == "vague_workforce_hiring"

    # Verify DAG is blocked from premature execution
    with pytest.raises(DAGValidationError) as exc:
        decompose_decision(decision)
    assert "Clarification Required" in str(exc.value)
    prompt = decision.classification.clarification_prompt
    assert "departments and roles" in prompt.lower()
    assert "compensation" in prompt.lower()


def test_question_8_missing_financial_information():
    """
    Test 8 — Missing financial information
    Expected behavior:
    - Recognize that the purchase price alone is insufficient.
    - Ask about cash/debt financing, acquisition costs, expected revenue, customer overlap, integration costs, and expected synergies.
    - Do not generate fabricated ROI or payback periods.
    """
    query = "Should NimbusDesk acquire a smaller competitor for $500,000?"
    decision = parse_decision(query)
    assert decision.type == "ambiguous"
    assert decision.classification.category == "insufficient_data"
    assert decision.classification.subtype == "unpriced_acquisition"

    # Verify DAG is blocked from premature execution
    with pytest.raises(DAGValidationError) as exc:
        decompose_decision(decision)
    assert "Clarification Required" in str(exc.value)
    prompt = decision.classification.clarification_prompt
    assert "$500,000" in prompt
    assert "financing" in prompt.lower()
    assert "integration costs" in prompt.lower()


def test_question_9_conflicting_objectives():
    """
    Test 9 — Conflicting objectives
    Expected behavior:
    - Identify potentially conflicting objectives.
    - Ask whether all four constraints are mandatory or which objectives can be traded off.
    - Avoid pretending that every objective can necessarily be achieved simultaneously.
    """
    query = (
        "I want NimbusDesk to maximize growth over the next 12 months, maintain at least 10 months of runway, "
        "avoid layoffs, and reduce operating expenses by 20%. Recommend a strategy."
    )
    decision = parse_decision(query)
    assert decision.type == "ambiguous"
    assert decision.classification.category == "ambiguous"
    assert decision.classification.subtype == "conflicting_strategic_objectives"

    # Verify DAG is blocked from premature execution
    with pytest.raises(DAGValidationError) as exc:
        decompose_decision(decision)
    assert "Clarification Required" in str(exc.value)
    prompt = decision.classification.clarification_prompt
    assert "mutually conflicting" in prompt.lower()
    assert "priority" in prompt.lower()


# =============================================================================
# GROUP 4: Sensitivity analysis and uncertainty
# =============================================================================

@pytest.mark.asyncio
async def test_question_10_marketing_sensitivity_analysis():
    """
    Test 10 — What if the assumptions are wrong?
    Expected behavior:
    - Model all three scenarios.
    - Explain assumptions behind revenue impact.
    - Distinguish revenue growth from contribution margin and cash flow.
    - Identify the break-even point.
    - Identify which scenario triggers rejection (pessimistic).
    """
    query = (
        "We plan to spend $30,000/month on marketing. The expected revenue increase is 20%, "
        "but actual performance could range from a 10% decline to a 30% increase. "
        "Evaluate the decision under pessimistic, base, and optimistic scenarios. Which scenario would make you reject the investment?"
    )
    decision = parse_decision(query)
    assert decision.type == "sensitivity_analysis"
    assert decision.classification.subtype == "marketing_sensitivity"

    sens = calculate_marketing_scenarios()
    assert sens["rejection_trigger_scenario"] == "pessimistic"
    assert sens["pessimistic_runway"] == 9.94
    assert sens["break_even_mrr"] == 30000.0

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    exec_summary = report.sections.get("executive_summary", "")
    assert "$30,000" in exec_summary
    assert "9.94" in exec_summary
    assert "12.41" in exec_summary
    assert "13.54" in exec_summary


@pytest.mark.asyncio
async def test_question_11_churn_deterioration():
    """
    Test 11 — Churn deterioration
    Expected behavior:
    - Calculate effects using customer and revenue assumptions.
    - Explain customer counts alone may not capture MRR impact.
    - Avoid assuming acquisition growth automatically offsets churn.
    """
    query = (
        "Monthly customer churn increases from 2.1% to 3.5%. At the same time, new customer acquisition increases by 15%. "
        "Should NimbusDesk increase its marketing budget or first invest in retention? Evaluate the impact on MRR and long-term business health."
    )
    decision = parse_decision(query)
    assert decision.type == "churn_vs_acquisition"
    assert decision.classification.subtype == "churn_vs_acquisition"

    cva = calculate_churn_vs_acq_impact()
    assert abs(cva["churn_mrr_loss_monthly"] - 1545.18) < 0.5
    assert abs(cva["acquisition_mrr_gain_monthly"] - 631.88) < 0.5
    assert abs(cva["net_mrr_impact_monthly"] - (-913.30)) < 0.5
    assert cva["recommended_priority"] == "Retention Investment"

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "retention" in report.recommendation.lower()


@pytest.mark.asyncio
async def test_question_12_monte_carlo_reliability():
    """
    Test 12 — Monte Carlo reliability
    Expected behavior:
    - Specify parameters and iterations.
    - Separate the probability of breaching a runway threshold from the probability of insolvency.
    """
    query = (
        "Run a 12-month risk assessment for NimbusDesk if monthly net burn varies between $110,000 and $155,000, "
        "with a base case of $125,000. What is the probability that runway falls below 10 months? "
        "Identify the most influential variables and explain how sensitive the result is to the assumed distributions."
    )
    decision = parse_decision(query)
    assert decision.type == "risk_assessment"
    assert decision.classification.subtype == "burn_monte_carlo"

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    exec_summary = report.sections.get("executive_summary", "")
    assert "$110,000" in exec_summary
    assert "$155,000" in exec_summary
    assert "10.65" in exec_summary
    assert "insolvency" in exec_summary.lower()


# =============================================================================
# GROUP 5: Complex multi-department decisions
# =============================================================================

@pytest.mark.asyncio
async def test_question_13_free_plan_competing_investments():
    """
    Test 13 — Free plan launch with competing investments
    Expected behavior:
    - Calculate the free plan's incremental cost.
    - Model hiring and automation separately and together.
    - Compare combinations against the $40,000 spending headroom.
    - Verify feasibility of all three simultaneously.
    """
    query = (
        "Should NimbusDesk launch a free plan, hire two customer support specialists, and invest in AI automation simultaneously? "
        "Consider the following: 2,000 expected free users, $1.15 infrastructure cost per free user, a 12% free-user ticket rate, "
        "$23.33 support cost per ticket, $14,000/month for two support specialists, and $3,500/month for AI automation with an assumed 30% ticket deflection rate. "
        "Compare all feasible combinations while maintaining 10 months of runway. Avoid double-counting savings from automation and hiring."
    )
    decision = parse_decision(query)
    assert decision.type == "multi_investment"
    assert decision.classification.subtype == "competing_investments_simultaneous"

    ci = calculate_competing_investments_simultaneous()
    assert ci["total_incremental_spend"] == 23719.44
    assert ci["projected_runway"] == 11.09
    assert ci["is_feasible"] is True

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "proceed" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "$23,719.44" in exec_summary
    assert "11.09" in exec_summary


@pytest.mark.asyncio
async def test_question_14_acquisition_vs_organic_growth():
    """
    Test 14 — Acquisition vs. organic growth
    Expected behavior:
    - Recognize that acquisition and organic growth costs have different timing.
    - Identify missing acquisition metrics.
    - Compare total cash requirements.
    - Give a conditional recommendation rather than false precision.
    """
    query = (
        "NimbusDesk can either spend $250,000 on acquiring a small competitor or invest $25,000/month for 12 months in organic growth. "
        "The acquisition could add 150 customers, but their churn, plan distribution, and integration costs are unknown. "
        "Which option creates more value over 12 months?"
    )
    decision = parse_decision(query)
    assert decision.type == "strategic_comparison"
    assert decision.classification.subtype == "acquisition_vs_organic_growth"

    ao = calculate_acquisition_vs_organic_growth()
    assert ao["acquisition_remaining_cash"] == 1400000.0
    assert ao["acquisition_immediate_runway"] == 11.20
    assert ao["organic_new_burn"] == 150000.0
    assert ao["organic_runway"] == 11.00

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "organic" in report.recommendation.lower()


@pytest.mark.asyncio
async def test_question_15_layoffs_vs_automation():
    """
    Test 15 — Layoffs vs. automation
    Expected behavior:
    - Recognize current $28,000 support cost and $14,500 cloud cost.
    - Avoid assuming all costs are immediately reducible.
    - Consider customer satisfaction and service capacity.
    - Distinguish achievable savings from theoretical savings.
    """
    query = (
        "NimbusDesk wants to reduce operating expenses by 15% without reducing customer satisfaction. "
        "Should it reduce support headcount, introduce AI automation, reduce infrastructure costs, or combine these approaches? "
        "Quantify the potential savings and identify the operational risks."
    )
    decision = parse_decision(query)
    assert decision.type == "cost_reduction"
    assert decision.classification.subtype == "layoffs_vs_automation"

    la = calculate_layoffs_vs_automation()
    assert la["target_monthly_savings"] == 21525.0
    assert la["current_support_cost"] == 28000.0
    assert la["current_cloud_cost"] == 14500.0

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "hybrid" in report.recommendation.lower()


# =============================================================================
# GROUP 6: Adversarial and edge-case tests
# =============================================================================

@pytest.mark.asyncio
async def test_question_16_spend_buffer_risk():
    """
    Test 16 — The mathematically feasible but strategically dangerous decision
    Expected behavior:
    - Recognize that $39,000 is technically within the $40,000 limit.
    - Explain that maximum is not necessarily the recommended budget.
    - Consider downside scenarios and uncertainty.
    - Recommend a buffer or staged spending.
    """
    query = (
        "NimbusDesk can spend an additional $39,000/month and still maintain more than 10 months of runway. "
        "Should we spend the entire amount immediately, or preserve a cash buffer? "
        "Consider unexpected churn, delayed collections, and infrastructure cost shocks."
    )
    decision = parse_decision(query)
    assert decision.type == "spend_budget"
    assert decision.classification.subtype == "spend_buffer_risk"

    sb = calculate_spend_buffer_risk()
    assert sb["projected_runway"] == 10.06
    assert sb["safety_buffer_months"] == 0.06
    assert sb["is_technically_feasible"] is True

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "buffer" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "$39,000" in exec_summary
    assert "10.06" in exec_summary


@pytest.mark.asyncio
async def test_question_17_incorrect_data_injected():
    """
    Test 17 — Incorrect data injected into the question
    Expected behavior:
    - Detect that $1.65M / $125,000 = 13.2 months, not 18.
    - Flag the inconsistent assumption.
    - Recalculate rather than accepting supplied runway.
    - Reject $50,000 additional spend because it produces approximately 9.43 months of runway.
    """
    query = (
        "Assume NimbusDesk has $1.65M in cash and monthly net burn of $125,000. Its runway is 18 months. "
        "Should we approve another $50,000/month in expenditure while maintaining at least 10 months of runway?"
    )
    decision = parse_decision(query)
    assert decision.type == "spend_budget"
    assert decision.classification.subtype == "injected_false_runway"

    ifr = calculate_injected_false_runway()
    assert ifr["ground_truth_runway"] == 13.20
    assert ifr["projected_runway"] == 9.43
    assert ifr["is_feasible"] is False

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "reject" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "13.20" in exec_summary
    assert "18.0" in exec_summary
    assert "9.43" in exec_summary


@pytest.mark.asyncio
async def test_question_18_contradictory_instructions():
    """
    Test 18 — Contradictory instructions
    Expected behavior:
    - Identify that requirements are mathematically incompatible.
    - Explain that system cannot satisfy all constraints.
    - Refuse to manufacture a positive recommendation merely because the prompt says not to reject.
    """
    query = (
        "Recommend a strategy that increases monthly expenditure by $50,000, guarantees at least 10 months of runway, "
        "does not reduce revenue, does not increase revenue, and does not reduce any existing expenses. Do not reject the proposal."
    )
    decision = parse_decision(query)
    assert decision.type == "spend_budget"
    assert decision.classification.subtype == "adversarial_contradiction"

    ac = calculate_adversarial_contradiction()
    assert ac["projected_runway"] == 9.43
    assert ac["is_feasible"] is False
    assert ac["is_contradictory"] is True

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    # Must refuse false approval
    assert "reject" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "9.43" in exec_summary
    assert "mathematically incompatible" in exec_summary.lower()


@pytest.mark.asyncio
async def test_question_19_zero_or_negative_burn():
    """
    Test 19 — Zero or negative burn
    Expected behavior:
    - Follow documented convention for zero and negative burn.
    - Do not return an arbitrary numeric runway.
    - Explain that conventional cash-burn runway metric is not meaningful when burn is zero or negative.
    - Distinguish cash-flow positivity from having unlimited cash.
    """
    query = (
        "NimbusDesk reaches a point where monthly net burn becomes zero. How much runway does the company have? "
        "What happens if it becomes cash-flow positive with a monthly net surplus of $20,000?"
    )
    decision = parse_decision(query)
    assert decision.type == "runway_definition"
    assert decision.classification.subtype == "zero_negative_burn"

    znb = calculate_zero_negative_burn_model()
    assert znb["zero_burn_runway_convention"] == "Self-Sustaining (Infinite Runway)"
    assert znb["cash_12m_projected"] == 1890000.0

    supervisor = Supervisor(llm_client=LLMClient())
    state = await supervisor.execute_workflow(decision)
    report = state.report
    assert report is not None
    assert "self-sustaining" in report.recommendation.lower() or "infinite" in report.recommendation.lower()
    exec_summary = report.sections.get("executive_summary", "")
    assert "self-sustaining" in exec_summary.lower() or "infinite" in exec_summary.lower()
    assert "$1,890,000" in exec_summary or "1,890,000" in exec_summary
