# VentureTwin — Data-First Onboarding & Company Context Engine

> **A technical breakdown of document ingestion, website scraping, heuristic and LLM extraction, provenance tracking, and dynamic company grounding in VentureTwin.**

---

## 1. Overview & Architectural Motivation

In real enterprise decision-making, companies do not conform to hardcoded JSON configuration files. When leadership teams evaluate critical strategic questions, the decision intelligence platform must ingest and understand their specific business model, customer segments, pricing tiers, unit economics, and competitive headwinds.

VentureTwin features a **Data-First Onboarding Engine** that dynamically populates company context from two primary ingestion pathways:
1. **Unstructured Markdown Documents:** Executive summaries, pitch decks, investor memos, and internal strategy docs.
2. **Public Corporate Websites:** Automated, SSRF-protected scraping of corporate domains, product pages, and pricing tiers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DATA-FIRST ONBOARDING INGESTION                       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│    Pathway A: Markdown Uploads       │    Pathway B: Website Scraper        │
│   (Strategy Docs, Pitch Decks)       │   (SSRF Protected, Domain Parse)     │
└──────────────────┬───────────────────┴──────────────────┬───────────────────┘
                   │                                      │
                   ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 EXTRACTION & RECONCILIATION ENGINE                          │
│   • LLM Extraction with Structured Pydantic Output (9 Core Fields)          │
│   • Heuristic Fallback Parser (Robust Zero-Key Extraction)                  │
│   • Field-Level Provenance Tracking (uploaded_documents vs website_scrape)  │
│   • Completeness Score Calculation (completeness_pct)                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPANY CONTEXT STORE (SQLite ACID)                      │
│   • venturetwin_company_context.db (Multi-profile context store)            │
│   • Automatic user isolation & active context selection                     │
│   • Dynamic injection into Simulation Engine & 1-on-1 Agent Dialogue        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Extraction Schema: The 9 Core Fields

The context extraction engine maps raw unstructured text into 9 core business parameters and 4 optional extension fields:

### Core Required Fields

| Field Name | Type | Description | Example Extracted Value |
|:---|:---:|:---|:---|
| `company_name` | `string` | Legal / brand name of the SaaS enterprise | `"NimbusDesk"` |
| `industry` | `string` | Primary market segment / vertical | `"B2B Customer Support & Helpdesk Software"` |
| `business_model` | `string` | Core operational model | `"B2B SaaS with Self-Serve & Inside Sales"` |
| `description` | `string` | Concise operational overview | `"AI-assisted customer support ticketing platform..."` |
| `products_services` | `string` | Core platform capabilities & modules | `"Omnichannel Inbox, SLA Tracking, Knowledge Base"` |
| `target_customers` | `string` | Ideal customer profile (ICP) & buyer persona | `"Mid-market SaaS companies (50–500 employees)"` |
| `revenue_model` | `string` | Monetization tiers, seats, and billing cadence | `"Tiered monthly subscription per support agent seat"` |
| `stage` | `string` | Maturity & capitalization phase | `"Series A ($1.65M Cash, $110k MRR)"` |
| `strategic_goals` | `string` | 12-month key executive objectives | `"Expand net contribution, test freemium acquisition"` |

### Optional Extension Fields

- `geographic_presence`: Primary operating regions and datacenter deployments.
- `major_challenges`: Known headwinds (e.g., rising AWS compute costs, support burnout).
- `key_competitors`: Primary incumbents and alternative market solutions.
- `website_url`: Verified corporate URL.

---

## 3. Ingestion Pathways & Implementation

### 3.1 Unstructured Markdown Ingestion (`services/company_extractor.py`)

Users upload raw Markdown documents via the frontend dropzone. The backend service processes multiple files concurrently:

