import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal

# Load local .env into os.environ if present (setdefault so caller env takes precedence)
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response, Depends, Cookie, Header
from fastapi.responses import StreamingResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api import auth

from services.company_extractor import (
    extract_company_context_from_markdown,
    ALL_FIELDS,
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    RawExtractedCompanyContext,
    ExtractionResult
)
from services.website_scraper import (
    enrich_company_context_from_website,
    WebsiteScrapeError
)
from services.company_context_store import (
    init_company_context_db,
    save_company_context,
    get_active_company_context,
    list_company_contexts,
    get_company_context_by_id,
    delete_company_context
)
from services.agent_chat import (
    chat_with_agent,
    AgentChatRequest,
    AgentChatResponse,
    AGENT_META_MAP
)

from data.loader import get_company_snapshot, load_company_data, load_seeded_decisions
from state.schemas import Decision, Report, DecisionRecord, Event
from state.shared_state import WorkflowState
from state.event_bus import EventBus
from orchestrator.parser import parse_decision_query
from orchestrator.supervisor import Supervisor
from orchestrator.checkpointer import SQLiteCheckpointer
from integrations.api_routes import router as integrations_router

app = FastAPI(
    title="VentureTwin API",
    description="Operational Digital Twin & AI Flight Simulator for SaaS CEOs",
    version="0.1.0"
)

app.include_router(integrations_router)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:8000,http://127.0.0.1:5173,http://localhost:3000"
cors_origins_env = os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session stores for active decisions
active_workflows: Dict[str, WorkflowState] = {}
active_supervisors: Dict[str, Supervisor] = {}
decision_records_store: List[Dict[str, Any]] = []

class HealthStatus(BaseModel):
    status: str
    version: str
    llm_mode: str
    provider: str
    model: str
    probe_latency_ms: Optional[float] = None

class FailureInjectionRequest(BaseModel):
    agent: str
    mode: Literal["timeout", "exception", "bad_output", "heal"]
    persist: bool = False
    fail_attempts: int = 3

class DecisionRequest(BaseModel):
    query: str
    constraints: Optional[Dict[str, Any]] = None
    injected_failure: Optional[FailureInjectionRequest] = None
    selected_specialists: Optional[List[str]] = None

class RoutingRequest(BaseModel):
    query: str
    company_id: Optional[str] = None

class ApprovalRequest(BaseModel):
    action: Literal["approve", "reject", "request_changes"]
    notes: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class ForgotPasswordRequest(BaseModel):
    email: str

class MarkdownFilePayload(BaseModel):
    filename: str
    content: str

class ExtractCompanyContextRequest(BaseModel):
    files: List[MarkdownFilePayload]

class ScrapeWebsiteRequest(BaseModel):
    url: str

class CompanyContextPayload(BaseModel):
    id: Optional[str] = None
    company_name: str
    industry: str
    business_model: str
    description: str
    products_services: str
    target_customers: str
    revenue_model: str
    geographic_presence: Optional[str] = ""
    stage: str
    strategic_goals: str
    major_challenges: Optional[str] = ""
    key_competitors: Optional[str] = ""
    website_url: Optional[str] = ""
    provenance: Optional[Dict[str, Any]] = None
    uploaded_documents: Optional[List[Dict[str, Any]]] = None

def extract_session_token(request: Request) -> Optional[str]:
    token = request.cookies.get("vt_session")
    if token:
        return token
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return None

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = extract_session_token(request)
    if not token:
        return None
    return auth.get_session_user(token)

