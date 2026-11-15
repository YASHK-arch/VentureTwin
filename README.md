<span id="venturetwin"></span>
<p align="center">
  <img src="docs/assets/readme/hero-venturetwin.png" alt="VentureTwin — AI Flight Simulator & Operational Digital Twin for SaaS Leaders" width="100%">
</p>

<p align="center">
  <a href="https://github.com/omsrajput977/VentureTwin/actions/workflows/ci.yml"><img src="https://github.com/omsrajput977/VentureTwin/actions/workflows/ci.yml/badge.svg" alt="CI Status"></a>
  <img src="https://img.shields.io/badge/Python-3.13.5-3776AB.svg?logo=python&logoColor=white" alt="Python 3.13.5">
  <img src="https://img.shields.io/badge/FastAPI-0.162.2-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI 0.162.2">
  <img src="https://img.shields.io/badge/React-19.0.0-61DAFB.svg?logo=react&logoColor=black" alt="React 19.0.0">
  <img src="https://img.shields.io/badge/TypeScript-5.7.0-3178C6.svg?logo=typescript&logoColor=white" alt="TypeScript 5.7.0">
  <img src="https://img.shields.io/badge/Tests-184%20passed-brightgreen.svg" alt="184 Pytest Suite Passing">
  <img src="https://img.shields.io/badge/Verification-15%20Automated%20Checks-teal.svg" alt="15 Automated Verification Checks">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
</p>

<p align="center">
  <a href="#1-what-is-venturetwin"><b>Overview</b></a> •
  <a href="#3-venturetwin-architecture"><b>Architecture</b></a> •
  <a href="#4-meet-the-executive-agents"><b>Executive Agents</b></a> •
  <a href="#6-what-makes-venturetwin-different"><b>Key Differentiators</b></a> •
  <a href="#7-simulation-engine"><b>Simulation Engine</b></a> •
  <a href="#8-product-tour--screenshots"><b>Product Tour</b></a> •
  <a href="#10-quick-start"><b>Quick Start</b></a> •
  <a href="#11-testing-and-reliability"><b>Reliability</b></a>
</p>

---

## 1. What is VentureTwin?

**VentureTwin** is an AI flight simulator and operational digital twin for SaaS founders, CEOs, and executive boards. When leadership evaluates strategic, high-stakes business questions—such as *"Should we launch a free plan?"* or *"What is our maximum affordable expenditure while protecting 10 months of runway?"*—traditional decision-making fractures between subjective opinions, siloed spreadsheets, and hallucinated LLM prose.

VentureTwin orchestrates a virtual executive board of specialized AI agents (CFO, Growth, CTO, Customer Success, Product, and an adversarial Skeptic) over an **11-node Directed Acyclic Graph (DAG)**. Instead of generating ungrounded textual advice or taking a naive consensus vote, agents debate assumptions that feed directly into a deterministic Python financial simulation engine.

> [!IMPORTANT]
> **The Core Thesis:** *"Agents propose assumptions. Python calculates outcomes. Verification checks the decisions."*

```
CEO Question ➔ Task Decomposition ➔ 11-Node DAG ➔ Parallel Specialists ➔ Adversarial Skeptic Audit
➔ Empirical Simulation ➔ 15-Check Verification Gate ➔ Consolidated Report ➔ Human Executive Sign-off
```

---

## 2. The Problem

High-stakes SaaS decisions fail under two common paradigms:

