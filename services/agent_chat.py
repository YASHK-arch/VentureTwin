import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from data.loader import load_company_data
from services.company_context_store import get_active_company_context
from agents.registry import default_registry
from agents.llm_client import LLMClient


class AgentChatRequest(BaseModel):
    agent_key: str
    message: str
    history: Optional[List[Dict[str, str]]] = None


class AgentChatResponse(BaseModel):
    agent_key: str
    agent_name: str
    role: str
    avatar: str
    response: str
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str = "proceed"
    confidence: float = 0.90
    timestamp: str


AGENT_META_MAP = {
    "supervisor": {
        "name": "Supervisor",
        "role": "Executive Chief of Staff & Strategy Orchestrator",
        "avatar": "🎯",
        "domain": "Strategic framing, departmental delegation, risk balancing, consensus synthesis"
    },
    "cfo": {
        "name": "CFO",
        "role": "Chief Financial Officer",
        "avatar": "💼",
        "domain": "Cash reserves, runway, net burn, gross margins, pricing models, CAC payback"
    },
    "growth": {
        "name": "Growth",
        "role": "VP Growth & CMO",
        "avatar": "📈",
        "domain": "Traffic, funnel conversion, trial signups, customer acquisition, CAC"
    },
    "cto": {
        "name": "CTO",
        "role": "Chief Technology Officer",
        "avatar": "⚡",
        "domain": "Cloud infrastructure spend, per-user compute costs, SLA uptime, scaling bottlenecks"
    },
    "customer": {
        "name": "Customer Success",
        "role": "VP Customer Success",
        "avatar": "🤝",
        "domain": "Customer churn, net retention cohorts, support ticket volume, agent resolution capacity"
    },
    "product": {
        "name": "Product",
        "role": "Chief Product Officer",
        "avatar": "📦",
        "domain": "Plan tiering, feature limits, packaging, self-serve upgrade velocity, user engagement"
    },
    "skeptic": {
        "name": "Skeptic",
        "role": "Independent Risk Auditor",
        "avatar": "🛡️",
        "domain": "Devil's advocate critique, downside vulnerabilities, competitor retaliation, stress-tests"
    }
}


