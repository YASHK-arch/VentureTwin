"""
Populates Linear with realistic Shopify engineering & product development data:
- Sprints / Cycles: Sprint 42 (Shop Pay & Checkout) and Sprint 43 (Sidekick AI & Headless)
- 6 Shopify Roadmap Projects: Shop Pay, Sidekick AI, Hydrogen/Oxygen, POS Go, Markets Pro, B2B
- 24 Detailed Engineering Issues across Done, In Progress, Todo, and Backlog states
- Story point estimates, priorities, labels (Bug, Feature, Improvement), and markdown specs
"""

import os
import sys
import time
import json
from pathlib import Path
import httpx

# Load LINEAR_API_KEY dynamically from .env or environment
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("LINEAR_API_KEY="):
                os.environ["LINEAR_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("[ERROR] LINEAR_API_KEY is not set in environment or .env file.")
    sys.exit(1)

ENDPOINT = "https://api.linear.app/graphql"
HEADERS = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json",
}

PROJECTS_DATA = [
    {
        "key": "shoppay",
        "name": "Shop Pay One-Click Checkout & Performance Optimization",
        "description": "Sub-second global checkout latency, zero-friction mobile biometric passkeys, and dynamic payment routing for Shopify merchants.",
        "color": "#5E6AD2",
        "targetDate": "2027-03-31",
    },
    {
        "key": "sidekick",
        "name": "Sidekick AI — Autonomous Merchant Commerce Assistant",
        "description": "Deep LLM integration directly into Shopify Admin allowing merchants to segment customers, update discounts, analyze sales cliffs, and execute store edits via conversational agent prompts.",
        "color": "#8A3FFC",
        "targetDate": "2027-06-30",
    },
    {
        "key": "hydrogen",
        "name": "Hydrogen & Oxygen Headless Commerce Framework v3",
        "description": "Next-gen Remix-powered headless storefront framework with sub-50ms edge caching on Cloudflare workers and Oxygen edge runtime.",
        "color": "#00C7B7",
        "targetDate": "2027-05-15",
    },
    {
        "key": "pos",
        "name": "Shopify POS Go & Retail Hardware Fleet Management",
        "description": "Next-gen handheld barcode scanner and integrated chip-and-PIN terminal fleet synchronization for omnichannel brick-and-mortar stores.",
        "color": "#F59E0B",
        "targetDate": "2027-02-28",
    },
    {
        "key": "markets",
        "name": "Shopify Markets Pro — Global Duties & Cross-Border Engine",
        "description": "Automated landed cost calculation, localized customs compliance, multi-currency settlement, and cross-border carrier integration in 175+ countries.",
        "color": "#10B981",
        "targetDate": "2027-08-31",
    },
    {
        "key": "b2b",
        "name": "B2B Wholesale Portal & Custom Price Lists",
        "description": "Native B2B wholesale capabilities with company hierarchies, negotiated tier pricing, Net 30/60 invoicing terms, and self-serve reordering.",
        "color": "#EC4899",
        "targetDate": "2027-04-30",
    },
]

