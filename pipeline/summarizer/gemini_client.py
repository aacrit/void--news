"""
Gemini API client for the void --news pipeline.

Uses the google-genai SDK (not the deprecated google-generativeai).

Gemini is the sole LLM primary (Claude retired 2026-06-22). Two-model split:
    - gemini-2.5-flash-lite (_MODEL)       → story/cluster summaries. High
      volume (~30-50/run), so it rides the high-RPD lite tier.
    - gemini-2.5-flash (_FLASH_MODEL)      → daily brief TL;DR + opinion. A few
      calls/day, comfortably under flash's 20-requests/DAY free cap.
Claude and Groq are retired; Gemini is the only LLM (rule-based fallback).

Free-tier protection:
    - Rate limited to ~8.5 RPM (7s between calls) — under flash-lite's 10 RPM
    - Hard cap of 70 calls per pipeline run (summarization budget safety net)
    - 0 retries by default (each retry burns scarce daily quota)

At 1 pipeline run/day the summarization pass makes ~30-50 flash-lite calls and
the brief ~2-4 flash calls — both well inside their respective free quotas.

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

# 2026-06-20: gemini-2.5-flash free tier was cut to just 20 requests/DAY
# (RESOURCE_EXHAUSTED: GenerateRequestsPerDayPerProjectPerModel-FreeTier=20),
# which can't cover a ~30-call summarization run. flash-LITE is the high-volume
# free tier (far higher RPD, same JSON/structured-output mode, ample quality for
# grounded summarization). Override per-deploy with GEMINI_MODEL if needed.
#
# 2026-06-22: two-model split (Gemini is now the sole primary; Claude retired).
#   _MODEL (flash-lite)  → story/cluster summaries. High volume (~30-50/run),
#                          so it MUST be the high-RPD lite tier.
#   _FLASH_MODEL (flash) → daily brief TL;DR + opinion. Low volume (a few
#                          calls/day, well under flash's 20/day cap), so we
#                          spend the higher-quality flash tier where it shows.
# Callers pick per-call via generate_json(..., model=...). Both overridable.
_MODEL = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash-lite"
_FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL", "").strip() or "gemini-2.5-flash"

# Rate limiting state (module-level singleton). flash-lite free tier is 15 RPM,
# so ~4.2s spacing (≈14 RPM) keeps every run under the per-minute ceiling — this
# is the "staggering" that prevents minute-limit 429s. Calls are emitted one at
# a time with this gap, never bursted.
_last_call_time: float = 0.0
# flash-lite free tier is 10 requests/MINUTE (GenerateRequestsPerMinute
# FreeTier=10, confirmed 2026-06-20). 7s spacing ≈ 8.5 RPM keeps every run
# clearly under that ceiling — this is the staggering that prevents 429
# throttles. Override with GEMINI_MIN_INTERVAL if a model/tier differs.
_MIN_INTERVAL: float = float(os.environ.get("GEMINI_MIN_INTERVAL", "") or 7.0)

# Per-run call cap — safety net. The daily run summarizes the displayed top-50
# post-rerank (step 8d) plus the step-7b brief-input pass, so on a low-cache day
# it can approach ~80 flash-lite calls — well under flash-lite's high daily
# request quota. Cap set above that so full top-50 coverage is never truncated.
_MAX_CALLS_PER_RUN: int = 90
_call_count: int = 0

# Persistent failure flag — set on billing/spending-cap errors to skip all
# subsequent calls in the same run (avoids wasting minutes on doomed retries).
_persistent_failure: bool = False

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
    max_retries: int = 0,
    count_call: bool = True,
    max_output_tokens: int = 8192,
    model: str | None = None,
) -> dict | None:
    """
    Send a prompt to Gemini Flash and parse the JSON response.

    2026-06-20: default max_retries 1 -> 0. Each retry is a NEW request against
    the free tier's 20-requests/day cap, so retrying a throttle/error just burns
    scarce quota. Fail fast instead — the caller falls back to rule-based (summaries)
    or carry-forward (brief). Pass max_retries explicitly to opt back in.

    Args:
        prompt: The user-turn prompt text.
        system_instruction: Optional persistent role/style instruction passed
            as the system turn. When None (default), no system instruction is
            sent and behavior is identical to the previous implementation.
        max_retries: Number of additional attempts on transient failures.
        count_call: When True (default), increments the per-run call counter
            and enforces the 25-call summarization budget cap. When False,
            both the cap check and the increment are skipped — use for
            editorial triage calls that have their own separate budget.
        max_output_tokens: Maximum output tokens including thinking tokens.
            Default 8192 for cluster summaries. Use 65536 for briefs which
            produce TL;DR + audio script (~1200 words of output).

    Returns parsed JSON dict, or None on failure (caller falls back
    to rule-based generation).
    """
    global _call_count, _persistent_failure

    if _persistent_failure:
        return None

    client = _get_client()
    if client is None:
        return None

    # Hard cap: stop calling to protect free tier (skipped for out-of-budget callers)
    if count_call and _call_count >= _MAX_CALLS_PER_RUN:
        return None

    # Default to flash-lite (high-RPD summarization tier); brief callers pass
    # model=_FLASH_MODEL for the higher-quality, low-volume TL;DR + opinion.
    use_model = (model or "").strip() or _MODEL

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        max_output_tokens=max_output_tokens,
        system_instruction=system_instruction,  # None = no system turn (backward-compatible)
    )

    # Increment call count ONCE before the retry loop — failed retries should
    # not burn additional budget.
    if count_call:
        _call_count += 1

    for attempt in range(max_retries + 1):
        try:
            _rate_limit()
            response = client.models.generate_content(
                model=use_model,
                contents=prompt,
                config=config,
            )

            if not response.text:
                print(f"  [warn] Gemini returned empty response (attempt {attempt + 1})")
                continue

            text = response.text.strip()
            # Handle markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            return json.loads(text)

        except json.JSONDecodeError as je:
            # Log what Gemini actually returned so we can diagnose format issues
            snippet = (text[:200] + "...") if len(text) > 200 else text
            print(f"  [warn] Gemini JSON parse failed (attempt {attempt + 1}): "
                  f"{je} — response starts with: {snippet!r}")
            if attempt < max_retries:
                continue
            return None
        except Exception as e:
            error_str = str(e).lower()
            # Transient FIRST. A free-tier 429 RESOURCE_EXHAUSTED (e.g. the
            # flash-lite 10-RPM cap) embeds "check your plan and billing
            # details", so checking billing keywords first would misread a
            # per-minute throttle as a terminal failure and disable Gemini for
            # the ENTIRE run (2026-06-20: this killed a whole pipeline run after
            # the first throttle). Order matters — rate limit is checked first.
            if ("429" in error_str or "resource_exhausted" in error_str
                    or "quota" in error_str or "rate" in error_str):
                print(f"  [warn] Gemini rate limit (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(10)
                    continue
                return None
            if "503" in error_str or "unavailable" in error_str or "overloaded" in error_str or "high demand" in error_str:
                # 503 = transient server overload — wait longer before retry
                print(f"  [warn] Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(30)
                    continue
                return None
            # Genuinely terminal: a blocked/invalid key or a hard spending cap.
            # NOT bare "billing"/"credit" — those appear in transient quota text.
            if any(k in error_str for k in (
                "api key not valid", "api_key_invalid", "invalid api key",
                "permission_denied", "permission denied", "suspended",
                "spending cap",
            )):
                _persistent_failure = True
                print(f"  [error] Gemini terminal failure — disabling for this run: {e}")
                return None
            print(f"  [warn] Gemini API error (attempt {attempt + 1}): {e}")
            return None

    return None


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    count_call: bool = True,
    max_output_tokens: int = 8192,
    model: str | None = None,
) -> str | None:
    """Send a prompt to Gemini and return the PLAIN-TEXT response (no JSON).

    For a single long free-text output (e.g. the ~3000-word weekly audio script),
    wrapping the text in JSON is fragile — one unescaped quote inside the string
    breaks json.loads and drops the whole result. This path skips JSON entirely.
    Returns the stripped text, or None on failure (caller falls back).
    """
    global _call_count, _persistent_failure

    if _persistent_failure:
        return None
    client = _get_client()
    if client is None:
        return None
    if count_call and _call_count >= _MAX_CALLS_PER_RUN:
        return None

    use_model = (model or "").strip() or _MODEL
    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=max_output_tokens,
        system_instruction=system_instruction,
    )
    if count_call:
        _call_count += 1

    try:
        _rate_limit()
        response = client.models.generate_content(
            model=use_model, contents=prompt, config=config,
        )
        if not response.text:
            print("  [warn] Gemini returned empty text response")
            return None
        text = response.text.strip()
        # Strip markdown fences if the model added them despite instructions.
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return text
    except Exception as e:
        error_str = str(e).lower()
        if any(k in error_str for k in (
            "api key not valid", "api_key_invalid", "invalid api key",
            "permission_denied", "permission denied", "suspended", "spending cap",
        )):
            _persistent_failure = True
            print(f"  [error] Gemini terminal failure — disabling for this run: {e}")
        else:
            print(f"  [warn] Gemini text generation failed: {e}")
        return None


def is_available() -> bool:
    """Check if Gemini is configured, the SDK is installed, and no persistent failure."""
    # 2026-05-24 — mirror DISABLE_ANTHROPIC kill switch. When set, every
    # Gemini call short-circuits to None. cluster_summarizer falls back
    # to rule-based summary; daily_brief writes a stub. Costs → $0
    # immediately. Required for the CEO's "strictly no LLM" iteration
    # mode where clustering + ranking are tuned against deterministic
    # rule-based output only.
    if os.environ.get("DISABLE_GEMINI", "").strip().lower() in ("1", "true", "yes"):
        return False
    if _persistent_failure:
        return False
    if not GEMINI_AVAILABLE:
        return False
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return bool(api_key)


def get_call_count() -> int:
    """Return the number of Gemini API calls made this run."""
    return _call_count


# ---------------------------------------------------------------------------
# Editorial triage — ask Gemini to editorially rank top candidates
# Separate budget from summarization (max 5 calls per run)
# ---------------------------------------------------------------------------
_triage_call_count: int = 0
_MAX_TRIAGE_CALLS: int = 5

_TRIAGE_SYSTEM_INSTRUCTION = (
    "You are a senior front-page editor at a major international newspaper. "
    "Your job is to look at a list of today's stories and decide which deserve "
    "the most prominent placement. You select and order — you do not write.\n\n"
    "Selection criteria (priority order):\n"
    "1. Scale of real-world consequences: how many people affected, how binding, "
    "how irreversible?\n"
    "2. Novelty: genuinely new, or incremental update on yesterday's story?\n"
    "3. Institutional authority: head of state > cabinet minister > local official\n"
    "4. Global vs local: multiple countries > one country > one city\n"
    "5. Source consensus: many independent outlets covering it = editors agree it matters\n\n"
    "NEVER consider political lean or partisan implications. A conservative policy "
    "win and a progressive policy win of equal consequence receive equal placement."
)


def editorial_triage(
    candidates: list[dict],
    section: str,
) -> dict | None:
    """
    Ask Gemini to editorially rank top ~30 cluster candidates for a section.

    Args:
        candidates: List of cluster dicts with id, title, summary, source_count
        section: Section name (world/us/india)

    Returns dict with:
        ranked_ids: list of cluster IDs in editorial priority order (top 10)
        duplicate_flags: list of [id_a, id_b] pairs (possible same story)
        incremental_flags: list of cluster IDs that are incremental updates
    Returns None if unavailable or budget exhausted.
    """
    global _triage_call_count

    if not is_available():
        return None
    if _triage_call_count >= _MAX_TRIAGE_CALLS:
        return None

    # Build candidate list
    lines = []
    for c in candidates[:30]:
        cid = c.get("id", "")
        title = (c.get("title", "") or "")[:120]
        summary = (c.get("summary", "") or "")[:200]
        src_count = c.get("source_count", 0)
        lines.append(f"[{cid}] ({src_count} sources) {title}")
        if summary:
            lines.append(f"  {summary}")

    candidate_block = "\n".join(lines)

    prompt = (
        f"You are editing the {section.upper()} section front page. "
        f"Below are today's top candidate stories. Return a JSON object with "
        f"exactly three fields:\n\n"
        f'1. "ranked_ids" — array of up to 10 cluster IDs from the list below, '
        f"ordered from most front-page-worthy to least. Only include IDs from the list.\n"
        f'2. "duplicate_flags" — array of [id_a, id_b] pairs where two stories '
        f"appear to be about the same event. Empty array if none.\n"
        f'3. "incremental_flags" — array of cluster IDs that are incremental '
        f"updates on a prior story (not genuinely new). Empty array if none.\n\n"
        f"CANDIDATES:\n{candidate_block}\n\n"
        f"Return JSON only. No markdown fences.\n"
        f'{{"ranked_ids": ["...", ...], "duplicate_flags": [["...", "..."], ...], '
        f'"incremental_flags": ["...", ...]}}'
    )

    _triage_call_count += 1
    result = generate_json(
        prompt,
        system_instruction=_TRIAGE_SYSTEM_INSTRUCTION,
        count_call=False,  # Don't count against summarization budget
    )

    if not result:
        return None

    return {
        "ranked_ids": result.get("ranked_ids", []),
        "duplicate_flags": result.get("duplicate_flags", []),
        "incremental_flags": result.get("incremental_flags", []),
    }
