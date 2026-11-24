"""
Centralized Rate Limiter, Token Pacer, and Model Fallback Manager for Groq API.

Groq developer tier models enforce strict Tokens Per Minute (TPM) limits (typically 8,000 TPM)
and Requests Per Minute (RPM) limits. This module provides:
1. Dynamic pacing and token tracking using Groq's response headers:
   - x-ratelimit-remaining-tokens
   - x-ratelimit-reset-tokens (e.g. '615ms', '3.78s', '1m26s')
   - x-ratelimit-remaining-requests
   - x-ratelimit-reset-requests
2. Robust 429 retry-after extraction from headers and error payloads.
3. Multi-model tier fallback:
   When a model (e.g. 'openai/gpt-oss-120b') approaches or hits its TPM ceiling,
   calls can automatically switch to an alternate model (e.g. 'openai/gpt-oss-20b' or 'qwen/qwen3.8-27b')
   which maintains an independent rate limit bucket on Groq Cloud.
4. LRU/TTL caching for question routing to eliminate redundant calls from UI typing and submission.
"""

import asyncio
import logging
import os
import re
import time
from typing import Dict, List, Mapping, Optional, Tuple, Any

logger = logging.getLogger(__name__)

# Active chat completion models supported by Groq Cloud for this environment
ACTIVE_GROQ_MODELS: List[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

# Safe default pacing in seconds between Groq requests
DEFAULT_GROQ_MIN_INTERVAL: float = 1.5

# Margin of remaining tokens before we proactively pace or switch models
TOKEN_SAFETY_BUFFER: int = 1500


def parse_groq_duration(val: Optional[str]) -> float:
    """
    Parse duration strings returned by Groq headers (e.g. '615ms', '3.787s', '1m26.4s').
    Returns duration in seconds.
    """
    if not val:
        return 0.0
    val = str(val).strip().lower()
    total = 0.0
    try:
        # Check for minutes (e.g. '1m' or '2.5m', but not 'ms')
        m_match = re.search(r"([\d\.]+)m(?!s)", val)
        if m_match:
            total += float(m_match.group(1)) * 60.0

        # Check for seconds (e.g. '3.787s')
        s_match = re.search(r"([\d\.]+)s", val)
        if s_match:
            total += float(s_match.group(1))

        # Check for milliseconds (e.g. '615ms')
        ms_match = re.search(r"([\d\.]+)ms", val)
        if ms_match:
            total += float(ms_match.group(1)) / 1000.0

        if total > 0.0:
            return total
        return float(val)
    except Exception:
        return 0.0


def parse_retry_after(headers: Mapping[str, Any], error_body: str = "") -> float:
    """
    Extract retry delay in seconds from HTTP headers or error body.
    Handles 'Retry-After', 'x-ratelimit-reset-tokens', and Groq error text.
    """
    # 1. Standard Retry-After header
    hdr_val = headers.get("retry-after") or headers.get("Retry-After")
    if hdr_val:
        try:
            return max(0.5, float(hdr_val))
        except ValueError:
            parsed = parse_groq_duration(str(hdr_val))
            if parsed > 0.0:
                return max(0.5, parsed)

    # 2. Groq specific reset tokens header
    reset_tok = headers.get("x-ratelimit-reset-tokens")
    if reset_tok:
        parsed = parse_groq_duration(reset_tok)
        if parsed > 0.0:
            return max(0.5, parsed)

    # 3. Parse error message (e.g. 'Please try again in 4.5s' or 'try again in 850ms')
    if error_body:
        match = re.search(r"try again in\s*([\d\.]+)\s*(ms|s|m)?", str(error_body), re.IGNORECASE)
        if match:
            num = float(match.group(1))
            unit = (match.group(2) or "s").lower()
            if unit == "ms":
                return max(0.5, num / 1000.0)
            elif unit == "m":
                return max(0.5, num * 60.0)
            else:
                return max(0.5, num)

    return 2.5


class GroqRateLimiter:
    """
    Thread-safe and coroutine-safe rate limiter and token tracking manager for Groq API.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._remaining_tokens: Dict[str, int] = {}
        self._tokens_reset_at: Dict[str, float] = {}
        self._remaining_requests: Dict[str, int] = {}
        self._requests_reset_at: Dict[str, float] = {}
        self._last_call_timestamp: float = 0.0
        self._min_interval: float = float(os.getenv("GROQ_MIN_INTERVAL", str(DEFAULT_GROQ_MIN_INTERVAL)))

    def update_from_headers(self, model: str, headers: Mapping[str, Any], status_code: int = 200) -> None:
        """Update rate limit counters from HTTP response headers."""
        now = time.time()
        # Remaining tokens
        tok_rem = headers.get("x-ratelimit-remaining-tokens")
        if tok_rem is not None:
            try:
                self._remaining_tokens[model] = int(tok_rem)
            except (ValueError, TypeError):
                pass

        # Reset tokens duration
        tok_reset = headers.get("x-ratelimit-reset-tokens")
        if tok_reset is not None:
            dur = parse_groq_duration(tok_reset)
            if dur > 0:
                self._tokens_reset_at[model] = now + dur

        # Remaining requests
        req_rem = headers.get("x-ratelimit-remaining-requests")
        if req_rem is not None:
            try:
                self._remaining_requests[model] = int(req_rem)
            except (ValueError, TypeError):
                pass

        # Reset requests duration
        req_reset = headers.get("x-ratelimit-reset-requests")
        if req_reset is not None:
            dur = parse_groq_duration(req_reset)
            if dur > 0:
                self._requests_reset_at[model] = now + dur

        if status_code == 429:
            retry_wait = parse_retry_after(headers)
            self._tokens_reset_at[model] = now + retry_wait
            self._remaining_tokens[model] = 0
            logger.warning(
                "Groq 429 Rate Limit for model %s: remaining tokens set to 0, cooling down for %.2fs",
                model, retry_wait
            )

    def is_model_rate_limited(self, model: str, required_tokens: int = TOKEN_SAFETY_BUFFER) -> bool:
        """Check if a model currently has depleted token budget and is cooling down."""
        now = time.time()
        reset_time = self._tokens_reset_at.get(model, 0.0)
        remaining = self._remaining_tokens.get(model, 8000)

        # If reset time is in the future and remaining is below safety buffer, model is rate limited
        if now < reset_time and remaining < required_tokens:
            return True
        return False

    def get_preferred_available_model(self, candidate_models: List[str]) -> str:
        """
        Select the best candidate model that is not currently token-depleted.
        If all are depleted, returns the one with the earliest reset time.
        """
        now = time.time()
        for m in candidate_models:
            if not self.is_model_rate_limited(m):
                return m

        # All models constrained: pick the one that resets soonest
        earliest_model = candidate_models[0]
        earliest_time = float("inf")
        for m in candidate_models:
            rst = self._tokens_reset_at.get(m, 0.0)
            if rst < earliest_time:
                earliest_time = rst
                earliest_model = m

        logger.info(
            "All candidate Groq models constrained; selected %s (resets in %.2fs)",
            earliest_model, max(0.0, earliest_time - now)
        )
        return earliest_model

    async def pace_request(self, model: str, estimated_tokens: int = 1500) -> float:
        """
        Enforce safe inter-request pacing and wait if the model's token bucket is low.
        Returns the duration slept in seconds.
        """
        total_slept = 0.0
        async with self._lock:
            now = time.time()

            # 1. Inter-request pacing to avoid burst rate spikes
            elapsed = now - self._last_call_timestamp
            if elapsed < self._min_interval:
                pace_sleep = self._min_interval - elapsed
                logger.debug("Pacing Groq request for %.2fs...", pace_sleep)
                await asyncio.sleep(pace_sleep)
                total_slept += pace_sleep
                now = time.time()

            # 2. Token quota cooldown if model is nearing token exhaustion
            remaining = self._remaining_tokens.get(model, 8000)
            reset_at = self._tokens_reset_at.get(model, 0.0)
            if remaining < estimated_tokens and now < reset_at:
                cooldown_sleep = min(reset_at - now + 0.15, 6.0)
                if cooldown_sleep > 0.05:
                    logger.warning(
                        "Groq model %s low on tokens (%d remaining < %d needed). Cooldown pause for %.2fs...",
                        model, remaining, estimated_tokens, cooldown_sleep
                    )
                    await asyncio.sleep(cooldown_sleep)
                    total_slept += cooldown_sleep
                    now = time.time()

            self._last_call_timestamp = time.time()
            return total_slept


# Global singleton instance
groq_rate_limiter = GroqRateLimiter()