1. **Document Tokenization & Truncation:** Content is normalized and bounded to prevent context window overflow.
2. **Dual-Mode Extraction:**
   - **Mode 1 (LLM Extraction):** When running with an active LLM provider (`gemini`, `openai`, `groq`, `cerebras`), prompts are dispatched to extract structured JSON conforming to `RawExtractedCompanyContext`.
   - **Mode 2 (Deterministic Heuristic Fallback):** When running in `mock` or offline mode, an intelligent regex and section parser extracts headers, bullet points, and key-value attributes with zero external network dependencies.
3. **Completeness Scoring:**
   $$\text{completeness\_pct} = \frac{\sum_{i=1}^{N} \mathbb{I}(\text{field}_i \text{ is non-empty})}{N} \times 100$$
   Where $N = 9$ core required fields.

### 3.2 SSRF-Protected Website Scraper (`services/website_scraper.py`)

The website scraper ingests corporate URLs with production-grade Server-Side Request Forgery (SSRF) protections:

- **Loopback & Private Subnet Blocking:** Rejects `127.0.0.1`, `localhost`, `0.0.0.0`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, and link-local `169.254.0.0/16`.
- **Protocol Enforcement:** Strictly allows only `http://` and `https://`.
- **Timeout & Size Guards:** Limits payload size to 1MB and enforces a 10.0-second network timeout.
- **HTML DOM Parsing:** Strips scripts, styles, and SVGs, prioritizing `<meta name="description">`, `<h1>`, `<h2>`, and main semantic text.

---

## 4. Field-Level Provenance & Human Verification

Every extracted field carries an immutable provenance indicator:

```json
{
  "provenance": {
    "company_name": "uploaded_documents",
    "description": "website_scrape",
    "revenue_model": "manual_edit",
    "stage": "uploaded_documents"
  }
}
```

- **`uploaded_documents`:** Extracted directly from executive Markdown memos.
- **`website_scrape`:** Enriched via public website crawl.
- **`manual_edit`:** Adjusted or reviewed by the human executive in the interactive UI table.

---

## 5. Persistence & Context Injection (`services/company_context_store.py`)

Extracted profiles are persisted in SQLite (`venturetwin_company_context.db`):

```sql
CREATE TABLE IF NOT EXISTS company_contexts (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    company_name TEXT NOT NULL,
    industry TEXT NOT NULL,
    business_model TEXT NOT NULL,
    description TEXT NOT NULL,
    products_services TEXT NOT NULL,
    target_customers TEXT NOT NULL,
    revenue_model TEXT NOT NULL,
    geographic_presence TEXT,
    stage TEXT NOT NULL,
    strategic_goals TEXT NOT NULL,
    major_challenges TEXT,
    key_competitors TEXT,
    website_url TEXT,
    provenance_json TEXT,
    uploaded_documents_json TEXT,
    completeness_pct REAL NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### Dynamic Runtime Fallback (`data/loader.py`)

The hardcoded `synthetic_company.json` file has been cleanly removed. At runtime:
1. `data/loader.py` queries `get_active_company_context()`.
2. If active user context is found, it dynamically configures the financial model and agent prompts.
3. If no custom context exists yet, it falls back to the verified in-memory benchmark baseline for **NimbusDesk** (`$110k MRR`, `$1.65M Cash`).

---

## 6. REST API Reference

| Endpoint | Method | Payload / Parameters | Description |
|:---|:---:|:---|:---|
| `/api/company/extract` | `POST` | `{"files": [{"filename": str, "content": str}]}` | Extracts 9-field company context from Markdown. |
| `/api/company/scrape-website` | `POST` | `{"url": str}` | Scrapes corporate website and enriches fields. |
| `/api/company/context` | `POST` | `CompanyContextPayload` | Saves verified company context to SQLite. |
| `/api/company/context` | `GET` | *(Session Cookie / Bearer)* | Retrieves current active company context profile. |
| `/api/company/contexts` | `GET` | *(Session Cookie / Bearer)* | Lists all saved company context profiles. |
| `/api/company/context/{id}` | `DELETE` | `id: str` | Deletes a saved company profile. |
