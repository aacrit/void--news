"""
Gemini API client for the void --news pipeline.

Uses the google-genai SDK (not the deprecated google-generativeai).
Aggressive free-tier protection:
    - Rate limited to ~14 RPM (4.2s between calls)
    - Hard cap of 25 calls per pipeline run (summarization budget)
    - Separate 5-call budget for editorial triage
    - 1 retry max on transient failures

At 2 pipeline runs/day: max 50 RPD (summarization) + 10 RPD (triage) = 3.3% of the 1500 RPD free limit.

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
    count_call: bool = True,
    max_output_tokens: int = 8192,
) -> dict | None:
    """
    Send a prompt to Gemini Flash and parse the JSON response.

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
    global _call_count

    client = _get_client()
    if client is None:
        return None

    # Hard cap: stop calling to protect free tier (skipped for out-of-budget callers)
    if count_call and _call_count >= _MAX_CALLS_PER_RUN:
        return None

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        max_output_tokens=max_output_tokens,
        system_instruction=system_instruction,  # None = no system turn (backward-compatible)
    )

    for attempt in range(max_retries + 1):
        try:
            _rate_limit()
            if count_call:
                _call_count += 1
            response = client.models.generate_content(
                model=_MODEL,
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
            if "429" in error_str or "quota" in error_str or "rate" in error_str:
                print(f"  [warn] Gemini rate limit (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(15)
                    continue
            else:
                print(f"  [warn] Gemini API error (attempt {attempt + 1}): {e}")
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
