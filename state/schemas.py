from datetime import datetime, timezone
from typing import Literal, Optional, Any, Dict, List
from pydantic import BaseModel, Field, model_validator

# Provenance types
ProvenanceType = Literal[
    "verified_data",
    "external_research",
    "simulated_estimate",
    "ai_assumption",
    "fallback_degraded"
]

class Assumption(BaseModel):
    id: Optional[str] = None
    name: str
    low: float
    base: float
    high: float
    unit: str
    provenance: ProvenanceType
    source_ref: Optional[str] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    proposed_by: Optional[str] = None
    challenged_by_skeptic: bool = False
    revision_of: Optional[Any] = None
    revision_rationale: Optional[str] = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "Assumption":
        if self.low > self.base:
            raise ValueError(f"Assumption '{self.name}' low ({self.low}) cannot exceed base ({self.base})")
        if self.base > self.high:
            raise ValueError(f"Assumption '{self.name}' base ({self.base}) cannot exceed high ({self.high})")
        return self

class DraftAssumption(BaseModel):
    name: str
    low: float
    base: float
    high: float
    unit: str
    basis: str
    rationale: str

    @model_validator(mode="after")
    def validate_draft_bounds(self) -> "DraftAssumption":
        if self.low > self.base:
            self.low = self.base
        if self.base > self.high:
            self.high = self.base
        return self

class Evidence(BaseModel):
    source_type: Literal["company_data", "external", "calculation"]
    source_ref: str
    snippet: str

# Recommendation types
RecommendationType = Literal[
    "proceed",
    "proceed_with_limits",
    "needs_more_info",
    "reject"
]

class AgentFindingDraft(BaseModel):
    claim: str
    recommendation: RecommendationType = "proceed"
    assumptions: List[DraftAssumption] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)

class Finding(BaseModel):
    agent: str
    task_id: str
    claim: str
    recommendation: RecommendationType = "proceed"
    assumptions: List[Assumption] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    limitations: List[str] = Field(default_factory=list)
    status: Literal["ok", "failed", "needs_more_info"] = "ok"
    degraded: bool = False
    degraded_reason: Optional[str] = None
    recovered_via_backup: bool = False

class DecisionClassification(BaseModel):
    category: Literal[
        "decision_ready",
        "ambiguous",
        "informational",
        "insufficient_data",
        "out_of_domain"
    ] = "decision_ready"
    subtype: Optional[str] = None
    department: Optional[str] = None
    target_fte: Optional[int] = None
    target_spend: Optional[float] = None
    clarification_prompt: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)

class Decision(BaseModel):
    id: str
    type: str = "strategic_decision"
    question: str
    objective: str
    constraints: Dict[str, Any] = Field(default_factory=dict)
    classification: Optional[DecisionClassification] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

TaskKind = Literal[
    "agent_analysis",
    "skeptic_audit",
    "discussion",
    "conflict_resolution",
    "simulation",
    "report_draft",
    "verification",
    "report_finalize"
]

class Task(BaseModel):
    id: str
    owner_agent: str
    depends_on: List[str] = Field(default_factory=list)
    status: Literal["pending", "running", "done", "failed", "retrying", "blocked"] = "pending"
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    kind: TaskKind = "agent_analysis"

class Conflict(BaseModel):
    id: str
    type: str
    agents: List[str]
    disputed_item: str
    evidence: List[Evidence] = Field(default_factory=list)
    resolution: Optional[str] = None
    simulation_ids: List[str] = Field(default_factory=list)
    unresolved: bool = False
    status: Literal["resolved", "resolved_immaterial", "resolved_converged", "unresolved_material", "unresolved_immaterial"] = "resolved"
    verdict: Optional[str] = None
    resolution_method: Optional[Literal["simulation_isolation", "rebuttal_concession", "skeptic_audit", "procedural"]] = None
    sides: List[Dict[str, Any]] = Field(default_factory=list)
    isolated_simulation_deltas: Optional[Dict[str, float]] = None

