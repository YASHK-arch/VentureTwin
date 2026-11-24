import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ALL_SPECIALISTS = ["cfo", "growth", "cto", "customer", "product"]

SPECIALIST_ROLES = {
    "cfo": "Financial Analyst (runway, burn rate, gross margin, pricing floors, ARPU)",
    "growth": "Acquisition Strategist (top-of-funnel traffic, trial conversion, CAC, funnel velocity)",
    "cto": "Infrastructure Architect (cloud compute costs, server scaling, database load, latency)",
    "customer": "Retention & Success Specialist (churn rate, support ticket volume, CSAT, onboarding)",
    "product": "Packaging & Pricing Strategist (tier boundaries, feature gating, user experience, limits)"
}


class SupervisorRoutingDecision(BaseModel):
    context_summary: str = Field(
        ...,
        description="Concise strategic context and core intent extracted from boardroom question"
    )
    selected_specialists: List[str] = Field(
        ...,
        description="List of specialist agent keys (cfo, growth, cto, customer, product) involved in DAG"
    )
    specialist_directives: Dict[str, str] = Field(
        default_factory=dict,
        description="Specific strategic analysis directive assigned by Supervisor to each selected specialist"
    )
    reasoning: str = Field(
        ...,
        description="Executive rationale from Supervisor explaining why these specialists were selected"
    )
    source: str = Field(
        default="deterministic_router",
        description="Routing engine used: 'groq' or 'deterministic_router'"
    )


