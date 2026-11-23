# Nango Provider Availability & Capabilities Report

**Target Platform:** VentureTwin AI Flight Simulator & Multi-Agent Executive Boardroom  
**Verification Date:** November 2026  
**Reference Source:** Official Nango Integration Catalogue (`https://nango.dev/api-integrations`) & Provider API Specifications  

---

## 1. Executive Summary

VentureTwin utilizes a hybrid architecture:
- **Nango Managed Integrations:** Used for external SaaS platforms requiring complex OAuth2 handshakes, multi-tenant token refresh, and unified API proxying (`stripe`, `quickbooks`, `hubspot`, `github`, `intercom`, `zendesk`, `linear`).
- **Direct API & Custom Connectors:** Used for product analytics and infrastructure observability with high-frequency event ingestion (`mixpanel`, `datadog`, `amplitude`), as well as real-time web scraping and search intelligence engines (`firecrawl`, `brave_search`).
- **VentureTwin Core:** Retains 100% of business logic, 12-month synthetic telemetry generation, data normalization, provenance tracking, and agent-scoped security policies.

---

## 2. Provider Availability Matrix

| Provider Name | Executive Agent | Prebuilt Nango Integration | Exact Provider Config Key | Supported Auth Method | Required Scopes / Permissions | Available API Operations | Custom API Proxy Supported | Supports Synthetic Creation |
|---|---|---|---|---|---|---|---|---|
| **Stripe** | CFO | Yes | `stripe` | OAuth2 / API Key | `read_write`, `customers`, `charges`, `subscriptions` | Customers, Invoices, Charges, Subscriptions, Refunds | Yes (via `/proxy/*`) | Yes (via Test Mode API) |
| **QuickBooks** | CFO | Yes | `quickbooks` | OAuth2 | `com.intuit.quickbooks.accounting` | Reports (P&L, Balance Sheet), Invoices, Accounts, Expenses | Yes (via `/proxy/*`) | Yes (Sandbox realm insertion) |
| **HubSpot** | Growth | Yes | `hubspot` | OAuth2 | `crm.objects.contacts.read`, `crm.objects.deals.read`, `crm.schemas.contacts.read` | Contacts, Companies, Deals, Pipelines | Yes (via `/proxy/*`) | Yes (Developer Test Portal) |
| **Mixpanel** | Growth | Custom / Direct | `mixpanel` | API Secret / Project Token | Project Data Ingest & Query permissions | Event Track, JQL / Funnel Query, Engage Profiles | Yes | Yes (Ingestion API supports historical timestamps) |
| **GitHub** | CTO | Yes | `github` | OAuth2 | `repo`, `read:org`, `read:user` | Commits, Pull Requests, Issues, Releases, Workflows | Yes (via `/proxy/*`) | Yes (Dedicated Test Repository) |
| **Datadog** | CTO | Prebuilt / Direct | `datadog` / `datadog-oauth` | API Key + App Key / OAuth2 | `metrics_read`, `events_read`, `incident_read` | Metric Query, Series Post, Incidents, Error Logs | Yes | Yes (Custom Metrics via Post Series API) |
| **Intercom** | Customer Success | Yes | `intercom` | OAuth2 | `read`, `write`, `conversations`, `users` | Contacts, Conversations, Teams, Support Stats | Yes (via `/proxy/*`) | Yes (Developer Workspace) |
| **Zendesk** | Customer Success | Yes | `zendesk` | OAuth2 | `read`, `write`, `tickets` | Tickets, Users, Organizations, Audits, SLA Metrics | Yes (via `/proxy/*`) | Yes (Sandbox Portal) |
| **Amplitude** | Product | Prebuilt / Direct | `amplitude` | API Key + Secret Key / OAuth2 MCP | Project Read / Write | HTTP V2 Event Ingestion, Cohorts, Funnels, User Activity | Yes | Yes (Batch Event Ingestion API) |
| **Linear** | Product | Yes | `linear` | OAuth2 | `read`, `write`, `issues:create` | Issues, Projects, Cycles, Labels, Roadmaps | Yes (via `/proxy/*`) | Yes (Dedicated Test Workspace) |
| **Firecrawl** | Skeptic | Direct API | `firecrawl` | Bearer API Key | Standard Firecrawl Tier API Token | `/v1/scrape`, `/v1/crawl`, Markdown extraction | N/A (Direct) | No (Retrieves Real External Web Intelligence) |
| **Brave Search** | Skeptic | Direct API | `brave_search` | API Key (`X-Subscription-Token`) | Web Search & Summarizer APIs | `/res/v1/web/search`, `/res/v1/summarizer/search` | N/A (Direct) | No (Retrieves Real Market Intelligence) |

---

## 3. Architectural Design

```
                     VENTURETWIN BOARDROOM
                               │
                      Integration Manager
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
      Nango Service                     Direct API Connectors
  (OAuth, Refresh, Proxy)             (High-Throughput / Direct)
     ├── Stripe                           ├── Mixpanel
     ├── QuickBooks                       ├── Datadog
     ├── HubSpot                          ├── Amplitude
     ├── GitHub                           ├── Firecrawl
     ├── Intercom                         └── Brave Search
     ├── Zendesk
     └── Linear
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
               Normalized Ingested Records Store
               (SQLite: venturetwin_auth.db)
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
  Scoped Agent Data Access              Synthetic Data Engine
 (CFO, Growth, CTO, etc.)          (Shopify & Nextcloud Telemetry)
```

### Key Architectural Guarantees:
1. **Zero Credential Exposure:** Frontend code never receives `NANGO_SECRET_KEY` or raw third-party access tokens. The backend issues short-lived Connect Session tokens (`POST /connect/sessions`).
2. **Provenance Isolation:** Real API records are strictly tagged with `provenance.type = "real_api"`. Locally generated simulation data is tagged with `"synthetic_internal"` or `"synthetic_external"`. Competitor web research is tagged with `"external_research"`.
3. **Graceful Fallback:** If Nango credentials are not yet configured in the environment, the integration manager transitions the provider to `awaiting_credentials` and documents missing variables without blocking application startup or crashing offline test suites.
