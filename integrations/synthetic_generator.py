"""
Synthetic Data Generation Service for VentureTwin.

Generates logically linked, multi-domain synthetic business telemetry
for companies such as Shopify and Nextcloud across 12-month historical windows:
- Merchants / Customers
- Payments & Invoices (Stripe / QuickBooks)
- Subscriptions & MRR cohorts
- CRM Leads, Pipelines & Deals (HubSpot)
- Web Traffic, Sessions & Funnel Conversions (GA4)
- Engineering Commits, PRs & Issues (GitHub)
- Cloud Infrastructure Metrics & SLA Latency (CloudWatch)
- Support Tickets & Customer Inquiries (Intercom / Zendesk)
- Product Analytics Events & Feature Adoption (PostHog)
- Roadmap Backlog, Cycles & Initiatives (Linear)
"""

import random
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional


FIRST_NAMES = ["Elena", "Marcus", "Siddharth", "Aisha", "Liam", "Chen", "Sophia", "Mateo", "Priya", "Oliver", "Zoe", "Kenji"]
LAST_NAMES = ["Rostova", "Vance", "Mehta", "Al-Mansoor", "O'Connor", "Wei", "Lindqvist", "Silva", "Patel", "Davies", "Dubois", "Tanaka"]
COMPANY_SUFFIXES = ["Labs", "Technologies", "Commerce", "Cloud", "Logistics", "Ventures", "Systems", "HQ", "Direct"]