def deterministic_supervisor_routing(
    query: str,
    company_data: Optional[Dict[str, Any]] = None
) -> SupervisorRoutingDecision:
    """
    High-fidelity deterministic context extraction and agent selection.
    Evaluates domain intent, company telemetry, and keyword indicators
    to dynamically assemble the optimal specialist DAG.
    """
    q_lower = query.lower()
    
    # Financial telemetry context if present
    fin = (company_data or {}).get("financials", {})
    mrr_val = fin.get("mrr", 110370)
    runway_val = fin.get("runway_months", 13.2)

    # 1. Broad Freemium / Free Plan / Tier Overhaul (All 5 Specialists)
    if any(k in q_lower for k in [
        "free plan", "freemium", "free tier", "launch a free", "packaging overhaul",
        "self-serve tier", "community edition", "open source edition"
    ]):
        return SupervisorRoutingDecision(
            context_summary="Freemium & Free Plan packaging overhaul with cross-functional unit economics impact",
            selected_specialists=["cfo", "growth", "cto", "customer", "product"],
            specialist_directives={
                "cfo": f"Model gross margin compression, runway impact (current {runway_val} mo), and cash burn from unpaid users.",
                "growth": "Forecast top-of-funnel velocity, organic visitor influx, and paid-to-free cannibalization risk.",
                "cto": "Quantify marginal infrastructure cost per free user ($0.10-$0.45/mo) and database cluster load.",
                "customer": "Estimate support ticket inflation, self-serve onboarding friction, and net retention changes.",
                "product": "Define feature gating boundaries between Free and Starter ($79) to maximize upgrade velocity."
            },
            reasoning="A free tier impacts every operational organ: infrastructure hosting capacity (CTO), acquisition funnel (Growth), tier boundary gating (Product), support ticket load (Customer), and gross margin/runway (CFO). All 5 specialists must execute in parallel.",
            source="deterministic_router"
        )

    # 2. Infrastructure / Cloud / Database / Scaling (CTO + CFO)
    if any(k in q_lower for k in [
        "infra", "infrastructure", "aws", "gcp", "cloud", "server", "cluster",
        "database", "latency", "tech debt", "hosting", "kubernetes", "gpu", "compute"
    ]):
        return SupervisorRoutingDecision(
            context_summary="Cloud infrastructure architecture, server scaling capacity, and hosting cost optimization",
            selected_specialists=["cto", "cfo"],
            specialist_directives={
                "cto": "Assess server cluster elasticity, database read/write bottlenecks, and architectural failure modes.",
                "cfo": "Evaluate hosting expenditure payback, reserve instance commitments, and COGS gross margin impact."
            },
            reasoning="Technical infrastructure changes and cloud migrations primarily impact engineering architecture and cash expense. Orchestration isolates CTO and CFO for precise technical-economic evaluation.",
            source="deterministic_router"
        )

    # 3. Pricing Increase / Price Elasticity / Tier Expansion (CFO + Growth + Product)
    if any(k in q_lower for k in [
        "raise price", "increase price", "price by", "starter price", "pro price",
        "pricing increase", "elasticity", "arpu", "higher price", "discount"
    ]):
        return SupervisorRoutingDecision(
            context_summary="Pricing elasticity, ARPU expansion, and trial conversion trade-off analysis",
            selected_specialists=["cfo", "growth", "product"],
            specialist_directives={
                "cfo": f"Simulate MRR expansion (current ${mrr_val:,.0f}) vs contraction churn risk from existing subscriber renewals.",
                "growth": "Model trial conversion velocity drop and price elasticity resistance across top-of-funnel visitors.",
                "product": "Ensure feature packaging and perceived value justify higher tier pricing without user rebellion."
            },
            reasoning="Price modifications directly involve financial margins (CFO), acquisition conversion sensitivity (Growth), and tier packaging perceived value (Product). Infrastructure and customer support are non-critical to elasticity modeling.",
            source="deterministic_router"
        )

    # 4. Acquisition / Marketing / Paid Ads / Sales Funnel (Growth + CFO)
    if any(k in q_lower for k in [
        "marketing", "ad spend", "google ads", "paid search", "cac", "funnel",
        "acquisition", "sales cycle", "outbound", "lead generation", "visitor"
    ]):
        return SupervisorRoutingDecision(
            context_summary="Acquisition channel expansion, paid CAC payback, and conversion funnel throughput",
            selected_specialists=["growth", "cfo"],
            specialist_directives={
                "growth": "Calculate channel-specific CAC, signup velocity uplift, and conversion drop-offs along the funnel.",
                "cfo": "Verify CAC payback timeline under 12 months and model cash burn from upfront marketing spend."
            },
            reasoning="Marketing acquisition programs primarily affect customer acquisition velocity and cash burn. Growth and CFO provide targeted focus on CAC:LTV efficiency.",
            source="deterministic_router"
        )

    # 5. Churn / Customer Success / Retention / CSAT (Customer + Product + CFO)
    if any(k in q_lower for k in [
        "churn", "retention", "support", "csat", "ticket", "nps", "onboarding",
        "customer success", "cancellation", "churn rate"
    ]):
        return SupervisorRoutingDecision(
            context_summary="Customer churn mitigation, onboarding retention, and support ticket resolution",
            selected_specialists=["customer", "product", "cfo"],
            specialist_directives={
                "customer": "Analyze cancellation root causes, time-to-first-value friction, and support response latency.",
                "product": "Identify sticky workflows, feature utilization gaps, and UX stumbling blocks driving churn.",
                "cfo": "Quantify revenue drag from logo churn and calculate ROI of proactive customer success interventions."
            },
            reasoning="Retention requires deep customer relationship telemetry (Customer), product workflow stickiness (Product), and net revenue retention modeling (CFO).",
            source="deterministic_router"
        )

    # 6. Enterprise / Sales-Assisted Tier (Product + Growth + CFO)
    if any(k in q_lower for k in ["enterprise", "sales-assist", "annual contract", "soc2", "security tier"]):
        return SupervisorRoutingDecision(
            context_summary="Enterprise tier introduction, sales-assisted motion, and ACV expansion",
            selected_specialists=["product", "growth", "cfo"],
            specialist_directives={
                "product": "Define enterprise security, SSO, audit logs, and dedicated SLA packaging requirements.",
                "growth": "Evaluate inbound pipeline demand, sales demo conversion, and sales cycle duration.",
                "cfo": "Model ACV uplift, sales commission costs, and cash acceleration from upfront annual contracts."
            },
            reasoning="Enterprise motions demand product security packaging, enterprise sales funnel modeling, and annual cash flow evaluation.",
            source="deterministic_router"
        )

    # 7. Default Fallback: Full Board Cross-Functional Consensus (All 5 Specialists)
    return SupervisorRoutingDecision(
        context_summary=f"Comprehensive strategic inquiry: '{query[:80]}...'",
        selected_specialists=["cfo", "growth", "cto", "customer", "product"],
        specialist_directives={
            "cfo": "Evaluate financial health, runway preservation, and revenue impact.",
            "growth": "Examine user acquisition pace, channel dynamics, and conversion.",
            "cto": "Assess technical feasibility, infrastructure overhead, and scalability.",
            "customer": "Review user sentiment, support implications, and retention risks.",
            "product": "Analyze tier architecture, feature prioritization, and market fit."
        },
        reasoning="Broad strategic scope touches all key executive domains. Deploying full 5-specialist orchestration topology for holistic consensus.",
        source="deterministic_router"
    )


