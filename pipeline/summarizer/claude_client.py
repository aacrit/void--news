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

# Three-strike consecutive-failure counter. A single billing blip or transient
# 500 must NOT kill Claude for the entire run (P0 from UAT 2026-05-13 — one
# transient billing error caused only 1/65 calls to reach Claude). Hard-latch
# only on signals that are definitely terminal: credit/balance/billing/auth.
_consecutive_failures: int = 0
_MAX_CONSECUTIVE_FAILURES: int = 3
_persistent_failure: bool = False           # set when 3 in a row, OR billing dead
_billing_dead: bool = False                 # latches immediately on credit/auth

_client: object = None


def _record_failure(error_str: str, run_id: str | None = None) -> None:
    """Record a Claude failure. Latches _billing_dead immediately on terminal
    signals; otherwise increments a 3-strike consecutive counter."""
    global _consecutive_failures, _persistent_failure, _billing_dead
    err_l = error_str.lower()
    terminal = any(k in err_l for k in (
        "credit", "balance", "billing",
        "invalid_api_key", "invalid api key",
        "authentication", "unauthorized",
    ))
    if terminal:
        _billing_dead = True
        _persistent_failure = True
        print(f"  [error] Claude TERMINAL failure (billing/auth) — disabling for this run: {error_str}")
        _report_failure_to_run("claude_billing_dead", error_str, run_id)
        return

    _consecutive_failures += 1
    print(f"  [warn] Claude failure {_consecutive_failures}/{_MAX_CONSECUTIVE_FAILURES}: {error_str}")
    if _consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
        _persistent_failure = True
        print(f"  [error] Claude tripped {_MAX_CONSECUTIVE_FAILURES}-strike consecutive-failure latch — disabling for this run")
        _report_failure_to_run("claude_3strike_latch", error_str, run_id)


def _record_success() -> None:
    """Reset consecutive-failure counter on any successful Claude call."""
    global _consecutive_failures
    if _consecutive_failures > 0:
        _consecutive_failures = 0


def _report_failure_to_run(code: str, detail: str, run_id: str | None) -> None:
    """Best-effort push of a Claude failure marker into pipeline_runs.errors.
    Silent on failure — we never let observability code break the pipeline."""
    try:
        from utils.supabase_client import supabase
        # run_id may be None — fall back to most recent running row
        if not run_id:
            r = supabase.table("pipeline_runs").select("id,errors").eq(
                "status", "running"
            ).order("started_at", desc=True).limit(1).execute()
            if not (r.data and len(r.data) > 0):
                return
            run_id = r.data[0]["id"]
            existing = r.data[0].get("errors") or []
        else:
            r = supabase.table("pipeline_runs").select("errors").eq("id", run_id).execute()
            existing = (r.data[0].get("errors") or []) if (r.data and len(r.data) > 0) else []
        from datetime import datetime, timezone
        existing.append({
            "source": "claude_client",
            "code": code,
            "error": detail[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        supabase.table("pipeline_runs").update({"errors": existing}).eq("id", run_id).execute()
    except Exception:
        pass


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
                parsed = json.loads(text)
                _record_success()
                return parsed
            except json.JSONDecodeError:
                pass

            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start >= 0 and brace_end > brace_start:
                parsed = json.loads(text[brace_start:brace_end + 1])
                _record_success()
                return parsed

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
            error_str_lower = str(e).lower()
            # Terminal signals: latch immediately
            if any(k in error_str_lower for k in (
                "credit", "balance", "billing",
                "invalid_api_key", "invalid api key",
                "authentication", "unauthorized",
            )):
                _record_failure(str(e))
                return None
            if "429" in error_str_lower or "rate" in error_str_lower:
                print(f"  [warn] Claude rate limit (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(15)
                    continue
                # Exhausted retries on rate-limit -- count as a strike
                _record_failure(str(e))
            else:
                # Generic transient error — count as a strike (3 in a row latches)
                _record_failure(str(e))
            return None

    return None


def is_available() -> bool:
    # PERMANENTLY DISABLED (2026-06-20). Claude/Anthropic was retired in the
    # move to a sustainable $0 stack. Gemini is now the sole primary: cluster
    # summaries run on gemini-2.5-flash-lite (high-RPD tier) and the daily brief
    # TL;DR + opinion run on gemini-2.5-flash; Groq (openai/gpt-oss-20b) is the
    # $0 fallback for both. This hard return False is the master switch — it
    # cascades to all callers (cluster_summarizer, daily_brief, weekly_digest,
    # ig_caption), so no ANTHROPIC_API_KEY or env change can re-enable a paid call.
    #
    # To re-enable later: delete this early return and restore the gated logic
    # below (env DISABLE_ANTHROPIC + key presence).
    return False

    if os.environ.get("DISABLE_ANTHROPIC", "").strip().lower() in ("1", "true", "yes"):
        return False
    if _persistent_failure:
        return False
    if not CLAUDE_AVAILABLE:
        return False
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(api_key)


def get_call_count() -> int:
    return _call_count
