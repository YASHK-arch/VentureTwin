"""
Populates HubSpot CRM with realistic simulated Shopify merchant ecosystem data:
- 18 High-growth Shopify Merchant Companies (DTC, Retail, Omni-channel)
- 18 Executive Contacts (Founders, VPs of E-Commerce, Chief Digital Officers)
- 18 High-value Deals across standard pipeline stages (Shopify Plus, POS, B2B, Markets Pro)
- 2-way and 3-way Associations linking Contacts -> Companies and Deals -> Companies & Contacts
"""

import os
import sys
import time
import json
from pathlib import Path
import httpx

# Load HUBSPOT_ACCESS_TOKEN dynamically from .env or environment
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("HUBSPOT_ACCESS_TOKEN="):
                os.environ["HUBSPOT_ACCESS_TOKEN"] = line.split("=", 1)[1].strip().strip('"').strip("'")

HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN")
if not HUBSPOT_TOKEN:
    print("[ERROR] HUBSPOT_ACCESS_TOKEN is not set in environment or .env file.")
    sys.exit(1)

BASE_URL = "https://api.hubapi.com"
HEADERS = {
    "Authorization": f"Bearer {HUBSPOT_TOKEN}",
    "Content-Type": "application/json",
}

MERCHANTS_DATA = [
    {
        "company": {
            "name": "Aura Athletics",
            "domain": "auraathletics.com",
            "industry": "APPAREL_FASHION",
            "annualrevenue": "42000000",
            "numberofemployees": "180",
            "city": "New York",
            "state": "NY",
            "country": "United States",
            "description": "High-growth direct-to-consumer athletic wear and activewear brand.",
        },
        "contact": {
            "firstname": "Sarah",
            "lastname": "Lin",
            "email": "sarah.lin@auraathletics.com",
            "jobtitle": "VP of Global E-Commerce",
            "phone": "+1-212-555-0143",
            "lifecyclestage": "customer",
        },
        "deal": {
            "dealname": "Aura Athletics - Shopify Plus Global Enterprise Migration",
            "amount": "140000",
            "pipeline": "default",
            "dealstage": "closedwon",
        },
    },
    {
        "company": {
            "name": "Nordic Wool Co.",
            "domain": "nordicwoolshoes.com",
            "industry": "APPAREL_FASHION",
            "annualrevenue": "18500000",
            "numberofemployees": "75",
            "city": "Seattle",
            "state": "WA",
            "country": "United States",
            "description": "Sustainable merino wool footwear and outdoor apparel.",
        },
        "contact": {
            "firstname": "Henrik",
            "lastname": "Lindqvist",
            "email": "h.lindqvist@nordicwoolshoes.com",
            "jobtitle": "Chief Digital Officer",
            "phone": "+1-206-555-0182",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Nordic Wool - Shopify Markets Pro Cross-Border Rollout",
            "amount": "55000",
            "pipeline": "default",
            "dealstage": "contractsent",
        },
    },
    {
        "company": {
            "name": "Tokyo Matcha Direct",
            "domain": "tokyomatchadirect.jp",
            "industry": "FOOD_BEVERAGES",
            "annualrevenue": "12000000",
            "numberofemployees": "45",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
            "description": "Ceremonial grade Uji matcha and traditional Japanese teaware.",
        },
        "contact": {
            "firstname": "Kenji",
            "lastname": "Tanaka",
            "email": "kenji@tokyomatchadirect.jp",
            "jobtitle": "Head of Growth & E-Commerce",
            "phone": "+1-415-555-0129",
            "lifecyclestage": "customer",
        },
        "deal": {
            "dealname": "Tokyo Matcha - Shopify Plus & Shop Pay Integration",
            "amount": "48000",
            "pipeline": "default",
            "dealstage": "closedwon",
        },
    },
    {
        "company": {
            "name": "Artisan Oak Furniture",
            "domain": "artisanoakwood.com",
            "industry": "FURNITURE",
            "annualrevenue": "28000000",
            "numberofemployees": "110",
            "city": "Austin",
            "state": "TX",
            "country": "United States",
            "description": "Handcrafted sustainable hardwood furniture and home accents.",
        },
        "contact": {
            "firstname": "Marcus",
            "lastname": "Vance",
            "email": "m.vance@artisanoakwood.com",
            "jobtitle": "VP Omnichannel Strategy",
            "phone": "+1-512-555-0177",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Artisan Oak - POS Pro Showroom Fleet (18 Locations)",
            "amount": "72000",
            "pipeline": "default",
            "dealstage": "decisionmakerboughtin",
        },
    },
    {
        "company": {
            "name": "Velvet & Vine Boutique",
            "domain": "velvetandvine.shop",
            "industry": "COSMETICS",
            "annualrevenue": "34000000",
            "numberofemployees": "130",
            "city": "Los Angeles",
            "state": "CA",
            "country": "United States",
            "description": "Clean luxury skincare formulations and botanical wellness.",
        },
        "contact": {
            "firstname": "Chloe",
            "lastname": "DuPont",
            "email": "chloe@velvetandvine.shop",
            "jobtitle": "Director of Digital Experience",
            "phone": "+1-310-555-0164",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Velvet & Vine - Shopify Audiences & B2B Expansion",
            "amount": "85000",
            "pipeline": "default",
            "dealstage": "presentationscheduled",
        },
    },
    {
        "company": {
            "name": "Peak Performance Apparel",
            "domain": "peakapparel.fit",
            "industry": "HEALTH_WELLNESS_AND_FITNESS",
            "annualrevenue": "52000000",
            "numberofemployees": "220",
            "city": "Denver",
            "state": "CO",
            "country": "United States",
            "description": "Technical mountaineering outerwear and endurance training gear.",
        },
        "contact": {
            "firstname": "David",
            "lastname": "Sterling",
            "email": "dsterling@peakapparel.fit",
            "jobtitle": "Chief Operating Officer",
            "phone": "+1-303-555-0195",
            "lifecyclestage": "lead",
        },
        "deal": {
            "dealname": "Peak Performance - B2B Wholesale Portal Deployment",
            "amount": "95000",
            "pipeline": "default",
            "dealstage": "qualifiedtobuy",
        },
    },
    {
        "company": {
            "name": "Kobe Craft Knives",
            "domain": "kobecraftknives.com",
            "industry": "CONSUMER_GOODS",
            "annualrevenue": "8500000",
            "numberofemployees": "30",
            "city": "Chicago",
            "state": "IL",
            "country": "United States",
            "description": "Hand-forged Damascus steel culinary knives and chef equipment.",
        },
        "contact": {
            "firstname": "Akira",
            "lastname": "Sato",
            "email": "akira.sato@kobecraftknives.com",
            "jobtitle": "Managing Director",
            "phone": "+1-312-555-0112",
            "lifecyclestage": "lead",
        },
        "deal": {
            "dealname": "Kobe Craft Knives - Shopify Plus Commerce Upgrade",
            "amount": "42000",
            "pipeline": "default",
            "dealstage": "appointmentscheduled",
        },
    },
    {
        "company": {
            "name": "Lumina Skincare Labs",
            "domain": "luminaglow.co",
            "industry": "COSMETICS",
            "annualrevenue": "24000000",
            "numberofemployees": "95",
            "city": "Boston",
            "state": "MA",
            "country": "United States",
            "description": "Clinical-grade dermatological LED light therapy and serums.",
        },
        "contact": {
            "firstname": "Emily",
            "lastname": "Watson",
            "email": "emily.watson@luminaglow.co",
            "jobtitle": "VP E-Commerce Operations",
            "phone": "+1-617-555-0138",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Lumina Skincare - Markets Pro Multi-Currency Expansion",
            "amount": "62000",
            "pipeline": "default",
            "dealstage": "decisionmakerboughtin",
        },
    },
    {
        "company": {
            "name": "Terra Flora Botanical",
            "domain": "terraflorabev.com",
            "industry": "FOOD_BEVERAGES",
            "annualrevenue": "15000000",
            "numberofemployees": "50",
            "city": "Portland",
            "state": "OR",
            "country": "United States",
            "description": "Organic adaptogenic sparkling teas and herbal wellness beverages.",
        },
        "contact": {
            "firstname": "Liam",
            "lastname": "O'Connor",
            "email": "liam@terraflorabev.com",
            "jobtitle": "Head of Direct-to-Consumer",
            "phone": "+1-503-555-0151",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Terra Flora - POS Go Retail Pop-Up Fleet (25 Units)",
            "amount": "38000",
            "pipeline": "default",
            "dealstage": "contractsent",
        },
    },
    {
        "company": {
            "name": "Hyperion Audio Labs",
            "domain": "hyperionaudio.com",
            "industry": "CONSUMER_ELECTRONICS",
            "annualrevenue": "31000000",
            "numberofemployees": "125",
            "city": "San Diego",
            "state": "CA",
            "country": "United States",
            "description": "Reference-grade audiophile planar headphones and DAC systems.",
        },
        "contact": {
            "firstname": "Rachel",
            "lastname": "Chen",
            "email": "rachel.chen@hyperionaudio.com",
            "jobtitle": "VP Digital Merchandising",
            "phone": "+1-619-555-0186",
            "lifecyclestage": "customer",
        },
        "deal": {
            "dealname": "Hyperion Audio - Shopify Plus Enterprise Replatform",
            "amount": "110000",
            "pipeline": "default",
            "dealstage": "closedwon",
        },
    },
    {
        "company": {
            "name": "Driftwood Surf Apparel",
            "domain": "driftwoodsurf.com",
            "industry": "APPAREL_FASHION",
            "annualrevenue": "19000000",
            "numberofemployees": "80",
            "city": "Honolulu",
            "state": "HI",
            "country": "United States",
            "description": "Recycled limestone wetsuits and technical Pacific surf apparel.",
        },
        "contact": {
            "firstname": "Kai",
            "lastname": "Morrison",
            "email": "kai@driftwoodsurf.com",
            "jobtitle": "Chief Executive Officer",
            "phone": "+1-808-555-0173",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Driftwood Surf - Omnichannel POS Fleet Modernization",
            "amount": "58000",
            "pipeline": "default",
            "dealstage": "presentationscheduled",
        },
    },
    {
        "company": {
            "name": "Solstice Eyewear",
            "domain": "solsticeeyewear.com",
            "industry": "LUXURY_GOODS_JEWELRY",
            "annualrevenue": "22000000",
            "numberofemployees": "90",
            "city": "Miami",
            "state": "FL",
            "country": "United States",
            "description": "Italian-acetate polarized handcrafted sunglasses and optical frames.",
        },
        "contact": {
            "firstname": "Sofia",
            "lastname": "Rodriguez",
            "email": "sofia@solsticeeyewear.com",
            "jobtitle": "Director of Growth Marketing",
            "phone": "+1-305-555-0125",
            "lifecyclestage": "lead",
        },
        "deal": {
            "dealname": "Solstice Eyewear - Shopify Audiences Campaign Network",
            "amount": "50000",
            "pipeline": "default",
            "dealstage": "qualifiedtobuy",
        },
    },
    {
        "company": {
            "name": "Alpine Roasters",
            "domain": "alpineroasters.com",
            "industry": "FOOD_BEVERAGES",
            "annualrevenue": "14500000",
            "numberofemployees": "60",
            "city": "Salt Lake City",
            "state": "UT",
            "country": "United States",
            "description": "High-altitude roasted specialty single-origin coffee subscriptions.",
        },
        "contact": {
            "firstname": "Tyler",
            "lastname": "Briggs",
            "email": "tyler@alpineroasters.com",
            "jobtitle": "Head of Digital Subscriptions",
            "phone": "+1-801-555-0149",
            "lifecyclestage": "customer",
        },
        "deal": {
            "dealname": "Alpine Roasters - Shopify Subscriptions & Plus Migration",
            "amount": "68000",
            "pipeline": "default",
            "dealstage": "closedwon",
        },
    },
    {
        "company": {
            "name": "Kinetic Footwear",
            "domain": "kineticfootwear.com",
            "industry": "SPORTING_GOODS",
            "annualrevenue": "39000000",
            "numberofemployees": "160",
            "city": "Boulder",
            "state": "CO",
            "country": "United States",
            "description": "Biomechanical zero-drop running footwear and trail gear.",
        },
        "contact": {
            "firstname": "Maya",
            "lastname": "Patel",
            "email": "maya.patel@kineticfootwear.com",
            "jobtitle": "VP Commercial Operations",
            "phone": "+1-720-555-0167",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Kinetic Footwear - Enterprise B2B Wholesale Channel",
            "amount": "125000",
            "pipeline": "default",
            "dealstage": "contractsent",
        },
    },
    {
        "company": {
            "name": "Horizon Watchmakers Geneva",
            "domain": "horizonhorology.ch",
            "industry": "LUXURY_GOODS_JEWELRY",
            "annualrevenue": "26000000",
            "numberofemployees": "55",
            "city": "Philadelphia",
            "state": "PA",
            "country": "United States",
            "description": "Independent mechanical timepieces and chronometer manufacturing.",
        },
        "contact": {
            "firstname": "Julian",
            "lastname": "Montgomery",
            "email": "julian@horizonhorology.ch",
            "jobtitle": "Founder & Creative Director",
            "phone": "+1-215-555-0190",
            "lifecyclestage": "lead",
        },
        "deal": {
            "dealname": "Horizon Horology - Shopify Plus Luxury Brand Onboarding",
            "amount": "105000",
            "pipeline": "default",
            "dealstage": "qualifiedtobuy",
        },
    },
    {
        "company": {
            "name": "Monolith Outdoor Gear",
            "domain": "monolithoutdoors.com",
            "industry": "SPORTING_GOODS",
            "annualrevenue": "27000000",
            "numberofemployees": "105",
            "city": "Seattle",
            "state": "WA",
            "country": "United States",
            "description": "Ultralight Dyneema backpacking shelters and technical packs.",
        },
        "contact": {
            "firstname": "Zachary",
            "lastname": "Evans",
            "email": "z.evans@monolithoutdoors.com",
            "jobtitle": "VP Digital Commerce",
            "phone": "+1-206-555-0118",
            "lifecyclestage": "lead",
        },
        "deal": {
            "dealname": "Monolith Outdoors - Legacy Magento Migration to Shopify Plus",
            "amount": "135000",
            "pipeline": "default",
            "dealstage": "appointmentscheduled",
        },
    },
    {
        "company": {
            "name": "Zenith Smart Devices",
            "domain": "zenithdevices.com",
            "industry": "CONSUMER_ELECTRONICS",
            "annualrevenue": "45000000",
            "numberofemployees": "190",
            "city": "San Jose",
            "state": "CA",
            "country": "United States",
            "description": "Connected smart home environmental hubs and sensor arrays.",
        },
        "contact": {
            "firstname": "Alex",
            "lastname": "Kovacs",
            "email": "alex.kovacs@zenithdevices.com",
            "jobtitle": "Chief Technology Officer",
            "phone": "+1-408-555-0144",
            "lifecyclestage": "opportunity",
        },
        "deal": {
            "dealname": "Zenith Smart Devices - Global Headless Hydrogen Storefront",
            "amount": "130000",
            "pipeline": "default",
            "dealstage": "presentationscheduled",
        },
    },
    {
        "company": {
            "name": "Apex Performance Parts",
            "domain": "apexautoparts.de",
            "industry": "CONSUMER_GOODS",
            "annualrevenue": "38000000",
            "numberofemployees": "140",
            "city": "Detroit",
            "state": "MI",
            "country": "United States",
            "description": "Precision performance automotive cooling systems and racing components.",
        },
        "contact": {
            "firstname": "Lars",
            "lastname": "Weber",
            "email": "lars.weber@apexautoparts.de",
            "jobtitle": "VP Wholesale & E-Commerce",
            "phone": "+1-313-555-0160",
            "lifecyclestage": "lead",
        },
        "deal": {
            "dealname": "Apex Performance Parts - High-SKU B2B Catalog Replatform",
            "amount": "150000",
            "pipeline": "default",
            "dealstage": "appointmentscheduled",
        },
    },
]