def generate_mock_agent_response(
    agent_key: str,
    query: str,
    company_data: Dict[str, Any],
    custom_context: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generates grounded, domain-specific executive responses in mock mode."""
    fin = company_data.get("financials", {})
    funnel = company_data.get("funnel", {})
    cust = company_data.get("customers", {})
    infra = company_data.get("infrastructure", {})
    support = company_data.get("support", {})
    unit = company_data.get("unit_economics", {})

    company_name = (custom_context or {}).get("company_name") or company_data.get("company_name", "the company")
    q_lower = query.lower()

    if agent_key == "cfo":
        cash = fin.get("cash_balance", 1650000)
        runway = fin.get("runway_months", 13.2)
        burn = fin.get("monthly_burn_net", 125000)
        mrr = fin.get("mrr", 110370)
        margin = fin.get("gross_margin", 0.78)

        if any(w in q_lower for w in ["runway", "cash", "burn", "balance"]):
            resp = (
                f"From our financial ledger for {company_name}, our cash reserves stand at "
                f"${cash:,.0f} with a net monthly burn rate of ${burn:,.0f}, yielding exactly "
                f"{runway:.1f} months of verified runway. Our monthly recurring revenue is ${mrr:,.0f} "
                f"at a {margin * 100:.0f}% gross margin. Any strategic initiative increasing burn without "
                f"immediate payback risks breaching our 12-month safety floor."
            )
        elif any(w in q_lower for w in ["price", "pricing", "raise", "increase", "tier"]):
            resp = (
                f"From a unit economics standpoint, our baseline CAC is ${unit.get('cac', 1450)} with an "
                f"LTV of ${unit.get('ltv', 4850)} (LTV:CAC ratio of {unit.get('ltv', 4850)/max(1, unit.get('cac', 1450)):.1f}x). "
                f"Adjusting pricing upwards expands contribution margin directly, but we must protect our "
                f"{fin.get('target_min_runway_months', 12)}-month minimum cash floor against conversion friction."
            )
        else:
            resp = (
                f"As CFO, I track our capital efficiency closely: current cash balance is ${cash:,.0f}, "
                f"runway is {runway:.1f} months, and MRR is ${mrr:,.0f}. For this proposal ('{query}'), "
                f"I recommend modeling the sensitivity against our monthly burn before committing capital."
            )

        return {
            "response": resp,
            "key_metrics": {
                "cash_balance": cash,
                "runway_months": runway,
                "monthly_burn_net": burn,
                "mrr": mrr
            },
            "recommendation": "proceed_with_conditions",
            "confidence": 0.94
        }

    elif agent_key == "growth":
        visitors = funnel.get("monthly_visitors", 45000)
        signups = funnel.get("trial_signups", 2250)
        conversion = funnel.get("trial_to_paid_conversion", 0.042)
        cac = unit.get("cac", 1450)

        resp = (
            f"Reviewing top-of-funnel telemetry for {company_name}: we currently attract {visitors:,} monthly unique visitors, "
            f"converting to {signups:,} trials ({signups/max(1, visitors)*100:.1f}% visitor-to-trial rate). "
            f"Our trial-to-paid conversion is currently {conversion * 100:.2f}%, and blended CAC is ${cac:,}. "
            f"Regarding your question ('{query}'): growth acceleration requires tightening the activation funnel and "
            f"shortening our payback period from the current {unit.get('cac_payback_months', 14.5):.1f} months."
        )
        return {
            "response": resp,
            "key_metrics": {
                "monthly_visitors": visitors,
                "trial_signups": signups,
                "trial_to_paid_conversion": conversion,
                "cac": cac
            },
            "recommendation": "proceed",
            "confidence": 0.91
        }

    elif agent_key == "cto":
        cloud_cost = infra.get("monthly_cloud_cost", 14500)
        cost_per_paid = infra.get("infra_cost_per_paid_user", 22.14)
        cost_per_free = infra.get("infra_cost_per_free_user_estimate", 0.85)

        resp = (
            f"From an infrastructure and systems architecture perspective at {company_name}: our current baseline cloud spend "
            f"is ${cloud_cost:,}/month across cluster instances, databases, and egress bandwidth. "
            f"Infra compute cost per paid customer is ${cost_per_paid:.2f}/month. If free or self-serve tiers are introduced, "
            f"our marginal compute cost is estimated at ${cost_per_free:.2f} per active user. "
            f"Regarding '{query}': we must ensure autoscaling safeguards and telemetry rate-limits are enforced to avoid cloud cost overrun."
        )
        return {
            "response": resp,
            "key_metrics": {
                "monthly_cloud_cost": cloud_cost,
                "infra_cost_per_paid_user": cost_per_paid,
                "infra_cost_per_free_user": cost_per_free
            },
            "recommendation": "proceed_with_conditions",
            "confidence": 0.89
        }

    elif agent_key == "customer":
        paying = cust.get("total_paying", 655)
        churn = cust.get("monthly_churn_rate", 0.021)
        headcount = support.get("headcount_fte", 4)
        support_cost = support.get("monthly_support_cost", 28000)

        resp = (
            f"Customer Success & Support status for {company_name}: we serve {paying:,} paying enterprise & mid-market accounts "
            f"with a monthly logo churn rate of {churn * 100:.2f}%. Support operations is staffed by {headcount} FTEs "
            f"costing ${support_cost:,}/month. Regarding your inquiry ('{query}'): maintaining customer satisfaction "
            f"and high net retention requires keeping ticket queue volume below 300 tickets/FTE/month."
        )
        return {
            "response": resp,
            "key_metrics": {
                "paying_customers": paying,
                "monthly_churn_rate": churn,
                "support_headcount": headcount,
                "support_cost_monthly": support_cost
            },
            "recommendation": "proceed",
            "confidence": 0.92
        }

    elif agent_key == "product":
        plans = cust.get("plans", [])
        plan_summary = ", ".join([f"{p.get('name')} (${p.get('price_monthly')}/mo)" for p in plans]) or "Starter ($49), Growth ($149), Enterprise"

        resp = (
            f"As Product Lead for {company_name}, our current tier structure spans: {plan_summary}. "
            f"Our primary packaging focus is value-metric alignment: ensuring features on higher tiers create natural expansion triggers. "
            f"Addressing your query ('{query}'): product roadmap priorities must balance self-serve adoption with enterprise feature gating "
            f"such as SSO, audit logs, and dedicated tenant isolation."
        )
        return {
            "response": resp,
            "key_metrics": {
                "total_plans": len(plans),
                "pricing_tiers": plan_summary
            },
            "recommendation": "proceed",
            "confidence": 0.90
        }

    elif agent_key == "skeptic":
        burn = fin.get("monthly_burn_net", 125000)
        runway = fin.get("runway_months", 13.2)
        churn = cust.get("monthly_churn_rate", 0.021)

        resp = (
            f"I challenge the optimistic baseline assumptions regarding '{query}'. "
            f"Here are the core downside vulnerabilities: First, our cash runway of {runway:.1f} months gives us very little room "
            f"for error if execution lags by even one quarter. Second, churn at {churn * 100:.2f}% per month means any pricing or packaging "
            f"friction could trigger sudden customer downgrades. Third, competitive alternatives will react quickly. "
            f"I strongly recommend running a stress-test scenario before authorizing irreversible organizational commitments."
        )
        return {
            "response": resp,
            "key_metrics": {
                "downside_risk_score": 0.72,
                "runway_months": runway,
                "churn_exposure": churn
            },
            "recommendation": "challenge",
            "confidence": 0.95
        }

    else:  # supervisor
        mrr = fin.get("mrr", 110370)
        runway = fin.get("runway_months", 13.2)
        resp = (
            f"As Executive Chief of Staff and Orchestrator for {company_name}: I evaluate this strategic inquiry ('{query}') "
            f"across all five executive domains simultaneously. At $110k MRR and 13.2 months of runway, our priority is durable growth "
            f"without reckless burn acceleration. For a deep cross-functional assessment with algorithmic trade-off reconciliation, "
            f"select 'Whole Board' from the dropdown to run the full 11-node multi-agent DAG."
        )
        return {
            "response": resp,
            "key_metrics": {
                "mrr": mrr,
                "runway_months": runway,
                "coordinated_agents": 7
            },
            "recommendation": "proceed",
            "confidence": 0.93
        }


async def chat_with_agent(
    agent_key: str,
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    user_id: Optional[str] = None
) -> AgentChatResponse:
    """Executes a direct 1-on-1 dialogue with an individual executive agent."""
    agent_key_clean = agent_key.lower().strip()
    if agent_key_clean not in AGENT_META_MAP:
        agent_key_clean = "supervisor"

    meta = AGENT_META_MAP[agent_key_clean]
    company_data = load_company_data()
    custom_context = get_active_company_context(user_id=user_id)

    client = LLMClient()
    now_iso = datetime.now(timezone.utc).isoformat()

    if client.mode == "mock":
        generated = generate_mock_agent_response(agent_key_clean, message, company_data, custom_context)
    else:
        # In real/record LLM mode
        system_prompt = (
            f"You are the {meta['name']} ({meta['role']}) of a growing SaaS company.\n"
            f"Your specific domain responsibility: {meta['domain']}.\n\n"
            f"Company Financials: Cash ${company_data.get('financials', {}).get('cash_balance'):,}, "
            f"Runway {company_data.get('financials', {}).get('runway_months')} months, "
            f"MRR ${company_data.get('financials', {}).get('mrr'):,}, "
            f"Burn ${company_data.get('financials', {}).get('monthly_burn_net'):,}.\n"
            f"Customers: {company_data.get('customers', {}).get('total_paying')} paying, "
            f"Monthly Churn {company_data.get('customers', {}).get('monthly_churn_rate')*100:.2f}%.\n\n"
            "Respond directly, concisely, and authoritatively to the CEO's inquiry in character as this executive officer. "
            "Reference specific operational numbers and provide clear, actionable guidance."
        )

        class LLMChatResponse(BaseModel):
            response: str
            recommendation: str = "proceed"
            confidence: float = 0.90
            key_metric_summary: Dict[str, Any] = Field(default_factory=dict)

        try:
            res_obj = await client.call(
                prompt=f"CEO Inquiry: {message}",
                response_model=LLMChatResponse,
                system_prompt=system_prompt,
                temperature=0.2
            )
            generated = {
                "response": res_obj.response,
                "key_metrics": res_obj.key_metric_summary,
                "recommendation": res_obj.recommendation,
                "confidence": res_obj.confidence
            }
        except Exception:
            generated = generate_mock_agent_response(agent_key_clean, message, company_data, custom_context)

    return AgentChatResponse(
        agent_key=agent_key_clean,
        agent_name=meta["name"],
        role=meta["role"],
        avatar=meta["avatar"],
        response=generated["response"],
        key_metrics=generated.get("key_metrics", {}),
        recommendation=generated.get("recommendation", "proceed"),
        confidence=generated.get("confidence", 0.90),
        timestamp=now_iso
    )