def require_current_user(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required or session expired.")
    return user

@app.get("/")
async def root():
    dist_index = os.path.join(os.path.dirname(__file__), "..", "ui", "dist", "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    return {
        "name": "VentureTwin API",
        "description": "SwarmFlow Multi-Agent Task Coordination Engine",
        "status": "healthy"
    }

# Mount static frontend assets if available
dist_assets = os.path.join(os.path.dirname(__file__), "..", "ui", "dist", "assets")
if os.path.exists(dist_assets):
    app.mount("/assets", StaticFiles(directory=dist_assets), name="assets")

dist_agents = os.path.join(os.path.dirname(__file__), "..", "ui", "dist", "agents")
public_agents = os.path.join(os.path.dirname(__file__), "..", "ui", "public", "agents")
if os.path.exists(dist_agents):
    app.mount("/agents", StaticFiles(directory=dist_agents), name="agents")
elif os.path.exists(public_agents):
    app.mount("/agents", StaticFiles(directory=public_agents), name="agents")

@app.get("/api/health", response_model=HealthStatus)
async def health(probe: bool = False):
    import time
    llm_mode = os.getenv("LLM_MODE", "mock").lower().strip()
    provider = os.getenv("LLM_PROVIDER", "mock").lower().strip()
    model = (os.getenv("LLM_MODEL") or "mock-agent-v1").strip()
    probe_latency: Optional[float] = None
    
    if llm_mode in ["real", "record"]:
        if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="ConfigurationError: LLM_MODE is real/record and provider is gemini but GEMINI_API_KEY is not set."
            )
        elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="ConfigurationError: LLM_MODE is real/record and provider is openai but OPENAI_API_KEY is not set."
            )
        elif provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="ConfigurationError: LLM_MODE is real/record and provider is anthropic but ANTHROPIC_API_KEY is not set."
            )
        elif provider == "cerebras" and not (os.getenv("CEREBRAS_API_KEY") or os.getenv("LLM_API_KEY")):
            raise HTTPException(
                status_code=500,
                detail="ConfigurationError: LLM_MODE is real/record and provider is cerebras but CEREBRAS_API_KEY is not set."
            )
        elif provider == "groq" and not (os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")):
            raise HTTPException(
                status_code=500,
                detail="ConfigurationError: LLM_MODE is real/record and provider is groq but GROQ_API_KEY is not set."
            )
        elif provider == "openai_compatible" and not (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")):
            raise HTTPException(
                status_code=500,
                detail="ConfigurationError: LLM_MODE is real/record and provider is openai_compatible but LLM_API_KEY is not set."
            )

        if probe:
            try:
                from agents.llm_client import LLMClient
                from pydantic import BaseModel
                class _ProbeSchema(BaseModel):
                    status: str
                probe_client = LLMClient(mode=llm_mode, provider=provider, model=model)
                t0 = time.time()
                await probe_client.call('Return JSON: {"status": "ok"}', _ProbeSchema)
                probe_latency = round((time.time() - t0) * 1000, 2)
            except Exception as probe_err:
                raise HTTPException(status_code=500, detail=f"LLM probe failed: {probe_err}")
            
    return HealthStatus(
        status="ok",
        version="0.1.0",
        llm_mode=llm_mode,
        provider=provider,
        model=model,
        probe_latency_ms=probe_latency
    )

@app.get("/api/company")
async def get_company():
    """Returns the company snapshot for NimbusDesk with synthetic data badge."""
    return get_company_snapshot()

@app.post("/api/company/extract")
async def extract_company_context(req: ExtractCompanyContextRequest):
    """Parses uploaded markdown files and extracts structured company context using LLM or heuristic fallback."""
    files_data = [{"filename": f.filename, "content": f.content} for f in req.files]
    result = await extract_company_context_from_markdown(files_data)
    return result.model_dump()

@app.post("/api/company/scrape-website")
async def scrape_company_website(req: ScrapeWebsiteRequest):
    """Scrapes a public corporate website and enriches company context fields."""
    try:
        result = await enrich_company_context_from_website(req.url)
        return result.model_dump()
    except WebsiteScrapeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scrape website: {e}")

@app.post("/api/company/context")
async def save_context(req: CompanyContextPayload, request: Request):
    """Saves or updates a company context profile in SQLite database."""
    required = [
        ("company_name", req.company_name),
        ("industry", req.industry),
        ("business_model", req.business_model),
        ("description", req.description),
        ("products_services", req.products_services),
        ("target_customers", req.target_customers),
        ("revenue_model", req.revenue_model),
        ("stage", req.stage),
        ("strategic_goals", req.strategic_goals),
    ]
    missing = [name for name, val in required if not val or not str(val).strip()]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required company context fields: {', '.join(missing)}"
        )
    user = get_current_user(request)
    user_id = user["id"] if user else None
    saved = save_company_context(req.model_dump(), user_id=user_id)
    return {"status": "saved", "context": saved}

@app.get("/api/company/context")
async def get_active_context(request: Request):
    """Returns the active company context profile."""
    user = get_current_user(request)
    user_id = user["id"] if user else None
    active = get_active_company_context(user_id=user_id)
    return {"active": active is not None, "context": active}

@app.get("/api/company/contexts")
async def list_contexts(request: Request):
    """Returns all company context profiles (multi-profile support)."""
    user = get_current_user(request)
    user_id = user["id"] if user else None
    contexts = list_company_contexts(user_id=user_id)
    return {"contexts": contexts}

@app.delete("/api/company/context/{context_id}")
async def delete_context(context_id: str):
    """Deletes a company context profile."""
    deleted = delete_company_context(context_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Company context profile not found.")
    return {"status": "deleted", "id": context_id}

@app.post("/api/agents/chat", response_model=AgentChatResponse)
async def agent_chat_endpoint(req: AgentChatRequest, request: Request):
    """Executes a direct 1-on-1 dialogue with a specific executive agent."""
    if req.agent_key.lower().strip() not in AGENT_META_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent '{req.agent_key}'. Available agents: {list(AGENT_META_MAP.keys())}"
        )
    user = get_current_user(request)
    user_id = user["id"] if user else None
    response = await chat_with_agent(
        agent_key=req.agent_key,
        message=req.message,
        history=req.history,
        user_id=user_id
    )
    return response

@app.post("/api/orchestration/route")
async def route_orchestration(req: RoutingRequest):
    """
    Extracts strategic context from boardroom question and uses Groq layer
    (with deterministic resilience fallback) to decide active specialist agents
    and directives for the orchestration topology.
    """
    from services.supervisor_groq import route_decision_specialists
    company_data = load_company_data()
    routing = await route_decision_specialists(req.query, company_data=company_data)
    return routing.model_dump()

@app.post("/api/decisions")
async def submit_decision(req: DecisionRequest, background_tasks: BackgroundTasks):
    """Submits a strategic decision query and launches the multi-agent workflow."""
    decision = parse_decision_query(req.query, req.constraints, allow_all=True)
    if decision.type == "unsupported":
        raise HTTPException(
            status_code=400,
            detail=decision.objective
        )
    if decision.type == "ambiguous" or (decision.classification and decision.classification.category in ["ambiguous", "insufficient_data"]):
        return {
            "status": "needs_clarification",
            "decision_id": decision.id,
            "category": decision.classification.category if decision.classification else "ambiguous",
            "question": decision.question,
            "clarification_prompt": decision.classification.clarification_prompt if decision.classification else decision.objective,
            "options": decision.classification.clarification_options if decision.classification else []
        }
    
    from services.supervisor_groq import route_decision_specialists
    company_data = load_company_data()
    routing = await route_decision_specialists(req.query, company_data=company_data)
    if req.selected_specialists:
        valid_specs = [s for s in ["cfo", "growth", "cto", "customer", "product"] if s in req.selected_specialists]
        if valid_specs:
            routing.selected_specialists = valid_specs

    decision.metadata["selected_specialists"] = routing.selected_specialists
    decision.metadata["routing"] = routing.model_dump()

    from agents.llm_client import LLMClient
    supervisor = Supervisor(llm_client=LLMClient(), company_data=company_data)
    active_supervisors[decision.id] = supervisor

    if req.injected_failure:
        supervisor.inject_failure(
            req.injected_failure.agent,
            req.injected_failure.mode,
            persist=req.injected_failure.persist,
            fail_attempts=req.injected_failure.fail_attempts
        )

    # Run workflow asynchronously
    async def run_flow():
        state = await supervisor.execute_workflow(decision)
        active_workflows[decision.id] = state

    background_tasks.add_task(run_flow)

    return {
        "decision_id": decision.id,
        "type": decision.type,
        "question": decision.question,
        "objective": decision.objective,
        "status": "started",
        "selected_specialists": routing.selected_specialists,
        "routing": routing.model_dump()
    }

@app.get("/api/decisions/{decision_id}")
async def get_decision_status(decision_id: str):
    """Returns status, task plan, findings, and events for a decision."""
    state = active_workflows.get(decision_id)
    if not state:
        supervisor = active_supervisors.get(decision_id)
        if supervisor and getattr(supervisor, "current_state", None):
            state = supervisor.current_state
        elif supervisor:
            return {"decision_id": decision_id, "status": "running"}
        else:
            raise HTTPException(status_code=404, detail="Decision not found")

    decision_meta = getattr(state.decision, "metadata", {}) or {}

    return {
        "decision_id": decision_id,
        "status": state.status,
        "round": state.round,
        "degraded_agents": state.degraded_agents,
        "recovered_agents": getattr(state, "recovered_agents", []),
        "has_report": getattr(state, "report", None) is not None,
        "tasks": {k: v.model_dump() for k, v in state.tasks.items()},
        "findings": [f.model_dump() for f in state.findings],
        "conflicts": [c.model_dump() for c in state.conflicts],
        "events_count": len(state.events),
        "selected_specialists": decision_meta.get("selected_specialists", ["cfo", "growth", "cto", "customer", "product"]),
        "routing": decision_meta.get("routing", None)
    }

@app.get("/api/decisions/{decision_id}/stream")
async def stream_decision_events(decision_id: str):
    """Server-Sent Events (SSE) stream for live agent execution telemetry."""
    supervisor = active_supervisors.get(decision_id)
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not active for decision")

    async def event_generator():
        queue: asyncio.Queue[Event] = asyncio.Queue()

        def on_event(evt: Event):
            queue.put_nowait(evt)

        supervisor.event_bus.subscribe(on_event)

        # Stream existing events first
        for past_evt in supervisor.event_bus.get_events():
            yield f"data: {past_evt.model_dump_json()}\n\n"

        try:
            while True:
                evt = await queue.get()
                yield f"data: {evt.model_dump_json()}\n\n"
                if evt.type in ["report_ready", "verification_failed"]:
                    break
        finally:
            supervisor.event_bus.unsubscribe(on_event)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/api/decisions/{decision_id}/inject-failure")
async def inject_failure(decision_id: str, req: FailureInjectionRequest):
    """Injects a simulated runtime fault (timeout, exception, bad_output) or heals/restores an agent."""
    supervisor = active_supervisors.get(decision_id)
    if not supervisor:
        if active_supervisors:
            supervisor = list(active_supervisors.values())[-1]
        else:
            raise HTTPException(status_code=404, detail="Active supervisor not found for decision")

    agent_key = req.agent.lower().split()[0]
    target_task_id = "task_skeptic_audit" if agent_key == "skeptic" else f"task_{agent_key}_analysis"
    agent_up = agent_key.upper()

    if req.mode == "heal":
        # Remove any injected fault for this agent
        supervisor.injected_failures.pop(agent_key, None)

        if supervisor.current_state:
            supervisor.current_state.recovered_agents = [a for a in supervisor.current_state.recovered_agents if a != agent_up]
            supervisor.current_state.degraded_agents = [a for a in supervisor.current_state.degraded_agents if a != agent_up]

            if target_task_id in supervisor.current_state.tasks:
                task = supervisor.current_state.tasks[target_task_id]
                task.status = "retrying"
                task.attempts = 0
                supervisor.current_state.findings = [f for f in supervisor.current_state.findings if f.task_id != target_task_id]
                supervisor.current_state.assumptions = [a for a in supervisor.current_state.assumptions if a.proposed_by != agent_key]

                async def _rerun_healed():
                    res = await supervisor._run_task_with_recovery(task, supervisor.current_state)
                    if res is not None:
                        supervisor.current_state.mark_task_done(task.id)
                        if not supervisor.current_state.recovered_agents and not supervisor.current_state.degraded_agents:
                            supervisor.current_state.status = "completed"
                        if supervisor.current_state.report is not None:
                            await supervisor._run_report_finalize_task(task, supervisor.current_state)
                asyncio.create_task(_rerun_healed())

        await supervisor.event_bus.emit(
            "agent_healed",
            agent=agent_key,
            payload={"agent": agent_up, "status": "restored"}
        )

        return {
            "decision_id": decision_id,
            "agent": agent_key,
            "mode": "heal",
            "status": "agent_restored"
        }

    supervisor.inject_failure(agent_key, req.mode, persist=req.persist, fail_attempts=req.fail_attempts)

    # Emit an SSE event so the live event feed shows the injected failure
    await supervisor.event_bus.emit(
        "failure_injected",
        agent=agent_key,
        payload={"mode": req.mode, "persist": req.persist, "fail_attempts": req.fail_attempts}
    )

    # If the target agent's task has already finished, re-trigger it so mid-run injection immediately takes effect
    if supervisor.current_state and target_task_id in supervisor.current_state.tasks:
        task = supervisor.current_state.tasks[target_task_id]
        if task.status == "done":
            task.status = "retrying"
            task.attempts = 0
            supervisor.current_state.findings = [f for f in supervisor.current_state.findings if f.task_id != target_task_id]
            supervisor.current_state.assumptions = [a for a in supervisor.current_state.assumptions if a.proposed_by != agent_key]
            supervisor.current_state.recovered_agents = [a for a in supervisor.current_state.recovered_agents if a != agent_up]
            supervisor.current_state.degraded_agents = [a for a in supervisor.current_state.degraded_agents if a != agent_up]

            async def _rerun_task():
                res = await supervisor._run_task_with_recovery(task, supervisor.current_state)
                if res is not None:
                    supervisor.current_state.mark_task_done(task.id)
                    if supervisor.current_state.recovered_agents or supervisor.current_state.degraded_agents:
                        supervisor.current_state.status = "degraded"
                    else:
                        supervisor.current_state.status = "completed"
                    if supervisor.current_state.report is not None:
                        await supervisor._run_report_finalize_task(task, supervisor.current_state)
            asyncio.create_task(_rerun_task())

    return {
        "decision_id": decision_id,
        "agent": agent_key,
        "mode": req.mode,
        "persist": req.persist,
        "status": "failure_injected"
    }

@app.get("/api/decisions/{decision_id}/report")
async def get_decision_report(decision_id: str):
    """Returns the consolidated 10-section decision report."""
    state = active_workflows.get(decision_id)
    if not state:
        supervisor = active_supervisors.get(decision_id)
        if supervisor and getattr(supervisor, "current_state", None):
            state = supervisor.current_state
    if not state:
        raise HTTPException(status_code=404, detail="Decision not found or still processing")
    if not state.report:
        raise HTTPException(status_code=400, detail="Report generation not yet completed")

    return state.report.model_dump()

@app.get("/api/decisions/{decision_id}/report.md")
async def get_decision_report_markdown(decision_id: str):
    """Returns the single cohesive markdown document for the decision report."""
    state = active_workflows.get(decision_id)
    if not state:
        supervisor = active_supervisors.get(decision_id)
        if supervisor and getattr(supervisor, "current_state", None):
            state = supervisor.current_state
    if not state:
        raise HTTPException(status_code=404, detail="Decision not found or still processing")
    if not state.report:
        raise HTTPException(status_code=400, detail="Report generation not yet completed")

    md_content = state.report.sections.get("markdown_report")
    if not md_content:
        from report.report_builder import render_markdown_report
        md_content = render_markdown_report(state.report)
    return PlainTextResponse(md_content, media_type="text/markdown")

@app.get("/api/reports/latest")
async def get_latest_report():
    """Returns the most recent completed decision report."""
    for w in reversed(list(active_workflows.values())):
        if w.report:
            return w.report.model_dump()
    kg_path = os.path.join(os.path.dirname(__file__), "..", "data", "known_good_run.json")
    if os.path.exists(kg_path):
        with open(kg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "report" in data and data["report"]:
                return data["report"]
    raise HTTPException(status_code=404, detail="No completed report found")

@app.post("/api/decisions/{decision_id}/approve")
async def approve_decision(decision_id: str, req: ApprovalRequest):
    """Human-in-the-loop gate: stores decision record on approval."""
    state = active_workflows.get(decision_id)
    if not state or not state.report:
        raise HTTPException(status_code=404, detail="Report not available for approval")

    top_strategy = state.report.sections.get("strategies_compared", [{}])[0].get("strategy", "Unknown")
    
    record = {
        "decision_id": decision_id,
        "action": req.action,
        "chosen_strategy": top_strategy,
        "notes": req.notes,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "predicted_metrics": state.report.sections.get("scenario_table", [{}])[0],
        "status": "awaiting_outcome" if req.action == "approve" else ("rejected" if req.action == "reject" else "changes_requested")
    }
    decision_records_store.append(record)
    return {"status": "recorded", "decision_record": record}

def compute_calibration_summary(seeded_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes past decision calibration error and primary drift factor dynamically."""
    if not seeded_decisions:
        return {
            "total_evaluated_past_decisions": 0,
            "mean_arr_error_pct": 0.0,
            "most_common_drift_factor": "none"
        }
    pct_errors = []
    drift_reasons = []
    for d in seeded_decisions:
        cal = d.get("calibration_error", {})
        for k, v in cal.items():
            if "error_pct" in k and isinstance(v, (int, float)):
                pct_errors.append(abs(float(v)))
        if "most_wrong_assumption" in cal:
            drift_reasons.append(cal["most_wrong_assumption"])

    mean_err = round(sum(pct_errors) / len(pct_errors), 1) if pct_errors else 0.0
    from collections import Counter
    most_common = Counter(drift_reasons).most_common(1)[0][0] if drift_reasons else "none"

    return {
        "total_evaluated_past_decisions": len(seeded_decisions),
        "mean_arr_error_pct": mean_err,
        "most_common_drift_factor": most_common
    }

@app.get("/api/history")
async def get_history():
    """Returns seeded past decisions with calibration error plus new approved decisions."""
    seeded = load_seeded_decisions()
    summary = compute_calibration_summary(seeded)
    return {
        "seeded_decisions": seeded,
        "live_approved_decisions": decision_records_store,
        "calibration_summary": summary
    }

@app.get("/api/graph")
async def get_company_graph():
    """Returns Company Intelligence Graph nodes and edges for React Flow."""
    data = load_company_data()
    fin = data["financials"]
    cust = data["customers"]
    
    nodes = [
        {"id": "mrr", "type": "financial", "data": {"label": f"MRR: ${fin['mrr']:,}"}, "position": {"x": 250, "y": 0}},
        {"id": "runway", "type": "financial", "data": {"label": f"Runway: {fin['runway_months']:.1f} mo"}, "position": {"x": 250, "y": 80}},
        {"id": "starter", "type": "plan", "data": {"label": "Starter ($79, 450 users)"}, "position": {"x": 50, "y": 180}},
        {"id": "pro", "type": "plan", "data": {"label": "Pro ($249, 180 users)"}, "position": {"x": 250, "y": 180}},
        {"id": "enterprise", "type": "plan", "data": {"label": "Enterprise ($1,200, 25 users)"}, "position": {"x": 450, "y": 180}},
        {"id": "infra", "type": "cost", "data": {"label": f"Cloud Infra: ${data['infrastructure']['monthly_cloud_cost']:,}/mo"}, "position": {"x": 100, "y": 300}},
        {"id": "support", "type": "cost", "data": {"label": f"Support: {data['support']['headcount_fte']} FTEs"}, "position": {"x": 350, "y": 300}}
    ]

    edges = [
        {"id": "e1", "source": "starter", "target": "mrr"},
        {"id": "e2", "source": "pro", "target": "mrr"},
        {"id": "e3", "source": "enterprise", "target": "mrr"},
        {"id": "e4", "source": "mrr", "target": "runway"},
        {"id": "e5", "source": "infra", "target": "runway"},
        {"id": "e6", "source": "support", "target": "runway"}
    ]

    return {"nodes": nodes, "edges": edges}

@app.post("/api/auth/register")
async def auth_register(req: RegisterRequest, response: Response):
    """Registers a new executive user account and establishes a session."""
    try:
        user = auth.create_user(req.email, req.password, req.full_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    session = auth.create_session(user["id"], remember_me=False)
    response.set_cookie(
        key="vt_session",
        value=session["token"],
        max_age=session["max_age_seconds"],
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )
    return {
        "status": "success",
        "authenticated": True,
        "user": user,
        "token": session["token"]
    }

@app.post("/api/auth/login")
async def auth_login(req: LoginRequest, response: Response):
    """Authenticates executive credentials and sets a secure session cookie."""
    user = auth.authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid executive credentials.")
    session = auth.create_session(user["id"], remember_me=req.remember_me)
    response.set_cookie(
        key="vt_session",
        value=session["token"],
        max_age=session["max_age_seconds"],
        httponly=True,
        samesite="lax",
        secure=False,
        path="/"
    )
    return {
        "status": "success",
        "authenticated": True,
        "user": user,
        "token": session["token"]
    }

@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Returns current authenticated executive profile if session is valid."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or not authenticated.")
    return {
        "authenticated": True,
        "user": user
    }

@app.post("/api/auth/logout")
async def auth_logout(request: Request, response: Response):
    """Invalidates active executive session and clears session cookie."""
    token = extract_session_token(request)
    if token:
        auth.delete_session(token)
    response.delete_cookie(key="vt_session", path="/", samesite="lax")
    return {"status": "logged_out", "authenticated": False}

@app.post("/api/auth/forgot-password")
async def auth_forgot_password(req: ForgotPasswordRequest):
    """Dispatches password reset instructions for verified account."""
    token = auth.create_password_reset(req.email)
    return {
        "status": "success",
        "message": "If this email belongs to a registered executive, recovery instructions have been initiated."
    }

