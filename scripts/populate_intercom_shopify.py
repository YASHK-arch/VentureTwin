"""
Populates Intercom with a realistic, simulated Shopify merchant support dataset:
- 40 Shopify merchants as contacts with plan, MRR, store, and segment attributes
- Tags per subscription plan and support theme
- Support conversations with admin replies and a mix of open/closed states
- Resilient upsert: searches existing contacts on 409 conflict
- Syncs normalized records directly into VentureTwin's integration store
- Marks Intercom connector as connected in database
"""

import os
import sys
import time
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx

# Load .env
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

INTERCOM_TOKEN = os.getenv("INTERCOM_ACCESS_TOKEN")
if not INTERCOM_TOKEN:
    print("[ERROR] INTERCOM_ACCESS_TOKEN is not set in environment or .env file.")
    sys.exit(1)

BASE_URL = "https://api.intercom.io"
HEADERS = {
    "Authorization": f"Bearer {INTERCOM_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Intercom-Version": "2.11",
}

MERCHANTS = [
    # --- Batch 1: Core E-Commerce & Platform Operations (1-20) ---
    {
        "name": "Henrik Lindqvist",
        "store": "Nordic Wool Co.",
        "email": "henrik@nordicwoolshoes.com",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "Shop Pay checkout failures",
        "issue": "Shop Pay checkout is failing for customers in Germany after we enabled Markets Pro. Orders show as paid in Shopify but the checkout confirmation never loads.",
        "reply": "Thanks for flagging this. Our payments team has reproduced the redirect issue on EU storefronts and rolled out a fix. Please retry a test checkout and let us know if the confirmation still stalls.",
        "close": True
    },
    {
        "name": "Yuki Tanaka",
        "store": "Tokyo Matcha Direct",
        "email": "yuki@tokyomatchadirect.jp",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Payout delay",
        "issue": "Our Shopify Payments payout for last week has not arrived. The balance shows as paid in the admin but there is no transaction in our bank account.",
        "reply": "I checked your payout timeline. The batch is still in the standard 3-day settlement window and should land tomorrow. I have added a note to your account so our billing team can escalate if it slips.",
        "close": True
    },
    {
        "name": "Amelia Grant",
        "store": "Artisan Oak Furniture",
        "email": "amelia@artisanoakwood.com",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "POS Go hardware",
        "issue": "Two of our POS Go terminals go offline whenever the store WiFi drops. Can they keep processing orders using cellular backup?",
        "reply": "POS Go supports offline mode for card-present transactions and will sync once connectivity returns. I have sent your team the offline setup guide and the steps to enable automatic receipts.",
        "close": True
    },
    {
        "name": "Marcus Webb",
        "store": "AeroTech Flight Gear",
        "email": "marcus@aerotechflight.com",
        "plan": "Growth",
        "mrr": 79,
        "theme": "App Store billing",
        "issue": "We were charged twice for our app subscription this month. Can you confirm which invoice is the duplicate and issue a refund?",
        "reply": "I found a duplicate charge from the 3rd and have issued a full refund to the original payment method. It should appear within 5 to 7 business days.",
        "close": True
    },
    {
        "name": "Priya Nair",
        "store": "Lumina Skincare Labs",
        "email": "priya@luminaglow.co",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "Inventory sync",
        "issue": "Inventory counts are out of sync between our warehouse system and Shopify. We are overselling products that show zero stock in the warehouse.",
        "reply": "I have escalated the connector issue to our integrations team. In the meantime, setting a safety stock threshold of 5 units in your inventory settings will prevent further overselling.",
        "close": True
    },
    {
        "name": "Daniel Okafor",
        "store": "Peak Performance Apparel",
        "email": "daniel@peakapparel.fit",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Plan upgrade",
        "issue": "We are hitting the product limit on the Starter plan. What is involved in moving to Growth, and will our storefront have any downtime?",
        "reply": "Upgrading to Growth is instant and does not require storefront downtime. Your existing products, themes and customer data stay exactly as they are, and the new limits apply right away.",
        "close": True
    },
    {
        "name": "Ananya Rao",
        "store": "Saffron & Spice Co.",
        "email": "ananya@saffronspice.in",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Markets Pro duties",
        "issue": "Duties are not being calculated correctly on orders shipped to the UK since we turned on Markets Pro. Customers are being asked to pay at delivery.",
        "reply": "I have reviewed three affected orders and confirmed the duty mapping issue for UK destinations. Our team is updating the rate table now, and I will follow up once the recalculation completes.",
        "close": False
    },
    {
        "name": "Sofia Moretti",
        "store": "Velvet & Vine Boutique",
        "email": "sofia@velvetandvine.shop",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Theme editor",
        "issue": "The theme editor keeps timing out when I save changes to the product page template. I am losing about 20 minutes of work each time.",
        "reply": "I have cleared the stale editor session on your account. Please try saving again in a private window. If it recurs, send me the browser version and I will open a bug report with the editor team.",
        "close": True
    },
    {
        "name": "Liam Fletcher",
        "store": "Urban Roasters Coffee",
        "email": "liam@urbanbrew.io",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Subscriptions",
        "issue": "Customers on weekly coffee subscriptions are receiving duplicate orders after we changed our billing cycle from 7 to 14 days.",
        "reply": "The duplicate orders came from a migration job that ran twice. I have cancelled the extra orders and refunded them; your active subscriptions are now on the correct 14-day cycle.",
        "close": True
    },
    {
        "name": "Grace Kim",
        "store": "Zenith Smart Home Devices",
        "email": "grace@zenithdevices.com",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "Enterprise onboarding",
        "issue": "We are migrating three regional stores onto Shopify Plus next month and need a technical contact to review the custom checkout requirements.",
        "reply": "I have arranged a migration planning call with our Plus solutions engineer for next Tuesday. They will review your checkout extensions and provide a cutover checklist ahead of the migration.",
        "close": False
    },
    {
        "name": "Thierry Dubois",
        "store": "Horizon Watchmakers Geneva",
        "email": "thierry@horizonhorology.ch",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "Fraud analysis",
        "issue": "We saw a spike in fraudulent orders using stolen cards last week. Can you review our fraud settings and suggest stricter rules?",
        "reply": "I reviewed your fraud rules and recommend enabling address verification and raising the risk threshold for orders above 2,000 CHF. Our risk team can walk through the settings with you on a short call.",
        "close": True
    },
    {
        "name": "Olivia Brooks",
        "store": "Starlight Gaming Keyboards",
        "email": "olivia@starlightperipherals.gg",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Launch day traffic",
        "issue": "Our store slowed to a crawl during a product launch last weekend. What can we do to handle sudden traffic spikes on the Starter plan?",
        "reply": "For launch spikes, I recommend pre-compressing product images and enabling the performance settings in your theme. If you regularly see this traffic, the Growth plan includes higher platform capacity.",
        "close": True
    },
    {
        "name": "Noah Bennett",
        "store": "EcoBottle Zero Waste",
        "email": "noah@ecobottleliving.org",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Refund request",
        "issue": "I would like a refund for the Shopify POS Go terminal we bought last month. It was never unboxed because our launch was postponed.",
        "reply": "I have approved a full refund under the 30-day return window. A return label has been emailed to you, and the refund will be issued once the tracking shows the unit is in transit.",
        "close": True
    },
    {
        "name": "Isla Hart",
        "store": "Oasis Swimwear Sydney",
        "email": "isla@oasisswim.au",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Localization",
        "issue": "Our Australian storefront still displays USD for some products even though we enabled AUD as the local currency.",
        "reply": "I found three products with a hardcoded USD price in their metafields. I have cleared those values so they inherit the market-specific AUD pricing; please refresh the storefront to confirm.",
        "close": True
    },
    {
        "name": "Rohan Mehta",
        "store": "PureSource Health Supplements",
        "email": "rohan@puresourcehealth.com",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "App permissions",
        "issue": "Our inventory app stopped syncing after we rotated the staff account password. I cannot find where to regenerate the API credentials.",
        "reply": "The credentials are under Settings, Apps and sales channels, then App permissions. I have refreshed the token on our side as well, so the sync should resume within the next 15 minutes.",
        "close": True
    },
    {
        "name": "Maya Rodriguez",
        "store": "Canvas & Clay Pottery Studio",
        "email": "maya@canvasclayceramics.art",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Domain setup",
        "issue": "Our custom domain shows an SSL pending error even though the DNS records have been in place for two days.",
        "reply": "I checked your DNS and the CNAME is pointing to the right target. The SSL certificate is now reissuing; these usually validate within a few hours once propagation completes.",
        "close": True
    },
    {
        "name": "Deepak Shah",
        "store": "Kavita Silk Sarees",
        "email": "deepak@kavitasilks.com",
        "plan": "Growth",
        "mrr": 79,
        "theme": "B2B wholesale",
        "issue": "Our wholesale customers are seeing retail prices after we enabled B2B on the Growth plan. How do I assign them to a wholesale price list?",
        "reply": "You can attach a price list to each B2B customer through the company profile in the admin. I have created a sample wholesale price list from your existing 40 percent volume discount so you can copy it.",
        "close": False
    },
    {
        "name": "Lukas Fischer",
        "store": "Apex Automotive Parts",
        "email": "lukas@apexautoparts.de",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "Data export",
        "issue": "Our finance team needs a daily export of orders and refunds, but the CSV export keeps truncating at 10,000 rows.",
        "reply": "I have enabled a scheduled export that splits by date range so no rows are truncated. Your finance team will receive the first file at 6 AM UTC tomorrow.",
        "close": True
    },
    {
        "name": "Elena Petrova",
        "store": "Solaris Home Clean Energy",
        "email": "elena@solarishomepower.com",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "Hydrogen storefront",
        "issue": "We are rebuilding our storefront on Hydrogen and need help connecting the checkout extension for financing eligibility.",
        "reply": "Our Hydrogen specialist has shared a sample checkout extension that calls the financing eligibility API. I have scheduled a 30-minute review call so your engineers can walk through the implementation.",
        "close": True
    },
    {
        "name": "Caleb Morgan",
        "store": "CyberShield VPN Hardware",
        "email": "caleb@cybershieldrouter.net",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Chargeback",
        "issue": "One of our customers opened a chargeback even though the order was delivered. What evidence should we submit?",
        "reply": "Submit the order confirmation, tracking details with delivery confirmation, and the customer's checkout IP record. I have attached a dispute template your team can fill in and upload in the payments section.",
        "close": True
    },

    # --- Batch 2: Advanced Logistics, Global Tax, B2B & Omni-Channel (21-40) ---
    {
        "name": "Vikram Singhania",
        "store": "Royal Jaipur Silks",
        "email": "vikram@royaljaipursilks.in",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "GST Tax Invoicing",
        "issue": "Our Indian GST tax invoices are missing the 6-digit HSN code on silk textiles, causing merchant audit failures with the local tax portal.",
        "reply": "We have updated your product category taxonomy to include mandatory HSN mappings for Indian textile codes. Your automated invoice templates will now display the verified HSN fields on all subsequent receipts.",
        "close": True
    },
    {
        "name": "Chloe Martin",
        "store": "Le Petit Macaron Bakery",
        "email": "chloe@petitmacaronparis.fr",
        "plan": "Growth",
        "mrr": 79,
        "theme": "POS Pro Cash Drawer",
        "issue": "Our Star Micronics receipt printer and APG cash drawer fail to kick open on cash tender through the Shopify POS Pro iPad app.",
        "reply": "This was caused by a Bluetooth protocol timeout after iOS 17.4. We pushed a firmware synchronization profile to your iPad station; please tap 'Reconnect Peripheral' in POS settings to verify.",
        "close": True
    },
    {
        "name": "Lucas Silva",
        "store": "Rio Carnival Apparel",
        "email": "lucas@riocarnivalwear.com.br",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Pix & BRL Currency",
        "issue": "Brazilian shoppers attempting to pay with PIX QR codes are experiencing gateway drop-offs during flash promotions.",
        "reply": "We have increased the PIX webhook timeout threshold to 300 seconds across the Latin America regional gateway cluster. Conversion telemetry indicates 99.4% settlement success over the last 6 hours.",
        "close": True
    },
    {
        "name": "Emily Zhao",
        "store": "Kyoto Minimalist Home",
        "email": "emily@kyotominimalist.jp",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "Multi-Location Transfers",
        "issue": "Transferring 450 units between our Osaka distribution hub and Tokyo flagship store shows stuck in 'In-Transit' status.",
        "reply": "The transit status was held up by a pending barcode scan batch. Our fulfillment service has cleared the lock, and the stock is now properly reflected in your Tokyo active inventory.",
        "close": True
    },
    {
        "name": "Matteo Rossi",
        "store": "Milano Leather Goods",
        "email": "matteo@rossipelletteria.it",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "Checkout Discount Stacking",
        "issue": "We need custom checkout rules that allow VIP loyalty points to combine with sitewide Black Friday automatic discounts.",
        "reply": "With Shopify Plus Checkout Extensibility, discount stacking can be configured via Shopify Functions. We have provisioned a custom Function script in your staging environment for testing.",
        "close": False
    },
    {
        "name": "Sarah Jenkins",
        "store": "Cascade Outdoor Gear",
        "email": "sarah@cascadeoutdoorgear.com",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Shopify Flow Webhooks",
        "issue": "Our Shopify Flow workflow designed to tag high-value orders above $500 is delaying triggers by up to 45 minutes.",
        "reply": "A rate limiter on your Klaviyo downstream webhook endpoint was throttling Flow execution. We added exponential backoff retry rules, and tag latency is now back under 1.2 seconds.",
        "close": True
    },
    {
        "name": "Tyler Brooks",
        "store": "Neon Wave Skateboards",
        "email": "tyler@neonwaveskate.co",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Shopify Collabs Affiliate",
        "issue": "Two of our brand ambassadors report that their affiliate discount links are not attributing commission in the Collabs dashboard.",
        "reply": "The ambassadors had tracking cookies disabled by an adblocker parameter. We have enabled fallback coupon-code attribution so their sales register automatically without relying on URL parameters.",
        "close": True
    },
    {
        "name": "Ayesha Khan",
        "store": "Kashmiri Pashmina Craft",
        "email": "ayesha@kashmiripashmina.shop",
        "plan": "Growth",
        "mrr": 79,
        "theme": "COD Fraud Verification",
        "issue": "Cash on Delivery (COD) order returns are hitting 28%. We need an OTP SMS verification gate before confirming Indian orders.",
        "reply": "We integrated the Shopify Inbox automated SMS OTP verification module for your checkout. Preliminary tests show COD cancellation rates drop by 65% when OTP verification is enforced.",
        "close": True
    },
    {
        "name": "Carlos Mendez",
        "store": "Havana Heritage Imports",
        "email": "carlos@havanaheritagecraft.com",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "Restricted Products Policy",
        "issue": "Our artisanal tobacco accessories store received a policy compliance notice. Can our merchant agreement clarify tobacco vs accessory distinctions?",
        "reply": "Our Merchant Review team examined your catalog and verified that non-consumable accessories are fully compliant under Shopify Acceptable Use. We have removed the flag from your account.",
        "close": True
    },
    {
        "name": "Hanna Lindstrom",
        "store": "Nordic Clean Beauty",
        "email": "hanna@nordiccleanbeauty.se",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Subscription Skip Logic",
        "issue": "Customers using our monthly facial serum subscription cannot skip a shipment directly from their customer portal without cancelling.",
        "reply": "We updated your customer portal settings to enable the native 'Skip Next Delivery' toggle. Over 180 subscribers have successfully utilized the self-serve skip option this week without churning.",
        "close": True
    },
    {
        "name": "Oliver Wright",
        "store": "Oxford Antiquarian Books",
        "email": "oliver@oxfordvintagebooks.co.uk",
        "plan": "Growth",
        "mrr": 79,
        "theme": "ISBN Barcode Scanning",
        "issue": "Our Socket Mobile S700 scanner reads ISBN barcodes as plain text instead of matching our 40,000 vintage book SKU database in POS.",
        "reply": "The scanner was operating in Basic HID Keyboard mode instead of Application Mode. We provided the setup barcode to toggle Application Mode, enabling instant SKU lookup in under 200ms.",
        "close": True
    },
    {
        "name": "Fatima Al-Mansoor",
        "store": "Dubai Oud & Gold",
        "email": "fatima@dubaioudluxury.ae",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "GCC Cross-Border DDP",
        "issue": "Orders shipping to Saudi Arabia and Qatar require Delivered Duty Paid (DDP) customs clearance to prevent customs holds at Riyadh airport.",
        "reply": "We configured Markets Pro DDP routing with DHL Express for all GCC territories. Customs duties and VAT are now collected upfront at checkout with automated clearance manifests.",
        "close": True
    },
    {
        "name": "Benjamin Cohen",
        "store": "Tel Aviv Cyber Wear",
        "email": "benjamin@telavivtechwear.io",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Cloudflare Proxy Conflict",
        "issue": "Pointing our custom domain with Cloudflare Orange Cloud (proxy enabled) caused SSL handshake errors on our Shopify store.",
        "reply": "Shopify requires direct DNS resolution (Grey Cloud / DNS Only) for the root and CNAME records so our Let's Encrypt automated SSL certificate can renew. Once switched to DNS only, SSL provisioned instantly.",
        "close": True
    },
    {
        "name": "Zoe Campbell",
        "store": "Auckland Merino Woolens",
        "email": "zoe@aucklandmerinowool.nz",
        "plan": "Growth",
        "mrr": 79,
        "theme": "POS Offline Batches",
        "issue": "During the agricultural expo in Hamilton our POS terminal operated offline for 8 hours. When reconnected, 12 transactions showed settlement pending.",
        "reply": "All 12 offline transactions have completed settlement with the clearing house. Funds have been posted to your Shopify Balance account with zero transaction loss.",
        "close": True
    },
    {
        "name": "Arjun Patel",
        "store": "Gujarat Spice Exporters",
        "email": "arjun@gujaratspiceco.in",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "B2B Net-30 Invoicing",
        "issue": "We need to offer Net-30 payment terms and custom bulk price catalogs for restaurant distributors purchasing over 50kg of spices.",
        "reply": "We activated Shopify B2B wholesale company profiles on your account. You can now invite corporate buyers, assign custom price lists, and set automatic Net-30 invoice terms.",
        "close": False
    },
    {
        "name": "Isabella Fontaine",
        "store": "Provence Lavender Farm",
        "email": "isabella@provencelavender.fr",
        "plan": "Starter",
        "mrr": 29,
        "theme": "Abandoned Cart Recovery",
        "issue": "Our automated abandoned checkout recovery emails stopped sending after we updated our European GDPR cookie consent banner.",
        "reply": "The cookie banner was blocking marketing consent collection prior to checkout entry. We revised the consent trigger so checkout email recovery stays compliant under GDPR Article 6(1)(f).",
        "close": True
    },
    {
        "name": "David Kim",
        "store": "Seoul K-Pop Merch Lab",
        "email": "david@kpopmerchglobal.kr",
        "plan": "Plus",
        "mrr": 2000,
        "theme": "Flash Sale Bot Protection",
        "issue": "We are dropping exclusive signed concert merchandise next Friday and anticipate 250,000 concurrent fans. How do we prevent scalper bots?",
        "reply": "We scheduled Shopify Plus Queue-it bot protection and Cloudflare turnstile verification for your drop window. The waiting room will automatically activate when concurrency exceeds 20,000 visitors.",
        "close": True
    },
    {
        "name": "Rachel Green",
        "store": "Brooklyn Plant Nursery",
        "email": "rachel@brooklynplantco.com",
        "plan": "Growth",
        "mrr": 79,
        "theme": "Local Pickup Scheduling",
        "issue": "Customers selecting local curbside pickup arrive before orders are assembled. Can we restrict pickup to specific 2-hour time slots?",
        "reply": "We enabled scheduled local pickup slots in your shipping settings. Customers can now select pickup windows between 10 AM and 6 PM with a minimum 4-hour prep buffer.",
        "close": True
    },
    {
        "name": "Sven Svensson",
        "store": "Stockholm Eco Living",
        "email": "sven@stockholmecofurniture.se",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "Carbon-Neutral Shipping",
        "issue": "We want our checkout to display Planet carbon-offset badges and calculate exact grams of CO2 offset per furniture shipment.",
        "reply": "We connected the Shopify Planet app with your checkout extensibility profile. All carbon offsets are now automatically calculated via climatic carbon removal partners with live customer tracking.",
        "close": True
    },
    {
        "name": "Nina Ivanova",
        "store": "Prague Crystal Atelier",
        "email": "nina@praguecrystalart.cz",
        "plan": "Advanced",
        "mrr": 299,
        "theme": "Fragile Transit Insurance",
        "issue": "Hand-blown crystal glassware requires mandatory transit insurance on international DHL shipments above 500 EUR.",
        "reply": "We implemented an automatic transit insurance line-item via custom carrier service API. High-value crystal orders now include full replacement coverage and signature upon delivery.",
        "close": True
    }
]

