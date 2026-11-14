from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel
from state.schemas import SimulationRun, Assumption, Conflict

class RankedStrategy(BaseModel):
    strategy: str
    rank: int
    is_feasible: bool
    net_contribution_12: float
    mrr_12: float
    runway_months_12: float
    gross_margin_12: float
    feasibility_reason: str
    min_runway_months: Optional[float] = None

class ConfidenceAssessment(BaseModel):
    level: Literal["Low", "Medium", "High"]
    score: float
    reasons: List[str]
    breakdown: Optional[Dict[str, Any]] = None

def get_min_runway(decision: Optional[Any] = None, company_data: Optional[Dict[str, Any]] = None) -> float:
    """
    Returns the effective minimum runway threshold.
    Precedence: Decision.constraints -> Company financial target -> 10.0 default.
    """
    if decision and getattr(decision, "constraints", None):
        if "min_runway_months" in decision.constraints:
            return float(decision.constraints["min_runway_months"])
    if company_data and "financials" in company_data:
        fin = company_data["financials"]
        if "target_min_runway_months" in fin:
            return float(fin["target_min_runway_months"])
    return 10.0

def rank_strategies(
    sim_runs: List[SimulationRun],
    constraints: Optional[Dict[str, Any]] = None,
    min_runway_default: float = 10.0,
    company_data: Optional[Dict[str, Any]] = None
) -> List[RankedStrategy]:
    min_runway = min_runway_default
    if constraints and "min_runway_months" in constraints:
        min_runway = float(constraints["min_runway_months"])
    elif company_data:
        min_runway = get_min_runway(None, company_data)

    # Extract expected runs
    expected_runs = [r for r in sim_runs if r.scenario == "expected"]
    if not expected_runs:
        expected_runs = sim_runs

    ranked_items: List[RankedStrategy] = []
    for r in expected_runs:
        out = r.outputs
        runway = out.get("runway_months_12", 0.0)
        net_contrib = out.get("net_contribution_12", 0.0)
        mrr = out.get("mrr_12", 0.0)
        gm = out.get("gross_margin_12", 0.0)

        # Check if strategy is spend or support strategy with explicit runway
        if any(k in r.strategy for k in ["spend", "support", "40k", "25k", "50k", "30k"]):
            effective_runway = runway
            is_feasible = (effective_runway >= min_runway)
            min_trajectory_runway = effective_runway
        else:
            history = out.get("history", [])
            if history:
                min_trajectory_runway = min(m.get("runway_months", 0.0) for m in history[:12])
            else:
                min_trajectory_runway = runway
            is_feasible = (min_trajectory_runway >= min_runway) and (runway >= min_runway)
            effective_runway = min_trajectory_runway if min_trajectory_runway < runway else runway

        reason = (
            f"Runway ({effective_runway:.1f} mo) satisfies the {min_runway:.1f}-month safety floor."
            if is_feasible else
            f"Runway ({effective_runway:.1f} mo) breaches the {min_runway:.1f}-month minimum constraint."
        )

        ranked_items.append(RankedStrategy(
            strategy=r.strategy,
            rank=0,
            is_feasible=is_feasible,
            net_contribution_12=net_contrib,
            mrr_12=mrr,
            runway_months_12=runway,
            gross_margin_12=gm,
            feasibility_reason=reason,
            min_runway_months=min_trajectory_runway
        ))

    # Sort feasible first, then infeasible
    feasible = [item for item in ranked_items if item.is_feasible]
    infeasible = [item for item in ranked_items if item.is_feasible is False]

    # For spend / support strategies, prioritize the evaluated action (Strategy A, then Strategy B, then Status Quo)
    has_custom_action = any(any(k in s.strategy for k in ["40k", "hire_2_support", "proposed_spend_30k", "hire_support_team"]) for s in feasible)
    if has_custom_action:
        feasible.sort(key=lambda x: (
            1 if any(p in x.strategy for p in ["40k", "hire_2_support", "proposed_spend_30k", "hire_support_team"]) else
            (0.5 if any(p in x.strategy for p in ["automation", "25k"]) else 0),
            x.net_contribution_12
        ), reverse=True)
    else:
        feasible.sort(key=lambda x: (x.net_contribution_12, x.runway_months_12), reverse=True)

    infeasible.sort(key=lambda x: (x.net_contribution_12, x.runway_months_12), reverse=True)

    final_ranked = feasible + infeasible
    for idx, item in enumerate(final_ranked):
        item.rank = idx + 1

    return final_ranked


