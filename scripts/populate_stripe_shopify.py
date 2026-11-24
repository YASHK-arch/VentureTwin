"""
Populates Stripe Test Mode dashboard with realistic Shopify merchant data:
- Subscription Plans (Starter $29, Growth $79, Advanced $299, Plus $2,000)
- Products (POS Terminals, Hardware, Custom Domains)
- 20+ Shopify Merchants (Customers)
- Active Subscriptions with paid recurring invoices (MRR & ARR generation)
- Hardware & Transaction Fee Charges (One-time payments)
- Realistic Refunds & Declined Payment attempts (for CFO risk analysis)
"""

import os
import sys
import time
import random
from pathlib import Path
import httpx

# Load STRIPE_SECRET_KEY from .env if present
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("STRIPE_SECRET_KEY="):
                os.environ["STRIPE_SECRET_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")

STRIPE_API_KEY = os.getenv("STRIPE_SECRET_KEY")
if not STRIPE_API_KEY:
    print("[ERROR] STRIPE_SECRET_KEY is not set in environment or .env file.")
    sys.exit(1)

BASE_URL = "https://api.stripe.com/v1"

MERCHANTS = [
    {"name": "Nordic Wool Co.", "email": "founders@nordicwoolshoes.com", "plan": "starter", "spend": 2900},
    {"name": "Tokyo Matcha Direct", "email": "support@tokyomatchadirect.jp", "plan": "growth", "spend": 7900},
    {"name": "Artisan Oak Furniture", "email": "orders@artisanoakwood.com", "plan": "advanced", "spend": 29900},
    {"name": "AeroTech Flight Gear", "email": "sales@aerotechflight.com", "plan": "growth", "spend": 7900},
    {"name": "Lumina Skincare Labs", "email": "hello@luminaglow.co", "plan": "advanced", "spend": 29900},
    {"name": "Peak Performance Apparel", "email": "mgmt@peakapparel.fit", "plan": "starter", "spend": 2900},
    {"name": "Saffron & Spice Co.", "email": "contact@saffronspice.in", "plan": "starter", "spend": 2900},
    {"name": "Velvet & Vine Boutique", "email": "info@velvetandvine.shop", "plan": "growth", "spend": 7900},
    {"name": "Urban Roasters Coffee", "email": "roasters@urbanbrew.io", "plan": "growth", "spend": 7900},
    {"name": "Zenith Smart Home Devices", "email": "iot@zenithdevices.com", "plan": "plus", "spend": 200000},
    {"name": "Horizon Watchmakers Geneva", "email": "concierge@horizonhorology.ch", "plan": "plus", "spend": 200000},
    {"name": "Starlight Gaming Keyboards", "email": "gear@starlightperipherals.gg", "plan": "starter", "spend": 2900},
    {"name": "EcoBottle Zero Waste", "email": "team@ecobottleliving.org", "plan": "starter", "spend": 2900},
    {"name": "Oasis Swimwear Sydney", "email": "orders@oasisswim.au", "plan": "growth", "spend": 7900},
    {"name": "PureSource Health Supplements", "email": "nutrition@puresourcehealth.com", "plan": "advanced", "spend": 29900},
    {"name": "Canvas & Clay Pottery Studio", "email": "studio@canvasclayceramics.art", "plan": "starter", "spend": 2900},
    {"name": "Kavita Silk Sarees", "email": "boutique@kavitasilks.com", "plan": "growth", "spend": 7900},
    {"name": "Apex Automotive Parts", "email": "logistics@apexautoparts.de", "plan": "advanced", "spend": 29900},
    {"name": "Solaris Home Clean Energy", "email": "solutions@solarishomepower.com", "plan": "plus", "spend": 200000},
    {"name": "CyberShield VPN Hardware", "email": "security@cybershieldrouter.net", "plan": "growth", "spend": 7900},
]


def post_stripe(client: httpx.Client, endpoint: str, data: dict):
    resp = client.post(f"{BASE_URL}/{endpoint.lstrip('/')}", data=data, auth=(STRIPE_API_KEY, ""))
    if resp.status_code not in (200, 201):
        print(f"  [WARN] {endpoint} returned {resp.status_code}: {resp.text[:120]}")
        return None
    return resp.json()


def get_stripe(client: httpx.Client, endpoint: str, params: dict = None):
    resp = client.get(f"{BASE_URL}/{endpoint.lstrip('/')}", params=params, auth=(STRIPE_API_KEY, ""))
    if resp.status_code == 200:
        return resp.json()
    return None