| Failure Mode | How It Fails in Practice | VentureTwin Solution |
|:---|:---|:---|
| **Human Executive Meetings** | Politicized debates, HiPPO bias (Highest Paid Person's Opinion), and static spreadsheet models that ignore cross-departmental friction. | **Autonomous Specialist Agents** evaluating decisions simultaneously across financial, technical, customer, and growth constraints. |
| **Monolithic LLM Prompts** | Asking a single LLM generates plausible-sounding essays with hallucinated math, unvalidated arithmetic, and zero balance sheet accountability. | **Empirical Separation of Concerns:** LLMs propose bounded parameter assumptions `[low, base, high]`; deterministic Python runs the balance sheet. |
| **Consensus / LLM Voting** | Averaging conflicting predictions (e.g., CFO's 1.0% conversion vs. Growth's 4.8% to 2.9%) yields an ungrounded compromise no expert supports. | **Simulation-Driven Resolution:** Dual 12-to-24 month dynamic simulations test whether parameter disagreements actually alter the optimal strategy. |

---

## 3. VentureTwin Architecture

VentureTwin coordinates multi-agent intelligence through a modular, decoupled architecture where qualitative reasoning and deterministic mathematics are strictly separated.

<p align="center">
  <img src="docs/assets/readme/multi-agent-architecture.png" alt="VentureTwin Multi-Agent Architecture" width="100%">
</p>

### The 11-Node Execution DAG

Every incoming decision prompt is parsed into an 11-node execution graph executed across sequential dependency waves:

```mermaid
flowchart TD
  subgraph Wave1["Wave 1: Parallel Specialist Analysis"]
    cfo["task_cfo_analysis<br/><b>CFO Agent</b>"]
    growth["task_growth_analysis<br/><b>Growth Agent</b>"]
    cto["task_cto_analysis<br/><b>CTO Agent</b>"]
    customer["task_customer_analysis<br/><b>Customer Agent</b>"]
    product["task_product_analysis<br/><b>Product Agent</b>"]
  end

  subgraph Wave2["Wave 2: Adversarial Audit"]
    skeptic["task_skeptic_audit<br/><b>Skeptic Agent</b>"]
  end

  subgraph Wave3["Wave 3: Bounded Debate"]
    discussion["task_agent_discussion<br/><b>Supervisor Engine</b>"]
  end

  subgraph Wave4["Wave 4: Simulation & Conflict Resolution"]
    conflict["task_conflict_resolution<br/><b>Conflict Engine</b>"]
    sim["task_simulation_engine<br/><b>Deterministic SaaS Dynamics</b>"]
  end

  subgraph Wave5["Wave 5: Synthesis & Verification"]
    draft["task_report_draft<br/><b>Supervisor Synthesis</b>"]
    verify["task_workflow_verification<br/><b>15-Check Algorithmic Verifier</b>"]
    finalize["task_report_finalize<br/><b>Sealed Executive Deliverable</b>"]
  end

  subgraph Governance["Governance Gate"]
    human["Human Executive Sign-Off<br/><b>POST /api/decisions/{id}/approve</b>"]
  end

  cfo --> skeptic
  growth --> skeptic
  cto --> skeptic
  customer --> skeptic
  product --> skeptic
  skeptic --> discussion
  discussion --> conflict
  conflict --> sim
  sim --> draft
  draft --> verify
  verify --> finalize
  finalize --> human

  classDef specialist fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f8fafc;
  classDef audit fill:#0f172a,stroke:#f87171,stroke-width:1.5px,color:#f8fafc;
  classDef engine fill:#0f172a,stroke:#2dd4bf,stroke-width:1.5px,color:#f8fafc;
  classDef gate fill:#134e4a,stroke:#14b8a6,stroke-width:2px,color:#f0fdfa;
  class cfo,growth,cto,customer,product specialist;
  class skeptic,verify audit;
  class discussion,conflict,sim,draft,finalize engine;
  class human gate;
```

---

## 4. Meet the Executive Agents

Each agent is an autonomous specialist operating with isolated context, a domain-specific objective function, private tool access, and structured Pydantic communication schemas:

<p align="center">
  <img src="docs/assets/readme/executive-agent-board.png" alt="Executive Agent Board" width="100%">
</p>

| Agent | Implementation | Core Objective | Key Parameters Proposed | Private Tool Access |
|:---|:---|:---|:---|:---|
| **Supervisor** | [`orchestrator/supervisor.py`](orchestrator/supervisor.py) | Coordinates the DAG, detects conflicts, manages state, synthesizes findings. | State transitions, task graphs, loopback limits | Full Blackboard & SQLite State |
| **CFO** | [`agents/specialists.py`](agents/specialists.py) | Defends cash runway (\$1.65M) and enforces solvency guardrails (10.0-mo floor). | `free_to_paid_conversion`, `infra_cost_per_user` | `company_financials`, `cash_burn_tool` |
| **Growth** | [`agents/specialists.py`](agents/specialists.py) | Maximizes acquisition velocity, signup volume, and top-of-funnel expansion. | `monthly_free_signups`, `paid_funnel_lift` | `traffic_funnel_tool`, `conversion_history` |
| **CTO** | [`agents/specialists.py`](agents/specialists.py) | Protects SLA stability, compute overhead, and infrastructure unit costs. | `infra_cost_per_free_user`, `usage_cap_reduction` | `infrastructure_costs`, `capacity_limits` |
| **Customer** | [`agents/specialists.py`](agents/specialists.py) | Prevents customer churn, protects CSAT, and models support ticket burden. | `paid_to_free_cannibalization`, `ticket_rate` | `support_tickets_tool`, `churn_telemetry` |
| **Product** | [`agents/specialists.py`](agents/specialists.py) | Designs tier boundaries, upgrade gating, and feature monetization elasticity. | `activation_drop_gating`, `cap_conversion_uplift` | `feature_usage_tool`, `tier_matrix` |
| **Skeptic** | [`agents/specialists.py`](agents/specialists.py) | Adversarially stress-tests claims, applies confidence haircuts, challenges provenance. | Challenges optimistic assumptions, emits critiques | `provenance_audit_tool`, `cross_examiner` |
| **Backup Analyst** | [`agents/backup_agent.py`](agents/backup_agent.py) | Autonomous failover agent activated upon specialist timeout or API rate limit. | Adaptive fallback parameter distributions | `domain_priors_tool`, `benchmarks` |

---

## 5. How the Orchestration Works

1. **Structured Pydantic Protocol:** Agents never exchange raw unstructured strings. All findings, critiques, and rebuttals are strictly validated Pydantic models (`Finding`, `Critique`, `Rebuttal`, `DiscussionMessage`) defined in [`state/schemas.py`](state/schemas.py).
2. **Immutable Blackboard & SQLite Snapshots:** Every state transition is written to an append-only event stream via [`state/shared_state.py`](state/shared_state.py) and persisted to SQLite checkpoints via [`orchestrator/checkpointer.py`](orchestrator/checkpointer.py).
3. **Bounded Rebuttal Debate:** The Skeptic reviews Wave 1 findings and issues formal critiques. Agents respond in a bounded single-round rebuttal to defend or adjust their bounds without infinite conversational loops.
4. **Real-Time Telemetry:** The backend broadcasts real-time Server-Sent Events (SSE) via [`state/event_bus.py`](state/event_bus.py) to render live agent states, execution timings, and node telemetry on the frontend.
5. **3-Tier Fault Recovery:**
   - *Tier 1:* Exponential backoff retries (2s, 4s, 8s) on LLM rate limits (HTTP 429).
   - *Tier 2:* Failover to autonomous `BackupAnalystAgent` ([`agents/backup_agent.py`](agents/backup_agent.py)).
   - *Tier 3:* Deterministic domain priors from [`data/benchmarks.json`](data/benchmarks.json) with permanent `DEGRADED` disclaimers.

---

## 6. What Makes VentureTwin Different?

<p align="center">
  <img src="docs/assets/readme/conflict-resolution.png" alt="Empirical Simulation vs Subjective Voting" width="100%">
</p>

1. **Empirical Conflict Resolution (No Voting):** When the CFO and Growth agents disagree on free-to-paid conversion (1.0% vs. 4.8%), VentureTwin evaluates both extremes in parallel 12-to-24 month SaaS models. If Strategy B (Usage Caps) yields superior Net Contribution under *both* assumptions, the conflict is classified as **`decided_by_simulation`** (Decision Invariant), eliminating arbitrary voting.
2. **Deterministic Mathematical Engine:** Pure Python in [`simulation/saas_model.py`](simulation/saas_model.py) computes cash burn, MRR, churn, and runway. LLMs are prohibited from performing financial calculations.
3. **Cryptographic Number Registry:** Every quantitative figure in the final deliverable is registered in [`report/number_registry.py`](report/number_registry.py) with source provenance (`verified_data`, `ai_assumption`, `simulation_output`, or `external_research`).
4. **15 Algorithmic Verification Checks:** [`verification/verifier.py`](verification/verifier.py) runs an automated 15-check audit matrix (units, math balance, solvency floors, prose numbers, and report completeness).
5. **Human-in-the-Loop Governance:** Autonomous execution halts at `pending_approval`. Decisions cannot take effect without explicit human executive sign-off (`POST /api/decisions/{id}/approve`).

---

## 7. Simulation Engine

VentureTwin evaluates strategy branches against a realistic synthetic B2B SaaS benchmark: **NimbusDesk (Series A)**.

<p align="center">
  <img src="docs/assets/readme/simulation-engine.png" alt="VentureTwin Simulation Engine" width="100%">
</p>

### Verified Benchmark Baseline (NimbusDesk)

```text
Cash Balance:                $1,650,000      Current MRR:         $110,370 ($1.32M ARR)
Monthly Net Burn:              $125,000      Paying Customers:                         655
Current Runway:             13.2 months      Customer Acquisition Cost (CAC):       $1,450
Minimum Runway Constraint:  10.0 months      Cloud Infrastructure Burn:         $14,500/mo
Max Additional Expenditure:  $40,000/mo      ($1,650,000 / 10.0mo - $125,000 = $40,000/mo)
```

### Deterministic & Stochastic Flight Charts

All charts are generated deterministically from verified simulation runs (seed=42):

| 1. Tornado Sensitivity Matrix | 2. Strategy Scenario Comparison |
|:---:|:---:|
| <img src="docs/assets/charts/tornado_sensitivity.svg" alt="Tornado Sensitivity Chart" width="100%"> | <img src="docs/assets/charts/scenario_comparison.svg" alt="Scenario Comparison Chart" width="100%"> |
| *Ranks financial swing of agent assumptions on 12-mo contribution* | *Conservative, Expected, and Optimistic 12-month net outcomes* |

| 3. Monte Carlo 500-Run Quantiles | 4. Cash Runway & Solvency Boundary |
|:---:|:---:|
| <img src="docs/assets/charts/monte_carlo_distribution.svg" alt="Monte Carlo Distribution Chart" width="100%"> | <img src="docs/assets/charts/runway_constraint.svg" alt="Runway Trajectory Chart" width="100%"> |
| *P10, P50, and P90 stochastic bands over 500 random draws* | *24-month cash runway tracking against the 10.0-month safety floor* |

---

## 8. Product Tour & Screenshots

The VentureTwin React dashboard provides end-to-end visibility into the multi-agent decision lifecycle:

<div align="center">

| Strategic Intake & Preset Scenarios | Active Multi-Agent Execution DAG |
|:---:|:---:|
| <img src="docs/assets/screenshots/02-strategic-question-intake.png" alt="Strategic Intake Console" width="100%"> | <img src="docs/assets/screenshots/08-orchestration-dag-active.jpg" alt="Active Orchestration DAG" width="100%"> |
| *Natural language intake with quick-start strategic presets* | *Live DAG tracking parallel agent waves and execution states* |

| Completed 11-Node Decision Topology | Specialist Finding Inspector Modal |
|:---:|:---:|
| <img src="docs/assets/screenshots/01-decision-console-complete.jpg" alt="Decision Console Complete" width="100%"> | <img src="docs/assets/screenshots/03-cfo-finding-modal.jpg" alt="CFO Finding Modal" width="100%"> |
| *Full execution graph resolved with audit and verification passes* | *Inspect bounded assumptions, confidence ratings, and provenance* |

</div>

<details>
<summary><b>🔍 View Additional Telemetry Views (Live Event Stream & Domain Inspectors)</b></summary>
<br/>

| Real-Time Event Stream (SSE) | Head of Growth Finding Inspector | VP Customer Success Finding Inspector |
|:---:|:---:|:---:|
| <img src="docs/assets/screenshots/07-live-event-stream.png" alt="Live Event Stream" width="100%"> | <img src="docs/assets/screenshots/04-growth-finding-modal.jpg" alt="Growth Inspector" width="100%"> | <img src="docs/assets/screenshots/06-customer-finding-modal.jpg" alt="Customer Inspector" width="100%"> |
| *Real-time SSE event log* | *Top-of-funnel acquisition bounds* | *Cannibalization and ticket ratios* |

</details>

---

## 9. Technology Stack

Verified directly from [`pyproject.toml`](pyproject.toml) and [`ui/package.json`](ui/package.json):

| Subsystem | Technology | Verified Version | Architectural Role |
|:---|:---|:---:|:---|
| **Runtime** | Python | `3.13.5` | Core language runtime |
| **API Framework** | FastAPI | `0.162.2` | High-performance asynchronous REST & SSE streaming server |
| **ASGI Server** | Uvicorn | `0.54.0` | Production ASGI web application server |
| **Type Validation** | Pydantic | `2.14.3` | Bounded parameter schemas, finding models, contract enforcement |
| **Scientific Math** | NumPy / SciPy | `2.5.4` / `1.18.1` | Monte Carlo distributions, quantile calculations, sensitivity sweeps |
| **Async HTTP** | HTTPX | `0.28.1` | Non-blocking LLM provider communications with retry management |
| **Test Harness** | Pytest / Pytest-Asyncio | `9.2.0` / `0.25.3` | 184 unit, integration, invariant, and chaos tests |
| **Frontend UI** | React / React-DOM | `19.0.0` | Mission-control reactive user interface component tree |
| **Frontend Tooling** | Vite / TypeScript | `6.2.0` / `5.7.0` | Lightning-fast HMR bundler and strict end-to-end type contracts |
| **UI Styling** | Tailwind CSS | `3.4.17` | Dark-mode mission-control design system |
| **Persistence** | SQLite | `3.x` | Zero-dependency transactional checkpoint and event store |

---

## 10. Quick Start

Run VentureTwin locally in **mock mode** with zero external API keys required:

### 1. Clone & Set Up Backend

```bash
git clone https://github.com/omsrajput977/VentureTwin.git
cd VentureTwin

# Initialize Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install verified dependencies
pip install -r requirements.txt
```

### 2. Set Up Frontend

```bash
cd ui
npm install
cd ..
```

### 3. Launch Services

```bash
# Terminal 1: Launch FastAPI Backend (Defaults to Mock Mode)
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Launch React Frontend
npm --prefix ui run dev
```

Open **`http://localhost:5173`** in your browser. Verify backend health with:

```bash
curl http://localhost:8000/api/health
# {"status":"ok","version":"0.1.0","llm_mode":"mock",...}
```

### Running with Real LLMs (Google Gemini, OpenAI, Groq, Cerebras)

To connect live models, update `.env` in the project root:

```env
LLM_MODE=real
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Test your provider credentials:

```bash
python3 scripts/check_provider.py
```

> [!TIP]
> Use **`LLM_MODE=record`** once to record live LLM responses into [`tests/cassettes/`](tests/cassettes/), then switch to **`LLM_MODE=replay`** for zero-latency, rate-limit-free demonstrations.

---

## 11. Testing and Reliability

VentureTwin maintains rigorous automated testing and algorithmic verification:

```bash
# Execute the complete automated test suite
pytest tests/ -q
# 184 passed, 3 skipped in 15.59s
```

### The 15 Algorithmic Verification Checks

Implemented in [`verification/verifier.py`](verification/verifier.py), these checks run automatically on every report draft:

```text
 1. verify_units                              9. verify_financial_reconciliation
 2. verify_company_financial_tie_outs       10. verify_runway_integrity
 3. verify_provenance_integrity              11. verify_assumption_consistency
 4. verify_report_data_traceability          12. verify_numerical_claim_traceability
 5. verify_required_sections                 13. verify_agent_participation_integrity
 6. verify_number_registry                   14. verify_simulation_reproducibility
 7. verify_prose_numbers                     15. verify_recommendation_constraints
 8. verify_decision_consistency
```

### Automated UI Number Verification

Run before every frontend build to ensure no hardcoded metric values exist in React components:

```bash
node ui/scripts/check-no-fake-numbers.mjs
# Pass: All displayed values trace to dynamic backend API responses
```

---

## 12. Limitations

1. **Synthetic Benchmark Focus:** NimbusDesk is a calibrated synthetic B2B SaaS company (\$110k MRR, \$1.65M cash) designed for consistent benchmarking. It is not connected to a live production database.
2. **SaaS Dynamics Scope:** The deterministic model specializes in subscription economics (churn, CAC, ARPU, support load, infra scaling). It is not designed for hardware manufacturing, crypto, or biotech modeling.
3. **Simulations are Scenarios, Not Guarantees:** Monte Carlo distributions project mathematical outcomes of stated assumptions under statistical distributions; they are decision stress-tests, not macroeconomic forecasts.
4. **Single-Tenant Local Execution:** Optimized for local hackathon evaluation with SQLite; does not include enterprise multi-tenant RBAC or cloud SSO.

---

## 13. Future Scope

- `[PLANNED]` **Live Billing & CRM Telemetry:** Native connectors for Stripe, HubSpot, and Datadog to auto-sync company parameters.
- `[PLANNED]` **Multi-Tenant Enterprise Workspaces:** Role-based access control allowing cross-functional executive teams to collaborate and sign off.
- `[PLANNED]` **Historical Decision Backtesting:** Comparing past simulated recommendations against actual company performance to dynamically calibrate agent confidence weights.
- `[PLANNED]` **Conversational Scenario Steering:** Direct dialogue with individual specialist agents within the console to stress-test micro-assumptions.

---

## 14. Team and Acknowledgements

- **Built by:** Om Rajput ([@omsrajput977](https://github.com/omsrajput977))
- **Submission for:** *SwarmFlow: Multi-Agent Task Coordination Engine Hackathon (2026)*
- **License:** Open source under the **[MIT License](LICENSE)**.
- **Acknowledgements:** Google DeepMind & Google AI Studio for the Gemini API platform.

---

<p align="center">
  <img src="docs/assets/footer.svg" alt="VentureTwin Footer" width="100%">
</p>

<p align="center">
  <a href="#venturetwin"><b>Back to Top ⬆️</b></a>
</p>
