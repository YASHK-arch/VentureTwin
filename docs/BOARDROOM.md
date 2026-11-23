# VentureTwin — The Executive Boardroom & Direct Agent Dialogue

> **A technical guide to the Cursor-inspired Boardroom panel, Whole Board multi-agent orchestration, and direct 1-on-1 specialist executive chat.**

---

## 1. Overview & Architectural Vision

In complex SaaS strategy, an executive needs both **comprehensive multi-agent simulation** and the ability to have **focused, direct dialogue** with specific domain leaders. 

The **VentureTwin Boardroom** provides a Cursor-inspired, sliding executive intelligence console on the right side of the workspace. It unifies two distinct operational paradigms:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTIVE BOARDROOM PANEL                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  Mode Selector: [ 👥 Whole Board (11-Node DAG) ▼ ]                          │
│                 [ 📊 CFO (Financial Analyst)     ]                          │
│                 [ 📈 Growth Strategist           ]                          │
│                 [ 🛠️ CTO (Infrastructure Arch)   ]                          │
│                 [ 🤝 VP Customer Success         ]                          │
│                 [ 📦 Head of Product             ]                          │
│                 [ 🔍 Independent Skeptic         ]                          │
│                 [ 🛡️ Backup General Analyst      ]                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Operational Pipeline A:             │  Operational Pipeline B:             │
│  Whole Board (11-Node DAG)          │  Direct 1-on-1 Specialist Dialogue   │
│  • Topological task dispatch         │  • Isolated domain persona           │
│  • Multi-agent bounded rebuttal      │  • Multi-turn conversation memory    │
│  • Empirical simulation engine       │  • Grounded in active company state  │
│  • 15 algorithmic verification gates │  • Sub-second response streaming     │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. The 7 Specialist Personas & System Prompts

Each specialist in `services/agent_chat.py` is initialized with a distinct objective function, domain vocabulary, and evaluation criteria:

| Agent Key | Executive Role | Domain Focus & Charter | Characteristic Prompt Persona |
|:---|:---|:---|:---|
| `cfo` | **Chief Financial Officer** | Defends cash runway, protects gross margins (74%+), tracks unit economics, burn rate, and capital efficiency. | *"I am your Chief Financial Officer. My priority is protecting cash runway ($1.65M), preserving margins, and ensuring we never breach our 10.0-month solvency floor."* |
| `growth` | **Acquisition Strategist** | Maximizes top-of-funnel velocity, organic virality, trial-to-paid conversion, and customer acquisition cost (CAC). | *"I am your Head of Growth. I look at every strategic opportunity through the lens of acquisition velocity, user expansion, and viral flywheel mechanics."* |
| `cto` | **Infrastructure Architect** | Safeguards SLA stability, models per-user cloud hosting costs ($14.5k/mo baseline), and enforces compute capacity limits. | *"I am your Chief Technology Officer. I evaluate compute overhead, database scaling thresholds, cloud infrastructure burn, and system uptime."* |
| `customer` | **VP Customer Success** | Protects retention, minimizes net churn (1.8%/mo), tracks support ticket burdens (2 FTEs), and defends CSAT. | *"I am your VP of Customer Success. I ensure aggressive expansion doesn't cannibalize our paying base or overwhelm our frontline support team."* |
| `product` | **Head of Product** | Designs tier packaging, feature gating, upgrade catalysts, and price elasticity boundaries. | *"I am your Head of Product. I design clean tier boundaries, feature monetization levers, and upgrade catalysts that maximize expansion revenue."* |
| `skeptic` | **Independent Auditor** | Adversarially stress-tests peer assumptions, challenges optimistic bias, and audits claim provenance. | *"I am your Independent Auditor & Skeptic. I do not accept optimistic assumptions without empirical provenance. I look for hidden risks, unvalidated numbers, and flawed logic."* |
| `backup` | **Backup General Analyst** | Generalist executive failover worker providing balanced, conservative scenario synthesis. | *"I am your Backup Strategic Analyst. I synthesize cross-functional perspectives and provide conservative, evidence-backed recommendations."* |

---

## 3. Dynamic Context Grounding

Direct 1-on-1 dialogues are never generic LLM chats. Every prompt is automatically grounded with the company's real operational telemetry:

```python
# From services/agent_chat.py
context = get_active_company_context(user_id=user_id)
if not context:
    context = get_company_snapshot() # NimbusDesk fallback

system_prompt = f"""
{meta['system_prompt']}

CURRENT COMPANY CONTEXT:
- Company Name: {context.get('company_name')}
- Industry: {context.get('industry')}
- Stage: {context.get('stage')}
- Business Model: {context.get('business_model')}
- MRR / ARR: ${context.get('mrr', 110370):,} / ${context.get('arr', 1324440):,}
- Cash Reserves: ${context.get('cash_balance', 1650000):,}
- Monthly Net Burn: ${context.get('monthly_burn_net', 125000):,}
- Current Runway: {context.get('runway_months', 13.2):.1f} months (Safety floor: 10.0 mo)
- Paying Customers: {context.get('paying_customers', 655)}
- Cloud Infrastructure Burn: ${context.get('infra_cost_monthly', 14500):,}/month
"""
```

---

## 4. UI Engineering: The Cursor Dark Theme

The Boardroom interface (`ui/src/components/mission/BoardroomPanel.tsx`) adheres strictly to modern high-end IDE aesthetics:

- **Color Palette:**
  - Base Background: Deep obsidian `#141414`
  - Border Lines: Clean hairline `#282828`
  - Input Canvas: `#1a1a1a`
  - Accent Palette: Muted purple (`#8b5cf6`), emerald (`#10b981`), and cyan (`#06b6d4`)
- **Downward-Opening Mode Dropdown:**
  - Engineered with explicit positioning (`top-full mt-1.5 z-50`) to guarantee that the dropdown menu expands downwards rather than upwards off-screen.
- **Typewriter Streaming:**
  - Smooth 18ms character-pacing simulation delivers an authentic live-thinking aesthetic without UI freezing.
- **Quick-Prompt Chips:**
  - Contextual one-click prompt pills for each agent (e.g., CFO: *"Can we afford an extra $35k/mo marketing spend?"*, CTO: *"What happens to AWS bills under 5x signups?"*).

---

## 5. REST API Reference

### `POST /api/agents/chat`

Executes a direct 1-on-1 dialogue with a named executive specialist.

#### Request Body
```json
{
  "agent_key": "cfo",
  "message": "What is our maximum additional monthly expenditure while protecting 10 months of runway?",
  "history": [
    {
      "sender": "user",
      "text": "Hello CFO, what is our current runway?",
      "timestamp": "2026-11-24T04:00:00Z"
    }
  ]
}
```

#### Response Body
```json
{
  "agent_key": "cfo",
  "agent_name": "CFO",
  "role_title": "Financial Analyst",
  "reply": "With our current cash balance of $1,650,000 and net monthly burn of $125,000, our maximum allowable burn to maintain at least 10.0 months of runway is $165,000/mo ($1.65M / 10mo). This leaves us exactly $40,000/month in maximum additional expenditure headroom ($165,000 - $125,000 = $40,000).",
  "provenance": "grounded_context",
  "context_used": {
    "cash_balance": 1650000,
    "monthly_burn_net": 125000,
    "runway_months": 13.2,
    "target_min_runway_months": 10.0
  }
}
```
