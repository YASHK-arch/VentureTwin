import pytest
from data.loader import load_company_data
from orchestrator.parser import parse_decision
from orchestrator.decomposer import decompose_decision, DAGValidationError
from orchestrator.supervisor import Supervisor
from state.schemas import Decision, Finding, Assumption
from simulation.finance import (
    calculate_runway,
    calculate_max_additional_spend,
    calculate_spend_runway,
    calculate_support_hiring,
    calculate_support_automation
)
from verification.verifier import run_all_verification_checks


def test_deterministic_finance_calculations():
    company_data = load_company_data()
    cash = float(company_data["financials"]["cash_balance"])  # $1,650,000
    burn = float(company_data["financials"]["monthly_burn_net"])  # $125,000

    # Test baseline runway: 1,650,000 / 125,000 = 13.2 months
    assert calculate_runway(cash, burn) == 13.2
    assert calculate_runway(cash, 0) is None
    assert calculate_runway(cash, -1000) is None

    # Test A: Max allowable spend to maintain 10.0 months runway
    # 1,650,000 / 10 = 165,000 allowable burn -> 165,000 - 125,000 = 40,000
    max_spend = calculate_max_additional_spend(cash, burn, 10.0)
    assert max_spend == 40000.0

    # Test D: Spend $50,000 -> 1,650,000 / 175,000 = 9.43 months
    rw_50k = calculate_spend_runway(cash, burn, 50000.0)
    assert rw_50k == 9.43
    assert rw_50k < 10.0  # Infeasible

    # Test E: Spend $30,000 -> 1,650,000 / 155,000 = 10.65 months
    rw_30k = calculate_spend_runway(cash, burn, 30000.0)
    assert rw_30k == 10.65
    assert rw_30k >= 10.0  # Feasible

    # Test B: Support hiring (2 FTEs)
    hiring = calculate_support_hiring(company_data, additional_fte=2)
    assert hiring["additional_fte"] == 2
    assert hiring["additional_monthly_expenditure"] == 14000.0
    assert hiring["new_total_support_cost"] == 42000.0
    assert hiring["new_monthly_net_burn"] == 139000.0
    assert hiring["projected_runway_months"] == 11.87
    assert hiring["projected_ticket_capacity"] == 1800
    assert hiring["is_feasible"] is True

    # Test F: Support automation alternative
    auto = calculate_support_automation(company_data, monthly_tooling_cost=3500.0, deflection_rate=0.30)
    assert auto["monthly_tooling_cost"] == 3500.0
    assert auto["deflected_tickets_monthly"] == 360
    assert auto["new_monthly_net_burn"] == 128500.0
    assert auto["projected_runway_months"] == 12.84
    assert auto["is_feasible"] is True


@pytest.mark.asyncio
async def test_case_a_max_additional_expenditure():
    """
    Test Case 1 / Test A:
    Query: 'What is the maximum additional monthly expenditure NimbusDesk can afford while maintaining at least 10 months of cash runway?'
    """
    query = "What is the maximum additional monthly expenditure NimbusDesk can afford while maintaining at least 10 months of cash runway?"
    decision = parse_decision(query)
    assert decision.type == "max_expenditure"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)
    report = state.report

    # 1. Recommendation specifies $40,000/month
    assert "40,000" in report.recommendation
    assert "Maximum Additional Monthly Expenditure: $40,000/month" in report.recommendation

    # 2. Executive summary mentions $40,000 and reconciles CTO's $25,000 infrastructure figure
    exec_sum = report.sections["executive_summary"]
    assert "40,000" in exec_sum
    assert "25,000" in exec_sum
    assert "CTO" in exec_sum

    # 3. Reconciled financial model section exists and contains exact numbers
    fin_model = report.sections.get("reconciled_financial_model", {})
    assert fin_model.get("maximum_additional_monthly_expenditure") == 40000.0

    # 4. Top strategy is feasible
    strats = report.sections["strategies_compared"]
    assert len(strats) >= 3
    top_strat = strats[0]
    assert top_strat["is_feasible"] is True
    assert "40k" in top_strat["strategy"]
    assert top_strat["runway_months_12"] >= 10.0

    # 5. All 8 verification checks pass
    verifs = report.sections["verification_summary"]
    for v in verifs:
        assert v["status"] == "passed", f"Check {v['check_name']} failed: {v['detail']}"


@pytest.mark.asyncio
async def test_case_b_support_team_expansion():
    """
    Test Case 2 / Test B:
    Query: 'Should NimbusDesk hire two additional customer support specialists to improve support capacity?'
    """
    query = "Should NimbusDesk hire two additional customer support specialists to improve support capacity?"
    decision = parse_decision(query)
    assert decision.type == "support_hiring"
    assert decision.classification.target_fte == 2
    assert decision.classification.department == "Customer Support"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)
    report = state.report

    # 1. Recommendation is Proceed with Limits (Hire 2 support specialists)
    assert "Hire Two Customer Support Specialists" in report.recommendation
    assert "14,000" in report.recommendation

    # 2. Numbers tie out: 4 -> 6 FTEs, $14k cost, $139k burn, 11.87mo runway, 1,800 tickets
    exec_sum = report.sections["executive_summary"]
    assert "14,000" in exec_sum
    assert "139,000" in exec_sum
    assert "11.87" in exec_sum or "11.9" in exec_sum
    assert "1,800" in exec_sum

    # 3. Product alternative (AI automation $3,500, 360 deflected, 12.84mo) evaluated
    assert "3,500" in exec_sum or "automation" in exec_sum.lower()

    # 4. Must NOT be transformed into generic engineering or growth headcount
    assert "engineering" not in report.recommendation.lower()
    assert "growth roles" not in report.recommendation.lower()

    # 5. All verification checks pass
    verifs = report.sections["verification_summary"]
    for v in verifs:
        assert v["status"] == "passed", f"Check {v['check_name']} failed: {v['detail']}"