async def route_decision_specialists(
    query: str,
    company_data: Optional[Dict[str, Any]] = None
) -> SupervisorRoutingDecision:
    """
    Supervisor decision layer powered by Groq (LLMClient or direct Groq completion)
    with robust deterministic fallback in mock mode / when GROQ_API_KEY is unset.
    
    1. Extracts strategic context from the CEO/Boardroom query.
    2. Identifies relevant company telemetry.
    3. Selects the exact specialist agents needed for the orchestration topology.
    4. Generates tailored directives for each chosen specialist.
    """
    mode = os.getenv("LLM_MODE", "mock").lower().strip()
    groq_api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
    
    # If explicitly in mock mode or no Groq key available, run deterministic router
    if mode == "mock" or not groq_api_key:
        logger.info("Supervisor routing: using deterministic router (mode=%s, key_present=%s)", mode, bool(groq_api_key))
        return deterministic_supervisor_routing(query, company_data)

    # Prepare company telemetry summary
    fin = (company_data or {}).get("financials", {})
    funnel = (company_data or {}).get("funnel", {})
    infra = (company_data or {}).get("infrastructure", {})
    cust = (company_data or {}).get("customers", {})

    telemetry_brief = (
        f"MRR: ${fin.get('mrr', 110370):,.0f}, Runway: {fin.get('runway_months', 13.2)} mo, "
        f"Cash: ${fin.get('cash_balance', 1450000):,.0f}, "
        f"Monthly Visitors: {funnel.get('monthly_visitors', 65000):,}, "
        f"Monthly Cloud Infra: ${infra.get('monthly_cloud_cost', 14500):,.0f}, "
        f"Paying Customers: {cust.get('total_paying', 655):,}"
    )

    system_prompt = (
        "You are the Executive Supervisor of VentureTwin, an autonomous digital twin for high-growth SaaS CEOs.\n"
        "Your task is to analyze the CEO / Boardroom question and company telemetry, extract the strategic context, "
        "and decide which functional specialist agents must be activated in the multi-agent orchestration DAG.\n\n"
        "Available specialist agents:\n"
        "- cfo: Financial Analyst (runway, burn rate, gross margin, pricing floors, ARPU)\n"
        "- growth: Acquisition Strategist (top-of-funnel traffic, trial conversion, CAC, funnel velocity)\n"
        "- cto: Infrastructure Architect (cloud compute costs, server scaling, database load, latency)\n"
        "- customer: Retention & Success Specialist (churn rate, support ticket volume, CSAT, onboarding)\n"
        "- product: Packaging & Pricing Strategist (tier boundaries, feature gating, user experience, limits)\n\n"
        "Rules:\n"
        "1. Select between 2 and 5 specialist agents based on the query domains.\n"
        "2. Broad packaging overhauls (e.g. launching a free plan) require all 5 specialists.\n"
        "3. Focused questions (cloud infra, pricing changes, marketing CAC, churn) require only the 2 to 4 relevant specialists.\n"
        "4. Output strictly valid JSON matching this schema:\n"
        "{\n"
        '  "context_summary": "<brief summary of the question context>",\n'
        '  "selected_specialists": ["<agent1>", "<agent2>", ...],\n'
        '  "specialist_directives": {\n'
        '    "<agent1>": "<specific analysis directive>",\n'
        '    "<agent2>": "<specific analysis directive>"\n'
        "  },\n"
        '  "reasoning": "<executive rationale explaining agent selection>"\n'
        "}"
    )

    active_ctx = None
    try:
        from services.company_context_store import get_active_company_context
        active_ctx = get_active_company_context()
    except Exception:
        pass

    comp_name = (active_ctx or {}).get("company_name") or (company_data or {}).get("company_name", "the company")
    comp_desc = (active_ctx or {}).get("description") or (company_data or {}).get("tagline", "")
    comp_industry = (active_ctx or {}).get("industry") or "B2B SaaS"
    comp_model = (active_ctx or {}).get("business_model") or "Subscription"

    user_prompt = (
        f"Company: {comp_name} ({comp_industry}, {comp_model})\n"
        f"Strategic Overview: {comp_desc}\n\n"
        f"Boardroom Question: \"{query}\"\n\n"
        f"Company Telemetry:\n{telemetry_brief}\n\n"
        "Decide which specialist agents to activate in the orchestration topology and generate directives."
    )

    try:
        import httpx

        groq_base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        configured_model = os.getenv("GROQ_MODEL")
        candidate_models = [m for m in [
            configured_model,
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
            "llama-3.3-70b-versatile"
        ] if m]
        seen = set()
        models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]
        
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }

        data = None
        used_model = None
        async with httpx.AsyncClient(timeout=15.0) as client:
            for model_name in models_to_try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"}
                }
                res = await client.post(f"{groq_base_url}/chat/completions", json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    used_model = model_name
                    break
                elif res.status_code in [400, 404]:
                    continue
                else:
                    res.raise_for_status()

            if not data:
                raise RuntimeError("No Groq candidate models responded successfully.")
            raw_content = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_content)

            # Validate and normalize specialists
            raw_specs = parsed.get("selected_specialists", [])
            valid_specs = [s.lower().strip() for s in raw_specs if s.lower().strip() in ALL_SPECIALISTS]
            if len(valid_specs) < 2:
                # Guarantee at least 2 specialists
                valid_specs = [s for s in ALL_SPECIALISTS if s in valid_specs]
                for fallback_spec in ["cfo", "growth"]:
                    if fallback_spec not in valid_specs:
                        valid_specs.append(fallback_spec)

            # Sort specialists in canonical roster order
            sorted_specs = [s for s in ALL_SPECIALISTS if s in valid_specs]

            directives = parsed.get("specialist_directives", {})
            for spec in sorted_specs:
                if spec not in directives:
                    directives[spec] = f"Analyze {spec.upper()} domain metrics for: {query}"

            return SupervisorRoutingDecision(
                context_summary=parsed.get("context_summary", query),
                selected_specialists=sorted_specs,
                specialist_directives=directives,
                reasoning=parsed.get("reasoning", "Selected by Groq Supervisor based on boardroom query context."),
                source="groq"
            )

    except Exception as e:
        logger.warning("Groq supervisor routing failed (%s), engaging deterministic fallback: %s", type(e).__name__, e)
        fallback = deterministic_supervisor_routing(query, company_data)
        fallback.reasoning += f" (Autonomous fallback engaged: Groq routing offline)"
        return fallback