TAG_NAMES = [
    "plan:starter", "plan:growth", "plan:advanced", "plan:plus",
    "status:vip", "region:emea", "region:apac", "region:americas", "region:india",
    "theme:payments", "theme:pos_hardware", "theme:international", "theme:b2b"
] + sorted({m["theme"] for m in MERCHANTS})

CUSTOM_ATTRIBUTES = {
    "store_name": "string",
    "shopify_plan": "string",
    "mrr_usd": "integer",
    "support_theme": "string",
    "merchant_segment": "string",
    "seed_source": "string",
}


def request(client: httpx.Client, method: str, endpoint: str, payload: dict = None, params: dict = None):
    resp = client.request(
        method,
        f"{BASE_URL}/{endpoint.lstrip('/')}",
        headers=HEADERS,
        json=payload,
        params=params,
        timeout=25.0,
    )
    if resp.status_code not in (200, 201):
        return {"_error_status": resp.status_code, "_error_text": resp.text}
    return resp.json()


def search_contact_by_email(client: httpx.Client, email: str) -> Optional[str]:
    body = {"query": {"field": "email", "operator": "=", "value": email}}
    res = request(client, "POST", "/contacts/search", payload=body)
    if res and not res.get("_error_status") and res.get("data"):
        return str(res["data"][0]["id"])
    return None


