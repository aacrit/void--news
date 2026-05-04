"""
Claude API client for the void --news pipeline.

Mirrors the generate_json() interface from gemini_client.py so callers
can swap between models transparently. Uses the Anthropic Python SDK.

Budget: All cluster summarization + brief + opinion + weekly digest.
Per pipeline run (1x/day, world edition only):
    50 cluster summaries + 1 brief + 1 opinion + ~3.6 weekly avg = ~55 calls
    ~$1/day at Sonnet 4.6 rates with prompt caching = ~$30-40/month.

Environment:
    ANTHROPIC_API_KEY — required for Claude content generation.
    Set in .env and GitHub Actions secrets.
"""

import json
import os
import time

try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

_MODEL = "claude-sonnet-4-6"

_last_call_time: float = 0.0
_MIN_INTERVAL: float = 1.0

# Per-run call cap. 1x/day cadence: 50 clusters + 1 brief + 1 opinion +
# weekly spike + retries. 80 is a safety net, not a budget — Anthropic
# tier-3 limits handle the burst comfortably.
_MAX_CALLS_PER_RUN: int = 80
_call_count: int = 0

_persistent_failure: bool = False

_client: object = None


def _get_client():
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
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_call_time = time.time()


def calls_remaining() -> int:
    return max(0, _MAX_CALLS_PER_RUN - _call_count)


def _build_system_block(system_instruction: str | None):
    """
    Wrap the system instruction in a cacheable content block when present.

    Anthropic prompt caching has a 1024-token minimum (Sonnet) and a 5-minute
    TTL. Blocks below the minimum still pass through fine — they just don't
    activate the cache. Marking unconditionally is safe; if the system block
    grows past 1024 tokens later, caching auto-engages with no code change.
    """
    if not system_instruction:
        return None
    return [{
        "type": "text",
        "text": system_instruction,
        "cache_control": {"type": "ephemeral"},
    }]


def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    max_retries: int = 1,
    count_call: bool = True,
    max_output_tokens: int = 8192,
) -> dict | None:
    """
    Send a prompt to Claude and parse the JSON response.

    Interface mirrors gemini_client.generate_json() exactly so callers can
    swap transparently. Returns parsed JSON dict, or None on failure.
    """
    global _call_count, _persistent_failure

    if _persistent_failure:
        return None

    client = _get_client()
    if client is None:
        return None

    if count_call and _call_count >= _MAX_CALLS_PER_RUN:
        return None

    messages = [{"role": "user", "content": prompt}]

    if count_call:
        _call_count += 1

    for attempt in range(max_retries + 1):
        try:
            _rate_limit()

            kwargs = {
                "model": _MODEL,
                "max_tokens": max_output_tokens,
                "messages": messages,
                "temperature": 0.3,
            }
            system_block = _build_system_block(system_instruction)
            if system_block is not None:
                kwargs["system"] = system_block

            response = client.messages.create(**kwargs)

            if not response.content:
                print(f"  [warn] Claude returned empty response (attempt {attempt + 1})")
                continue

            text = response.content[0].text.strip()

            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

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
            if "credit" in error_str or "balance" in error_str or "billing" in error_str:
                _persistent_failure = True
                print(f"  [error] Claude persistent billing failure — disabling for this run: {e}")
                return None
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
    if _persistent_failure:
        return False
    if not CLAUDE_AVAILABLE:
        return False
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(api_key)


def get_call_count() -> int:
    return _call_count