def seed_hubspot():
    print("=" * 60)
    print("🚀 SWARMING HUBSPOT CRM WITH SIMULATED SHOPIFY DATA")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=20.0)

    created_companies = []
    created_contacts = []
    created_deals = []
    total_deal_value = 0

    try:
        for idx, item in enumerate(MERCHANTS_DATA, start=1):
            comp_spec = item["company"]
            contact_spec = item["contact"]
            deal_spec = item["deal"]

            print(f"\n[{idx}/{len(MERCHANTS_DATA)}] Processing Merchant: {comp_spec['name']}")

            # 1. Create Company
            comp_body = {
                "properties": {
                    "name": comp_spec["name"],
                    "domain": comp_spec["domain"],
                    "industry": comp_spec["industry"],
                    "annualrevenue": comp_spec["annualrevenue"],
                    "numberofemployees": comp_spec["numberofemployees"],
                    "city": comp_spec["city"],
                    "state": comp_spec["state"],
                    "country": comp_spec["country"],
                    "description": comp_spec["description"],
                }
            }
            resp = client.post("/crm/v3/objects/companies", json=comp_body)
            if resp.status_code not in (200, 201):
                print(f"  ❌ Company creation failed: {resp.status_code} - {resp.text[:120]}")
                continue
            company_obj = resp.json()
            company_id = company_obj["id"]
            created_companies.append({"id": company_id, "name": comp_spec["name"]})
            print(f"  🏢 Created Company: {comp_spec['name']} (ID: {company_id})")
            time.sleep(0.15)

            # 2. Create Contact associated to Company (typeId 1: Primary)
            contact_body = {
                "properties": {
                    "firstname": contact_spec["firstname"],
                    "lastname": contact_spec["lastname"],
                    "email": contact_spec["email"],
                    "jobtitle": contact_spec["jobtitle"],
                    "phone": contact_spec["phone"],
                    "lifecyclestage": contact_spec["lifecyclestage"],
                    "company": comp_spec["name"],
                },
                "associations": [
                    {
                        "to": {"id": company_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 1}],
                    }
                ],
            }
            resp = client.post("/crm/v3/objects/contacts", json=contact_body)
            if resp.status_code not in (200, 201):
                print(f"  ❌ Contact creation failed: {resp.status_code} - {resp.text[:120]}")
                contact_id = None
            else:
                contact_obj = resp.json()
                contact_id = contact_obj["id"]
                created_contacts.append({
                    "id": contact_id,
                    "name": f"{contact_spec['firstname']} {contact_spec['lastname']}",
                    "email": contact_spec["email"],
                })
                print(f"  👤 Created Contact: {contact_spec['firstname']} {contact_spec['lastname']} (ID: {contact_id})")
            time.sleep(0.15)

            # 3. Create Deal associated to Company (typeId 5) & Contact (typeId 3)
            deal_associations = [
                {
                    "to": {"id": company_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}],
                }
            ]
            if contact_id:
                deal_associations.append({
                    "to": {"id": contact_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}],
                })

            deal_body = {
                "properties": {
                    "dealname": deal_spec["dealname"],
                    "amount": deal_spec["amount"],
                    "pipeline": deal_spec["pipeline"],
                    "dealstage": deal_spec["dealstage"],
                },
                "associations": deal_associations,
            }
            resp = client.post("/crm/v3/objects/deals", json=deal_body)
            if resp.status_code not in (200, 201):
                print(f"  ❌ Deal creation failed: {resp.status_code} - {resp.text[:120]}")
            else:
                deal_obj = resp.json()
                deal_id = deal_obj["id"]
                amount_num = int(deal_spec["amount"])
                total_deal_value += amount_num
                created_deals.append({
                    "id": deal_id,
                    "name": deal_spec["dealname"],
                    "stage": deal_spec["dealstage"],
                    "amount": amount_num,
                })
                print(f"  💼 Created Deal: {deal_spec['dealname']} (${amount_num:,.2f}) [Stage: {deal_spec['dealstage']}] (ID: {deal_id})")
            time.sleep(0.15)

    finally:
        client.close()

    print("\n" + "=" * 60)
    print("✅ HUBSPOT SHOPIFY CRM SEEDING COMPLETE")
    print("=" * 60)
    print(f"• Companies Created: {len(created_companies)}")
    print(f"• Contacts Created:  {len(created_contacts)}")
    print(f"• Deals Created:     {len(created_deals)}")
    print(f"• Total Pipeline:    ${total_deal_value:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    seed_hubspot()