class SkepticAuditReport(BaseModel):
    challenged_assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    financial_inconsistencies: List[Dict[str, Any]] = Field(default_factory=list)
    unsupported_claims: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_gaps: List[Dict[str, Any]] = Field(default_factory=list)
    recommendation_risks: List[Dict[str, Any]] = Field(default_factory=list)
    verification_status: Literal["passed", "failed"] = "passed"

class Critique(BaseModel):
    skeptic_agent: str = "Skeptic"
    target_agent: str = ""
    target_parameter: str = ""
    concern: str = "Benchmark check"
    severity: Literal["low", "medium", "high"] = "medium"

    @model_validator(mode="before")
    @classmethod
    def normalize_critique_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Target parameter normalization across all variations
            for k in ["target_parameter", "target_assumption", "assumption", "parameter", "param", "metric", "disputed_item", "name"]:
                if k in data and data[k]:
                    data["target_parameter"] = str(data[k]).strip()
                    break
            # Target agent normalization across all variations
            for k in ["target_agent", "agent", "specialist", "agent_name", "target", "role"]:
                if k in data and data[k]:
                    data["target_agent"] = str(data[k]).strip()
                    break
            if "skeptic_agent" not in data or not data["skeptic_agent"]:
                data["skeptic_agent"] = "Skeptic"
            if "concern" not in data or not data["concern"]:
                data["concern"] = data.get("challenge") or data.get("critique") or data.get("rationale") or "Audited assumption against grounded benchmarks"
            if "severity" in data:
                s = str(data["severity"]).strip().lower()
                data["severity"] = s if s in ["low", "medium", "high"] else "medium"
        return data

class Rebuttal(BaseModel):
    agent: str = ""
    parameter: str = ""
    stance: Literal["concede", "defend", "compromise"] = "defend"
    updated_base: Optional[float] = None
    updated_low: Optional[float] = None
    updated_high: Optional[float] = None
    rationale: str = "Maintained position based on data."

    @model_validator(mode="before")
    @classmethod
    def normalize_rebuttal(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in ["agent", "agent_name", "target_agent", "specialist", "role"]:
                if k in data and data[k]:
                    data["agent"] = str(data[k]).strip()
                    break
            for k in ["parameter", "target_parameter", "assumption", "param", "metric", "name"]:
                if k in data and data[k]:
                    data["parameter"] = str(data[k]).strip()
                    break
            if "rationale" not in data or not data["rationale"]:
                data["rationale"] = data.get("justification") or data.get("explanation") or "Maintained position based on data."
            if "stance" in data:
                s = str(data["stance"]).lower()
                if "defend" in s:
                    data["stance"] = "defend"
                elif "concede" in s:
                    data["stance"] = "concede"
                elif "compromise" in s:
                    data["stance"] = "compromise"
                else:
                    data["stance"] = "defend"
        return data

class DiscussionRebuttalsDraft(BaseModel):
    rebuttals: List[Rebuttal] = Field(default_factory=list)

class Message(BaseModel):
    from_agent: str
    to_agent: str
    round: int
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SimulationRun(BaseModel):
    id: str
    strategy: str
    scenario: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    seed: int = 42

class VerificationResult(BaseModel):
    check_name: str
    status: Literal["passed", "failed", "waived"]
    detail: str

class Report(BaseModel):
    decision_id: str
    sections: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    confidence: Literal["Low", "Medium", "High"]
    disclaimers: List[str] = Field(default_factory=list)

class DecisionRecord(BaseModel):
    decision_id: str
    snapshot: Dict[str, Any]
    chosen_strategy: str
    predicted_metrics: Dict[str, Any]
    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actual_metrics: Optional[Dict[str, Any]] = None

class Event(BaseModel):
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    type: Literal[
        "task_created",
        "routing_decided",
        "agent_started",
        "finding_posted",
        "conflict_detected",
        "simulation_run",
        "agent_failed",
        "recovery_started",
        "recovery_done",
        "verification_passed",
        "verification_failed",
        "report_ready",
        "workflow_failed",
        "failure_injected",
        "agent_healed"
    ]
    agent: str
    payload: Dict[str, Any] = Field(default_factory=dict)

