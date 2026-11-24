import pytest
import time
from services.groq_limiter import (
    parse_groq_duration,
    parse_retry_after,
    GroqRateLimiter,
    ACTIVE_GROQ_MODELS
)
from services.supervisor_groq import (
    route_decision_specialists,
    _ROUTING_CACHE
)


def test_parse_groq_duration_various_formats():
    assert parse_groq_duration("615ms") == 0.615
    assert parse_groq_duration("3.787s") == 3.787
    assert parse_groq_duration("1m26.4s") == 86.4
    assert parse_groq_duration("2m") == 120.0
    assert parse_groq_duration("500ms") == 0.5
    assert parse_groq_duration("") == 0.0
    assert parse_groq_duration(None) == 0.0


def test_parse_retry_after_from_headers_and_error():
    # From header
    assert parse_retry_after({"retry-after": "4.5"}) == 4.5
    assert parse_retry_after({"x-ratelimit-reset-tokens": "850ms"}) == 0.85

    # From Groq error message
    err_body = "Rate limit reached. Please try again in 3.2s. Visit console.groq.com"
    assert parse_retry_after({}, error_body=err_body) == 3.2

    err_body_ms = "Rate limit reached. Please try again in 500ms."
    assert parse_retry_after({}, error_body=err_body_ms) == 0.5


def test_groq_rate_limiter_header_tracking():
    limiter = GroqRateLimiter()
    model = "openai/gpt-oss-120b"

    headers = {
        "x-ratelimit-remaining-tokens": "7500",
        "x-ratelimit-reset-tokens": "1.2s",
        "x-ratelimit-remaining-requests": "990",
        "x-ratelimit-reset-requests": "30s"
    }
    limiter.update_from_headers(model, headers, status_code=200)

    assert limiter.is_model_rate_limited(model, required_tokens=1000) is False
    assert limiter.get_preferred_available_model([model, "openai/gpt-oss-20b"]) == model

    # Simulate 429 rate limit
    limiter.update_from_headers(model, {"retry-after": "2.0"}, status_code=429)
    assert limiter.is_model_rate_limited(model, required_tokens=1000) is True

    # Alternate model should be selected
    preferred = limiter.get_preferred_available_model([model, "openai/gpt-oss-20b"])
    assert preferred == "openai/gpt-oss-20b"


@pytest.mark.asyncio
async def test_supervisor_query_cache():
    _ROUTING_CACHE.clear()
    q = "Should we launch a free plan?"
    
    # First call
    dec1 = await route_decision_specialists(q)
    assert dec1 is not None

    # Second call should be served from in-memory cache
    dec2 = await route_decision_specialists(q)
    assert dec2.context_summary == dec1.context_summary
    assert dec2.selected_specialists == dec1.selected_specialists