def ensure_custom_attributes(client: httpx.Client) -> None:
    existing = request(client, "GET", "/data_attributes", params={"model": "contact"}) or {}
    registered = {attr["name"] for attr in existing.get("data", [])}
    for name, data_type in CUSTOM_ATTRIBUTES.items():
        if name in registered:
            continue
        request(client, "POST", "/data_attributes", {
            "name": name,
            "model": "contact",
            "data_type": data_type,
            "description": f"Simulated Shopify merchant data: {name}",
        })
    print("  Custom attributes ready")


def ensure_tags(client: httpx.Client) -> dict:
    existing = request(client, "GET", "/tags", params={"per_page": 100}) or {}
    tags = {tag["name"]: str(tag["id"]) for tag in existing.get("data", [])}
    for name in TAG_NAMES:
        if name in tags:
            continue
        created = request(client, "POST", "/tags", {"name": name})
        if created and created.get("id"):
            tags[name] = str(created["id"])
    print(f"  Tags ready: {len(tags)}")
    return tags


def sync_to_venturetwin_store(contacts: List[Dict[str, Any]], conversations: List[Dict[str, Any]]) -> None:
    """Store sync history in VentureTwin SQLite database and mark Intercom connected."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from integrations.store import save_connection_state, save_sync_record
    from integrations.base import SyncRecord

    now = datetime.now(timezone.utc).isoformat()
    # Save connection state as connected
    save_connection_state(
        connector_id="intercom",
        status="connected",
        credentials_configured=True,
        last_sync=now,
        error=None,
        provider_name="Intercom",
        authentication_type="token",
        environment="developer",
        metadata={
            "app_name": "Shopify",
            "total_contacts": len(contacts),
            "total_conversations": len(conversations),
            "seeded_at": now
        }
    )

    # Save sync record
    sync_rec = SyncRecord(
        connector_id="intercom",
        sync_start=now,
        sync_end=now,
        records_fetched=len(contacts) + len(conversations),
        records_created=len(contacts) + len(conversations),
        status="success"
    )
    save_sync_record(sync_rec)
    print("  [VentureTwin Store] Saved connection state: Intercom marked CONNECTED.")


def main():
    print("=" * 68)
    print("Swarming Intercom with 40 Simulated Shopify Merchant Support Cases")
    print("=" * 68)

    with httpx.Client() as client:
        me = request(client, "GET", "/me")
        if not me or me.get("_error_status"):
            print(f"[ERROR] Could not authenticate with Intercom: {me}")
            sys.exit(1)

        admin_id = str(me["id"])
        app_name = me.get("app", {}).get("name", "Shopify")
        app_id_code = me.get("app", {}).get("id_code", "")
        print(f"Workspace: {app_name} ({app_id_code}) | Admin: {me.get('name')} ({admin_id})")

        ensure_custom_attributes(client)
        tags = ensure_tags(client)

        contacts_created = 0
        contacts_matched = 0
        conversations_created = 0
        replies_sent = 0
        closed_count = 0

        synced_contacts = []
        synced_conversations = []

        for idx, m in enumerate(MERCHANTS, 1):
            plan_tag = tags.get(f"plan:{m['plan'].lower()}")
            theme_tag = tags.get(m["theme"])
            created_at = int((datetime.now(timezone.utc) - timedelta(days=(idx % 21) + 1, hours=idx % 12)).timestamp())

            contact_id = None
            contact_payload = {
                "role": "user",
                "email": m["email"],
                "name": m["name"],
                "custom_attributes": {
                    "store_name": m["store"],
                    "shopify_plan": m["plan"],
                    "mrr_usd": m["mrr"],
                    "support_theme": m["theme"],
                    "merchant_segment": "DTC / E-Commerce",
                    "seed_source": "shopify_support_simulation",
                },
            }

            res = request(client, "POST", "/contacts", contact_payload)
            if res and not res.get("_error_status"):
                contact_id = str(res["id"])
                contacts_created += 1
                synced_contacts.append(res)
            elif res and res.get("_error_status") == 409:
                # Contact already exists - search to get ID
                contact_id = search_contact_by_email(client, m["email"])
                if contact_id:
                    contacts_matched += 1
                    # Update custom attributes
                    request(client, "PUT", f"/contacts/{contact_id}", contact_payload)
                    synced_contacts.append({"id": contact_id, "name": m["name"], "email": m["email"], **contact_payload["custom_attributes"]})

            if not contact_id:
                print(f"  [{idx:02d}/{len(MERCHANTS)}] Could not create or find contact {m['email']}")
                continue

            if plan_tag:
                request(client, "POST", f"/contacts/{contact_id}/tags", {"id": plan_tag})

            print(f"  [{idx:02d}/{len(MERCHANTS)}] Merchant: {m['name']} ({m['store']}) -> ID: {contact_id}")

            # Create Support Conversation
            convo_res = request(client, "POST", "/conversations", {
                "from": {"type": "user", "id": contact_id},
                "body": m["issue"],
                "created_at": created_at,
            })

            if not convo_res or convo_res.get("_error_status"):
                print(f"    [WARN] Failed to create conversation for {m['name']}: {convo_res}")
                time.sleep(0.2)
                continue

            convo_id = str(convo_res.get("conversation_id", convo_res.get("id")))
            conversations_created += 1

            # Admin Reply
            reply_res = request(client, "POST", f"/conversations/{convo_id}/reply", {
                "message_type": "comment",
                "type": "admin",
                "admin_id": admin_id,
                "body": m["reply"],
            })
            if reply_res and not reply_res.get("_error_status"):
                replies_sent += 1

            # Theme Tag
            if theme_tag:
                request(client, "POST", f"/conversations/{convo_id}/tags", {
                    "id": theme_tag,
                    "admin_id": admin_id,
                })

            # Close if specified
            if m.get("close", False):
                close_res = request(client, "POST", f"/conversations/{convo_id}/reply", {
                    "message_type": "close",
                    "type": "admin",
                    "admin_id": admin_id,
                    "body": "Ticket resolved by Shopify Merchant Support Engineering."
                })
                if close_res and not close_res.get("_error_status"):
                    closed_count += 1

            synced_conversations.append({
                "id": convo_id,
                "contact_id": contact_id,
                "customer_name": m["name"],
                "store_name": m["store"],
                "subject": m["theme"],
                "issue": m["issue"],
                "status": "closed" if m.get("close", False) else "open",
                "created_at": created_at
            })

            time.sleep(0.15)

        # Store in VentureTwin
        sync_to_venturetwin_store(synced_contacts, synced_conversations)

        print("\n" + "=" * 68)
        print("Intercom Shopify Support Database Swarm Complete!")
        print(f"  Total Merchants Processed:   {len(MERCHANTS)}")
        print(f"  New Contacts Created:        {contacts_created}")
        print(f"  Existing Contacts Matched:   {contacts_matched}")
        print(f"  Conversations Created:       {conversations_created}")
        print(f"  Admin Replies Sent:          {replies_sent}")
        print(f"  Tickets Resolved/Closed:     {closed_count}")
        print(f"  Intercom Inbox URL:          https://app.intercom.com/a/apps/{app_id_code}/inbox")
        print("=" * 68)


if __name__ == "__main__":
    main()
