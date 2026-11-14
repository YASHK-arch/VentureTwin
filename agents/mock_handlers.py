"""
Deterministic mock handlers for unit testing and offline demo fallback.
Provides structured responses for specialist agents and rebuttals using explicit agent_key routing.
Note: Mock mode contains illustrative hardcoded ranges for parameters not directly present in company telemetry.
"""
from typing import Type, TypeVar, Any, Dict, Optional
from pydantic import BaseModel
from state.schemas import AgentFindingDraft, DraftAssumption, Evidence, Rebuttal
from data.loader import load_company_data

T = TypeVar("T", bound=BaseModel)

def default_mock_handler(
    prompt: str,
    response_model: Type[T],
    metadata: Optional[Dict[str, Any]] = None
) -> T:
    if metadata is None or "agent_key" not in metadata:
        try:
            return response_model.model_validate({
                "greeting": "Fallback mock response",
                "model_name": "mock-fallback",
                "status": "ok",
                "verified": True
            })
        except Exception:
            raise KeyError(f"Mock mode requires 'agent_key' in metadata, received: {metadata}")

    agent_key = str(metadata["agent_key"]).lower()

    if response_model is AgentFindingDraft:
        return _generate_finding_draft(agent_key, prompt=prompt, metadata=metadata)  # type: ignore
    if response_model is Rebuttal:
        return _generate_rebuttal(agent_key, metadata)  # type: ignore

    # Fallback to model instantiation
    if response_model.__name__ in ["EchoProbe", "_ProbeSchema"]:
        return response_model.model_validate({
            "greeting": "Fallback mock response",
            "model_name": "mock-fallback",
            "status": "ok",
            "verified": True
        })
    return response_model.model_validate({})

def _generate_rebuttal(agent_key: str, metadata: Dict[str, Any]) -> Rebuttal:
    param = metadata.get("parameter", "parameter")
    return Rebuttal(
        agent=agent_key.upper(),
        parameter=param,
        stance="defend",
        updated_base=None,
        updated_low=None,
        updated_high=None,
        rationale=f"{agent_key.upper()} defends its baseline assumption for {param} based on operating constraints."
    )

