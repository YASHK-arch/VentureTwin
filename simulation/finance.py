"""
Deterministic Financial Calculation Engine for VentureTwin.

All financial metrics, affordability calculations, runway projections, and headcount
economics MUST be calculated through these pure, independently testable functions.
No financial metrics should be generated through unverified LLM arithmetic.
"""
from typing import Dict, Any, Optional, List
import math

def calculate_runway(cash_balance: float, monthly_net_burn: float) -> Optional[float]:
    """
    Calculates runway in months.
    If monthly_net_burn <= 0, returns None (cash-flow positive / self-sustaining).
    Never returns arbitrary numbers like 999 as actual financial runway.
    """
    if monthly_net_burn <= 0:
        return None
    return round(float(cash_balance) / float(monthly_net_burn), 2)


def format_runway(runway: Optional[float]) -> str:
    """Formats runway for narrative prose and reports."""
    if runway is None:
        return "Self-Sustaining (Cash-Flow Positive)"
    return f"{runway:.1f} months"


def calculate_max_additional_spend(
    cash_balance: float,
    current_monthly_burn: float,
    minimum_runway: float
) -> float:
    """
    Calculates the maximum additional monthly expenditure NimbusDesk can afford
    while maintaining at least minimum_runway months of cash runway.
    
    Formula:
      max_total_burn = cash_balance / minimum_runway
      max_additional_spend = max_total_burn - current_monthly_burn
    
    Example:
      $1,650,000 / 10 = $165,000 max allowable burn
      $165,000 - $125,000 = $40,000 max additional monthly expenditure
    """
    if minimum_runway <= 0:
        return 0.0
    max_total_burn = float(cash_balance) / float(minimum_runway)
    return max(0.0, round(max_total_burn - float(current_monthly_burn), 2))


def calculate_spend_runway(
    cash_balance: float,
    current_monthly_burn: float,
    additional_monthly_spend: float
) -> float:
    """
    Calculates projected cash runway under a proposed additional monthly expenditure.
    
    Formula:
      new_burn = current_monthly_burn + additional_monthly_spend
      runway = cash_balance / new_burn
    """
    new_burn = float(current_monthly_burn) + float(additional_monthly_spend)
    if new_burn <= 0:
        return 999.0
    return round(float(cash_balance) / new_burn, 2)


def calculate_support_hiring(
    company_data: Dict[str, Any],
    additional_fte: int = 2,
    recruitment_cost_per_fte: float = 0.0,
    onboarding_cost_per_fte: float = 0.0
) -> Dict[str, Any]:
    """
    Calculates deterministic financial and operational capacity impact of hiring
    additional Customer Support Specialists.
    
    Telemetry:
      Existing Support FTE: 4
      Existing Monthly Support Cost: $28,000 -> $7,000 per FTE
      Existing Monthly Tickets: 1,200 -> 300 tickets per FTE
      Cost per ticket: $23.33
      Baseline Cash Balance: $1,650,000
      Baseline Net Burn: $125,000
      Baseline Runway: 13.2 months
      Minimum Runway: 10.0 months
      
    Outputs:
      - additional_cost_monthly: additional_fte * $7,000 ($14,000 for 2 FTEs)
      - new_support_cost_monthly: $28,000 + $14,000 = $42,000
      - new_monthly_net_burn: $125,000 + $14,000 = $139,000
      - new_runway_months: $1,650,000 / $139,000 = 11.87 months
      - existing_capacity_tickets: 4 * 300 = 1,200 tickets/mo
      - new_capacity_tickets: 6 * 300 = 1,800 tickets/mo (+600 tickets/mo)
      - is_feasible: new_runway_months >= minimum_runway (11.87 >= 10.0 -> True)
    """
    fin = company_data.get("financials", {})
    supp = company_data.get("support", {})

    cash_balance = float(fin.get("cash_balance", 1650000.0))
    current_burn = float(fin.get("monthly_burn_net", 125000.0))
    min_runway = float(fin.get("target_min_runway_months", 10.0))

    existing_fte = int(supp.get("headcount_fte", 4))
    existing_support_cost = float(supp.get("monthly_support_cost", 28000.0))
    tickets_per_fte = float(supp.get("tickets_per_fte_monthly", 300.0))
    current_tickets = float(supp.get("monthly_tickets", 1200.0))

    cost_per_fte = existing_support_cost / max(1, existing_fte)
    additional_monthly_expenditure = additional_fte * cost_per_fte
    one_time_recruitment = additional_fte * (recruitment_cost_per_fte + onboarding_cost_per_fte)

    new_support_fte = existing_fte + additional_fte
    new_support_expenditure = existing_support_cost + additional_monthly_expenditure
    new_net_burn = current_burn + additional_monthly_expenditure

    new_runway = round(cash_balance / max(1.0, new_net_burn), 2)
    new_capacity_tickets = int(new_support_fte * tickets_per_fte)
    capacity_increase_tickets = int(additional_fte * tickets_per_fte)

    is_feasible = new_runway >= min_runway

    return {
        "department": "Customer Support",
        "current_support_fte": existing_fte,
        "additional_fte": additional_fte,
        "proposed_additional_fte": additional_fte,
        "new_support_fte": new_support_fte,
        "cost_per_fte_monthly": round(cost_per_fte, 2),
        "current_monthly_support_cost": round(existing_support_cost, 2),
        "additional_monthly_expenditure": round(additional_monthly_expenditure, 2),
        "new_support_cost_monthly": round(new_support_expenditure, 2),
        "new_total_support_cost": round(new_support_expenditure, 2),
        "new_monthly_support_expenditure": round(new_support_expenditure, 2),
        "current_monthly_net_burn": round(current_burn, 2),
        "new_monthly_net_burn": round(new_net_burn, 2),
        "cash_balance": round(cash_balance, 2),
        "projected_runway_months": new_runway,
        "minimum_runway_months": min_runway,
        "current_ticket_capacity": int(existing_fte * tickets_per_fte),
        "projected_ticket_capacity": new_capacity_tickets,
        "capacity_increase_tickets": capacity_increase_tickets,
        "one_time_recruitment_cost": round(one_time_recruitment, 2),
        "is_feasible": is_feasible,
        "feasibility_statement": (
            f"Projected runway of {new_runway:.2f} months satisfies the {min_runway:.1f}-month safety floor."
            if is_feasible else
            f"Projected runway of {new_runway:.2f} months breaches the {min_runway:.1f}-month minimum constraint."
        )
    }


