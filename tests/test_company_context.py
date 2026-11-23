import pytest
import os
from httpx import AsyncClient, ASGITransport
from api.app import app
from services.company_extractor import (
    extract_company_context_from_markdown,
    heuristic_markdown_extractor,
    RawExtractedCompanyContext,
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    ALL_FIELDS
)
from services.website_scraper import validate_scrape_url
from services.company_context_store import (
    init_company_context_db,
    save_company_context,
    get_active_company_context,
    list_company_contexts,
    delete_company_context
)


@pytest.mark.asyncio
async def test_markdown_heuristic_extraction():
    md_content = """# CloudPulse Technologies
Industry: B2B SaaS
Business Model: Subscription (SaaS)
Stage: Series A
Geographic Presence: San Francisco, CA & London, UK
Key Competitors: Datadog, Dynatrace

## Description
CloudPulse provides automated real-time observability and anomaly detection for distributed cloud architectures.

## Products & Services
- CloudPulse Core APM
- Anomaly Sentinel AI
- Distributed Trace Visualizer

## Target Customers
Mid-market engineering teams and enterprise cloud infrastructure architects running Kubernetes clusters.

## Revenue Model
Tiered monthly subscription per host agent: Starter ($49/host), Growth ($149/host), and Enterprise custom contracts.

## Strategic Goals
- Scale ARR to $5M in the next 18 months
- Launch automated root-cause remediation engine

## Major Challenges
High infrastructure compute cost per ingest stream and increasing sales cycle length for enterprise accounts.
"""
    result = await extract_company_context_from_markdown([{"filename": "company_overview.md", "content": md_content}])
    assert result.fields["company_name"] == "CloudPulse Technologies"
    assert result.fields["industry"] == "B2B SaaS"
    assert result.fields["business_model"] == "Subscription (SaaS)"
    assert result.fields["stage"] == "Series A"
    assert "CloudPulse provides automated" in result.fields["description"]
    assert "CloudPulse Core APM" in result.fields["products_services"]
    assert "Mid-market engineering teams" in result.fields["target_customers"]
    assert "Tiered monthly subscription" in result.fields["revenue_model"]
    assert "Scale ARR to $5M" in result.fields["strategic_goals"]
    assert "High infrastructure compute" in result.fields["major_challenges"]
    assert "Datadog" in result.fields["key_competitors"]
    assert result.fields["geographic_presence"] == "San Francisco, CA & London, UK"
    assert len(result.missing_fields) == 0


@pytest.mark.asyncio
async def test_missing_fields_never_invented():
    sparse_md = """# Minimalist Tools
Industry: DevTools & Infrastructure
Description: A minimalist CLI for git workflows.
"""
    result = await extract_company_context_from_markdown([{"filename": "sparse.md", "content": sparse_md}])
    assert result.fields["company_name"] == "Minimalist Tools"
    assert result.fields["industry"] == "DevTools & Infrastructure"
    assert result.fields["description"] == "A minimalist CLI for git workflows."
    # Unavailable fields must remain empty string
    assert result.fields["target_customers"] == ""
    assert result.fields["strategic_goals"] == ""
    assert result.fields["revenue_model"] == ""
    assert "target_customers" in result.missing_fields
    assert "strategic_goals" in result.missing_fields


def test_website_url_validation_ssrf_protection():
    # Valid public URLs
    is_valid, url = validate_scrape_url("https://stripe.com")
    assert is_valid is True
    assert url == "https://stripe.com"

    is_valid, url = validate_scrape_url("github.com/about")
    assert is_valid is True
    assert url == "https://github.com/about"

    # Block localhost & private IPs
    is_valid, err = validate_scrape_url("http://localhost:8000")
    assert is_valid is False
    assert "Localhost" in err

    is_valid, err = validate_scrape_url("http://127.0.0.1:3000")
    assert is_valid is False

    is_valid, err = validate_scrape_url("http://10.0.0.1/admin")
    assert is_valid is False
    assert "Private" in err

    is_valid, err = validate_scrape_url("http://192.168.1.1")
    assert is_valid is False

    is_valid, err = validate_scrape_url("http://169.254.169.254/latest/meta-data")
    assert is_valid is False

    # Block non-http schemes
    is_valid, err = validate_scrape_url("file:///etc/passwd")
    assert is_valid is False
    assert "scheme" in err


def test_sqlite_company_context_store():
    init_company_context_db()
    data = {
        "company_name": "TestCo Systems",
        "industry": "B2B SaaS",
        "business_model": "Subscription (SaaS)",
        "description": "Enterprise test platform",
        "products_services": "TestRunner Pro",
        "target_customers": "DevOps Engineers",
        "revenue_model": "Annual contract value",
        "geographic_presence": "Austin, TX",
        "stage": "Seed",
        "strategic_goals": "Achieve product-market fit",
        "major_challenges": "Customer acquisition",
        "key_competitors": "CompetitorX",
        "website_url": "https://testco.example",
        "provenance": {"company_name": {"source": "manual", "confidence": 1.0, "extracted": False}}
    }
    saved = save_company_context(data, user_id="test_user_1")
    assert saved["company_name"] == "TestCo Systems"
    assert saved["is_active"] == 1
    assert saved["provenance"]["company_name"]["source"] == "manual"

    active = get_active_company_context(user_id="test_user_1")
    assert active is not None
    assert active["id"] == saved["id"]

    all_contexts = list_company_contexts(user_id="test_user_1")
    assert len(all_contexts) >= 1

    deleted = delete_company_context(saved["id"])
    assert deleted is True


@pytest.mark.asyncio
async def test_company_context_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test extraction endpoint
        md_text = """# Acme Analytics
Industry: B2B SaaS
Business Model: Subscription (SaaS)
Stage: Series B
Description: Acme provides real-time customer analytics.
Products & Services: Acme Core, Acme Dashboards
Target Customers: Growth Marketers
Revenue Model: $199/month per seat
Strategic Goals: Expand into EU market
"""
        extract_res = await client.post("/api/company/extract", json={
            "files": [{"filename": "acme.md", "content": md_text}]
        })
        assert extract_res.status_code == 200
        data = extract_res.json()
        assert data["fields"]["company_name"] == "Acme Analytics"
        assert data["fields"]["industry"] == "B2B SaaS"

        # 2. Test saving context endpoint
        context_payload = {
            "company_name": "Acme Analytics",
            "industry": "B2B SaaS",
            "business_model": "Subscription (SaaS)",
            "description": "Acme provides real-time customer analytics.",
            "products_services": "Acme Core, Acme Dashboards",
            "target_customers": "Growth Marketers",
            "revenue_model": "$199/month per seat",
            "geographic_presence": "New York, NY",
            "stage": "Series B",
            "strategic_goals": "Expand into EU market",
            "major_challenges": "GDPR compliance",
            "key_competitors": "Mixpanel, Amplitude",
            "website_url": "https://acme.example",
            "provenance": data["provenance"]
        }
        save_res = await client.post("/api/company/context", json=context_payload)
        assert save_res.status_code == 200
        saved_obj = save_res.json()["context"]
        assert saved_obj["company_name"] == "Acme Analytics"

        # 3. Test get active context
        get_res = await client.get("/api/company/context")
        assert get_res.status_code == 200
        assert get_res.json()["active"] is True
        assert get_res.json()["context"]["company_name"] == "Acme Analytics"

        # 4. Clean up test context
        del_res = await client.delete(f"/api/company/context/{saved_obj['id']}")
        assert del_res.status_code == 200