ISSUES_DATA = [
    # Project 1: Shop Pay Checkout
    {
        "project": "shoppay",
        "cycle_index": 0,
        "state": "Done",
        "priority": 1,
        "estimate": 8,
        "label": "Feature",
        "title": "Migrate checkout session state machine to Rust WebAssembly edge workers",
        "description": "### Problem\nNode.js checkout session serialization adds 80-110ms of TTFB during high-concurrency flash drops.\n\n### Solution\n- Re-implemented checkout cart validator in Rust compiled to Wasm.\n- Deployed to Cloudflare Edge workers across 280 PoPs.\n- P99 checkout start latency dropped from 120ms to 24ms.",
    },
    {
        "project": "shoppay",
        "cycle_index": 0,
        "state": "In Progress",
        "priority": 2,
        "estimate": 5,
        "label": "Improvement",
        "title": "Reduce Shop Pay biometric passkey authentication P99 latency below 350ms",
        "description": "### Objective\nOptimize WebAuthn FIDO2 public-key challenge verification round-trips for FaceID and TouchID users on iOS and Android.\n\n### Milestones\n- [x] Profile cryptographic signature verification bottleneck.\n- [ ] Pre-warm session keys upon phone number input.\n- [ ] Validate across Safari 18 and Chrome Mobile.",
    },
    {
        "project": "shoppay",
        "cycle_index": 0,
        "state": "Done",
        "priority": 1,
        "estimate": 3,
        "label": "Bug",
        "title": "Fix race condition in multi-currency conversion cache during flash sales",
        "description": "### Defect\nConcurrent checkout requests for non-USD currencies caused intermittent cache stampede on Redis rate-quote cluster.\n\n### Resolution\nImplemented probabilistic early expiration (XFetch algorithm) on currency exchange rates cache keys.",
    },
    {
        "project": "shoppay",
        "cycle_index": 1,
        "state": "Todo",
        "priority": 2,
        "estimate": 5,
        "label": "Feature",
        "title": "Dynamic payment routing engine failover for Adyen and Stripe acquirers",
        "description": "Implement automated algorithmic acquirer failover when primary processor reports elevated HTTP 5xx or authorization decline rates exceed 4.5% over a 60-second sliding window.",
    },

    # Project 2: Sidekick AI
    {
        "project": "sidekick",
        "cycle_index": 0,
        "state": "In Progress",
        "priority": 1,
        "estimate": 8,
        "label": "Feature",
        "title": "Build streaming LLM intent router for merchant catalog batch updates",
        "description": "### Architecture\nSidekick needs to parse complex merchant prompts (e.g., 'Apply a 15% discount to all winter jackets with inventory > 50 and update SEO meta tags') into validated Shopify GraphQL Admin API bulk mutations.\n\n### Tech Stack\n- Fast Semantic Router\n- Structured JSON schema enforcement\n- SSE streaming progress indicators in Admin UI.",
    },
    {
        "project": "sidekick",
        "cycle_index": 1,
        "state": "In Progress",
        "priority": 2,
        "estimate": 8,
        "label": "Feature",
        "title": "Fine-tune Sidekick function-calling model on Shopify Admin GraphQL mutations",
        "description": "Curate synthetic fine-tuning dataset of 15,000 multi-turn merchant dialogues mapped to exact GraphQL schema arguments for discounts, products, themes, and shipping zones.",
    },
    {
        "project": "sidekick",
        "cycle_index": 0,
        "state": "Done",
        "priority": 1,
        "estimate": 5,
        "label": "Improvement",
        "title": "Sidekick contextual guardrails preventing unauthorized pricing drops",
        "description": "Added deterministic validation layer ensuring Sidekick never executes price drops exceeding 50% without an explicit secondary merchant confirmation modal.",
    },
    {
        "project": "sidekick",
        "cycle_index": None,
        "state": "Backlog",
        "priority": 3,
        "estimate": 5,
        "label": "Feature",
        "title": "Natural language customer segmentation query generator for email campaigns",
        "description": "Enable merchants to ask Sidekick: 'Show customers who placed 2+ orders in last 90 days but haven't opened our newsletter' and output Shopify Customer Segments query syntax.",
    },

    # Project 3: Hydrogen & Oxygen Headless
    {
        "project": "hydrogen",
        "cycle_index": 0,
        "state": "Done",
        "priority": 2,
        "estimate": 8,
        "label": "Feature",
        "title": "Sub-50ms SSR edge caching layer for Hydrogen React Server Components",
        "description": "Integrated Stale-While-Revalidate (SWR) headers with automatic cache invalidation upon Shopify Storefront API Webhook events (product update, collection reorder).",
    },
    {
        "project": "hydrogen",
        "cycle_index": 0,
        "state": "Done",
        "priority": 1,
        "estimate": 5,
        "label": "Bug",
        "title": "Oxygen worker memory leak during concurrent large product graph queries",
        "description": "Resolved V8 isolate heap memory retention caused by unreleased circular reference in GraphQL Storefront client AST cache under 5,000 req/sec load.",
    },
    {
        "project": "hydrogen",
        "cycle_index": 1,
        "state": "In Progress",
        "priority": 2,
        "estimate": 3,
        "label": "Improvement",
        "title": "Headless Customer Account API token refresh rotation in Remix middleware",
        "description": "Support automatic OAuth PKCE refresh token exchange without forcing user redirects during active storefront browsing sessions.",
    },
    {
        "project": "hydrogen",
        "cycle_index": 1,
        "state": "Todo",
        "priority": 3,
        "estimate": 2,
        "label": "Improvement",
        "title": "Automated Lighthouse CI performance regression audit for Hydrogen starter",
        "description": "Add GitHub Actions workflow running Google Lighthouse on simulated 4G mobile devices; fail PRs if Performance drops below 95 or LCP exceeds 1.8s.",
    },

    # Project 4: Shopify POS Go & Retail Hardware
    {
        "project": "pos",
        "cycle_index": 0,
        "state": "Done",
        "priority": 1,
        "estimate": 8,
        "label": "Feature",
        "title": "Offline-first SQLite queue sync for POS Go handheld barcode scans",
        "description": "Implemented background SQLite sync manager allowing POS Go units to process scans and line-item lookups during internet connectivity drops in retail warehouses.",
    },
    {
        "project": "pos",
        "cycle_index": 0,
        "state": "In Progress",
        "priority": 2,
        "estimate": 5,
        "label": "Bug",
        "title": "Bluetooth LE pairing handshake timeout on Verifone terminal hardware",
        "description": "Investigating BLE advertising packet drops on firmware v4.12 causing 12% of retail terminal pairing attempts to fail during initial showroom setup.",
    },
    {
        "project": "pos",
        "cycle_index": 1,
        "state": "Todo",
        "priority": 2,
        "estimate": 8,
        "label": "Feature",
        "title": "Multi-store retail inventory allocation locking algorithm",
        "description": "Real-time distributed lock on physical store stock during omnichannel 'Buy Online, Pick Up In Store' (BOPIS) checkout sessions to prevent in-store double-selling.",
    },
    {
        "project": "pos",
        "cycle_index": None,
        "state": "Backlog",
        "priority": 4,
        "estimate": 2,
        "label": "Bug",
        "title": "POS Go receipt thermal printer spooler buffer overflow fix",
        "description": "Truncate merchant logo bitmap data if ESC/POS payload exceeds 32KB hardware RAM limit on companion Star Micronics printers.",
    },

    # Project 5: Shopify Markets Pro
    {
        "project": "markets",
        "cycle_index": 1,
        "state": "In Progress",
        "priority": 1,
        "estimate": 8,
        "label": "Feature",
        "title": "Landed cost duties & tariff calculation microservice integration with Avalara",
        "description": "Integrate HS code classification and localized import duty calculations at checkout for cross-border shipments to UK, EU, Japan, and Australia.",
    },
    {
        "project": "markets",
        "cycle_index": 0,
        "state": "Done",
        "priority": 2,
        "estimate": 5,
        "label": "Feature",
        "title": "Real-time DHL Express cross-border shipping label generation API",
        "description": "Automated commercial invoice PDF generation and paperless customs document transmission via DHL Express MyDHL API.",
    },
    {
        "project": "markets",
        "cycle_index": 0,
        "state": "Done",
        "priority": 2,
        "estimate": 2,
        "label": "Bug",
        "title": "Fix VAT round-off discrepancy for European union B2C orders",
        "description": "Adjusted gross-price rounding algorithm to calculate VAT at the line-item level rather than cart subtotal to strictly adhere to EU One-Stop Shop (OSS) regulations.",
    },
    {
        "project": "markets",
        "cycle_index": 1,
        "state": "Todo",
        "priority": 3,
        "estimate": 5,
        "label": "Feature",
        "title": "Localized payment methods integration: iDEAL, Bancontact, and Pix",
        "description": "Expand localized instant bank transfer payment options for Dutch, Belgian, and Brazilian merchants on Markets Pro checkout.",
    },

    # Project 6: B2B Wholesale Portal
    {
        "project": "b2b",
        "cycle_index": 0,
        "state": "Done",
        "priority": 1,
        "estimate": 8,
        "label": "Feature",
        "title": "Net 30/60 deferred payment terms invoicing workflow engine",
        "description": "Automated B2B payment terms evaluation with merchant credit limit verification and automated dunning invoice email sequences.",
    },
    {
        "project": "b2b",
        "cycle_index": 0,
        "state": "In Progress",
        "priority": 2,
        "estimate": 5,
        "label": "Feature",
        "title": "Tiered wholesale volume pricing matrix evaluator in Storefront API",
        "description": "High-performance evaluation of negotiated catalog pricing rules (e.g. 50+ units = 20% off, 200+ units = 35% off) within Storefront GraphQL query response.",
    },
    {
        "project": "b2b",
        "cycle_index": 1,
        "state": "Todo",
        "priority": 2,
        "estimate": 8,
        "label": "Feature",
        "title": "Company account hierarchy with purchaser spending approval limits",
        "description": "Multi-tier organizational structure allowing B2B buyers to invite procurement staff with order submission limits and manager sign-off workflows.",
    },
    {
        "project": "b2b",
        "cycle_index": None,
        "state": "Backlog",
        "priority": 3,
        "estimate": 3,
        "label": "Improvement",
        "title": "B2B quick-order CSV upload parser and line-item bulk validator",
        "description": "Allow enterprise wholesale buyers to drag-and-drop a CSV file with SKU and quantity columns, adding 500+ items directly to their B2B checkout cart in < 2 seconds.",
    },
]