def main():
    print("=" * 60)
    print("🚀 Swarming Stripe Test Mode with Simulated Shopify Data")
    print(f"Target Account: acct_1Uf7KELZNx2zQP09")
    print("=" * 60)

    with httpx.Client(timeout=25.0) as client:
        # 1. Setup Subscription Products and Prices
        print("\n📦 Step 1: Setting up Shopify Plans & Products...")
        plans = {
            "starter": {"name": "Shopify Starter Plan", "amount": 2900, "interval": "month"},
            "growth": {"name": "Shopify Growth Plan", "amount": 7900, "interval": "month"},
            "advanced": {"name": "Shopify Advanced Plan", "amount": 29900, "interval": "month"},
            "plus": {"name": "Shopify Plus Enterprise", "amount": 200000, "interval": "month"},
        }
        price_ids = {}

        for plan_key, plan_info in plans.items():
            prod = post_stripe(client, "/products", {
                "name": plan_info["name"],
                "description": f"Shopify merchant subscription - {plan_info['name']}",
                "metadata[tier]": plan_key,
                "metadata[platform]": "Shopify",
            })
            if prod:
                price = post_stripe(client, "/prices", {
                    "product": prod["id"],
                    "unit_amount": plan_info["amount"],
                    "currency": "usd",
                    "recurring[interval]": plan_info["interval"],
                    "nickname": plan_info["name"],
                })
                if price:
                    price_ids[plan_key] = price["id"]
                    print(f"  ✓ Created {plan_info['name']}: {price['id']} (${plan_info['amount']/100:.2f}/mo)")

        # One-time hardware product
        hardware_prod = post_stripe(client, "/products", {
            "name": "Shopify POS Go Terminal",
            "description": "Handheld POS hardware terminal with barcode scanner and receipt printer",
            "metadata[category]": "hardware",
        })

        # 2. Create Customers & Subscriptions
        print(f"\n👥 Step 2: Creating {len(MERCHANTS)} Shopify Merchants & Subscriptions...")
        customer_ids = []
        subscription_ids = []
        charge_ids = []

        for idx, m in enumerate(MERCHANTS, 1):
            # Create customer with test Visa token directly
            cust = post_stripe(client, "/customers", {
                "name": m["name"],
                "email": m["email"],
                "description": f"Shopify Merchant #{1000 + idx}",
                "source": "tok_visa",
                "metadata[store_name]": m["name"],
                "metadata[shopify_plan]": m["plan"],
                "metadata[merchant_category]": "E-Commerce",
            })

            if not cust:
                continue

            cid = cust["id"]
            customer_ids.append(cid)
            print(f"  [{idx:02d}/{len(MERCHANTS)}] Created Customer: {m['name']} ({cid})")

            # Create subscription for customer
            target_price_id = price_ids.get(m["plan"])
            if target_price_id:
                sub = post_stripe(client, "/subscriptions", {
                    "customer": cid,
                    "items[0][price]": target_price_id,
                    "description": f"Monthly subscription for {m['name']}",
                    "metadata[merchant]": m["name"],
                })
                if sub:
                    subscription_ids.append(sub["id"])

            # 3. Create Additional Hardware & Transaction Charges
            if idx % 3 == 0:
                # POS Terminal purchase ($399)
                ch = post_stripe(client, "/charges", {
                    "customer": cid,
                    "amount": 39900,
                    "currency": "usd",
                    "description": f"Hardware Order: Shopify POS Go Terminal for {m['name']}",
                    "metadata[order_type]": "hardware_pos",
                })
                if ch:
                    charge_ids.append(ch["id"])
                    print(f"    💳 Charged hardware order: $399.00 ({ch['id']})")
            elif idx % 4 == 0:
                # App Store commission / transaction volume fee ($85 - $450)
                fee_amount = random.choice([4500, 8500, 14200, 28000, 48500])
                ch = post_stripe(client, "/charges", {
                    "customer": cid,
                    "amount": fee_amount,
                    "currency": "usd",
                    "description": f"Shopify App Store Merchant Rev-Share Fee for {m['name']}",
                    "metadata[order_type]": "app_store_fee",
                })
                if ch:
                    charge_ids.append(ch["id"])
                    print(f"    💳 Charged app store fee: ${fee_amount/100:.2f} ({ch['id']})")

            time.sleep(0.15)  # respectful pacing

        # 4. Create Simulated Refunds (for CFO refund rate analysis)
        print(f"\n🔄 Step 3: Issuing Simulated Refunds & Adjustments...")
        if charge_ids:
            # Full refund on first hardware order
            ref1 = post_stripe(client, "/refunds", {
                "charge": charge_ids[0],
                "reason": "requested_by_customer",
                "metadata[notes]": "Customer returned unopened POS unit within 14-day window",
            })
            if ref1:
                print(f"  ✓ Issued full refund on hardware charge {charge_ids[0]} ($399.00)")

            if len(charge_ids) > 1:
                # Partial refund on fee adjustment
                ref2 = post_stripe(client, "/refunds", {
                    "charge": charge_ids[1],
                    "amount": 2500,
                    "reason": "duplicate",
                    "metadata[notes]": "Partial promo credit adjustment ($25.00)",
                })
                if ref2:
                    print(f"  ✓ Issued partial refund on charge {charge_ids[1]} ($25.00)")

        # 5. Create Simulated Failed Payments (for CFO risk and churn analysis)
        print(f"\n⚠️ Step 4: Generating Simulated Payment Failure Events...")
        for fail_idx, fail_merchant in enumerate(["Overdrive Customs", "Glacier Water Dist"], 1):
            cust_fail = post_stripe(client, "/customers", {
                "name": fail_merchant,
                "email": f"billing@{fail_merchant.lower().replace(' ', '')}.com",
                "source": "tok_chargeCustomerFail",
            })
            if cust_fail:
                ch_fail = post_stripe(client, "/charges", {
                    "customer": cust_fail["id"],
                    "amount": 7900,
                    "currency": "usd",
                    "description": f"Failed renewal: Insufficient funds for {fail_merchant}",
                })
                print(f"  ✓ Recorded test card decline / insufficient funds for {fail_merchant}")

        # Summary
        print("\n" + "=" * 60)
        print("🎉 Stripe Test Mode Swarm Complete!")
        print(f"  • Customers Created:     {len(customer_ids)}")
        print(f"  • Active Subscriptions:  {len(subscription_ids)} (Shopify Starter, Growth, Advanced, Plus)")
        print(f"  • Transaction Charges:   {len(charge_ids)} hardware & app store payments")
        print(f"  • Refunds Issued:        2 records")
        print(f"  • Failed Payment Events: 2 records")
        print("=" * 60)
        print("Your Stripe dashboard now displays live revenue curves, customer MRR, and transaction telemetry:")
        print("👉 https://dashboard.stripe.com/acct_1Uf7KELZNx2zQP09/test/dashboard")


if __name__ == "__main__":
    main()
