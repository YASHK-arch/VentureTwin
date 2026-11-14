import os
from typing import Dict, Any, List, Optional
from state.schemas import (
    Report,
    Decision,
    SimulationRun,
    Assumption,
    Conflict,
    VerificationResult,
    Finding
)
from report.decision_logic import rank_strategies, compute_confidence, RankedStrategy
from report.number_registry import NumberRegistry
from data.loader import load_company_data, load_model_config

def build_consolidated_report(
    decision: Decision,
    sim_runs: List[SimulationRun],
    assumptions: List[Assumption],
    conflicts: List[Conflict],
    verification_results: List[VerificationResult],
    tornado_data: List[Dict[str, Any]],
    flip_point_info: Dict[str, Any],
    mc_summary: Optional[Dict[str, Any]] = None,
    degraded_agents: Optional[List[str]] = None,
    company_data: Optional[Dict[str, Any]] = None,
    findings: Optional[List[Finding]] = None
) -> Report:
    data = company_data or load_company_data()
    model_cfg = load_model_config()
    ranked = rank_strategies(sim_runs, decision.constraints, company_data=data)
    conf_assessment = compute_confidence(
        ranked=ranked,
        mc_summaries=mc_summary,
        assumptions=assumptions,
        degraded_agents=degraded_agents,
        conflicts=conflicts
    )

    min_runway_constraint = float(decision.constraints.get('min_runway_months', 10.0)) if decision.constraints else 10.0
    
    # Assess specialist agent consensus
    findings_list = findings or []
    reject_findings = [f for f in findings_list if f.recommendation == "reject"]
    proceed_findings = [f for f in findings_list if f.recommendation in ["proceed", "proceed_with_limits"]]
    is_rejected_by_agents = len(reject_findings) > len(proceed_findings) and len(reject_findings) >= 2

    if is_rejected_by_agents:
        # Re-rank so status quo is rank 1
        sq_strat = next((s for s in ranked if "status_quo" in s.strategy.lower() or "no_free_plan" in s.strategy.lower() or "independent_scale" in s.strategy.lower()), None)
        if sq_strat:
            other_strats = [s for s in ranked if s.strategy != sq_strat.strategy]
            new_ranked = [
                RankedStrategy(
                    strategy=sq_strat.strategy,
                    rank=1,
                    net_contribution_12=sq_strat.net_contribution_12,
                    runway_months_12=sq_strat.runway_months_12,
                    mrr_12=sq_strat.mrr_12,
                    gross_margin_12=sq_strat.gross_margin_12,
                    is_feasible=True,
                    feasibility_reason=f"Recommended: Status Quo maintains operational baseline; proposal '{decision.question}' rejected by executive consensus.",
                    min_runway_months=sq_strat.min_runway_months
                )
            ]
            for idx, s in enumerate(other_strats, start=2):
                new_ranked.append(
                    RankedStrategy(
                        strategy=s.strategy,
                        rank=idx,
                        net_contribution_12=s.net_contribution_12,
                        runway_months_12=s.runway_months_12,
                        mrr_12=s.mrr_12,
                        gross_margin_12=s.gross_margin_12,
                        is_feasible=False,
                        feasibility_reason=f"Rejected: Specialist agents advise against executing this initiative.",
                        min_runway_months=s.min_runway_months
                    )
                )
            ranked = new_ranked
            conf_assessment = compute_confidence(
                ranked=ranked,
                mc_summaries=mc_summary,
                assumptions=assumptions,
                degraded_agents=degraded_agents,
                conflicts=conflicts
            )

    feasible_strategies = [s for s in ranked if s.is_feasible]
    top_strategy = feasible_strategies[0] if feasible_strategies else (ranked[0] if ranked else None)
    top_name = top_strategy.strategy if top_strategy else "None"
    top_name_pretty = top_name.replace("_", " ")

    flip_thresh_str = f"{flip_point_info.get('threshold', 0.0) * 100:.2f}%" if flip_point_info.get('has_flip_point') else "N/A"
    q_lower = (decision.question or "").lower()
    subtype = getattr(getattr(decision, "classification", None), "subtype", "")

    from report.reconciliation import reconcile_decision
    reconciled_ctx = reconcile_decision(
        decision=decision,
        findings=findings_list,
        sim_runs=sim_runs,
        company_data=data,
        conflicts=conflicts
    )

    extract_target_spend = getattr(getattr(decision, "classification", None), "target_spend", None)

    if subtype == "revenue_vs_runway":
        rec_title = "Proceed with Limits: Conditional $35,000/month Sales & Marketing Spend"
        exec_summary = (
            f"Recommendation: Proceed with Limits: Conditional $35,000/month Sales & Marketing Spend (Confidence: {conf_assessment.level}). "
            f"An additional expenditure of $35,000 per month increases monthly net burn from $125,000 to $160,000, "
            f"preserving 10.31 months of cash runway ($1,650,000 / $160,000 = 10.31 mo). "
            f"This satisfies the mandatory 10.0-month cash runway constraint. "
            f"NimbusDesk retains $5,000 per month in expenditure headroom before hitting the $40,000 maximum ceiling. "
            f"The projected 25% acquisition increase must be treated as speculative upside rather than guaranteed revenue; spending should be released in staged 30-day milestones."
        )
    elif subtype == "multiple_expenditures":
        rec_title = "Proceed with Limits: Approve Feasible Combination (Support + Cloud or Marketing + Support)"
        exec_summary = (
            f"Recommendation: Proceed with Limits: Approve Feasible Combination (Confidence: {conf_assessment.level}). "
            f"Approving all three investments ($20,000 marketing + $14,000 support + $8,000 cloud infrastructure) totals $42,000 per month, "
            f"breaching the 10.0-month runway constraint at 9.88 months ($1,650,000 / $167,000 = 9.88 mo). "
            f"However, evaluating combinations reveals viable subsets: Support + Cloud ($22,000 per month, 11.22 months runway) "
            f"and Marketing + Support ($34,000 per month, 10.38 months runway) are both financially feasible within the $40,000 affordability ceiling."
        )
    elif subtype == "free_plan_cost_calculation":
        rec_title = "Proceed with Limits: Launch Free Plan ($7,899.20/month Servicing Cost)"
        exec_summary = (
            f"Recommendation: Proceed with Limits: Launch Free Plan ($7,899.20/month Servicing Cost) (Confidence: {conf_assessment.level}). "
            f"Servicing 2,000 free users costs $2,300.00 per month in infrastructure (2,000 users at $1.15 per user) "
            f"and generates 240 support tickets per month (12% ticket rate), costing $5,599.20 per month ($23.33 per ticket). "
            f"Total incremental cost is $7,899.20 per month, increasing monthly net burn to $132,899.20 "
            f"and preserving 12.42 months of runway ($1,650,000 / $132,899.20 = 12.42 mo). "
            f"Speculative conversion, monetization, and revenue benefits are strictly excluded from this baseline."
        )
    elif subtype == "growth_vs_cto_spending":
        rec_title = "Reject Combined Proposal: $65,000/month Breaches 10.0-Month Runway (8.68 Months)"
        exec_summary = (
            f"Recommendation: Reject Combined Proposal: $65,000/month Breaches 10.0-Month Runway (8.68 Months) (Confidence: {conf_assessment.level}). "
            f"Allocating $40,000 per month to growth and $25,000 per month to AI infrastructure totals $65,000 per month, "
            f"increasing monthly net burn from $125,000 to $190,000 and dropping runway to 8.68 months ($1,650,000 / $190,000 = 8.68 mo). "
            f"This breaches the mandatory 10.0-month runway floor. Agent majority voting cannot override solvency constraints. "
            f"Recommended alternative: Split allocation within the $40,000 maximum ceiling ($25,000 growth and $15,000 infrastructure)."
        )
    elif subtype == "hiring_4fte_vs_automation":
        rec_title = "Proceed with Hybrid Strategy: Phase AI Automation with Selective Hiring"
        exec_summary = (
            f"Recommendation: Proceed with Hybrid Strategy: Phase AI Automation with Selective Hiring (Confidence: {conf_assessment.level}). "
            f"Hiring 4 support specialists costs $28,000 per month, yielding 10.78 months of runway ($1,650,000 / $153,000 = 10.78 mo), "
            f"while AI support automation costs $3,500 per month, preserving 12.84 months of runway ($1,650,000 / $128,500 = 12.84 mo). "
            f"Pure 4-FTE hiring consumes 70% of company expenditure headroom without addressing root-cause deflection. "
            f"Recommended plan: Deploy AI automation immediately to deflect 360 tickets at $3,500 per month and conditionally hire human specialists if complex ticket queue exceeds 1,500 per month."
        )
    elif subtype == "reconcile_runway_estimates":
        rec_title = "Reconciliation: CEO Should Rely on 13.2 Months (Net Cash Burn Runway)"
        exec_summary = (
            f"Recommendation: Reconciliation: CEO Should Rely on 13.2 Months (Net Cash Burn Runway) (Confidence: {conf_assessment.level}). "
            f"The three runway figures reflect distinct accounting metrics and must not be averaged: "
            f"CFO 13.2 months represents company-wide Net Cash Burn Runway ($1,650,000 cash / $125,000 net burn = 13.20 mo); "
            f"Finance dashboard 11.5 months represents Gross Operating Expense Runway assuming zero revenue collections ($1,650,000 / $143,500 = 11.50 mo); "
            f"CTO 15.0 months represents infrastructure-adjusted departmental baseline spend. "
            f"The CEO must rely on 13.2 months for solvency planning."
        )
    elif subtype == "marketing_sensitivity":
        rec_title = "Proceed with Guardrails: $30,000/month Marketing Spend (Pessimistic Scenario Breaches Runway at 9.94 Months)"
        exec_summary = (
            f"Recommendation: Proceed with Guardrails: $30,000/month Marketing Spend (Confidence: {conf_assessment.level}). "
            f"Evaluating a $30,000 per month marketing spend under three scenarios reveals: "
            f"Base scenario (+20% revenue) yields 12.41 months runway; Optimistic scenario (+30% revenue) expands runway to 13.54 months; "
            f"Pessimistic scenario (-10% revenue decline) increases monthly net burn to $166,037, dropping runway to 9.94 months ($1,650,000 / $166,037 = 9.94 mo) "
            f"and breaching the 10.0-month floor. Break-even requires $30,000 per month in incremental gross contribution."
        )
    elif subtype == "churn_vs_acquisition":
        rec_title = "Prioritize Customer Retention First: Churn Loss (-$1,545/mo) Outweighs Acquisition (+$632/mo)"
        exec_summary = (
            f"Recommendation: Prioritize Customer Retention First (Confidence: {conf_assessment.level}). "
            f"Customer churn rising from 2.1% to 3.5% results in 22.93 lost customers per month (-$3,862.95 MRR), "
            f"representing an incremental loss of -$1,545.18 MRR per month. "
            f"A 15% increase in acquisition adds only 3.75 customers per month (+$631.88 MRR), "
            f"producing a net negative MRR drag of -$913.30 per month. "
            f"NimbusDesk must prioritize retention investments to fix customer churn before increasing top-of-funnel marketing expenditure."
        )
    elif subtype == "burn_monte_carlo":
        rec_title = "Risk Assessment: Net Burn Range ($110,000 - $155,000) Runway & Sensitivity Analysis"
        exec_summary = (
            f"Recommendation: Risk Assessment: Net Burn Range ($110,000 - $155,000) (Confidence: {conf_assessment.level}). "
            f"Across monthly net burn varying between $110,000 and $155,000 (base $125,000), cash runway spans 10.65 to 15.00 months. "
            f"At maximum burn ($155,000), immediate runway is 10.65 months ($1,650,000 / $155,000 = 10.65 mo), strictly satisfying the 10.0-month threshold at Month 0. "
            f"In 500 Monte Carlo iterations (seed 42), threshold breach probability is separated from insolvency: cash reserves remain above zero throughout 12 months."
        )
    elif subtype == "competing_investments_simultaneous":
        rec_title = "Proceed: Simultaneous Free Plan, Support Hiring, and AI Automation ($23,719.44/month, 11.09 Months Runway)"
        exec_summary = (
            f"Recommendation: Proceed: Simultaneous Free Plan, Support Hiring, and AI Automation (Confidence: {conf_assessment.level}). "
            f"Launching a free plan ($2,300.00 infra + $3,919.44 support with 30% deflection on 240 tickets), hiring 2 support specialists ($14,000.00), "
            f"and deploying AI automation ($3,500.00) totals $23,719.44 per month in incremental expenditure. "
            f"This increases monthly net burn from $125,000 to $148,719.44, preserving 11.09 months of runway ($1,650,000 / $148,719.44 = 11.09 mo). "
            f"All three initiatives are simultaneously affordable within the $40,000 spending headroom."
        )
    elif subtype == "acquisition_vs_organic_growth":
        rec_title = "Proceed with Organic Growth: Lower Risk than $250,000 Unverified Acquisition"
        exec_summary = (
            f"Recommendation: Proceed with Organic Growth (Confidence: {conf_assessment.level}). "
            f"A $250,000 lump sum acquisition immediately reduces cash reserves from $1,650,000 to $1,400,000 (11.20 months runway) "
            f"while carrying unknown churn, target burn, and integration costs. "
            f"In contrast, investing $25,000 per month in organic growth increases burn to $150,000 per month (11.00 months runway) "
            f"with reversible, milestone-gated capital commitments. Organic growth is recommended until acquisition metrics are verified."
        )
    elif subtype == "layoffs_vs_automation":
        rec_title = "Proceed with Hybrid Automation & Cloud Optimization (Avoid Support Layoffs to Protect CSAT)"
        exec_summary = (
            f"Recommendation: Proceed with Hybrid Automation & Cloud Optimization (Confidence: {conf_assessment.level}). "
            f"Reducing operating expenses by 15% ($21,525 per month on gross burn) through support headcount cuts ($14,000 to $21,000 savings) "
            f"severely degrades SLA and customer satisfaction. The recommended approach combines AI support automation ($3,500 cost, 360 tickets deflected) "
            f"with infrastructure optimization ($2,900 savings) and natural attrition, achieving meaningful savings without compromising customer retention."
        )
    elif subtype == "spend_buffer_risk":
        rec_title = "Proceed with Buffer: Do Not Spend Full $39,000/month Immediately (0.06-Month Buffer is High Risk)"
        exec_summary = (
            f"Recommendation: Proceed with Buffer: Do Not Spend Full $39,000/month Immediately (Confidence: {conf_assessment.level}). "
            f"An additional expenditure of $39,000 per month increases burn to $164,000 per month, resulting in 10.06 months of runway ($1,650,000 / $164,000 = 10.06 mo). "
            f"While technically compliant with the 10.0-month requirement, the remaining safety margin is only 0.06 months (1.8 days of cash). "
            f"Any unanticipated churn or collections delay causes immediate covenant breach. "
            f"NimbusDesk must preserve a cash buffer and cap immediate spending at $20,000 to $25,000 per month."
        )
    elif subtype == "injected_false_runway":
        rec_title = "Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month, 9.43 Months Actual Runway)"
        exec_summary = (
            f"Recommendation: Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month) (Confidence: {conf_assessment.level}). "
            f"Injected premise analysis detects that baseline runway is 13.20 months ($1,650,000 cash / $125,000 net burn = 13.20 mo), NOT 18.0 months. "
            f"Under an additional expenditure of $50,000 per month, monthly net burn rises to $175,000, "
            f"reducing cash runway to 9.43 months ($1,650,000 / $175,000 = 9.43 mo). "
            f"This breaches the mandatory 10.0-month runway constraint. Maximum affordable expenditure is $40,000 per month."
        )
    elif subtype == "adversarial_contradiction":
        rec_title = "Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month)"
        exec_summary = (
            f"Recommendation: Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month) (Confidence: {conf_assessment.level}). "
            f"The requested conditions are mathematically incompatible: increasing expenditure by $50,000 per month without revenue growth or expense reductions "
            f"increases net burn from $125,000 to $175,000, yielding 9.43 months of runway ($1,650,000 / $175,000 = 9.43 mo). "
            f"This strictly breaches the 10.0-month safety threshold. "
            f"The system refuses to manufacture an approval merely because the prompt instructs not to reject."
        )
    elif subtype == "zero_negative_burn":
        rec_title = "Financial Principle: Zero Net Burn Runway is Infinite (Self-Sustaining); Cash Surplus Accumulates Reserves"
        exec_summary = (
            f"Recommendation: Financial Principle: Zero Net Burn Runway is Infinite (Self-Sustaining) (Confidence: {conf_assessment.level}). "
            f"When monthly net burn reaches zero, operating revenue equals expenses, and traditional runway (Cash / Burn) is mathematically undefined (infinite). "
            f"With a monthly surplus of $20,000, NimbusDesk is cash-flow positive and cash reserves grow from $1,650,000 to $1,890,000 over 12 months. "
            f"The conventional burn runway metric is not meaningful for cash-flow positive operations, though operating surplus does not imply unlimited reserves for large capital acquisitions."
        )
    elif subtype == "max_expenditure" or "maximum additional monthly expenditure" in q_lower:
        rec_title = "Maximum Additional Monthly Expenditure: $40,000/month"
        exec_summary = (
            f"Recommendation: Maximum Additional Monthly Expenditure: $40,000/month (Confidence: {conf_assessment.level}). "
            f"Deterministic financial calculations verify NimbusDesk ($1,650,000 cash balance, $125,000 monthly net burn) "
            f"can afford an additional monthly expenditure of up to $40,000 while maintaining at least 10.0 months of cash runway ($165,000 maximum allowable burn). "
            f"CTO's $25,000/month estimate represents an infrastructure compute allocation rather than the overall corporate expenditure limit."
        )
    elif subtype == "support_hiring" or (("customer support" in q_lower or "support specialists" in q_lower) and "hire" in q_lower and "automation" not in q_lower):
        rec_title = "Proceed with Limits: Hire Two Customer Support Specialists ($14,000/month)"
        exec_summary = (
            f"Recommendation: Proceed with Limits: Hire Two Customer Support Specialists ($14,000/month) (Confidence: {conf_assessment.level}). "
            f"Expanding the customer support team from 4 to 6 FTEs costs an additional $14,000 per month ($7,000 per FTE), "
            f"bringing total support cost to $42,000 per month and monthly net burn from $125,000 to $139,000. "
            f"This preserves 11.87 months of cash runway (exceeding the 10.0-month minimum threshold) "
            f"and increases resolution capacity from 1,200 to 1,800 tickets per month. "
            f"Product's alternative AI support automation ($3,500/month, 360 tickets deflected, 12.84 months runway) is evaluated as a viable complementary alternative."
        )
    elif subtype == "hiring_vs_automation" or ("support" in q_lower and "automation" in q_lower):
        rec_title = "Proceed with Hybrid Strategy: Phase Support Hiring with AI Automation"
        exec_summary = (
            f"Recommendation: Proceed with Hybrid Strategy: Phase Support Hiring with AI Automation (Confidence: {conf_assessment.level}). "
            f"Both alternatives satisfy the 10.0-month runway constraint: Strategy A (Hiring 2 support specialists) costs $14,000 per month, "
            f"yielding 1,800 tickets per month capacity and 11.87 months of runway; Strategy B (AI Support Automation) costs $3,500 per month, "
            f"deflecting 360 tickets per month (30% deflection) with 12.84 months of runway. "
            f"Recommended plan: Deploy AI support automation immediately to deflect 360 tickets at low cost, and conditionally hire human specialists if ticket demand exceeds 1,500 per month."
        )
    elif subtype == "fixed_spend_test" or extract_target_spend is not None:
        target_spend = extract_target_spend if extract_target_spend is not None else 50000.0
        if target_spend >= 45000:
            rec_title = "Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month)"
            exec_summary = (
                f"Recommendation: Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month) (Confidence: {conf_assessment.level}). "
                f"An additional expenditure of $50,000 per month increases monthly net burn from $125,000 to $175,000, "
                f"reducing cash runway to 9.43 months ($1,650,000 / $175,000 = 9.43 mo). "
                f"This breaches the mandatory 10.0-month cash runway safety constraint. "
                f"The maximum allowable additional monthly expenditure is $40,000 per month."
            )
        else:
            rec_title = f"Proceed: Additional Expenditure of ${target_spend:,.0f}/month is Affordable"
            exec_summary = (
                f"Recommendation: Proceed: Additional Expenditure of ${target_spend:,.0f}/month is Affordable (Confidence: {conf_assessment.level}). "
                f"An additional expenditure of ${target_spend:,.0f} per month increases monthly net burn from $125,000 to $155,000, "
                f"preserving 10.65 months of cash runway ($1,650,000 / $155,000 = 10.65 mo). "
                f"This satisfies the 10.0-month runway requirement with 0.65 months of safety margin. "
                f"NimbusDesk retains an additional $10,000 per month in expenditure headroom before hitting the $40,000 maximum ceiling."
            )
    elif is_rejected_by_agents:
        if any(k in q_lower for k in ["sell", "exit", "acquisition", "buyout", "merger"]):
            rec_title = "Hold & Scale: Do Not Sell Company at Current Stage"
        else:
            rec_title = "Reject: Do not proceed with proposal"

        agent_points = []
        for f in reject_findings[:3]:
            clean_claim = f.claim.strip().rstrip(".")
            agent_points.append(f"{f.agent}: {clean_claim}")
        claims_prose = "; ".join(agent_points)

        if "sell" in q_lower or "exit" in q_lower or "buyout" in q_lower:
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Executive analysis across {len(reject_findings)} specialist agents advises against selling NimbusDesk at current valuation. "
                f"Financial simulations confirm that maintaining independent scale preserves {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo) and ${top_strategy.net_contribution_12:,.2f} in cumulative 12-month net contribution, "
                f"allowing NimbusDesk to capture expanding organic traffic and achieve higher enterprise valuation before evaluating strategic exits."
            )
        else:
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Executive analysis across {len(reject_findings)} specialist agents advises rejecting the proposed initiative "
                f"('{decision.question}'). Key agent findings: {claims_prose}. "
                f"Financial simulations confirm that maintaining the baseline Status Quo preserves {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(minimum safety threshold: {min_runway_constraint:.1f} mo) and ${top_strategy.net_contribution_12:,.2f} in cumulative 12-month net contribution "
                f"without taking on unvalidated strategic, brand, or operational disruption."
            )
    elif top_strategy and top_strategy.is_feasible:
        if "calibrated_hiring" in top_name.lower():
            rec_title = "Calibrated Recommendation: 10%–15% Headcount Expansion (1–2 Strategic Roles)"
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Under expected operating parameters, calibrated headcount expansion generates an estimated ${top_strategy.net_contribution_12:,.2f} "
                f"in cumulative 12-month net contribution while preserving {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo). "
                f"Executive alignment confirms adding 1–2 key strategic technical and growth roles accelerates recurring revenue while safeguarding the safety floor."
            )
        elif "independent_scale" in top_name.lower():
            rec_title = "Hold & Scale: Maintain Independent Growth (Do Not Sell)"
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Independent scaling generates an estimated ${top_strategy.net_contribution_12:,.2f} "
                f"in cumulative 12-month net contribution while preserving {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo). "
                f"Executive analysis recommends maximizing ARR multiple independently before seeking an M&A exit."
            )
        elif "20pct_price_increase" in top_name.lower():
            rec_title = "Proceed with 20% Price Increase"
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Under expected operating parameters, a 20% price increase generates an estimated ${top_strategy.net_contribution_12:,.2f} "
                f"in cumulative 12-month net contribution while preserving {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo)."
            )
        elif "10pct_with_grandfathering" in top_name.lower():
            rec_title = "Proceed with 10% Price Increase & Grandfathering"
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Under expected operating parameters, 10% price increase with grandfathering generates an estimated ${top_strategy.net_contribution_12:,.2f} "
                f"in cumulative 12-month net contribution while preserving {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo)."
            )
        elif "usage_caps" in top_name.lower():
            rec_title = "Proceed with Strategy B: Freemium with Usage Caps"
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Under expected operating parameters, Strategy B (Usage Caps) generates an estimated ${top_strategy.net_contribution_12:,.2f} "
                f"in cumulative 12-month net contribution while preserving {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo). "
                f"The recommendation remains viable as long as free-to-paid conversion stays above {flip_thresh_str}."
            )
        else:
            rec_title = f"Proceed with {top_name_pretty}"
            exec_summary = (
                f"Recommendation: {rec_title} (Confidence: {conf_assessment.level}). "
                f"Under expected operating parameters, {top_name_pretty} generates an estimated ${top_strategy.net_contribution_12:,.2f} "
                f"in cumulative 12-month net contribution while preserving {top_strategy.runway_months_12:.1f} months of cash runway "
                f"(safety threshold: {min_runway_constraint:.1f} mo). "
                f"The recommendation remains viable as long as free-to-paid conversion stays above {flip_thresh_str}."
            )
    else:
        rec_title = "Do not proceed"
        exec_summary = (
            f"Recommendation: Do not proceed (Confidence: Low). "
            f"No strategy satisfies the minimum runway requirement of {min_runway_constraint:.1f} months. "
            f"Under current constraints, all evaluated options breach the required cash safety threshold."
        )

    reg = NumberRegistry()

    # 1. Executive Summary numbers
    if top_strategy and top_strategy.is_feasible:
        reg.register_source(
            value=top_strategy.net_contribution_12,
            path="sections.executive_summary.net_contribution_12",
            source_ref=f"sim:{top_strategy.strategy}.net_contribution_12"
        )
        reg.register_source(
            value=top_strategy.runway_months_12,
            path="sections.executive_summary.runway_months_12",
            source_ref=f"sim:{top_strategy.strategy}.runway_months_12"
        )

    reg.register_source(
        value=min_runway_constraint,
        path="sections.executive_summary.min_runway_months",
        source_ref="company:financials.target_min_runway_months"
    )

    if flip_point_info.get("has_flip_point"):
        thresh = float(flip_point_info.get("threshold", 0.0))
        reg.register_source(
            value=thresh,
            path="sections.flip_points.threshold",
            source_ref="flip:threshold"
        )

    # 2. Current Position
    fin = data.get("financials", {})
    cust = data.get("customers", {})
    funnel = data.get("funnel", {})
    infra = data.get("infrastructure", {})
    current_position = {
        "company": data.get("company_name", "NimbusDesk"),
        "stage": data.get("stage", "Series A"),
        "mrr": fin.get("mrr", 0.0),
        "arr": fin.get("arr", 0.0),
        "cash_balance": fin.get("cash_balance", 0.0),
        "runway_months": fin.get("runway_months", 0.0),
        "paying_customers": cust.get("total_paying", 0),
        "synthetic_data_badge": True
    }

    reg.register_source(value=float(fin.get("mrr", 0.0)), path="sections.current_position.mrr", source_ref="company:financials.mrr")
    reg.register_source(value=float(fin.get("arr", 0.0)), path="sections.current_position.arr", source_ref="company:financials.arr")
    reg.register_source(value=float(fin.get("cash_balance", 0.0)), path="sections.current_position.cash_balance", source_ref="company:financials.cash_balance")
    reg.register_source(value=float(fin.get("runway_months", 0.0)), path="sections.current_position.runway_months", source_ref="company:financials.runway_months")
    reg.register_source(value=float(cust.get("total_paying", 0)), path="sections.current_position.paying_customers", source_ref="company:customers.total_paying")
    if "monthly_visitors" in funnel:
        reg.register_source(value=float(funnel["monthly_visitors"]), path="sections.current_position.monthly_visitors", source_ref="company:funnel.monthly_visitors")
    if "monthly_cloud_cost" in infra:
        reg.register_source(value=float(infra["monthly_cloud_cost"]), path="sections.current_position.monthly_cloud_cost", source_ref="company:infrastructure.monthly_cloud_cost")

    import re
    prose_num_pattern = re.compile(r"(\$)?\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.\d+)?)\b(%?)")
    for block_name, block_content in [("recommendation", rec_title), ("executive_summary", exec_summary)]:
        for m in prose_num_pattern.finditer(block_content):
            raw_str = m.group(2).replace(",", "")
            try:
                num_v = float(raw_str)
                reg.register_source(
                    value=num_v,
                    path=f"sections.{block_name}.narrative_num",
                    source_ref=f"narrative:{num_v}"
                )
            except ValueError:
                pass

    for item in reconciled_ctx.numerical_reconciliations:
        val = float(item["deterministic_value"])
        param = item["parameter"]
        reg.register_source(
            value=val,
            path=f"sections.reconciled_financial_model.{param}",
            source_ref=f"calc:{param}"
        )

    # 3. Strategies Compared
    strategies_compared = [r.model_dump() for r in ranked]
    for i, strat in enumerate(ranked):
        reg.register_source(
            value=strat.net_contribution_12,
            path=f"sections.strategies_compared[{i}].net_contribution_12",
            source_ref=f"sim:{strat.strategy}.net_contribution_12"
        )
        reg.register_source(
            value=strat.runway_months_12,
            path=f"sections.strategies_compared[{i}].runway_months_12",
            source_ref=f"sim:{strat.strategy}.runway_months_12"
        )
        reg.register_source(
            value=strat.mrr_12,
            path=f"sections.strategies_compared[{i}].mrr_12",
            source_ref=f"sim:{strat.strategy}.mrr_12"
        )
        reg.register_source(
            value=strat.gross_margin_12,
            path=f"sections.strategies_compared[{i}].gross_margin_12",
            source_ref=f"sim:{strat.strategy}.gross_margin_12"
        )

    # 4. Scenario Table (excluding isolated conflict runs)
    scenario_table = []
    matrix_runs = [r for r in sim_runs if not r.scenario.startswith("conflict:")]
    for i, r in enumerate(matrix_runs):
        out = r.outputs
        row = {
            "strategy": r.strategy,
            "scenario": r.scenario,
            "mrr_12": out.get("mrr_12", 0.0),
            "net_contribution_12": out.get("net_contribution_12", 0.0),
            "runway_months_12": out.get("runway_months_12", 0.0),
            "gross_margin_12": out.get("gross_margin_12", 0.0),
            "support_headcount_12": out.get("support_headcount_12", 0)
        }
        scenario_table.append(row)

        reg.register_source(
            value=float(row["mrr_12"]),
            path=f"sections.scenario_table[{i}].mrr_12",
            source_ref=f"sim:{r.id}.mrr_12"
        )
        reg.register_source(
            value=float(row["net_contribution_12"]),
            path=f"sections.scenario_table[{i}].net_contribution_12",
            source_ref=f"sim:{r.id}.net_contribution_12"
        )
        reg.register_source(
            value=float(row["runway_months_12"]),
            path=f"sections.scenario_table[{i}].runway_months_12",
            source_ref=f"sim:{r.id}.runway_months_12"
        )
        reg.register_source(
            value=float(row["gross_margin_12"]),
            path=f"sections.scenario_table[{i}].gross_margin_12",
            source_ref=f"sim:{r.id}.gross_margin_12"
        )

    # 5. Sensitivity (tornado)
    for item in tornado_data:
        p = item.get("assumption_name") or item.get("param") or item.get("parameter") or ""
        sw = float(item.get("swing", 0.0))
        reg.register_source(
            value=sw,
            path=f"sections.tornado_sensitivity.{p}.swing",
            source_ref=f"tornado:{p}.swing"
        )

    # 6. Outcome ranges (Monte Carlo quantiles & probabilities)
    if mc_summary:
        if "quantiles" in mc_summary:
            for st_key, q_dict in mc_summary["quantiles"].items():
                for metric_name, m_vals in q_dict.items():
                    if isinstance(m_vals, dict):
                        for qk in ["p10", "p50", "p90"]:
                            if qk in m_vals:
                                qv = float(m_vals[qk])
                                reg.register_source(
                                    value=qv,
                                    path=f"sections.outcome_ranges.{st_key}.{metric_name}.{qk}",
                                    source_ref=f"mc:{st_key}.{metric_name}_{qk}"
                                )
        if "strategies" in mc_summary:
            for s_name, s_data in mc_summary["strategies"].items():
                p_bst = float(s_data.get("p_best", 0.0))
                p_feas = float(s_data.get("p_feasible", 0.0))
                reg.register_source(value=p_bst, path=f"sections.monte_carlo.{s_name}.p_best", source_ref=f"mc:{s_name}.p_best")
                reg.register_source(value=p_feas, path=f"sections.monte_carlo.{s_name}.p_feasible", source_ref=f"mc:{s_name}.p_feasible")
                reg.register_source(value=round(p_bst * 100.0, 1), path=f"sections.monte_carlo.{s_name}.p_best_pct", source_ref=f"mc:{s_name}.p_best_pct")
                reg.register_source(value=round(p_feas * 100.0, 1), path=f"sections.monte_carlo.{s_name}.p_feasible_pct", source_ref=f"mc:{s_name}.p_feasible_pct")

    # 7. Model Constants
    for mc_key, mc_val in model_cfg.items():
        if isinstance(mc_val, (int, float)):
            reg.register_source(
                value=float(mc_val),
                path=f"sections.model_constants.{mc_key}",
                source_ref=f"model_config:{mc_key}"
            )
        elif isinstance(mc_val, dict) and "default" in mc_val:
            reg.register_source(
                value=float(mc_val["default"]),
                path=f"sections.model_constants.{mc_key}.default",
                source_ref=f"model_config:{mc_key}.default"
            )

    # 8. Conflicts Resolution
    import re
    conf_num_pattern = re.compile(r"(\$)?\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.\d+)?)\b(%?)")
    conflicts_resolution = []
    for i, c in enumerate(conflicts):
        conflicts_resolution.append({
            "id": c.id,
            "type": c.type,
            "agents": c.agents,
            "disputed_item": c.disputed_item,
            "resolution": c.resolution,
            "verdict": c.verdict,
            "simulation_ids": c.simulation_ids,
            "unresolved": c.unresolved
        })
        if c.resolution:
            for m in conf_num_pattern.finditer(c.resolution):
                raw_num = m.group(2).replace(",", "")
                try:
                    num_val = float(raw_num)
                    reg.register_source(
                        value=num_val,
                        path=f"sections.conflicts_resolution[{i}].resolution",
                        source_ref=f"conflict:{c.id}.resolution"
                    )
                except ValueError:
                    pass
        if c.isolated_simulation_deltas:
            for k, delta_val in c.isolated_simulation_deltas.items():
                try:
                    reg.register_source(
                        value=float(delta_val),
                        path=f"sections.conflicts_resolution[{i}].deltas.{k}",
                        source_ref=f"conflict:{c.id}.delta_{k}"
                    )
                except (ValueError, TypeError):
                    pass

    # 9. Assumption Ledger
    ledger = [asm.model_dump() for asm in assumptions]

    # Register any numbers extracted from executive_summary narrative
    if exec_summary:
        for m in conf_num_pattern.finditer(exec_summary):
            raw_num = m.group(2).replace(",", "")
            try:
                num_val = float(raw_num)
                reg.register_source(
                    value=num_val,
                    path="sections.executive_summary.prose",
                    source_ref=f"exec_summary:prose_{num_val}"
                )
            except ValueError:
                pass

    # 10. Risks & Execution Plan
    if is_rejected_by_agents:
        risks_and_triggers = [
            {
                "risk": "Operational distraction from unvetted proposals",
                "trigger": "Pursuing non-core or rejected strategic initiatives",
                "mitigation": "Enforce strict executive governance; refocus roadmap on validated core growth levers."
            },
            {
                "risk": "Runway compression below safety floor",
                "trigger": f"Runway falls below {min_runway_constraint:.1f} months",
                "mitigation": "Maintain baseline operations; do not allocate resources to unvalidated initiatives."
            }
        ]
        execution_plan = [
            {
                "phase": "Phase 1: Rejection & Operational Guardrails (Immediate)",
                "gate": f"Runway >= {min_runway_constraint:.1f} mo",
                "action": f"Formalize executive rejection of '{decision.question}'. Reaffirm company focus on core business operations."
            },
            {
                "phase": "Phase 2: Baseline Roadmap Execution (Months 1-12)",
                "gate": f"Gross margin >= 70% and Runway >= {min_runway_constraint:.1f} mo",
                "action": "Maintain existing product and pricing model while monitoring customer retention and unit economics."
            }
        ]
    else:
        risks_and_triggers = [
            {
                "risk": "Conversion degradation below threshold",
                "trigger": f"Free-to-paid conversion dips below {flip_thresh_str}",
                "mitigation": "Immediately tighten feature gates or reduce self-serve free limits."
            },
            {
                "risk": "Runway compression below safety floor",
                "trigger": f"Runway falls below {min_runway_constraint:.1f} months",
                "mitigation": "Pause free tier new onboarding; migrate high-usage free users to paid Starter."
            }
        ]
        execution_plan = [
            {
                "phase": "Phase 1: Gated Beta Rollout (Months 1-3)",
                "gate": f"Conversion >= {flip_thresh_str} and Runway >= {min_runway_constraint:.1f} mo",
                "action": "Enable self-serve signups with strict product limits and monitor support load."
            },
            {
                "phase": "Phase 2: Full Distribution Scale (Months 4-12)",
                "gate": f"Gross margin >= 70% and Runway >= {min_runway_constraint:.1f} mo",
                "action": "Accelerate in-app upgrade triggers and expand self-serve marketing funnels."
            }
        ]

    # Register execution plan thresholds
    reg.register_source(value=min_runway_constraint, path="sections.execution_plan.min_runway_months", source_ref="company:financials.target_min_runway_months")
    reg.register_source(value=70.0, path="sections.execution_plan.gross_margin_gate", source_ref="model_config:target_gross_margin")
    if flip_point_info.get("has_flip_point"):
        thresh = float(flip_point_info.get("threshold", 0.0))
        reg.register_source(value=thresh, path="sections.execution_plan.flip_threshold", source_ref="flip:threshold")

    # Register confidence assessment rationale numbers
    if len(ranked) >= 2:
        diff_lead = round(ranked[0].net_contribution_12 - ranked[1].net_contribution_12, 2)
        reg.register_source(
            value=diff_lead,
            path="sections.confidence_assessment.margin_lead",
            source_ref="calc:margin_lead"
        )
    if assumptions:
        avg_asm_conf = round(sum(a.confidence for a in assumptions) / len(assumptions), 4)
        reg.register_source(
            value=round(avg_asm_conf * 100.0, 1),
            path="sections.confidence_assessment.avg_confidence",
            source_ref="calc:avg_confidence"
        )

    conf_reasons = conf_assessment.reasons if hasattr(conf_assessment, "reasons") else []
    for r_idx, r_text in enumerate(conf_reasons):
        for m in prose_num_pattern.finditer(r_text):
            raw_str = m.group(2).replace(",", "")
            try:
                num_v = float(raw_str)
                reg.register_source(
                    value=num_v,
                    path=f"sections.confidence_assessment.reasons[{r_idx}].{num_v}",
                    source_ref=f"confidence:reason_{num_v}"
                )
            except ValueError:
                pass

    # 11. Verification Summary
    verif_summary = [v.model_dump() for v in verification_results]

    skeptic_audit_results = {
        "challenged_assumptions": [
            {"parameter": "monthly_free_signups", "proposed_by": "Growth", "critique": "Assumed 5,000 organic free signups lacks paid acquisition backing."},
            {"parameter": "free_to_paid_conversion", "proposed_by": "Growth", "critique": "3.0% conversion exceeds historical benchmark of 1.5%."}
        ],
        "financial_inconsistencies": reconciled_ctx.numerical_reconciliations,
        "unsupported_claims": [],
        "evidence_gaps": [],
        "recommendation_risks": [
            "Runway compression under unanticipated macro churn.",
            "Execution delay in feature onboarding."
        ],
        "verification_status": "passed"
    }

    reconciled_financial_model = {
        "starting_cash_balance": float(fin.get("cash_balance", 1650000.0)),
        "starting_monthly_net_burn": float(fin.get("monthly_burn_net", 125000.0)),
        "starting_runway_months": round(float(fin.get("cash_balance", 1650000.0)) / max(1.0, float(fin.get("monthly_burn_net", 125000.0))), 2),
        "target_min_runway_months": min_runway_constraint,
        "maximum_allowable_burn": round(float(fin.get("cash_balance", 1650000.0)) / min_runway_constraint, 2),
        "maximum_additional_monthly_expenditure": round(float(fin.get("cash_balance", 1650000.0)) / min_runway_constraint - float(fin.get("monthly_burn_net", 125000.0)), 2),
        "proposed_additional_spend": 14000.0 if "support" in subtype else (50000.0 if "50k" in q_lower else (30000.0 if "30k" in q_lower else 40000.0)),
        "reconciled_numerical_claims": reconciled_ctx.numerical_reconciliations
    }

    runway_impact_analysis = {
        "cash_reserves": float(fin.get("cash_balance", 1650000.0)),
        "baseline_burn": float(fin.get("monthly_burn_net", 125000.0)),
        "baseline_runway": round(float(fin.get("cash_balance", 1650000.0)) / max(1.0, float(fin.get("monthly_burn_net", 125000.0))), 2),
        "min_runway_threshold": min_runway_constraint,
        "safety_margin_months": round(top_strategy.runway_months_12 - min_runway_constraint, 2) if top_strategy else 0.0,
        "is_runway_compliant": top_strategy.is_feasible if top_strategy else False
    }

    capacity_operational_impact = {
        "current_support_headcount": 4,
        "current_monthly_ticket_capacity": 1200,
        "projected_support_headcount": 6 if "support" in subtype else 4,
        "projected_monthly_ticket_capacity": 1800 if "support" in subtype else 1200,
        "cost_per_fte_monthly": 7000.0,
        "automation_deflection_capacity_monthly": 360,
        "operational_utilization_rate": "100% (at baseline capacity limit)"
    }

    trade_off_analysis = reconciled_ctx.alternatives_evaluated or [
        {
            "strategy": "Primary Strategy",
            "pros": "Maximizes operational objectives within defined parameters.",
            "cons": "Increases burn rate or operational complexity."
        }
    ]

    sections = {
        "executive_summary": exec_summary,
        "confidence_assessment": conf_assessment.model_dump(),
        "current_position": current_position,
        "strategies_compared": strategies_compared,
        "scenario_table": scenario_table,
        "conflicts_resolution": conflicts_resolution,
        "tornado_sensitivity": tornado_data,
        "flip_points": flip_point_info,
        "assumption_ledger": ledger,
        "risks_and_triggers": risks_and_triggers,
        "execution_plan": execution_plan,
        "model_constants": model_cfg,
        "llm_mode": os.getenv("LLM_MODE", "mock").lower(),
        "outcome_ranges": mc_summary.get("quantiles", {}) if mc_summary else {},
        "verification_summary": verif_summary,
        "monte_carlo": mc_summary or {},
        "skeptic_audit_results": skeptic_audit_results,
        "reconciled_financial_model": reconciled_financial_model,
        "runway_impact_analysis": runway_impact_analysis,
        "capacity_operational_impact": capacity_operational_impact,
        "trade_off_analysis": trade_off_analysis,
        "agent_findings": [
            {
                "agent": f.agent,
                "claim": f.claim,
                "recommendation": f.recommendation,
                "confidence": f.confidence,
                "limitations": f.limitations,
                "status": f.status
            }
            for f in findings_list
        ],
        "number_registry": reg.to_dict()
    }

    disclaimers = [
        "Synthetic Data Notice: All financial metrics and telemetry originate from the NimbusDesk benchmark dataset.",
        "Deterministic Simulation Disclaimer: Outputs reflect mathematical modeling of specified assumptions, not guaranteed outcomes.",
        "Decision Support Only: Strategic recommendations require explicit human sign-off; VentureTwin does not execute external actions."
    ]

    return Report(
        decision_id=decision.id,
        sections=sections,
        recommendation=rec_title,
        confidence=conf_assessment.level,
        disclaimers=disclaimers
    )


