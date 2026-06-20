"""
Groq API client for the void --news pipeline.

Free, OpenAI-compatible inference. Mirrors the generate_json() interface from
gemini_client.py / claude_client.py exactly so callers can swap between
providers transparently. Used as the preferred $0 provider for cluster
summaries + TL;DR when Claude is disabled (DISABLE_ANTHROPIC=1).

Why Groq for the free path:
    - Genuinely free tier (no expiring trial credit).
    - Schema-constrained JSON via response_format={"type":"json_object"} —
      keeps the downstream json.loads() safe.
    - Fast (LPU inference), OpenAI-compatible API callable from GitHub Actions.

Model: openai/gpt-oss-20b (override with GROQ_MODEL). The deprecated
llama-3.1-8b-instant / llama-3.3-70b-versatile are intentionally NOT defaults.

Free-tier limits to respect (verify in console.groq.com — they move):
    gpt-oss-20b ≈ 30 RPM / 1,000 RPD / 8k TPM / 200k TPD.
    The per-run cap + rate limit below stay well inside RPM/RPD. The big
    65k-token daily brief is intentionally NOT routed here (TPM/TPD make a
    single giant completion impractical) — generate_json() returns None for
    oversized requests so the caller falls through to Gemini.

Model: llama-3.1-8b-instant (a non-reasoning instruct model). 2026-06-20: the
default was openai/gpt-oss-20b, but that's a REASONING model — with json_object
mode + a small token budget it burns its output on internal reasoning and emits
'max completion tokens reached before generating a valid document', failing
nearly every summary. llama-3.1-8b-instant returns clean JSON in few tokens and
has far more generous RPD/TPD, so it carries the bulk of cluster summaries.
NOTE: Groq's Llama models are slated to deprecate ~2026-08-16 — when that lands,
set GROQ_MODEL to whatever instruct model Groq offers then (one-line change).

Environment:
    GROQ_API_KEY — required. Get one free at https://console.groq.com/keys
    GROQ_MODEL   — optional model override (default llama-3.1-8b-instant).
"""

import json
import os
import time

# SDK is optional — pipeline works without it (falls through to Gemini)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

_MODEL = os.environ.get("GROQ_MODEL", "").strip() or "llama-3.1-8b-instant"

# Rate limiting state (module-level singleton). 30 RPM free tier → 2.1s spacing.
_last_call_time: float = 0.0
_MIN_INTERVAL: float = 2.1

# Per-run call cap — safety net well under the 1,000 RPD free limit.
_MAX_CALLS_PER_RUN: int = 70
_call_count: int = 0

# Groq free-tier TPM/TPD make very large single completions impractical. Skip
# any request asking for more than this so the 65k-token daily brief routes to
# Gemini instead. The brief (65536) is deferred; summaries are clamped below.
_MAX_SAFE_OUTPUT_TOKENS: int = 16384
# Hard cap on tokens we actually REQUEST from Groq per call. Critical: the free
# tier enforces an 8,000 tokens-per-minute (TPM) limit and counts max_tokens as
# a reservation against it, so input + max_tokens must stay under 8,000 or the
# call 413s outright. A cluster summary/TL;DR only needs a few hundred tokens of
# output; 2048 leaves ~5,900 tokens of input headroom under the TPM cap.
_OUTPUT_CEILING: int = 2048

# Persistent failure flag — set on billing/auth/quota errors so we stop wasting
# the run on doomed retries and let the next provider take over immediately.
_persistent_failure: bool = False

_client: object = None


def _get_client():
    """Lazily create the Groq client. Returns the client or None."""
    global _client
    if not GROQ_AVAILABLE:
        return None
    if _client is not None:
        return _client
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    _client = Groq(api_key=api_key)
    return _client


def _rate_limit():
    """Sleep if needed to stay within the free-tier RPM limit."""
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
    Send a prompt to Groq and parse the JSON response.

    Interface mirrors gemini_client.generate_json() / claude_client.generate_json()
    exactly so callers can swap transparently. Returns parsed JSON dict, or None
    on failure (caller falls back to the next provider / rule-based generation).

    Oversized requests (max_output_tokens > _MAX_SAFE_OUTPUT_TOKENS, e.g. the
    65k daily brief) return None immediately without burning budget — the caller
    falls through to Gemini, which handles big single-shot output.
    """
    global _call_count, _persistent_failure

    if _persistent_failure:
        return None

    # Defer oversized completions to Gemini (see _MAX_SAFE_OUTPUT_TOKENS).
    if max_output_tokens > _MAX_SAFE_OUTPUT_TOKENS:
        return None

    client = _get_client()
    if client is None:
        return None

    # Hard cap: stop calling to protect free tier.
    if count_call and _call_count >= _MAX_CALLS_PER_RUN:
        return None

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    # Increment ONCE before the retry loop — failed retries don't burn budget.
    if count_call:
        _call_count += 1

    out_tokens = min(max_output_tokens, _OUTPUT_CEILING)

    for attempt in range(max_retries + 1):
        try:
            _rate_limit()
            response = client.chat.completions.create(
                model=_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=out_tokens,
            )

            if not response.choices or not response.choices[0].message.content:
                print(f"  [warn] Groq returned empty response (attempt {attempt + 1})")
                continue

            text = response.choices[0].message.content.strip()
            # json_object mode returns clean JSON, but strip fences defensively.
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError as je:
            snippet = (text[:200] + "...") if len(text) > 200 else text
            print(f"  [warn] Groq JSON parse failed (attempt {attempt + 1}): "
                  f"{je} — response starts with: {snippet!r}")
            if attempt < max_retries:
                continue
            return None
        except Exception as e:
            error_str = str(e).lower()
            # Transient FIRST: 429/413 rate-limit / TPM-exceeded. Groq's rate
            # message embeds a "console.groq.com/settings/billing" upsell URL, so
            # checking billing keywords first would misread a rate limit as a
            # terminal billing failure. Order matters.
            if ("rate_limit" in error_str or "429" in error_str
                    or "413" in error_str or "tokens per minute" in error_str
                    or "quota" in error_str):
                print(f"  [warn] Groq rate/TPM limit (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(15)
                    continue
                return None
            # Terminal signals: stop trying for the rest of the run. Tight
            # keyword set so upsell URLs don't false-positive.
            if any(k in error_str for k in (
                "invalid_api_key", "invalid api key", "authentication",
                "unauthorized", "permission", "insufficient",
            )):
                _persistent_failure = True
                print(f"  [error] Groq terminal failure — disabling for this run: {e}")
                return None
            print(f"  [warn] Groq API error (attempt {attempt + 1}): {e}")
            return None

    return None


def is_available() -> bool:
    """Check if Groq is configured, the SDK is installed, and no persistent failure."""
    # Kill switch mirroring DISABLE_ANTHROPIC / DISABLE_GEMINI: set
    # DISABLE_GROQ=1 to short-circuit every Groq call to None (falls through
    # to Gemini, then rule-based).
    if os.environ.get("DISABLE_GROQ", "").strip().lower() in ("1", "true", "yes"):
        return False
    if _persistent_failure:
        return False
    if not GROQ_AVAILABLE:
        return False
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    return bool(api_key)


def get_call_count() -> int:
    """Return the number of Groq API calls made this run."""
    return _call_count