class SyntheticDataGenerator:
    """Generates cohesive cross-domain synthetic business records."""

    def __init__(self, company_profile: Optional[Dict[str, Any]] = None):
        self.profile = company_profile or {}
        self.company_name = self.profile.get("company_name", "ShopifyStorefront")
        self.industry = self.profile.get("industry", "E-commerce & SaaS")
        self.business_model = self.profile.get("business_model", "B2B SaaS / Marketplace")
        # Deterministic seed based on company name
        seed_int = int(hashlib.sha256(self.company_name.encode()).hexdigest()[:8], 16)
        self.rng = random.Random(seed_int)

    def _rand_date(self, days_back_max: int = 365, days_back_min: int = 0) -> str:
        delta = self.rng.randint(days_back_min, days_back_max)
        dt = datetime.now(timezone.utc) - timedelta(days=delta, minutes=self.rng.randint(0, 1440))
        return dt.isoformat()

    def generate_customer_base(self, count: int = 50, months_back: int = 12) -> List[Dict[str, Any]]:
        """Generates consistent customer identities used across all integrations."""
        customers = []
        clean_name = "".join(c.lower() for c in self.company_name if c.isalnum())
        plans = ["Starter ($79/mo)", "Pro ($249/mo)", "Enterprise ($1,200/mo)"]
        weights = [0.65, 0.28, 0.07]

        for i in range(count):
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            comp = f"{last} {self.rng.choice(COMPANY_SUFFIXES)}"
            plan = self.rng.choices(plans, weights=weights)[0]
            cid = f"cus_{clean_name}_{i+1001}"
            created_at = self._rand_date(days_back_max=months_back * 30, days_back_min=5)
            
            customers.append({
                "customer_id": cid,
                "name": f"{first} {last}",
                "email": f"{first.lower()}.{last.lower()}@{clean_name}user.io",
                "company": comp,
                "plan": plan,
                "mrr": 79 if "Starter" in plan else (249 if "Pro" in plan else 1200),
                "created_at": created_at,
                "status": "active" if i % 15 != 0 else "churned",
            })
        return customers

    def generate_financial_records(self, customers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Generates Stripe & QuickBooks records linked to customers."""
        charges = []
        invoices = []
        expenses = []

        for c in customers:
            if c["status"] == "active":
                amount_cents = c["mrr"] * 100
                charge_id = f"ch_syn_{c['customer_id'][-4:]}"
                charges.append({
                    "id": charge_id,
                    "customer_id": c["customer_id"],
                    "customer_name": c["name"],
                    "amount": c["mrr"],
                    "currency": "usd",
                    "status": "succeeded",
                    "plan": c["plan"],
                    "created_at": self._rand_date(days_back_max=30),
                })
                invoices.append({
                    "id": f"inv_syn_{c['customer_id'][-4:]}",
                    "customer_id": c["customer_id"],
                    "amount": c["mrr"],
                    "status": "paid",
                    "due_date": self._rand_date(days_back_max=15),
                })

        # Operational SaaS expenses (QuickBooks)
        expense_cats = [
            ("AWS Cloud Hosting", 14500.0),
            ("GSuite & Dev Tooling", 3200.0),
            ("Customer Support Salaries", 28000.0),
            ("Marketing & Paid Acquisition", 24000.0),
            ("Office & Distributed Stipends", 4500.0),
        ]
        for idx, (cat, base_amt) in enumerate(expense_cats):
            variation = base_amt * (1.0 + self.rng.uniform(-0.08, 0.08))
            expenses.append({
                "id": f"exp_syn_{idx+101}",
                "category": cat,
                "amount": round(variation, 2),
                "vendor": cat.split()[0],
                "date": self._rand_date(days_back_max=30),
            })

        return {"charges": charges, "invoices": invoices, "expenses": expenses}

    def generate_growth_records(self, count: int = 100) -> Dict[str, Any]:
        """Generates HubSpot CRM deals and GA4 session events."""
        deals = []
        stages = ["Lead", "Demo Scheduled", "Trial Initiated", "Security Review", "Closed Won", "Closed Lost"]
        stages_weights = [0.35, 0.20, 0.18, 0.12, 0.10, 0.05]

        for i in range(count):
            first = self.rng.choice(FIRST_NAMES)
            last = self.rng.choice(LAST_NAMES)
            stage = self.rng.choices(stages, weights=stages_weights)[0]
            val = self.rng.choice([948, 2988, 14400])
            deals.append({
                "deal_id": f"deal_syn_{i+5001}",
                "deal_name": f"{last} Enterprise Expansion",
                "contact_email": f"{first.lower()}@{last.lower()}enterprises.com",
                "stage": stage,
                "amount": val,
                "pipeline": "Mid-Market B2B",
                "close_probability": 0.9 if stage == "Closed Won" else (0.6 if stage == "Security Review" else 0.25),
                "created_at": self._rand_date(days_back_max=90),
            })

        # Web analytics aggregate metrics (GA4)
        ga4_summary = {
            "monthly_active_users": 65000 + self.rng.randint(-2000, 4000),
            "sessions": 112000 + self.rng.randint(-5000, 8000),
            "bounce_rate": 0.42 + self.rng.uniform(-0.03, 0.04),
            "avg_session_duration_sec": 195 + self.rng.randint(-20, 30),
            "trial_conversions": 1100 + self.rng.randint(-80, 120),
            "top_channels": [
                {"channel": "Organic Search", "share": 0.44},
                {"channel": "Direct", "share": 0.26},
                {"channel": "Referral", "share": 0.18},
                {"channel": "Paid Search", "share": 0.12},
            ]
        }
        return {"deals": deals, "analytics": ga4_summary}

    def generate_engineering_records(self, repo_name: str = "main-app") -> Dict[str, Any]:
        """Generates GitHub commits/PRs and CloudWatch system telemetry."""
        commits = []
        prs = []
        commit_msgs = [
            "feat: optimize database connection pooling for high load",
            "fix: reconcile billing invoice timestamp formatting",
            "chore: upgrade node dependencies and patch security alerts",
            "perf: cache user permissions in Redis for fast dashboard load",
            "test: add integration test suite for payment refund webhooks"
        ]
        for i in range(25):
            commits.append({
                "sha": hashlib.sha1(f"commit_{i}_{self.company_name}".encode()).hexdigest()[:10],
                "message": commit_msgs[i % len(commit_msgs)],
                "author": f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                "date": self._rand_date(days_back_max=30),
            })

        for i in range(8):
            prs.append({
                "number": 120 + i,
                "title": f"PR: {commit_msgs[i % len(commit_msgs)]}",
                "state": "closed" if i < 6 else "open",
                "author": self.rng.choice(FIRST_NAMES).lower(),
                "created_at": self._rand_date(days_back_max=20),
            })

        cloudwatch_metrics = {
            "avg_cpu_utilization_pct": round(32.4 + self.rng.uniform(-4.0, 8.0), 1),
            "avg_memory_utilization_pct": round(58.2 + self.rng.uniform(-5.0, 6.0), 1),
            "api_p95_latency_ms": round(142.0 + self.rng.uniform(-15.0, 30.0), 1),
            "monthly_cloud_spend_usd": 14500.0,
            "sla_availability_pct": 99.94,
            "error_rate_pct": 0.08,
        }
        return {"commits": commits, "pull_requests": prs, "cloudwatch": cloudwatch_metrics}

    def generate_support_records(self, customers: List[Dict[str, Any]], count: int = 40) -> List[Dict[str, Any]]:
        """Generates Intercom & Zendesk support tickets linked to real customer profiles."""
        tickets = []
        subjects = [
            "Assistance with SSO authentication setup",
            "Question regarding invoice VAT line item",
            "API rate limit exceeded during batch export",
            "Webhook delivery delay during peak hours",
            "Feature request: custom role permissions",
            "Integration with external warehouse catalog"
        ]
        priorities = ["normal", "high", "low", "urgent"]

        for i in range(count):
            cust = customers[i % len(customers)]
            subj = subjects[i % len(subjects)]
            tickets.append({
                "ticket_id": f"ticket_syn_{i+2001}",
                "customer_id": cust["customer_id"],
                "customer_name": cust["name"],
                "subject": subj,
                "status": "solved" if i % 4 != 0 else "pending",
                "priority": self.rng.choice(priorities),
                "resolution_time_hrs": round(self.rng.uniform(1.2, 18.5), 1),
                "created_at": self._rand_date(days_back_max=45),
            })
        return tickets

    def generate_full_company_dataset(self) -> Dict[str, Any]:
        """Generates a cohesive 12-domain company telemetry bundle."""
        customers = self.generate_customer_base(count=60)
        financials = self.generate_financial_records(customers)
        growth = self.generate_growth_records(count=80)
        engineering = self.generate_engineering_records()
        support = self.generate_support_records(customers, count=50)

        return {
            "company_name": self.company_name,
            "industry": self.industry,
            "business_model": self.business_model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provenance": {
                "type": "synthetic_internal",
                "source": "venturetwin_generator",
                "generator_version": "1.0.0"
            },
            "customers": customers,
            "financials": financials,
            "growth": growth,
            "engineering": engineering,
            "support": support,
        }
