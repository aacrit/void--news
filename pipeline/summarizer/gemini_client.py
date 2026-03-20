"""
Gemini API client for the void --news pipeline.

Uses the google-genai SDK (not the deprecated google-generativeai).
Aggressive free-tier protection:
    - Rate limited to ~14 RPM (4.2s between calls)
    - Hard cap of 15 calls per pipeline run
    - 1 retry max on transient failures

At 2 pipeline runs/day: max 30 RPD = 2% of the 1500 RPD free limit.

Environment:
    GEMINI_API_KEY — required. Get one free at https://aistudio.google.com/apikey
"""

import json
import os
import time

# SDK is optional — pipeline works without it
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

_MODEL = "gemini-2.5-flash"

# Rate limiting state (module-level singleton)
_last_call_time: float = 0.0
_MIN_INTERVAL: float = 4.2  # 60s / 14 calls = ~4.3s (stay under 15 RPM)

# Per-run call cap — hard limit to stay within free tier (1500 RPD).
# Pipeline runs 2x/day, so 25 calls/run × 2 runs = 50 RPD (3.3% of limit).
_MAX_CALLS_PER_RUN: int = 25
_call_count: int = 0

_client: object = None


def _get_client():
    """Lazily create the Gemini client. Returns the client or None."""
    global _client
    if not GEMINI_AVAILABLE:
        return None
    if _client is not None:
        return _client
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    _client = genai.Client(api_key=api_key)
    return _client


def _rate_limit():
    """Sleep if needed to stay within the free-tier 15 RPM limit."""
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call_time = time.time()


def calls_remaining() -> int:
    """Return how many API calls are left in this pipeline run."""
    return max(0, _MAX_CALLS_PER_RUN - _call_count)


def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    max_retries: int = 1,
) -> dict | None:
    """
    Send a prompt to Gemini Flash and parse the JSON response.

    Args:
        prompt: The user-turn prompt text.
        system_instruction: Optional persistent role/style instruction passed
            as the system turn. When None (default), no system instruction is
            sent and behavior is identical to the previous implementation.
        max_retries: Number of additional attempts on transient failures.

    Returns parsed JSON dict, or None on failure (caller falls back
    to rule-based generation).
    """
    global _call_count

    client = _get_client()
    if client is None:
        return None

    # Hard cap: stop calling to protect free tier
    if _call_count >= _MAX_CALLS_PER_RUN:
        return None

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        max_output_tokens=8192,  # Gemini 2.5 Flash uses thinking tokens internally
        system_instruction=system_instruction,  # None = no system turn (backward-compatible)
    )

    for attempt in range(max_retries + 1):
        try:
            _rate_limit()
            _call_count += 1
            response = client.models.generate_content(
                model=_MODEL,
                contents=prompt,
                config=config,
            )

            if not response.text:
                continue

            text = response.text.strip()
            # Handle markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError:
            if attempt < max_retries:
                continue
            return None
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "rate" in error_str:
                if attempt < max_retries:
                    time.sleep(15)
                    continue
            print(f"  [warn] Gemini API error: {e}")
            return None

    return None


def is_available() -> bool:
    """Check if Gemini is configured and the SDK is installed."""
    if not GEMINI_AVAILABLE:
        return False
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return bool(api_key)


def get_call_count() -> int:
    """Return the number of Gemini API calls made this run."""
    return _call_count