def execute_graphql(client: httpx.Client, query: str, variables: dict = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = client.post(ENDPOINT, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if "errors" in data and not data.get("data"):
        raise RuntimeError(f"GraphQL Errors: {json.dumps(data['errors'])}")
    return data


def seed_linear():
    print("=" * 65)
    print("🚀 SWARMING LINEAR WITH SIMULATED SHOPIFY PRODUCT & ENG TELEMETRY")
    print("=" * 65)

    client = httpx.Client(headers=HEADERS, timeout=30.0)

    try:
        # 1. Fetch team SHO metadata
        team_query = """
        query {
          teams(first: 5) {
            nodes {
              id
              name
              key
              states(first: 20) {
                nodes { id name type }
              }
              labels(first: 20) {
                nodes { id name }
              }
            }
          }
        }
        """
        res = execute_graphql(client, team_query)
        teams = res.get("data", {}).get("teams", {}).get("nodes", [])
        if not teams:
            print("❌ No teams found in Linear workspace.")
            return

        team = teams[0]
        team_id = team["id"]
        print(f"🏢 Active Linear Team: {team['name']} ({team['key']}) [ID: {team_id}]")

        # Map states and labels
        states_map = {s["name"]: s["id"] for s in team.get("states", {}).get("nodes", [])}
        labels_map = {l["name"].lower(): l["id"] for l in team.get("labels", {}).get("nodes", [])}
        print(f"• States available: {list(states_map.keys())}")
        print(f"• Labels available: {list(labels_map.keys())}")

        # 2. Configure cycles
        print("\n📅 Configuring Sprint Cycles...")
        enable_cycles_mutation = """
        mutation TeamUpdate($id: String!, $input: TeamUpdateInput!) {
          teamUpdate(id: $id, input: $input) {
            success
            team {
              id
              cycles {
                nodes { id number name }
              }
            }
          }
        }
        """
        execute_graphql(client, enable_cycles_mutation, {
            "id": team_id,
            "input": {"cyclesEnabled": True, "cycleDuration": 2, "cycleStartDay": 1}
        })

        # Fetch cycles
        cycles_query = """
        query TeamCycles($id: String!) {
          team(id: $id) {
            cycles(first: 5) {
              nodes { id number name startsAt endsAt }
            }
          }
        }
        """
        c_res = execute_graphql(client, cycles_query, {"id": team_id})
        cycles = c_res.get("data", {}).get("team", {}).get("cycles", {}).get("nodes", [])
        # Sort by number
        cycles = sorted(cycles, key=lambda c: c.get("number", 0))

        cycle_update_mutation = """
        mutation CycleUpdate($id: String!, $input: CycleUpdateInput!) {
          cycleUpdate(id: $id, input: $input) {
            success
            cycle { id name number }
          }
        }
        """
        cycle_names = [
            "Sprint 42 - Shop Pay & Checkout Latency Optimization",
            "Sprint 43 - Sidekick AI & Headless Hydrogen Architecture"
        ]
        cycle_ids = []
        for i, cyc in enumerate(cycles[:2]):
            c_name = cycle_names[i]
            execute_graphql(client, cycle_update_mutation, {
                "id": cyc["id"],
                "input": {"name": c_name}
            })
            cycle_ids.append(cyc["id"])
            print(f"  ⚡ Cycle {cyc['number']}: {c_name} (ID: {cyc['id']})")

        # 3. Create Roadmap Projects
        print("\n🗺️ Creating Shopify Roadmap Projects...")
        project_create_mutation = """
        mutation ProjectCreate($input: ProjectCreateInput!) {
          projectCreate(input: $input) {
            success
            project { id name url }
          }
        }
        """
        created_projects = {}
        for p in PROJECTS_DATA:
            p_input = {
                "name": p["name"],
                "description": p["description"],
                "teamIds": [team_id],
                "color": p["color"],
                "targetDate": p["targetDate"],
            }
            res = execute_graphql(client, project_create_mutation, {"input": p_input})
            proj = res.get("data", {}).get("projectCreate", {}).get("project", {})
            created_projects[p["key"]] = proj.get("id")
            print(f"  📁 Project Created: {p['name']} (ID: {proj.get('id')})")
            time.sleep(0.2)

        # 4. Create Issues
        print(f"\n🎫 Creating {len(ISSUES_DATA)} Shopify Engineering Issues...")
        issue_create_mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { id title identifier url }
          }
        }
        """
        created_issues_count = 0
        for idx, item in enumerate(ISSUES_DATA, start=1):
            state_name = item["state"]
            state_id = states_map.get(state_name)
            project_id = created_projects.get(item["project"])
            cycle_idx = item.get("cycle_index")
            cycle_id = cycle_ids[cycle_idx] if (cycle_idx is not None and cycle_idx < len(cycle_ids)) else None
            
            label_id = labels_map.get(item["label"].lower())
            label_ids = [label_id] if label_id else []

            issue_input = {
                "teamId": team_id,
                "title": item["title"],
                "description": item["description"],
                "priority": item["priority"],
                "estimate": item["estimate"],
                "stateId": state_id,
                "projectId": project_id,
                "labelIds": label_ids,
            }
            if cycle_id:
                issue_input["cycleId"] = cycle_id

            res = execute_graphql(client, issue_create_mutation, {"input": issue_input})
            issue = res.get("data", {}).get("issueCreate", {}).get("issue", {})
            created_issues_count += 1
            print(f"  [{idx}/{len(ISSUES_DATA)}] ({issue.get('identifier', 'SHO')}) [{item['state'].upper()}] {item['title'][:55]}...")
            time.sleep(0.18)

        print("\n" + "=" * 65)
        print("✅ LINEAR SHOPIFY SEEDING COMPLETE")
        print("=" * 65)
        print(f"• Sprints / Cycles Configured: {len(cycle_ids)}")
        print(f"• Roadmap Projects Created:    {len(created_projects)}")
        print(f"• Engineering Issues Created:  {created_issues_count}")
        print("=" * 65)

    finally:
        client.close()


if __name__ == "__main__":
    seed_linear()