def test_case_c_ambiguous_question_clarification():
    """
    Test Case 3 / Test C:
    Query: 'How many employees should NimbusDesk hire?'
    Clarification Engine intercepts before running agent analysis.
    """
    query = "How many employees should NimbusDesk hire?"
    decision = parse_decision(query)

    assert decision.type == "ambiguous"
    assert decision.classification.category == "ambiguous"
    assert "Which department" in decision.classification.clarification_prompt
    assert "Customer Support" in decision.classification.clarification_options
    assert "Engineering" in decision.classification.clarification_options

    # Decomposer must raise DAGValidationError to prevent premature agent DAG execution
    with pytest.raises(DAGValidationError) as excinfo:
        decompose_decision(decision)
    assert "clarification required" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_case_d_proposed_spend_50k_infeasible():
    """
    Test Case 4 / Test D:
    Query: 'Can NimbusDesk afford an additional monthly expenditure of $50,000?'
    Runway: $1,650,000 / $175,000 = 9.43 months < 10.0 -> Infeasible, Rejected.
    """
    query = "Can NimbusDesk afford an additional monthly expenditure of $50,000?"
    decision = parse_decision(query)
    assert decision.type == "spend_budget"
    assert decision.classification.target_spend == 50000.0

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)
    report = state.report

    # 1. Final recommendation rejects due to breach of 10-month runway constraint
    assert "Reject" in report.recommendation
    assert "Breaches 10.0-Month Runway Constraint" in report.recommendation
    assert "50,000" in report.recommendation

    # 2. Executive summary explains 9.43 months runway and $40,000 maximum allowable
    exec_sum = report.sections["executive_summary"]
    assert "9.43" in exec_sum
    assert "175,000" in exec_sum
    assert "40,000" in exec_sum

    # 3. Strategy A is marked infeasible in strategies_compared
    strats = report.sections["strategies_compared"]
    a_strat = next(s for s in strats if "50k" in s["strategy"])
    assert a_strat["is_feasible"] is False
    assert a_strat["runway_months_12"] < 10.0

    # 4. Verification checks pass
    verifs = report.sections["verification_summary"]
    for v in verifs:
        assert v["status"] == "passed", f"Check {v['check_name']} failed: {v['detail']}"


@pytest.mark.asyncio
async def test_case_e_proposed_spend_30k_feasible():
    """
    Test Case 5 / Test E:
    Query: 'Can NimbusDesk afford an additional monthly expenditure of $30,000?'
    Runway: $1,650,000 / $155,000 = 10.65 months >= 10.0 -> Feasible, Proceed.
    """
    query = "Can NimbusDesk afford an additional monthly expenditure of $30,000?"
    decision = parse_decision(query)
    assert decision.type == "spend_budget"
    assert decision.classification.target_spend == 30000.0

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)
    report = state.report

    # 1. Final recommendation proceeds: affordable
    assert "Proceed" in report.recommendation
    assert "30,000" in report.recommendation
    assert "Affordable" in report.recommendation

    # 2. Executive summary explains 10.65 months runway and remaining $10,000 headroom
    exec_sum = report.sections["executive_summary"]
    assert "10.65" in exec_sum
    assert "155,000" in exec_sum
    assert "10,000" in exec_sum

    # 3. Top strategy is feasible
    strats = report.sections["strategies_compared"]
    a_strat = next(s for s in strats if "30k" in s["strategy"])
    assert a_strat["is_feasible"] is True
    assert a_strat["runway_months_12"] >= 10.0

    # 4. Verification checks pass
    verifs = report.sections["verification_summary"]
    for v in verifs:
        assert v["status"] == "passed", f"Check {v['check_name']} failed: {v['detail']}"


@pytest.mark.asyncio
async def test_case_f_hiring_vs_ai_automation_debate():
    """
    Test Case 6 / Test F:
    Query: 'Should NimbusDesk hire support employees or invest in AI support automation?'
    Evaluates both alternatives, side-by-side trade-off, hybrid recommendation.
    """
    query = "Should NimbusDesk hire support employees or invest in AI support automation?"
    decision = parse_decision(query)
    assert decision.type == "hiring_vs_automation"

    supervisor = Supervisor()
    state = await supervisor.execute_workflow(decision)
    report = state.report

    # 1. Recommendation is Hybrid/Phased
    assert "Hybrid" in report.recommendation or "Phase" in report.recommendation

    # 2. Both alternatives evaluated and feasible
    strats = report.sections["strategies_compared"]
    strat_a = next(s for s in strats if "hire" in s["strategy"].lower())
    strat_b = next(s for s in strats if "automation" in s["strategy"].lower())
    assert strat_a["is_feasible"] is True
    assert strat_b["is_feasible"] is True

    # 3. Trade-off analysis present
    trade_offs = report.sections.get("trade_off_analysis", [])
    assert len(trade_offs) >= 1

    # 4. Verification checks pass
    verifs = report.sections["verification_summary"]
    for v in verifs:
        assert v["status"] == "passed", f"Check {v['check_name']} failed: {v['detail']}"