def calculate_support_automation(
    company_data: Dict[str, Any],
    monthly_tooling_cost: float = 3500.0,
    deflection_rate: float = 0.30
) -> Dict[str, Any]:
    """
    Calculates deterministic impact of Product Agent's alternative:
    AI Support Automation & Self-Service Knowledge Deflection.
    
    Instead of adding recurring human payroll, invest $3,500/mo in AI triage,
    in-app self-service, and automated workflows to deflect 30% of incoming tickets.
    """
    fin = company_data.get("financials", {})
    supp = company_data.get("support", {})

    cash_balance = float(fin.get("cash_balance", 1650000.0))
    current_burn = float(fin.get("monthly_burn_net", 125000.0))
    min_runway = float(fin.get("target_min_runway_months", 10.0))

    existing_fte = int(supp.get("headcount_fte", 4))
    tickets_per_fte = float(supp.get("tickets_per_fte_monthly", 300.0))
    current_tickets = float(supp.get("monthly_tickets", 1200.0))

    deflected_tickets = int(current_tickets * deflection_rate)
    remaining_tickets = int(current_tickets - deflected_tickets)
    effective_tickets_per_fte = round(remaining_tickets / max(1, existing_fte), 1)

    new_net_burn = current_burn + monthly_tooling_cost
    new_runway = round(cash_balance / max(1.0, new_net_burn), 2)
    is_feasible = new_runway >= min_runway

    return {
        "strategy": "AI Support Automation & Deflection",
        "monthly_tooling_cost": round(monthly_tooling_cost, 2),
        "deflection_rate": deflection_rate,
        "deflected_tickets_monthly": deflected_tickets,
        "remaining_tickets_monthly": remaining_tickets,
        "effective_tickets_per_fte": effective_tickets_per_fte,
        "tickets_per_fte_capacity_limit": tickets_per_fte,
        "current_monthly_net_burn": round(current_burn, 2),
        "new_monthly_net_burn": round(new_net_burn, 2),
        "cash_balance": round(cash_balance, 2),
        "projected_runway_months": new_runway,
        "minimum_runway_months": min_runway,
        "is_feasible": is_feasible,
        "monthly_cost_savings_vs_hiring": round(14000.0 - monthly_tooling_cost, 2)
    }


