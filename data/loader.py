import json
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional

DATA_DIR = Path(__file__).resolve().parent
SYNTHETIC_COMPANY_PATH = DATA_DIR / "synthetic_company.json"
SEEDED_DECISIONS_PATH = DATA_DIR / "seeded_decisions.json"
BENCHMARKS_PATH = DATA_DIR / "benchmarks.json"
MODEL_CONFIG_PATH = DATA_DIR / "model_config.json"

DEFAULT_COMPANY_DATA: Dict[str, Any] = {
    "company_name": "NimbusDesk",
    "tagline": "AI-Powered Customer Support Platform for Mid-Market B2B",
    "stage": "Series A",
    "currency": "USD",
    "synthetic_data_badge": True,
    "financials": {
        "mrr": 110370,
        "arr": 1324440,
        "cash_balance": 1650000,
        "monthly_burn_gross": 235370,
        "monthly_burn_net": 125000,
        "runway_months": 13.2,
        "gross_margin": 0.74,
        "target_min_runway_months": 10.0
    },
    "customers": {
        "total_paying": 655,
        "monthly_churn_rate": 0.021,
        "plans": [
            {
                "name": "Starter",
                "price_monthly": 79,
                "count": 450,
                "mrr": 35550
            },
            {
                "name": "Pro",
                "price_monthly": 249,
                "count": 180,
                "mrr": 44820
            },
            {
                "name": "Enterprise",
                "price_monthly": 1200,
                "count": 25,
                "mrr": 30000
            }
        ]
    },
    "unit_economics": {
        "cac": 1450,
        "ltv": 4850,
        "arpu": 168.50,
        "payback_months": 8.6
    },
    "funnel": {
        "monthly_visitors": 65000,
        "trial_signups": 1100,
        "trial_to_paid_conversion": 0.048,
        "new_paid_customers_monthly": 53
    },
    "infrastructure": {
        "monthly_cloud_cost": 14500,
        "infra_cost_per_paid_user": 22.14,
        "infra_cost_per_free_user_estimate": 1.15
    },
    "support": {
        "headcount_fte": 4,
        "monthly_support_cost": 28000,
        "monthly_tickets": 1200,
        "tickets_per_fte_monthly": 300,
        "cost_per_ticket": 23.33,
        "free_user_ticket_rate_estimate": 0.12
    },
    "engineering": {
        "total_headcount": 8,
        "available_fte_for_packaging": 2.0
    }
}

def load_model_config(file_path: Optional[Path] = None) -> Dict[str, Any]:
    path = file_path or MODEL_CONFIG_PATH
    if not path.exists():
        return {
            "baseline_activation_rate": 0.35,
            "free_user_monthly_churn": 0.12,
            "monthly_support_cost_per_fte": 7000.0,
            "tickets_per_fte_monthly": 300,
            "paid_tickets_per_customer_monthly": 1.83,
            "illustrative": True
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_benchmarks(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = file_path or BENCHMARKS_PATH
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_company_data(file_path: Optional[Path] = None) -> Dict[str, Any]:
    path = file_path or SYNTHETIC_COMPANY_PATH
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return copy.deepcopy(DEFAULT_COMPANY_DATA)

def get_company_snapshot(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Returns high-level snapshot suitable for dashboard display and agent prompt context.
    """
    raw = load_company_data(file_path)
    return {
        "company_name": raw["company_name"],
        "stage": raw["stage"],
        "currency": raw["currency"],
        "synthetic_data_badge": raw["synthetic_data_badge"],
        "mrr": raw["financials"]["mrr"],
        "arr": raw["financials"]["arr"],
        "cash_balance": raw["financials"]["cash_balance"],
        "runway_months": raw["financials"]["runway_months"],
        "monthly_burn_net": raw["financials"]["monthly_burn_net"],
        "gross_margin": raw["financials"]["gross_margin"],
        "paying_customers": raw["customers"]["total_paying"],
        "monthly_churn_rate": raw["customers"]["monthly_churn_rate"],
        "cac": raw["unit_economics"]["cac"],
        "ltv": raw["unit_economics"]["ltv"],
        "monthly_visitors": raw["funnel"]["monthly_visitors"],
        "trial_to_paid_conversion": raw["funnel"]["trial_to_paid_conversion"],
        "infra_cost_monthly": raw["infrastructure"]["monthly_cloud_cost"],
        "support_headcount": raw["support"]["headcount_fte"],
        "support_cost_monthly": raw["support"]["monthly_support_cost"]
    }

def load_seeded_decisions(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = file_path or SEEDED_DECISIONS_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