def _generate_finding_draft(
    agent_key: str,
    prompt: str = "",
    metadata: Optional[Dict[str, Any]] = None
) -> AgentFindingDraft:
    data = load_company_data()
    fin = data["financials"]
    funnel = data["funnel"]
    infra = data["infrastructure"]
    cust = data["customers"]
    plans = cust.get("plans", [])

    # Identify domain from metadata or prompt
    meta = metadata or {}
    q_str = str(meta.get("question") or prompt or "").lower()
    dec_type = meta.get("decision_type") or ""

    is_max_expenditure = (
        dec_type == "max_expenditure" or
        any(k in q_str for k in ["maximum additional", "max additional", "max monthly expenditure", "maximum monthly expenditure", "maximum expenditure", "max expenditure"]) or
        ("afford" in q_str and any(k in q_str for k in ["spend", "expenditure", "burn"]) and any(k in q_str for k in ["max", "maximum", "how much"]))
    )
    is_support_hiring = (
        dec_type == "support_hiring" or
        (any(k in q_str for k in ["customer support", "support specialist", "support specialists", "support staff", "support employees", "support fte"]) and
         any(k in q_str for k in ["hire", "hiring", "recruit", "add"]) and not any(k in q_str for k in ["automation", "automate"]))
    )
    is_hiring_vs_automation = (
        dec_type == "hiring_vs_automation" or
        (("support" in q_str or "hire" in q_str) and any(k in q_str for k in ["automation", "ai support", "automate support", "ai automation"]))
    )
    is_spend_budget = (
        dec_type == "spend_budget" or
        (any(k in q_str for k in ["spend", "spending", "expenditure"]) and any(k in q_str for k in ["50,000", "50000", "30,000", "30000", "50k", "30k"]))
    )
    is_price_increase = (
        dec_type == "price_increase" or
        any(k in q_str for k in ["price", "raise", "increase price", "starter price", "rate hike", "pricing"])
    )
    is_enterprise = (
        dec_type == "enterprise_tier" or
        any(k in q_str for k in ["enterprise", "sla", "soc2", "dedicated"])
    )
    is_churn = (
        dec_type == "churn_reduction" or
        any(k in q_str for k in ["churn", "retention", "cancel", "health score", "nrr"])
    )
    is_m_and_a = (
        dec_type == "m_and_a_exit" or
        any(k in q_str for k in ["sell", "exit", "acquisition", "buyout", "merger", "acquire", "valuation"])
    )
    is_hiring = (
        dec_type == "hiring_headcount" or
        any(k in q_str for k in ["hire", "hiring", "headcount", "employee", "employees", "staff", "staffing", "payroll"])
    )

    runway = fin["runway_months"]
    cash = fin["cash_balance"]
    min_runway = fin.get("target_min_runway_months", 10.0)
    mrr = fin["mrr"]
    visitors = funnel["monthly_visitors"]
    trials = funnel["trial_signups"]
    cloud_cost = infra["monthly_cloud_cost"]
    paying = cust["total_paying"]
    starter_plan = next((p for p in plans if p.get("name") == "Starter"), None)
    starter_count = starter_plan.get("count", 450) if starter_plan else 450

    # =========================================================================
    # DOMAIN 0: STRATEGIC PROPOSAL / PERSONAL QUESTIONS (e.g. "Should I change my name to habibi for company strategy?")
    # =========================================================================
    if dec_type == "strategic_decision" and not any(k in q_str for k in ["free plan", "free tier", "freemium", "price", "enterprise", "churn"]):
        is_personal = any(k in q_str for k in ["my name", "name to", "habibi", "personal", "founder"])
        if is_personal:
            if agent_key == "cfo":
                claim = (
                    f"Changing your personal name has zero correlation with cash reserves (${cash:,.0f}) or our {runway:.1f}-month runway. "
                    "NimbusDesk requires focus on capital efficiency; personal naming actions are outside corporate operations."
                )
            elif agent_key == "growth":
                claim = (
                    f"A personal name change does not create an organic growth flywheel or accelerate acquisition beyond our current {visitors:,} monthly visitors. "
                    "Growth recommends rejecting personal naming proposals as a company strategy."
                )
            elif agent_key == "cto":
                claim = (
                    f"Changing your personal name has zero technical impact on cloud infrastructure (${cloud_cost:,.2f}/mo) or platform uptime. "
                    "CTO recommends rejecting non-technical distractions."
                )
            elif agent_key == "customer":
                claim = (
                    f"Customer satisfaction across our {paying} paying accounts depends on software reliability and support response, not personal naming changes. "
                    "Customer team recommends rejecting."
                )
            else:  # product
                claim = (
                    "Personal founder name changes have zero bearing on product packaging, roadmap features, or core tier gates. "
                    "Product team recommends rejecting."
                )

            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.cash_balance",
                        snippet=f"Baseline cash: ${cash:,.2f}, runway: {runway:.1f} months, paying accounts: {paying}."
                    )
                ],
                limitations=["Personal founder decisions have no operational telemetry."],
                confidence=0.95
            )

    # =========================================================================
    # DOMAIN MAX EXPENDITURE (e.g. "What is the maximum additional monthly expenditure...")
    # =========================================================================
    if is_max_expenditure and not (is_enterprise or is_churn or "free" in q_str):
        if agent_key == "cfo":
            claim = (
                f"NimbusDesk holds ${cash:,.0f} in cash with a current net burn of ${fin['monthly_burn_net']:,.0f}/mo ({runway:.1f} months runway). "
                f"To maintain at least {min_runway:.1f} months of runway, maximum allowable net burn is ${cash / min_runway:,.0f}/mo. "
                f"The maximum additional monthly expenditure NimbusDesk can afford is exactly $40,000/mo (${cash / min_runway:,.0f} - ${fin['monthly_burn_net']:,.0f})."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="paid_funnel_lift",
                        low=1.0,
                        base=1.0,
                        high=1.05,
                        unit="ratio",
                        basis="financials.mrr",
                        rationale="Preserves current baseline unit economics under calibrated budget cap"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.cash_balance",
                        snippet=f"Cash: ${cash:,.2f}, monthly net burn: ${fin['monthly_burn_net']:,.2f}, target min runway: {min_runway:.1f} mo."
                    )
                ],
                limitations=["Any expenditure above $40,000/mo will breach the 10.0-month runway constraint."],
                confidence=0.95
            )
        elif agent_key == "growth":
            claim = (
                "Growth confirms NimbusDesk can allocate up to $40,000/mo in additional growth and marketing investments "
                f"while strictly preserving the {min_runway:.1f}-month runway floor. Recommend allocating across paid acquisition and funnel optimization."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.monthly_visitors",
                        snippet=f"Monthly visitors: {visitors:,}."
                    )
                ],
                limitations=["Paid channel CAC must remain below $1,450."],
                confidence=0.85
            )
        elif agent_key == "cto":
            claim = (
                "From an infrastructure perspective, cloud infrastructure capacity can absorb up to $25,000/mo in additional compute "
                "and tooling expansions without architectural re-platforming. Note: this $25,000 is a technical infrastructure budget, "
                "within the overall company expenditure affordability limit of $40,000/mo."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Cloud spend: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["CTO figure represents departmental infrastructure budget allocation."],
                confidence=0.85
            )
        elif agent_key == "customer":
            claim = (
                f"Customer Success can deploy up to $40,000/mo in additional customer support staffing, tooling, and onboarding capacity "
                f"while maintaining the {min_runway:.1f}-month cash runway floor."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.total_paying",
                        snippet=f"Active paying accounts: {paying}."
                    )
                ],
                limitations=["Support hiring requires 4-week onboarding ramp."],
                confidence=0.85
            )
        elif agent_key == "product":
            claim = (
                f"Product team supports up to $40,000/mo in additional product engineering and packaging expenditure "
                f"while preserving the {min_runway:.1f}-month runway requirement."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.cash_balance",
                        snippet=f"Cash balance: ${cash:,.2f}."
                    )
                ],
                limitations=["Engineering roadmap prioritization must focus on core tier retention."],
                confidence=0.85
            )

    # =========================================================================
    # DOMAIN SUPPORT HIRING (e.g. "Should NimbusDesk hire two additional customer support specialists...")
    # =========================================================================
    if is_support_hiring and not (is_enterprise or is_churn or "free" in q_str):
        if agent_key == "cfo":
            claim = (
                "Existing support expenditure is $28,000/mo across 4 FTEs ($7,000/FTE/mo). Hiring 2 additional support specialists "
                f"adds $14,000/mo, increasing monthly net burn from ${fin['monthly_burn_net']:,.0f} to $139,000/mo. "
                f"With ${cash:,.0f} cash balance, projected runway is 11.87 months, which satisfies the {min_runway:.1f}-month safety threshold."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="paid_funnel_lift",
                        low=1.02,
                        base=1.05,
                        high=1.10,
                        unit="ratio",
                        basis="financials.mrr",
                        rationale="Customer onboarding retention lift from dedicated support capacity"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="support.monthly_support_cost",
                        snippet=f"Support cost: $28,000/mo across 4 FTEs ($7,000/FTE). Projected burn: $139,000/mo, runway: 11.87 months."
                    )
                ],
                limitations=["Assumes fully loaded employee cost of $7,000/mo per support specialist."],
                confidence=0.85
            )
        elif agent_key == "growth":
            claim = (
                "Higher support capacity protects customer trial onboarding and eliminates activation bottlenecks for new signups. "
                "Growth recommends proceeding with 2 support specialists."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.trial_signups",
                        snippet=f"Monthly trial signups: {trials}."
                    )
                ],
                limitations=["Support capacity should align with trial conversion velocity."],
                confidence=0.85
            )
        elif agent_key == "cto":
            claim = (
                "Engineering confirms technical onboarding for 2 support specialists is straightforward. "
                "Additionally, technical automation (AI ticket triage and self-service deflection) should be evaluated in parallel to compound support efficiency."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Cloud infrastructure baseline: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["Tooling licenses require standard SSO configuration."],
                confidence=0.85
            )
        elif agent_key == "customer":
            claim = (
                "Current team of 4 FTEs manages 1,200 tickets/mo (300 tickets/FTE, operating at 100% capacity). "
                "Hiring 2 additional specialists expands capacity to 1,800 tickets/mo (+600 tickets/mo), reducing ticket escalation risk "
                "and protecting customer CSAT under SLA."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="free_user_ticket_rate",
                        low=0.015,
                        base=0.020,
                        high=0.035,
                        unit="ratio",
                        basis="",
                        rationale="Target support capacity ratio maintained at <= 300 tickets/FTE"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="support.monthly_tickets",
                        snippet=f"Monthly tickets: 1,200 managed across 4 FTEs (300 tickets/FTE). New capacity: 1,800 tickets/mo."
                    )
                ],
                limitations=["Requires structured 2-week product training playbook."],
                confidence=0.85
            )
        elif agent_key == "product":
            claim = (
                "Product disagrees with adding $14,000/mo recurring payroll before addressing root-cause product friction. "
                "30% of incoming support tickets stem from repetitive onboarding and feature discovery friction. "
                "Recommends Strategy B: invest in AI Support Automation and self-service in-app guides ($3,500/mo) to deflect 360 tickets/mo at 75% lower recurring cost."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[
                    DraftAssumption(
                        name="usage_cap_infra_reduction",
                        low=0.20,
                        base=0.30,
                        high=0.45,
                        unit="rate",
                        basis="",
                        rationale="Estimated 30% ticket deflection via AI knowledge retrieval and self-service guides"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="support.monthly_tickets",
                        snippet="Support ticket analysis indicates 360 repetitive tier-1 inquiries."
                    )
                ],
                limitations=["Automation alternative requires 3 weeks engineering implementation."],
                confidence=0.85
            )

    # =========================================================================
    # DOMAIN FIXED SPEND BUDGET (e.g. $50,000 vs $30,000 spend)
    # =========================================================================
    if is_spend_budget and not (is_enterprise or is_churn or "free" in q_str):
        is_50k = any(k in q_str for k in ["50,000", "50000", "50k"])
        if is_50k:
            if agent_key == "cfo":
                claim = (
                    f"Spending an additional $50,000/mo increases monthly net burn from ${fin['monthly_burn_net']:,.0f} to $175,000/mo. "
                    f"At ${cash:,.0f} cash reserves, projected runway drops to 9.43 months ($1,650,000 / $175,000), which directly breaches "
                    f"the mandatory {min_runway:.1f}-month minimum runway requirement. Maximum affordable additional spend is $40,000/mo. CFO recommends reject."
                )
                return AgentFindingDraft(
                    claim=claim,
                    recommendation="reject",
                    assumptions=[],
                    evidence=[
                        Evidence(
                            source_type="company_data",
                            source_ref="financials.cash_balance",
                            snippet=f"Cash: ${cash:,.2f}, new burn: $175,000/mo, projected runway: 9.43 months, min constraint: {min_runway:.1f} mo."
                        )
                    ],
                    limitations=["Proposal violates minimum safety runway constraint."],
                    confidence=0.95
                )
            elif agent_key == "growth":
                claim = (
                    "While $50,000/mo would accelerate acquisition, burning cash below the 10.0-month runway threshold (to 9.43 months) "
                    "creates acute insolvency risk before series B. Recommend reducing proposed budget to <= $40,000/mo."
                )
                return AgentFindingDraft(claim=claim, recommendation="reject", assumptions=[], evidence=[], limitations=[], confidence=0.90)
            elif agent_key == "cto":
                claim = "Platform and infra scale does not justify taking runway below the 10.0-month constraint to 9.43 months. Recommend rejecting $50,000/mo expenditure."
                return AgentFindingDraft(claim=claim, recommendation="reject", assumptions=[], evidence=[], limitations=[], confidence=0.90)
            elif agent_key == "customer":
                claim = "Customer team advises against over-extending monthly burn to $175,000/mo when runway drops to 9.43 months."
                return AgentFindingDraft(claim=claim, recommendation="reject", assumptions=[], evidence=[], limitations=[], confidence=0.85)
            elif agent_key == "product":
                claim = "Product recommends rejecting $50,000/mo budget increase due to 9.43-month runway breach."
                return AgentFindingDraft(claim=claim, recommendation="reject", assumptions=[], evidence=[], limitations=[], confidence=0.85)
        else:  # $30k spend
            if agent_key == "cfo":
                claim = (
                    f"Spending an additional $30,000/mo increases monthly net burn from ${fin['monthly_burn_net']:,.0f} to $155,000/mo. "
                    f"At ${cash:,.0f} cash reserves, projected runway is 10.65 months ($1,650,000 / $155,000), which safely satisfies "
                    f"the {min_runway:.1f}-month minimum runway requirement. The proposal is financially affordable."
                )
                return AgentFindingDraft(
                    claim=claim,
                    recommendation="proceed",
                    assumptions=[],
                    evidence=[
                        Evidence(
                            source_type="company_data",
                            source_ref="financials.cash_balance",
                            snippet=f"Cash: ${cash:,.2f}, new burn: $155,000/mo, projected runway: 10.65 months, min constraint: {min_runway:.1f} mo."
                        )
                    ],
                    limitations=["Runway margin over 10.0-month floor is 0.65 months."],
                    confidence=0.95
                )
            elif agent_key == "growth":
                claim = "An additional $30,000/mo budget provides substantial growth leverage while keeping runway at 10.65 months above the 10.0-month floor. Growth recommends proceed."
                return AgentFindingDraft(claim=claim, recommendation="proceed", assumptions=[], evidence=[], limitations=[], confidence=0.90)
            elif agent_key == "cto":
                claim = "Infrastructure and technical scaling can absorb $30,000/mo while preserving 10.65 months of runway. CTO recommends proceed."
                return AgentFindingDraft(claim=claim, recommendation="proceed", assumptions=[], evidence=[], limitations=[], confidence=0.90)
            elif agent_key == "customer":
                claim = "Customer Success supports $30,000/mo expenditure with runway safely preserved at 10.65 months."
                return AgentFindingDraft(claim=claim, recommendation="proceed", assumptions=[], evidence=[], limitations=[], confidence=0.90)
            elif agent_key == "product":
                claim = "Product team supports $30,000/mo investment under 10.65-month runway safety."
                return AgentFindingDraft(claim=claim, recommendation="proceed", assumptions=[], evidence=[], limitations=[], confidence=0.90)

    # =========================================================================
    # DOMAIN HIRING VS AUTOMATION (e.g. "Should NimbusDesk hire support employees or invest in AI support automation?")
    # =========================================================================
    if is_hiring_vs_automation and not (is_enterprise or is_churn or "free" in q_str):
        if agent_key == "cfo":
            claim = (
                "CFO compares both options: Support Hiring (Strategy A) adds $14,000/mo ($139,000 net burn, 11.87 mo runway, 1,800 ticket capacity). "
                "AI Support Automation (Strategy B) adds $3,500/mo ($128,500 net burn, 12.84 mo runway, deflects 360 tickets/mo). "
                "Both are financially feasible under the 10.0-month runway constraint."
            )
            return AgentFindingDraft(claim=claim, recommendation="proceed_with_limits", assumptions=[], evidence=[], limitations=[], confidence=0.85)
        elif agent_key == "growth":
            claim = "Automation provides immediate 24/7 trial user responsiveness, while human specialists are needed for high-touch enterprise onboarding. Recommends a hybrid approach."
            return AgentFindingDraft(claim=claim, recommendation="proceed_with_limits", assumptions=[], evidence=[], limitations=[], confidence=0.80)
        elif agent_key == "cto":
            claim = "Engineering team can implement AI support automation (RAG-backed ticket deflection and automated triage) in 3 weeks at $3,500/mo tooling cost, deflecting ~30% of incoming tickets."
            return AgentFindingDraft(claim=claim, recommendation="proceed_with_limits", assumptions=[], evidence=[], limitations=[], confidence=0.90)
        elif agent_key == "customer":
            claim = "Customer team advocates for Support Hiring: enterprise customers require human touch, and complex technical tickets cannot be automated. Recommends hiring specialists as primary."
            return AgentFindingDraft(claim=claim, recommendation="proceed_with_limits", assumptions=[], evidence=[], limitations=[], confidence=0.85)
        elif agent_key == "product":
            claim = "Product advocates for AI Support Automation: repetitive questions (billing, password, basic setup) consume 400+ tickets/mo. Automating repetitive inquiries frees existing 4 FTEs to handle complex issues without adding $14k/mo payroll."
            return AgentFindingDraft(claim=claim, recommendation="proceed_with_limits", assumptions=[], evidence=[], limitations=[], confidence=0.90)

    # =========================================================================
    # DOMAIN M&A / EXIT (e.g. "Should I sell my company?")
    # =========================================================================
    if is_m_and_a and not (is_enterprise or is_churn or "free" in q_str):
        if agent_key == "cfo":
            claim = (
                f"NimbusDesk holds ${cash:,.0f} in cash reserves ({runway:.1f} months runway) and generates ${mrr:,.0f} MRR. "
                "Selling today commands a discounted early Series A multiple (~3-4x ARR, $4M-$5M); continuing independent scale "
                "to $2.5M ARR yields superior equity valuation. CFO advises Hold & Scale (Do Not Sell at current stage)."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.cash_balance",
                        snippet=f"Baseline cash reserves: ${cash:,.2f}, runway: {runway:.1f} months, MRR: ${mrr:,.2f}."
                    )
                ],
                limitations=["Assumes current organic conversion velocity holds."],
                confidence=0.95
            )
        elif agent_key == "growth":
            claim = (
                f"Top-of-funnel velocity of {visitors:,} monthly visitors represents strong compounding organic leverage. "
                "Selling now prematurely crystallizes equity before enterprise expansion. Growth recommends Hold & Scale."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.monthly_visitors",
                        snippet=f"Unique monthly traffic: {visitors:,} visitors."
                    )
                ],
                limitations=["Top-of-funnel conversion depends on continuous product optimization."],
                confidence=0.92
            )
        elif agent_key == "cto":
            claim = (
                f"Cloud infrastructure spend (${cloud_cost:,.0f}/mo) is highly efficient and architecture scales to 2,000+ accounts. "
                "Technical stability supports independent operations; CTO recommends Hold & Scale."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Cloud infrastructure baseline: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["Assumes compute workloads remain stable."],
                confidence=0.90
            )
        elif agent_key == "customer":
            claim = (
                f"Customer base of {paying} paying accounts exhibits healthy retention. "
                "M&A transitions trigger integration friction and customer churn; maintaining independent customer relationships is recommended."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.total_paying",
                        snippet=f"Total paying accounts: {paying}."
                    )
                ],
                limitations=["Feedback gathered from customer CSAT polls."],
                confidence=0.88
            )
        elif agent_key == "product":
            claim = (
                "The product roadmap has high-impact enterprise gating features scheduled for release; "
                "executing these features independently will significantly expand ARPU before considering an exit. Product recommends Hold & Scale."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="reject",
                assumptions=[],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.plans",
                        snippet="Monitored packaging tiers: Starter, Pro."
                    )
                ],
                limitations=["Roadmap delivery timeline assumes dedicated engineering focus."],
                confidence=0.90
            )

    # =========================================================================
    # DOMAIN HIRING / HEADCOUNT (e.g. "how many percent of employees should we hire?")
    # =========================================================================
    if is_hiring and not (is_enterprise or is_churn or "free" in q_str or is_m_and_a):
        if agent_key == "cfo":
            claim = (
                f"With ${cash:,.0f} in cash reserves and {runway:.1f} months runway, NimbusDesk can safely support "
                f"a calibrated 10%–15% headcount expansion (adding 1–2 strategic roles, ~$14k/mo incremental payroll) "
                f"while preserving an 11.8-month runway buffer well above the {min_runway:.1f}-month safety floor."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="paid_funnel_lift",
                        low=1.05,
                        base=1.14,
                        high=1.22,
                        unit="ratio",
                        basis="financials.mrr",
                        rationale="Productivity and sales capacity expansion from key strategic hires"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.cash_balance",
                        snippet=f"Cash: ${cash:,.2f}, runway: {runway:.1f} months, safety floor: {min_runway:.1f} mo."
                    )
                ],
                limitations=["Hiring beyond 20% headcount breaches the 10.0-month runway constraint."],
                confidence=0.88
            )
        elif agent_key == "growth":
            claim = (
                f"Top-of-funnel traffic of {visitors:,} monthly visitors converts at healthy rates but requires "
                "1 dedicated Growth Engineer to optimize trial onboarding. Growth recommends proceeding with calibrated 10%–15% headcount growth."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="free_to_paid_conversion",
                        low=0.020,
                        base=0.028,
                        high=0.038,
                        unit="rate",
                        basis="",
                        rationale="Conversion lift from dedicated growth engineering experiments"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.monthly_visitors",
                        snippet=f"Acquisition velocity: {visitors:,} visitors monthly."
                    )
                ],
                limitations=["Onboarding new hire requires a 4-week ramp period."],
                confidence=0.85
            )
        elif agent_key == "cto":
            claim = (
                f"Infrastructure spend (${cloud_cost:,.0f}/mo) is stable. Adding 1 platform/infrastructure engineer "
                "(10% headcount expansion) accelerates multi-tenant DB optimization and enterprise SLA readiness. CTO recommends proceeding."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="usage_cap_infra_reduction",
                        low=0.15,
                        base=0.25,
                        high=0.35,
                        unit="rate",
                        basis="infrastructure.monthly_cloud_cost",
                        rationale="Cloud efficiency and indexing improvements delivered by platform engineer"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Cloud infrastructure baseline: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["Requires candidate with PostgreSQL and Kubernetes expertise."],
                confidence=0.86
            )
        elif agent_key == "customer":
            claim = (
                f"Customer base of {paying} paying accounts is managed by support. Recommends adding 1 Customer Success Manager (CSM) "
                "once paying customer count crosses 700 to maintain support ticket resolution under SLA."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="free_user_ticket_rate",
                        low=0.010,
                        base=0.020,
                        high=0.035,
                        unit="ratio",
                        basis="",
                        rationale="Support load stabilization through proactive customer onboarding"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.total_paying",
                        snippet=f"Active paying accounts: {paying}."
                    )
                ],
                limitations=["Support ticket volume tracks paying customer expansion."],
                confidence=0.82
            )
        elif agent_key == "product":
            claim = (
                "Engineering bandwidth is currently allocated to maintenance; adding 1 full-stack product engineer "
                "allows timely execution of enterprise tier packaging. Product recommends proceeding."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="cap_conversion_uplift",
                        low=0.08,
                        base=0.15,
                        high=0.25,
                        unit="rate",
                        basis="",
                        rationale="Accelerated feature delivery driving higher account conversion"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.plans",
                        snippet="Plans monitored: Starter, Pro."
                    )
                ],
                limitations=["Requires clear sprint prioritisation."],
                confidence=0.84
            )

    # =========================================================================
    # DOMAIN 1: PRICE INCREASE (e.g. "Should we raise Starter price by 20%?")
    # =========================================================================
    if is_price_increase and not (is_enterprise or is_churn or "free" in q_str):
        if agent_key == "cfo":
            claim = (
                f"Starter tier is currently $79/mo across {starter_count} accounts (${starter_count * 79:,.0f}/mo MRR). "
                f"A 20% increase to $95/mo generates +$7,110/mo MRR (+$85k/yr) with {runway:.1f} months runway, "
                f"provided Starter cohort churn stays below 4.2%/mo."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="paid_funnel_lift",
                        low=1.02,
                        base=1.08,
                        high=1.15,
                        unit="ratio",
                        basis="financials.mrr",
                        rationale="Net revenue expansion from higher Starter and blended ARPU"
                    ),
                    DraftAssumption(
                        name="paid_to_free_cannibalization",
                        low=0.02,
                        base=0.04,
                        high=0.07,
                        unit="rate",
                        basis="",
                        rationale="Potential downgrade or churn elasticity among price-sensitive accounts"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.mrr",
                        snippet=f"Baseline MRR: ${mrr:,.2f}, cash runway: {runway:.1f} months."
                    )
                ],
                limitations=["Assumes annual contract billing option softens monthly churn."],
                confidence=0.86
            )

        elif agent_key == "growth":
            claim = (
                f"Top-of-funnel velocity of {visitors:,} monthly visitors will absorb a Starter increase from $79 to $95 "
                f"with less than 6% drop in trial conversion if Pro tier ($199) gap is preserved."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="free_to_paid_conversion",
                        low=0.018,
                        base=0.024,
                        high=0.032,
                        unit="rate",
                        basis="",
                        rationale="Projected trial-to-paid conversion elasticity under $95/mo Starter pricing"
                    ),
                    DraftAssumption(
                        name="cap_conversion_uplift",
                        low=0.08,
                        base=0.14,
                        high=0.22,
                        unit="rate",
                        basis="",
                        rationale="Conversion uplift from grandfathered promotional urgency"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.monthly_visitors",
                        snippet=f"Traffic velocity: {visitors:,} visitors with {trials} trial starts."
                    )
                ],
                limitations=["Requires clear value messaging on pricing page."],
                confidence=0.80
            )

        elif agent_key == "cto":
            claim = (
                f"Infrastructure spend of ${cloud_cost:,.0f}/mo has zero marginal cost impact from price changes; "
                f"higher ARPU directly expands server gross margin from 68% to 73%."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="usage_cap_infra_reduction",
                        low=0.20,
                        base=0.32,
                        high=0.45,
                        unit="rate",
                        basis="infrastructure.monthly_cloud_cost",
                        rationale="Gross margin efficiency buffer gained from higher per-account revenue"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Fixed cloud infrastructure baseline: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["Assumes compute workloads remain stable."],
                confidence=0.88
            )

        elif agent_key == "customer":
            claim = (
                f"Existing Starter cohort ({starter_count} accounts) has 2.1% baseline churn. "
                f"A 20% price hike without grandfathering risks customer resistance and an estimated 1.5-3.0% churn uptick; "
                f"grandfathering existing accounts for 6 months is recommended."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="paid_to_free_cannibalization",
                        low=0.03,
                        base=0.06,
                        high=0.10,
                        unit="rate",
                        basis="",
                        rationale="Churn and downgrade sensitivity from existing Starter accounts"
                    ),
                    DraftAssumption(
                        name="free_user_ticket_rate",
                        low=0.015,
                        base=0.030,
                        high=0.055,
                        unit="ratio",
                        basis="",
                        rationale="Temporary support ticket increase during pricing migration"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.total_paying",
                        snippet=f"Total paying accounts: {paying}, including {starter_count} on Starter."
                    )
                ],
                limitations=["Feedback gathered from quarterly customer CSAT polls."],
                confidence=0.76
            )

        elif agent_key == "product":
            claim = (
                "Pairing a 20% Starter price adjustment with expanded feature limits (e.g. automated reporting, extra seat) "
                "softens churn impact and improves perceived value."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="activation_drop_from_gating",
                        low=0.04,
                        base=0.08,
                        high=0.14,
                        unit="rate",
                        basis="",
                        rationale="Slight friction during new tier boundary introduction"
                    ),
                    DraftAssumption(
                        name="cap_conversion_uplift",
                        low=0.05,
                        base=0.12,
                        high=0.20,
                        unit="rate",
                        basis="",
                        rationale="Incentive to upgrade to Pro tier ($199) when Starter price gap closes"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.plans",
                        snippet="Monitored packaging tiers: Starter ($79), Pro ($199)."
                    )
                ],
                limitations=["Requires product packaging UI changes in billing portal."],
                confidence=0.82
            )

    # =========================================================================
    # DOMAIN 2: ENTERPRISE TIER (e.g. "Can we introduce an enterprise tier with custom SLAs?")
    # =========================================================================
    elif is_enterprise and not (is_churn or "free" in q_str):
        if agent_key == "cfo":
            claim = (
                f"NimbusDesk currently lacks high-tier ACV. An Enterprise tier ($1,500-$3,500/mo) "
                f"with annual upfront billing accelerates cash collection and extends runway beyond 18 months."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="paid_funnel_lift",
                        low=1.12,
                        base=1.24,
                        high=1.40,
                        unit="ratio",
                        basis="financials.cash_balance",
                        rationale="Cash collection velocity and blended ACV expansion from annual contracts"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.cash_balance",
                        snippet=f"Cash reserves: ${cash:,.2f}, baseline runway: {runway:.1f} months."
                    )
                ],
                limitations=["Requires establishing enterprise billing receivables and contract paper."],
                confidence=0.85
            )

        elif agent_key == "growth":
            claim = (
                f"Inbound requests from mid-market teams can convert 15-25 enterprise accounts in year 1, "
                f"generating $360k+ in high-margin ARR from current organic reach."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="monthly_free_signups",
                        low=3000.0,
                        base=4200.0,
                        high=5800.0,
                        unit="users/month",
                        basis="",
                        rationale="Enterprise sales lead generation from high-intent inbound visitors"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.monthly_visitors",
                        snippet=f"Organic traffic: {visitors:,} visitors monthly."
                    )
                ],
                limitations=["Requires sales-assisted lead routing."],
                confidence=0.79
            )

        elif agent_key == "cto":
            claim = (
                f"Enterprise SLAs require 99.99% uptime, dedicated database instances, and audit logging, "
                f"which adds approximately $2,800/mo to cloud baseline."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="infra_cost_per_free_user",
                        low=0.80,
                        base=1.35,
                        high=2.10,
                        unit="USD/user/month",
                        basis="infrastructure.monthly_cloud_cost",
                        rationale="Dedicated tenant isolation and VPC peering infrastructure cost"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Current infrastructure spend: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["Requires SOC2 compliance audit readiness."],
                confidence=0.84
            )

        elif agent_key == "customer":
            claim = (
                "Enterprise customers require high-touch CSM support (1 FTE per 25 enterprise accounts) "
                "and custom security onboarding playbooks."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed_with_limits",
                assumptions=[
                    DraftAssumption(
                        name="free_user_ticket_rate",
                        low=0.020,
                        base=0.040,
                        high=0.075,
                        unit="ratio",
                        basis="",
                        rationale="High-touch SLA response and onboarding support overhead"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.total_paying",
                        snippet=f"Current customer base: {paying} accounts managed by support team."
                    )
                ],
                limitations=["Requires hiring senior Solutions Architects for deployment."],
                confidence=0.77
            )

        elif agent_key == "product":
            claim = (
                "Package enterprise with SAML/SSO, role-based access control (RBAC), and SOC2 audit logs "
                "to create a strong boundary above Pro ($199/mo)."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="cap_conversion_uplift",
                        low=0.10,
                        base=0.20,
                        high=0.32,
                        unit="rate",
                        basis="",
                        rationale="Premium conversion velocity for security and compliance features"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.plans",
                        snippet="Existing plans: Starter, Pro."
                    )
                ],
                limitations=["Requires developing enterprise admin console."],
                confidence=0.83
            )

    # =========================================================================
    # DOMAIN 3: CHURN REDUCTION (e.g. "How do we reduce customer churn and preserve runway?")
    # =========================================================================
    elif is_churn and not ("free" in q_str):
        if agent_key == "cfo":
            claim = (
                f"At ${mrr:,.0f} MRR and 2.1% monthly churn, NimbusDesk loses ~$2,317 in recurring revenue monthly. "
                f"Reducing churn to 1.4% preserves $48,000 in cumulative cash reserves over 12 months."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="paid_to_free_cannibalization",
                        low=0.015,
                        base=0.030,
                        high=0.055,
                        unit="rate",
                        basis="financials.mrr",
                        rationale="Reduced customer attrition and preserved net recurring revenue"
                    ),
                    DraftAssumption(
                        name="paid_funnel_lift",
                        low=1.04,
                        base=1.10,
                        high=1.20,
                        unit="ratio",
                        basis="",
                        rationale="Compounded retention lift on monthly recurring cash flow"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="financials.mrr",
                        snippet=f"Current MRR: ${mrr:,.2f}, runway: {runway:.1f} months."
                    )
                ],
                limitations=["Assumes gross margin remains above 65% with retention investments."],
                confidence=0.87
            )

        elif agent_key == "growth":
            claim = (
                "Retaining customers longer raises LTV from $4,850 to $6,800, allowing higher payback flexibility "
                "and lifting Net Revenue Retention to 110%."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="free_to_paid_conversion",
                        low=0.020,
                        base=0.030,
                        high=0.045,
                        unit="rate",
                        basis="",
                        rationale="Higher NPS and customer advocacy driving organic referrals"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="funnel.monthly_visitors",
                        snippet=f"Acquisition velocity: {visitors:,} visitors monthly."
                    )
                ],
                limitations=["LTV expansion takes 6-9 months to fully materialize."],
                confidence=0.81
            )

        elif agent_key == "cto":
            claim = (
                f"Telemetry analysis shows platform latency spikes correlate with churn events; "
                f"investing in database caching and API latency reductions directly eliminates technical drop-offs."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="usage_cap_infra_reduction",
                        low=0.15,
                        base=0.28,
                        high=0.40,
                        unit="rate",
                        basis="infrastructure.monthly_cloud_cost",
                        rationale="Infrastructure efficiency and query optimization reducing compute burn"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="infrastructure.monthly_cloud_cost",
                        snippet=f"Cloud infrastructure baseline: ${cloud_cost:,.2f}/mo."
                    )
                ],
                limitations=["Requires 3-week engineering sprint for query indexing."],
                confidence=0.86
            )

        elif agent_key == "customer":
            claim = (
                "45% of churned accounts had zero support tickets in the 30 days prior to cancellation; "
                "proactive customer health alerts and check-ins will prevent silent cancellations."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="free_user_ticket_rate",
                        low=0.012,
                        base=0.022,
                        high=0.038,
                        unit="ratio",
                        basis="",
                        rationale="Targeted proactive health check-ins reduce emergency ticket escalation"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.total_paying",
                        snippet=f"Active paying accounts: {paying} monitored by customer success."
                    )
                ],
                limitations=["Requires setting up automated product usage telemetry alerts."],
                confidence=0.83
            )

        elif agent_key == "product":
            claim = (
                "Simplifying initial workflow onboarding and adding in-app feature checklists "
                "reduces time-to-first-value from 14 days to 4 days, locking in user habits."
            )
            return AgentFindingDraft(
                claim=claim,
                recommendation="proceed",
                assumptions=[
                    DraftAssumption(
                        name="activation_drop_from_gating",
                        low=0.03,
                        base=0.06,
                        high=0.12,
                        unit="rate",
                        basis="",
                        rationale="Minimizing activation friction to maximize early feature adoption"
                    ),
                    DraftAssumption(
                        name="cap_conversion_uplift",
                        low=0.06,
                        base=0.14,
                        high=0.24,
                        unit="rate",
                        basis="",
                        rationale="In-app milestone triggers driving engagement and renewal commitment"
                    )
                ],
                evidence=[
                    Evidence(
                        source_type="company_data",
                        source_ref="customers.plans",
                        snippet="Monitored packaging tiers: Starter, Pro."
                    )
                ],
                limitations=["Requires redesign of onboarding wizard."],
                confidence=0.80
            )

    # =========================================================================
    # DOMAIN 4: FREEMIUM / FREE PLAN (Default Baseline)
    # =========================================================================
    if agent_key == "cfo":
        is_constrained = runway < min_runway or cash < 500000
        rec = "reject" if is_constrained else "proceed_with_limits"
        claim = (
            f"Runway is {runway:.1f} months (${cash:,.0f} cash reserves). Free tier without strict limits "
            f"risks compressing runway below the {min_runway:.1f}-month safety floor."
        )
        return AgentFindingDraft(
            claim=claim,
            recommendation=rec,
            assumptions=[
                DraftAssumption(
                    name="free_to_paid_conversion",
                    low=0.010,
                    base=0.015,
                    high=0.022,
                    unit="rate",
                    basis="",
                    rationale="Conservative freemium cohort conversion rate to safeguard runway"
                )
            ],
            evidence=[
                Evidence(
                    source_type="company_data",
                    source_ref="financials.cash_balance",
                    snippet=f"Cash balance: ${cash:,.2f}, runway: {runway:.1f} months."
                )
            ],
            limitations=["Assumes baseline fixed operating expenses."],
            confidence=0.82
        )

    elif agent_key == "growth":
        return AgentFindingDraft(
            claim=f"Top-of-funnel velocity of {visitors:,} monthly visitors can generate self-serve expansion if trial barriers are removed.",
            recommendation="proceed",
            assumptions=[
                DraftAssumption(
                    name="free_to_paid_conversion",
                    low=0.025,
                    base=0.035,
                    high=0.050,
                    unit="rate",
                    basis="b2b_saas_freemium_conversion",
                    rationale="Benchmark self-serve freemium conversion rate for B2B tools"
                ),
                DraftAssumption(
                    name="monthly_free_signups",
                    low=2500.0,
                    base=3800.0,
                    high=5200.0,
                    unit="users/month",
                    basis="",
                    rationale="Projected signup volume from existing organic site traffic"
                )
            ],
            evidence=[
                Evidence(
                    source_type="company_data",
                    source_ref="funnel.monthly_visitors",
                    snippet=f"Unique monthly traffic: {visitors:,} visitors with {trials} trial starts."
                )
            ],
            limitations=["Requires self-serve onboarding flow."],
            confidence=0.78
        )

    elif agent_key == "cto":
        per_free = infra.get("infra_cost_per_free_user_estimate", 1.15)
        return AgentFindingDraft(
            claim=f"Current infrastructure spend of ${cloud_cost:,.0f}/mo can accommodate free accounts if database storage and API usage are strictly capped.",
            recommendation="proceed_with_limits",
            assumptions=[
                DraftAssumption(
                    name="infra_cost_per_free_user",
                    low=0.75,
                    base=per_free,
                    high=1.85,
                    unit="USD/user/month",
                    basis="infrastructure.infra_cost_per_free_user_estimate",
                    rationale="Marginal compute and multi-tenant database cost per active account"
                ),
                DraftAssumption(
                    name="usage_cap_infra_reduction",
                    low=0.20,
                    base=0.35,
                    high=0.50,
                    unit="rate",
                    basis="",
                    rationale="Infrastructure savings enabled by rate-limiting free tier compute"
                )
            ],
            evidence=[
                Evidence(
                    source_type="company_data",
                    source_ref="infrastructure.monthly_cloud_cost",
                    snippet=f"Baseline cloud compute cost: ${cloud_cost:,.2f}/mo."
                )
            ],
            limitations=["Requires automated Redis-backed quota enforcement."],
            confidence=0.85
        )

    elif agent_key == "customer":
        claim_text = (
            f"The Starter tier with {starter_count} accounts requires strict feature boundaries to avoid cannibalization."
            if starter_count is not None else
            f"Total paying customer base of {paying} requires strict feature boundaries to avoid cannibalization."
        )
        return AgentFindingDraft(
            claim=claim_text,
            recommendation="proceed_with_limits",
            assumptions=[
                DraftAssumption(
                    name="paid_to_free_cannibalization",
                    low=0.04,
                    base=0.08,
                    high=0.15,
                    unit="rate",
                    basis="",
                    rationale="Estimated fraction of potential Starter prospects settling for free"
                ),
                DraftAssumption(
                    name="usage_cap_cannibalization_reduction",
                    low=0.30,
                    base=0.50,
                    high=0.70,
                    unit="rate",
                    basis="",
                    rationale="Cannibalization reduction by withholding team seats from free tier"
                )
            ],
            evidence=[
                Evidence(
                    source_type="company_data",
                    source_ref="customers.total_paying",
                    snippet=f"Total active paying customers: {paying} across plans."
                )
            ],
            limitations=["Sample based on past Starter onboarding feedback."],
            confidence=0.72
        )

    elif agent_key == "product":
        plans = cust.get("plans", [])
        plan_names = ", ".join(p["name"] for p in plans) if plans else "existing tiers"
        return AgentFindingDraft(
            claim="Usage ceilings create a natural upgrade catalyst when users reach productivity scale.",
            recommendation="proceed_with_limits",
            assumptions=[
                DraftAssumption(
                    name="activation_drop_from_gating",
                    low=0.05,
                    base=0.10,
                    high=0.20,
                    unit="rate",
                    basis="",
                    rationale="Friction caused by usage limits on free tier"
                ),
                DraftAssumption(
                    name="cap_conversion_uplift",
                    low=0.05,
                    base=0.15,
                    high=0.25,
                    unit="rate",
                    basis="",
                    rationale="Conversion velocity increase upon reaching usage caps"
                )
            ],
            evidence=[
                Evidence(
                    source_type="company_data",
                    source_ref="customers.plans",
                    snippet=f"Monitored feature plans: {plan_names}."
                )
            ],
            limitations=["Requires clean in-app upgrade triggers."],
            confidence=0.80
        )

    raise KeyError(f"Unknown agent_key for mock draft: {agent_key}")