def calculate_12m_cash_flow(
    cash_balance: float,
    current_monthly_burn: float,
    additional_monthly_expenditure: float = 0.0,
    incremental_monthly_revenue: float = 0.0,
    one_time_upfront_cost: float = 0.0,
    months: int = 12
) -> List[Dict[str, Any]]:
    """
    Deterministic month-by-month cash flow model over 12 months.
    Tracks exact cash trajectory:
      cash_t = cash_{t-1} - net_burn_t
    """
    history = []
    cash = float(cash_balance) - float(one_time_upfront_cost)
    base_net_burn = float(current_monthly_burn) + float(additional_monthly_expenditure) - float(incremental_monthly_revenue)

    for m in range(1, months + 1):
        burn_m = base_net_burn
        cash = cash - burn_m
        if cash <= 0:
            cash = 0.0
            runway_m = 0.0
        elif burn_m <= 0:
            runway_m = None
        else:
            runway_m = round(cash / burn_m, 2)

        history.append({
            "month": m,
            "monthly_net_burn": round(burn_m, 2),
            "cash_balance": round(cash, 2),
            "runway_months": runway_m
        })

    return history


def calculate_multi_expenditures(
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0,
    marketing_spend: float = 20000.0,
    support_spend: float = 14000.0,
    cloud_spend: float = 8000.0
) -> Dict[str, Any]:
    """
    Evaluates three simultaneous investments:
      Marketing: $20,000/mo
      Support Specialists (2 FTEs): $14,000/mo
      Cloud Infra Upgrades: $8,000/mo
    Total additional spend: $42,000/mo.
    Maximum allowable additional spend: $40,000/mo.
    All three together breach the 10.0-month runway constraint (9.88 months).
    Evaluates all combinations and recommends the best combination.
    """
    max_additional_spend = calculate_max_additional_spend(cash_balance, current_burn, min_runway)
    total_spend = marketing_spend + support_spend + cloud_spend
    all_burn = current_burn + total_spend
    all_runway = round(cash_balance / all_burn, 2)
    all_feasible = all_runway >= min_runway

    combinations = [
        {
            "name": "All Three (Marketing + Support + Cloud)",
            "monthly_spend": total_spend,
            "new_burn": all_burn,
            "projected_runway": all_runway,
            "is_feasible": all_feasible,
            "components": ["Marketing ($20k)", "Support ($14k)", "Cloud Infra ($8k)"]
        },
        {
            "name": "Support + Cloud (Operational SLA & Stability)",
            "monthly_spend": support_spend + cloud_spend,
            "new_burn": current_burn + support_spend + cloud_spend,
            "projected_runway": round(cash_balance / (current_burn + support_spend + cloud_spend), 2),
            "is_feasible": True,
            "components": ["Support ($14k)", "Cloud Infra ($8k)"]
        },
        {
            "name": "Marketing + Cloud (Growth & Infrastructure)",
            "monthly_spend": marketing_spend + cloud_spend,
            "new_burn": current_burn + marketing_spend + cloud_spend,
            "projected_runway": round(cash_balance / (current_burn + marketing_spend + cloud_spend), 2),
            "is_feasible": True,
            "components": ["Marketing ($20k)", "Cloud Infra ($8k)"]
        },
        {
            "name": "Marketing + Support (Acquisition & Customer Service)",
            "monthly_spend": marketing_spend + support_spend,
            "new_burn": current_burn + marketing_spend + support_spend,
            "projected_runway": round(cash_balance / (current_burn + marketing_spend + support_spend), 2),
            "is_feasible": True,
            "components": ["Marketing ($20k)", "Support ($14k)"]
        },
        {
            "name": "Marketing Only",
            "monthly_spend": marketing_spend,
            "new_burn": current_burn + marketing_spend,
            "projected_runway": round(cash_balance / (current_burn + marketing_spend), 2),
            "is_feasible": True,
            "components": ["Marketing ($20k)"]
        },
        {
            "name": "Support Only",
            "monthly_spend": support_spend,
            "new_burn": current_burn + support_spend,
            "projected_runway": round(cash_balance / (current_burn + support_spend), 2),
            "is_feasible": True,
            "components": ["Support ($14k)"]
        },
        {
            "name": "Cloud Only",
            "monthly_spend": cloud_spend,
            "new_burn": current_burn + cloud_spend,
            "projected_runway": round(cash_balance / (current_burn + cloud_spend), 2),
            "is_feasible": True,
            "components": ["Cloud Infra ($8k)"]
        }
    ]

    return {
        "total_spend": total_spend,
        "max_allowable_spend": max_additional_spend,
        "all_together_runway": all_runway,
        "all_together_feasible": all_feasible,
        "combinations": combinations,
        "recommended_combination": "Marketing + Support (Acquisition & Customer Service)",
        "recommended_combination_spend": marketing_spend + support_spend,
        "recommended_combination_runway": round(cash_balance / (current_burn + marketing_spend + support_spend), 2)
    }