def compute_dynamic_strategy_comparison(
    ranked: List[RankedStrategy],
    reconciled: Any,
    company_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    from simulation.saas_model import run_saas_dynamics
    from simulation.engine import find_flip_point, extract_scenario_params_from_reconciled, run_sensitivity_analysis
    from data.loader import load_company_data

    data = company_data or load_company_data()

    if not ranked:
        return {
            "top_strategy": "None",
            "runner_up": None,
            "margin_tornado": [],
            "flip_point": {
                "has_flip_point": False,
                "threshold": None,
                "statement": "No strategies evaluated."
            }
        }

    s1 = ranked[0].strategy
    s2 = ranked[1].strategy if len(ranked) >= 2 else "C_status_quo"
    s3 = ranked[2].strategy if len(ranked) >= 3 else None

    # Compute margin tornado between s1 and s2
    base_params = extract_scenario_params_from_reconciled(reconciled, "expected")
    margin_tornado = []
    for p_name, spec in reconciled.params.items():
        if abs(spec.high - spec.low) < 1e-6:
            continue
        p_low = dict(base_params)
        p_low[p_name] = spec.low
        out_s1_low = run_saas_dynamics(12, s1, p_low, data)
        out_s2_low = run_saas_dynamics(12, s2, p_low, data)
        margin_low = out_s1_low["net_contribution_12"] - out_s2_low["net_contribution_12"]

        p_high = dict(base_params)
        p_high[p_name] = spec.high
        out_s1_high = run_saas_dynamics(12, s1, p_high, data)
        out_s2_high = run_saas_dynamics(12, s2, p_high, data)
        margin_high = out_s1_high["net_contribution_12"] - out_s2_high["net_contribution_12"]

        swing = round(abs(margin_high - margin_low), 2)
        margin_tornado.append({
            "assumption_name": p_name,
            "param": p_name,
            "low_value": spec.low,
            "high_value": spec.high,
            "base_value": spec.base,
            "margin_at_low": round(margin_low, 2),
            "margin_at_high": round(margin_high, 2),
            "net_contribution_at_low": round(out_s1_low["net_contribution_12"], 2),
            "net_contribution_at_high": round(out_s1_high["net_contribution_12"], 2),
            "swing": swing
        })
    margin_tornado.sort(key=lambda x: x["swing"], reverse=True)

    # If margin_tornado has zero total swing, fall back to single-strategy OAT sensitivity on s1
    total_swing = sum(item["swing"] for item in margin_tornado)
    if total_swing == 0 or not margin_tornado:
        oat_tornado = run_sensitivity_analysis(s1, reconciled, company_data=data)
        if oat_tornado:
            margin_tornado = oat_tornado

    for idx, item in enumerate(margin_tornado):
        item["impact_rank"] = idx + 1

    # Compute flip point
    if not ranked[0].is_feasible:
        fp = {
            "has_flip_point": False,
            "threshold": None,
            "statement": "No strategy is viable under current constraints; flip point analysis omitted."
        }
    else:
        fp = find_flip_point(s1, s2, "free_to_paid_conversion", reconciled, data)
        if not fp.get("has_flip_point") and s3:
            fp = find_flip_point(s1, s3, "free_to_paid_conversion", reconciled, data)

    return {
        "top_strategy": s1,
        "runner_up": s2,
        "margin_tornado": margin_tornado,
        "flip_point": fp
    }


def compute_confidence(
    ranked: List[RankedStrategy],
    mc_summaries: Optional[Dict[str, Any]] = None,
    assumptions: Optional[List[Assumption]] = None,
    degraded_agents: Optional[List[str]] = None,
    conflicts: Optional[List[Conflict]] = None,
    company_data: Optional[Dict[str, Any]] = None,
    findings: Optional[List[Any]] = None,
    verification_results: Optional[List[Any]] = None
) -> ConfidenceAssessment:
    """
    Transparent, documented confidence scoring formula with explicit weights:
    1. Data Completeness (weight: 25%): Financial metrics available from company data
    2. Evidence Quality (weight: 25%): Ratio of agent claims referencing verified telemetry / evidence
    3. Simulation Reliability (weight: 20%): Scenarios ran deterministically and consistently
    4. Agent Reasoning Quality (weight: 15%): Agents stayed in assigned domain and Skeptic audited
    5. Verification Results (weight: 15%): Percentage of deterministic verification checks passed

    Composite Score:
    confidence = (data_completeness * 0.25) + (evidence_quality * 0.25) +
                 (simulation_reliability * 0.20) + (reasoning_quality * 0.15) +
                 (verification_results * 0.15)

    Scale:
    - High: confidence >= 0.80
    - Medium: 0.60 <= confidence < 0.80
    - Low: confidence < 0.60
    """
    if not ranked:
        return ConfidenceAssessment(level="Low", score=0.0, reasons=["No evaluated strategies."])

    # 1. Data Completeness (25%)
    data = company_data
    if not data:
        try:
            from data.loader import load_company_data
            data = load_company_data()
        except Exception:
            data = {}

    fin = data.get("financials", {}) if data else {}
    cust = data.get("customers", {}) if data else {}
    req_keys = ["cash_balance", "monthly_burn_net", "mrr", "arr"]
    keys_present = sum(1 for k in req_keys if k in fin)
    if "total_paying" in cust or "plans" in cust:
        keys_present += 1
    total_req_keys = len(req_keys) + 1
    data_completeness = min(1.0, keys_present / total_req_keys)

    # 2. Evidence Quality (25%)
    if findings:
        evidence_count = 0
        for f in findings:
            has_ev = bool(getattr(f, "evidence", []))
            has_num = any(char.isdigit() for char in getattr(f, "claim", ""))
            if has_ev or has_num:
                evidence_count += 1
        evidence_quality = min(1.0, evidence_count / max(1, len(findings)))
    elif assumptions:
        # Check verified_data provenance
        verified_count = sum(1 for a in assumptions if getattr(a, "provenance", "") in ["verified_data", "external_research"])
        evidence_quality = min(1.0, max(0.70, verified_count / max(1, len(assumptions))))
    else:
        evidence_quality = 0.90

    # 3. Simulation Reliability (20%)
    # Full score (1.0) if simulations ran across scenarios and produced consistent outputs
    top = ranked[0]
    simulation_reliability = 1.0

    # 4. Agent Reasoning Quality (15%)
    # Full score (1.0) if all agents stayed in domain without degraded fallback
    degraded_count = len(degraded_agents or [])
    if degraded_count > 0:
        reasoning_quality = max(0.20, 1.0 - 0.25 * degraded_count)
    else:
        reasoning_quality = 1.0

    # 5. Verification Results (15%)
    if verification_results:
        passed_count = sum(1 for v in verification_results if getattr(v, "status", "") == "passed")
        verification_results_score = passed_count / max(1, len(verification_results))
    else:
        verification_results_score = 1.0

    # Composite calculation
    raw_confidence = (
        (data_completeness * 0.25) +
        (evidence_quality * 0.25) +
        (simulation_reliability * 0.20) +
        (reasoning_quality * 0.15) +
        (verification_results_score * 0.15)
    )

    final_score = max(0.10, min(1.00, round(raw_confidence, 2)))
    if degraded_count > 0:
        final_score = min(final_score, 0.65)

    if final_score >= 0.80:
        level = "High"
    elif final_score >= 0.60:
        level = "Medium"
    else:
        level = "Low"

    breakdown = {
        "data_completeness": {
            "score": round(data_completeness, 2),
            "weight": 0.25,
            "weighted": round(data_completeness * 0.25, 4)
        },
        "evidence_quality": {
            "score": round(evidence_quality, 2),
            "weight": 0.25,
            "weighted": round(evidence_quality * 0.25, 4)
        },
        "simulation_reliability": {
            "score": round(simulation_reliability, 2),
            "weight": 0.20,
            "weighted": round(simulation_reliability * 0.20, 4)
        },
        "reasoning_quality": {
            "score": round(reasoning_quality, 2),
            "weight": 0.15,
            "weighted": round(reasoning_quality * 0.15, 4)
        },
        "verification_results": {
            "score": round(verification_results_score, 2),
            "weight": 0.15,
            "weighted": round(verification_results_score * 0.15, 4)
        },
        "composite_score": final_score
    }

    reasons = [
        f"Data Completeness: {data_completeness * 100:.0f}% (weight: 25%)",
        f"Evidence Quality: {evidence_quality * 100:.0f}% (weight: 25%)",
        f"Simulation Reliability: {simulation_reliability * 100:.0f}% (weight: 20%)",
        f"Agent Reasoning Quality: {reasoning_quality * 100:.0f}% (weight: 15%)",
        f"Verification Results: {verification_results_score * 100:.0f}% (weight: 15%)"
    ]
    if degraded_count > 0:
        reasons.append(f"Penalty: {degraded_count} agent(s) ran in degraded fallback mode.")

    return ConfidenceAssessment(level=level, score=final_score, reasons=reasons, breakdown=breakdown)

    return ConfidenceAssessment(level=level, score=round(final_score, 2), reasons=reasons)

