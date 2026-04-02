"""
Claude API client for the void --news pipeline.

Mirrors the generate_json() interface from gemini_client.py so callers
can swap between models transparently. Uses the Anthropic Python SDK.

Budget: Brief generation only (not cluster summarization or triage).
At ~24 calls/day × 30 days = ~720 calls/month.
Cost at Sonnet rates: ~$0.05/month (negligible).

Environment:
    ANTHROPIC_API_KEY — required for Claude content generation.
    Set in .env and GitHub Actions secrets.
"""

import json
import os
import time

# SDK is optional — pipeline works without it
CLAUDE_AVAILABLE = False
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    pass

_MODEL = "claude-sonnet-4-6"

# Rate limiting state
_last_call_time: float = 0.0
_MIN_INTERVAL: float = 1.0  # Claude API is more generous than Gemini free tier

# Per-run call cap — safety net for brief generation
_MAX_CALLS_PER_RUN: int = 15
_call_count: int = 0

_client: object = None


def _get_client():
    """Lazily create the Anthropic client. Returns the client or None."""
    global _client
    if not CLAUDE_AVAILABLE:
        return None
    if _client is not None:
        return _client
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _rate_limit():
    """Sleep if needed to avoid burst requests."""
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
    count_call: bool = True,
    max_output_tokens: int = 8192,
) -> dict | None:
    """
    Send a prompt to Claude and parse the JSON response.

    Interface mirrors gemini_client.generate_json() exactly so callers
    can swap transparently. The count_call parameter is accepted for
    interface compatibility but all Claude calls share one budget.

    Returns parsed JSON dict, or None on failure.
    """
    global _call_count

    client = _get_client()
    if client is None:
        return None

    if count_call and _call_count >= _MAX_CALLS_PER_RUN:
        return None

    # Build messages
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(max_retries + 1):
        try:
            _rate_limit()
            if count_call:
                _call_count += 1

            # Cap max_tokens to 4096 for brief generation — keeps responses
            # focused and avoids the streaming requirement for long operations.
            effective_max = min(max_output_tokens, 4096)

            kwargs = {
                "model": _MODEL,
                "max_tokens": effective_max,
                "messages": messages,
                "temperature": 0.3,
            }
            if system_instruction:
                kwargs["system"] = system_instruction

            response = client.messages.create(**kwargs)

            if not response.content:
                print(f"  [warn] Claude returned empty response (attempt {attempt + 1})")
                continue

            text = response.content[0].text.strip()

            # Handle markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            # Try direct JSON parse first
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # Fallback: find JSON object in response
            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start >= 0 and brace_end > brace_start:
                return json.loads(text[brace_start:brace_end + 1])

            snippet = (text[:200] + "...") if len(text) > 200 else text
            print(f"  [warn] Claude JSON parse failed (attempt {attempt + 1}): "
                  f"response starts with: {snippet!r}")
            if attempt < max_retries:
                continue
            return None

        except json.JSONDecodeError as je:
            print(f"  [warn] Claude JSON parse failed (attempt {attempt + 1}): {je}")
            if attempt < max_retries:
                continue
            return None
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                print(f"  [warn] Claude rate limit (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(15)
                    continue
            else:
                print(f"  [warn] Claude API error (attempt {attempt + 1}): {e}")
            return None

    return None


def is_available() -> bool:
    """Check if Claude is configured and the SDK is installed."""
    if not CLAUDE_AVAILABLE:
        return False
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(api_key)


def get_call_count() -> int:
    """Return the number of Claude API calls made this run."""
    return _call_count