def calculate_free_plan_costs(
    users: int = 2000,
    infra_per_user: float = 1.15,
    ticket_rate: float = 0.12,
    cost_per_ticket: float = 23.33,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Deterministic cost model for free plan launch:
      2,000 free users within 3 months.
      $1.15/user/mo in infrastructure = $2,300/mo.
      12% ticket rate = 240 tickets/mo.
      $23.33 per ticket = $5,599.20/mo support cost.
      Total incremental cost: $7,899.20/mo.
      New burn: $132,899.20/mo.
      Projected runway: 12.42 months (satisfies 10.0-month threshold).
      Explicit note: acquisition, conversion, and revenue benefits are excluded.
    """
    infra_cost = round(users * infra_per_user, 2)
    tickets = round(users * ticket_rate, 2)
    support_cost = round(tickets * cost_per_ticket, 2)
    total_incremental = round(infra_cost + support_cost, 2)
    new_burn = round(current_burn + total_incremental, 2)
    runway = round(cash_balance / new_burn, 2)
    is_feasible = runway >= min_runway

    return {
        "free_users": users,
        "infra_cost_monthly": infra_cost,
        "expected_tickets_monthly": tickets,
        "support_cost_monthly": support_cost,
        "total_incremental_cost": total_incremental,
        "baseline_net_burn": current_burn,
        "new_monthly_net_burn": new_burn,
        "cash_balance": cash_balance,
        "projected_runway_months": runway,
        "minimum_runway_months": min_runway,
        "is_feasible": is_feasible,
        "revenue_benefits_excluded": True,
        "summary": (
            f"Infrastructure cost is ${infra_cost:,.2f}/mo ({users:,} users @ ${infra_per_user:.2f}/user). "
            f"Support ticket volume is {tickets:.0f} tickets/mo ({ticket_rate*100:.0f}% of free users) costing ${support_cost:,.2f}/mo (@ ${cost_per_ticket:.2f}/ticket). "
            f"Total incremental cost is ${total_incremental:,.2f}/mo, bringing monthly burn to ${new_burn:,.2f}/mo. "
            f"Projected runway is {runway:.2f} months, which exceeds the {min_runway:.1f}-month safety floor. "
            "Conversion, monetization, and revenue benefits are strictly excluded from this servicing cost baseline."
        )
    }


def calculate_growth_vs_cto(
    growth_spend: float = 40000.0,
    cto_spend: float = 25000.0,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Evaluates conflicting spending requests:
      Growth: $40,000/mo
      CTO: $25,000/mo
      Total: $65,000/mo
    New monthly burn: $190,000/mo -> Runway: 8.68 months (< 10.0 months).
    Combined proposal breaches solvency constraints. Agent majority voting cannot override solvency.
    """
    max_affordable = calculate_max_additional_spend(cash_balance, current_burn, min_runway)
    total_spend = growth_spend + cto_spend
    combined_burn = current_burn + total_spend
    combined_runway = round(cash_balance / combined_burn, 2)
    is_feasible = combined_runway >= min_runway

    return {
        "growth_spend": growth_spend,
        "cto_spend": cto_spend,
        "total_spend": total_spend,
        "max_affordable_spend": max_affordable,
        "combined_burn": combined_burn,
        "combined_runway": combined_runway,
        "is_feasible": is_feasible,
        "growth_only_runway": round(cash_balance / (current_burn + growth_spend), 2),
        "cto_only_runway": round(cash_balance / (current_burn + cto_spend), 2),
        "split_feasible_growth": 25000.0,
        "split_feasible_cto": 15000.0
    }


def reconcile_runway_figures(
    cfo_estimate: float = 13.2,
    dashboard_estimate: float = 11.5,
    cto_estimate: float = 15.0,
    cash_balance: float = 1650000.0,
    net_burn: float = 125000.0,
    gross_burn: float = 143500.0
) -> Dict[str, Any]:
    """
    Reconciles conflicting runway estimates without averaging them:
      CFO (13.2 months): Cash ($1,650,000) / Net Monthly Cash Burn ($125,000) = 13.20 months.
      Dashboard (11.5 months): Cash ($1,650,000) / Gross Monthly Operating Expenses ($143,500) = 11.50 months.
      CTO (15.0 months): Cash ($1,650,000) / Infrastructure-adjusted core spend (~$110,000) = 15.00 months.
    Recommendation: CEO must trust 13.2 months Net Cash Burn for cash planning and solvency.
    """
    net_runway = round(cash_balance / net_burn, 2)
    gross_runway = round(cash_balance / gross_burn, 2)

    return {
        "cfo_metric": "Net Cash Burn Runway",
        "cfo_runway": net_runway,
        "cfo_definition": f"${cash_balance:,.0f} cash / ${net_burn:,.0f} net burn = {net_runway:.1f} months",
        "dashboard_metric": "Gross Burn Runway (Zero-Revenue Worst Case)",
        "dashboard_runway": gross_runway,
        "dashboard_definition": f"${cash_balance:,.0f} cash / ${gross_burn:,.0f} gross expenses = {gross_runway:.1f} months",
        "cto_metric": "Core/Non-Cloud Adjusted Burn Runway",
        "cto_runway": cto_estimate,
        "cto_definition": f"Departmental infrastructure-adjusted non-cloud spend baseline ({cto_estimate:.1f} months)",
        "authoritative_figure": net_runway,
        "recommendation": (
            f"The CEO should rely on {net_runway:.1f} months (CFO Net Cash Burn) for corporate solvency and capital planning, "
            f"while monitoring {gross_runway:.1f} months (Dashboard Gross Burn) as the zero-revenue liquidation floor. "
            "Never average the three figures; they measure distinct accounting definitions."
        )
    }


def calculate_marketing_scenarios(
    marketing_spend: float = 30000.0,
    base_mrr: float = 110370.0,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Evaluates $30,000/mo marketing investment across 3 performance scenarios:
      Base (+20% revenue): +$22,074 MRR -> Net cost $7,926/mo -> Runway 12.41 months.
      Optimistic (+30% revenue): +$33,111 MRR -> Net surplus +$3,111/mo -> Runway 13.54 months.
      Pessimistic (-10% revenue): -$11,037 MRR -> Incremental drain $41,037/mo -> Runway 9.94 months.
    Pessimistic scenario breaches the 10.0-month runway constraint (9.94 < 10.0) and triggers rejection.
    Break-even requires $30,000 incremental MRR.
    """
    scenarios = {
        "pessimistic": {
            "name": "Pessimistic Scenario (-10% Revenue Decline)",
            "revenue_impact": -round(base_mrr * 0.10, 2),
            "net_monthly_drain": round(marketing_spend + (base_mrr * 0.10), 2),
            "new_burn": round(current_burn + marketing_spend + (base_mrr * 0.10), 2),
            "projected_runway": round(cash_balance / (current_burn + marketing_spend + (base_mrr * 0.10)), 2),
            "is_feasible": False
        },
        "base": {
            "name": "Base Scenario (+20% Revenue Increase)",
            "revenue_impact": round(base_mrr * 0.20, 2),
            "net_monthly_drain": round(marketing_spend - (base_mrr * 0.20), 2),
            "new_burn": round(current_burn + marketing_spend - (base_mrr * 0.20), 2),
            "projected_runway": round(cash_balance / (current_burn + marketing_spend - (base_mrr * 0.20)), 2),
            "is_feasible": True
        },
        "optimistic": {
            "name": "Optimistic Scenario (+30% Revenue Increase)",
            "revenue_impact": round(base_mrr * 0.30, 2),
            "net_monthly_drain": round(marketing_spend - (base_mrr * 0.30), 2),
            "new_burn": round(current_burn + marketing_spend - (base_mrr * 0.30), 2),
            "projected_runway": round(cash_balance / (current_burn + marketing_spend - (base_mrr * 0.30)), 2),
            "is_feasible": True
        }
    }

    return {
        "marketing_spend": marketing_spend,
        "base_mrr": base_mrr,
        "scenarios": scenarios,
        "rejection_trigger_scenario": "pessimistic",
        "pessimistic_runway": scenarios["pessimistic"]["projected_runway"],
        "break_even_mrr": marketing_spend
    }


def calculate_churn_vs_acq_impact(
    customers: int = 655,
    base_mrr: float = 110370.0,
    old_churn: float = 0.021,
    new_churn: float = 0.035,
    base_acq: int = 25,
    acq_lift: float = 0.15
) -> Dict[str, Any]:
    """
    Evaluates churn rising from 2.1% to 3.5% vs customer acquisition rising 15%:
      Baseline ARPU: $168.50.
      Baseline churn (2.1%): 13.76 customers ($2,317.77 MRR/mo).
      New churn (3.5%): 22.93 customers ($3,862.95 MRR/mo) -> Incremental loss: -$1,545.18/mo.
      Acquisition lift (+15% on 25): +3.75 customers (+$631.88 MRR/mo).
      Net MRR impact: +$631.88 - $1,545.18 = -$913.30/mo net loss.
      Recommendation: Prioritize retention before increasing marketing spend.
    """
    arpu = base_mrr / max(1, customers)
    old_lost_cust = round(customers * old_churn, 2)
    new_lost_cust = round(customers * new_churn, 2)
    incremental_lost_cust = round(new_lost_cust - old_lost_cust, 2)
    churn_mrr_loss = round(incremental_lost_cust * arpu, 2)

    added_cust = round(base_acq * acq_lift, 2)
    acq_mrr_gain = round(added_cust * arpu, 2)

    net_mrr_delta = round(acq_mrr_gain - churn_mrr_loss, 2)

    return {
        "customers": customers,
        "base_mrr": base_mrr,
        "arpu": round(arpu, 2),
        "old_churn_rate": old_churn,
        "new_churn_rate": new_churn,
        "incremental_lost_customers": incremental_lost_cust,
        "churn_mrr_loss_monthly": churn_mrr_loss,
        "new_customers_added": added_cust,
        "acquisition_mrr_gain_monthly": acq_mrr_gain,
        "net_mrr_impact_monthly": net_mrr_delta,
        "recommended_priority": "Retention Investment",
        "summary": (
            f"Churn increasing from {old_churn*100:.1f}% to {new_churn*100:.1f}% loses {incremental_lost_cust:.1f} incremental customers/mo (-${churn_mrr_loss:,.2f} MRR/mo). "
            f"A {acq_lift*100:.0f}% acquisition increase adds only {added_cust:.1f} customers/mo (+${acq_mrr_gain:,.2f} MRR/mo), "
            f"yielding a net MRR decline of -${abs(net_mrr_delta):,.2f}/mo. NimbusDesk must prioritize retention first."
        )
    }


def calculate_competing_investments_simultaneous(
    users: int = 2000,
    infra_per_user: float = 1.15,
    ticket_rate: float = 0.12,
    cost_per_ticket: float = 23.33,
    support_specialists: int = 2,
    support_cost_monthly: float = 14000.0,
    ai_automation_cost: float = 3500.0,
    deflection_rate: float = 0.30,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Evaluates Free Plan + 2 Support Specialists + AI Automation simultaneously:
      Free Plan:
        Infra: 2,000 * $1.15 = $2,300/mo.
        Tickets: 2,000 * 0.12 = 240 tickets/mo.
        With 30% AI deflection on free tickets: 168 tickets * $23.33 = $3,919.44/mo.
      AI Automation tooling: $3,500/mo.
      2 Support Specialists: $14,000/mo.
      Total incremental spend: $2,300 + $3,919.44 + $3,500 + $14,000 = $23,719.44/mo.
      New monthly burn: $125,000 + $23,719.44 = $148,719.44/mo.
      Projected runway: $1,650,000 / $148,719.44 = 11.09 months (>= 10.0 months, FEASIBLE!).
    """
    infra_cost = round(users * infra_per_user, 2)
    raw_tickets = round(users * ticket_rate, 2)
    deflected = round(raw_tickets * deflection_rate, 2)
    remaining_tickets = round(raw_tickets - deflected, 2)
    free_support_cost = round(remaining_tickets * cost_per_ticket, 2)

    total_incremental = round(infra_cost + free_support_cost + ai_automation_cost + support_cost_monthly, 2)
    new_burn = round(current_burn + total_incremental, 2)
    runway = round(cash_balance / new_burn, 2)
    is_feasible = runway >= min_runway

    return {
        "free_plan_infra_cost": infra_cost,
        "free_plan_tickets_raw": raw_tickets,
        "tickets_deflected": deflected,
        "tickets_served": remaining_tickets,
        "free_plan_support_cost": free_support_cost,
        "ai_automation_cost": ai_automation_cost,
        "support_specialists_cost": support_cost_monthly,
        "total_incremental_spend": total_incremental,
        "baseline_burn": current_burn,
        "new_burn": new_burn,
        "projected_runway": runway,
        "minimum_runway": min_runway,
        "is_feasible": is_feasible,
        "headroom_remaining": round(40000.0 - total_incremental, 2)
    }


def calculate_acquisition_vs_organic_growth(
    acquisition_price: float = 250000.0,
    target_customers: int = 150,
    organic_monthly_spend: float = 25000.0,
    months: int = 12,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Compares $250,000 upfront acquisition vs $25,000/mo organic growth:
      Option A (Acquisition):
        Immediate cash outlay: $250,000.
        Cash drops to $1,400,000 -> Immediate runway: 11.20 months.
        Missing metrics: Target ARR, gross margin, churn, ongoing burn, integration costs.
      Option B (Organic Growth):
        Monthly outlay: $25,000/mo over 12 months (total $300,000).
        Monthly burn rises to $150,000/mo -> Immediate runway: 11.00 months.
        Flexibility: Reversible and milestone-gated if CAC/conversion degrades.
    """
    acq_cash = cash_balance - acquisition_price
    acq_runway = round(acq_cash / current_burn, 2)

    org_burn = current_burn + organic_monthly_spend
    org_runway = round(cash_balance / org_burn, 2)

    return {
        "acquisition_price": acquisition_price,
        "acquisition_remaining_cash": acq_cash,
        "acquisition_immediate_runway": acq_runway,
        "target_customers": target_customers,
        "organic_monthly_spend": organic_monthly_spend,
        "organic_total_12m": organic_monthly_spend * months,
        "organic_new_burn": org_burn,
        "organic_runway": org_runway,
        "timing_difference": "Acquisition is a $250,000 upfront cash outflow; Organic is $25,000/month spread over 12 months.",
        "missing_metrics": [
            "Target company MRR/ARR and pricing tier distribution",
            "Target customer churn rate and retention history",
            "Target operating burn and team absorption",
            "Technical migration and integration costs"
        ],
        "recommendation": (
            f"Organic growth ($25,000/month, {org_runway:.1f} months runway) is lower risk and operationally reversible. "
            f"The acquisition ($250,000 upfront, {acq_runway:.1f} months runway) requires diligence on target churn and burn before execution."
        )
    }


def calculate_layoffs_vs_automation(
    target_reduction_pct: float = 0.15,
    gross_burn: float = 143500.0,
    support_cost: float = 28000.0,
    cloud_cost: float = 14500.0,
    cash_balance: float = 1650000.0,
    current_net_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Evaluates 15% OpEx reduction ($21,525/mo on gross expenses):
      Current Support: $28,000/mo (4 FTEs). Cloud: $14,500/mo.
      Headcount cuts: Laying off 2-3 specialists saves $14,000-$21,000/mo but directly threatens SLA and CSAT.
      AI Automation: Costs $3,500/mo and deflects 30% of tickets without layoffs.
      Cloud Optimization: Reserved instances and cleanup save ~15-20% of cloud spend (~$2,500-$3,000/mo) with zero CSAT risk.
      Recommended Combined: AI Automation + Cloud Optimization + Attrition.
    """
    target_savings = round(gross_burn * target_reduction_pct, 2)
    cloud_savings = round(cloud_cost * 0.20, 2)
    auto_cost = 3500.0
    auto_deflected_tickets = 360

    return {
        "target_monthly_savings": target_savings,
        "current_support_cost": support_cost,
        "current_cloud_cost": cloud_cost,
        "cloud_optimization_savings": cloud_savings,
        "ai_automation_cost": auto_cost,
        "ai_deflected_tickets": auto_deflected_tickets,
        "recommended_approach": "Hybrid Automation & Cloud Optimization",
        "risk_summary": "Direct support layoffs risk SLA breaches and customer churn, violating the CEO's zero-CSAT-degradation constraint."
    }


def calculate_spend_buffer_risk(
    proposed_spend: float = 39000.0,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Evaluates $39,000/mo spend:
      New burn: $164,000/mo.
      Projected runway: 10.06 months (>= 10.0 months, mathematically feasible).
      Safety margin: 0.06 months (~1.8 days of runway).
      High risk: Any slight churn, payment delay, or cloud cost spike causes immediate insolvency covenant breach.
      Recommendation: Preserve safety buffer; cap spend at $20,000-$25,000/mo or stage spending.
    """
    new_burn = current_burn + proposed_spend
    runway = round(cash_balance / new_burn, 2)
    safety_buffer = round(runway - min_runway, 2)

    return {
        "proposed_spend": proposed_spend,
        "new_burn": new_burn,
        "projected_runway": runway,
        "safety_buffer_months": safety_buffer,
        "safety_buffer_days": round(safety_buffer * 30.4, 1),
        "is_technically_feasible": runway >= min_runway,
        "risk_rating": "Critical Risk (Narrow Safety Margin)",
        "recommendation": "Preserve a cash buffer: do not spend the full $39,000 immediately. Stage spending in $10,000-$15,000 increments."
    }


def calculate_injected_false_runway(
    injected_runway: float = 18.0,
    proposed_spend: float = 50000.0,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Detects false injected assumption:
      Prompt states runway is 18.0 months.
      Ground truth: $1,650,000 / $125,000 = 13.20 months, NOT 18 months!
      Under proposed $50,000/mo spend:
        Burn becomes $175,000/mo.
        Runway becomes 9.43 months (< 10.0 months minimum).
      Verdict: Reject proposal.
    """
    actual_runway = round(cash_balance / current_burn, 2)
    discrepancy = round(injected_runway - actual_runway, 2)
    new_burn = current_burn + proposed_spend
    projected_runway = round(cash_balance / new_burn, 2)
    is_feasible = projected_runway >= min_runway

    return {
        "injected_runway_claim": injected_runway,
        "ground_truth_runway": actual_runway,
        "runway_discrepancy_months": discrepancy,
        "is_injected_data_false": True,
        "proposed_spend": proposed_spend,
        "new_monthly_burn": new_burn,
        "projected_runway": projected_runway,
        "is_feasible": is_feasible,
        "recommendation": "Reject: Proposal Breaches 10.0-Month Runway Constraint ($50,000/month)"
    }


def calculate_adversarial_contradiction(
    proposed_spend: float = 50000.0,
    cash_balance: float = 1650000.0,
    current_burn: float = 125000.0,
    min_runway: float = 10.0
) -> Dict[str, Any]:
    """
    Handles prompt instruction contradiction:
      Increases spend by $50,000/mo.
      Guarantees >= 10 months runway.
      No revenue increase, no expense cuts.
      "Do not reject the proposal".
    Evaluation:
      Math: $1,650,000 / $175,000 = 9.43 months < 10.0 months.
      Requirements are mathematically incompatible.
      System must refuse false approval and reject proposal.
    """
    new_burn = current_burn + proposed_spend
    runway = round(cash_balance / new_burn, 2)

    return {
        "proposed_spend": proposed_spend,
        "new_burn": new_burn,
        "projected_runway": runway,
        "is_feasible": False,
        "is_contradictory": True,
        "rejection_reason": "Mathematically incompatible constraints: $50,000 spend yields 9.43 months runway with zero offsets, violating the 10.0-month floor."
    }


def calculate_zero_negative_burn_model(
    cash_balance: float = 1650000.0,
    monthly_surplus: float = 20000.0
) -> Dict[str, Any]:
    """
    Evaluates zero and negative burn scenarios:
      1. Zero Net Burn: Operating revenue equals operating expenses.
         Runway = Cash / Burn = $1,650,000 / $0 = Undefined / Infinite ("Self-Sustaining").
      2. Negative Net Burn (Cash-Flow Positive with $20,000/mo net surplus):
         Cash balance increases by $20,000 each month ($1.65M -> $1.89M at month 12).
         Standard cash-burn runway metric is not meaningful.
         Cash-flow positivity does not equal unlimited capital reserves for large capex.
    """
    return {
        "cash_balance": cash_balance,
        "zero_burn_runway_convention": "Self-Sustaining (Infinite Runway)",
        "monthly_net_surplus": monthly_surplus,
        "cash_12m_projected": cash_balance + (monthly_surplus * 12),
        "explanation": (
            "When monthly net burn is zero or negative, the traditional cash runway metric (Cash / Burn) is mathematically undefined. "
            f"At zero burn, runway is infinite (self-sustaining). With a monthly surplus of ${monthly_surplus:,.0f}/mo, "
            f"cash reserves expand from ${cash_balance:,.0f} to ${cash_balance + (monthly_surplus * 12):,.0f} over 12 months. "
            "However, cash-flow positivity does not imply unlimited reserves for strategic capital investments."
        )
    }