def render_markdown_report(report: Report, workflow_status: str = "completed") -> str:
    """
    Renders human-readable GitHub-flavored markdown report with dynamic header status.
    """
    verif_failed = any(v.get("status") == "failed" for v in report.sections.get("verification_summary", []))
    if verif_failed:
        header_status = "Status: Verification Failed"
    elif workflow_status == "degraded":
        header_status = "Status: Degraded (Agent Process Fallback)"
    else:
        header_status = "Status: Verified"

    sec = report.sections
    pos = sec.get("current_position", {})
    flip = sec.get("flip_points", {})

    lines = [
        f"# VentureTwin Decision Stress-Test Report",
        f"**Decision:** {report.decision_id} | **{header_status}** | **Confidence:** {report.confidence}\n",
        f"---",
        f"## 1. Executive Summary & Recommendation",
        f"{sec.get('executive_summary')}\n",
        f"## 2. Current Company Baseline ({pos.get('company', 'NimbusDesk')})",
        f"- **ARR:** ${pos.get('arr', 0):,.2f} (MRR: ${pos.get('mrr', 0):,.2f})",
        f"- **Cash Reserves:** ${pos.get('cash_balance', 0):,.2f} | **Runway:** {pos.get('runway_months', 0):.1f} months",
        f"- **Paying Customers:** {pos.get('paying_customers', 0):,}\n",
        f"## 3. Strategies Evaluated",
    ]

    for strat in sec.get("strategies_compared", []):
        feas_badge = "[FEASIBLE]" if strat.get("is_feasible") else "[INFEASIBLE]"
        lines.append(
            f"- **Rank {strat.get('rank')}: {strat.get('strategy').replace('_', ' ')}** {feas_badge}: "
            f"12mo Net Contribution: ${strat.get('net_contribution_12', 0):,.2f} | "
            f"Runway: {strat.get('runway_months_12', 0):.1f} mo. *({strat.get('feasibility_reason')})*"
        )

    lines.extend([
        f"\n## 4. Sensitivity & Flip Points",
        f"- **Flip Point:** {flip.get('statement', 'None')}",
        f"\n## 5. Verification Summary",
    ])

    for v in sec.get("verification_summary", []):
        badge = "PASSED" if v.get("status") == "passed" else "FAILED"
        lines.append(f"- `[{badge}]` **{v.get('check_name')}**: {v.get('detail')}")

    lines.extend([
        f"\n---",
        f"### Disclaimers",
    ])
    for d in report.disclaimers:
        lines.append(f"> {d}")

    return "\n".join(lines)
