"""
ig_caption.py — Claude Sonnet 4.6 caption generator for Instagram posts.

Reuses pipeline/summarizer/claude_client.py (already in use for cluster
summaries + daily briefs). System prompt enforces project voice rules:
show-don't-tell, arrive-late-leave-early, no em dashes, niche-first hashtag
stack, 60–120 words, single CTA. Post-process regex checks bounce captions
that violate the rules; up to 3 retries before marking the row
state='caption_review' for manual edit.

Usage:
    python -m pipeline.social.ig_caption                       # all draftcaptionable
    python -m pipeline.social.ig_caption --post-id <uuid>      # one row

Environment:
    ANTHROPIC_API_KEY   required for Sonnet calls
    SUPABASE_URL / KEY  existing pipeline vars
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

try:
    from summarizer.claude_client import generate_json, is_available as claude_available
except ImportError:
    generate_json = None  # type: ignore
    claude_available = lambda: False  # noqa: E731

# ---------------------------------------------------------------------------
# Voice rules (mirrors CLAUDE.md project rules)
# ---------------------------------------------------------------------------

BANNED_PHRASES = [
    "notable", "notably",
    "significant", "significantly",
    "interesting", "interestingly",
    "it should be noted",
    "it is worth noting",
    "crucial", "crucially",
    "in conclusion",
    "to sum up",
    "in summary",
    "in essence",
    "needless to say",
]

EM_DASH_RE = re.compile(r"[—–]")
HASHTAG_RE = re.compile(r"#[A-Za-z0-9_]{2,}")
URL_RE = re.compile(r"https?://\S+|void-news\.pages\.dev")

IG_MAX_CAPTION_CHARS = 2200
WORD_MIN = 50
WORD_MAX = 130

# Approved hashtag stack. The caption LLM picks 6–8 from here.
HASHTAG_POOL = {
    "niche": [
        "medialiteracy", "newsmediabias", "algorithmaccountability",
        "datajournalism", "computationaljournalism", "explanatoryjournalism",
        "pressfreedom", "factchecking",
    ],
    "domain": [
        "journalism", "worldnews", "independentmedia",
        "publicinterest", "newsanalysis",
    ],
    "owned": [
        "voidnews", "seethroughthevoid",
    ],
}

SYSTEM_PROMPT = """You write Instagram captions for void --news.

Voice rules — enforced, not aspirational:

1. SHOW, DON'T TELL. Never use the words notable, notably, significant, significantly, interesting, interestingly, crucial, crucially, "it should be noted", "it is worth noting", "in conclusion", "in summary", "needless to say". Use concrete numbers, named outlets, named people, dates, places, verbs.

2. ARRIVE LATE, LEAVE EARLY. Open in the middle of the action. End before the conclusion is spelled out. The reader completes the thought.

3. NO EM DASHES (—) OR EN DASHES (–). Hyphens in compound words like "fact-check" are fine. Use two short sentences, a comma, a semicolon, a colon, or parentheses instead.

4. LENGTH: 50 to 130 words. One CTA at the end if useful. URL goes at the very end, no preamble.

5. HASHTAGS: pick 6 to 8 from the approved stack provided in the user message. Place them at the very end on a new line. No hashtags inside the body.

6. MANIFESTO: void --news is "Same stories. Same order. For everyone." Every caption ladders up to it. Quote the line verbatim at most once per week — usually paraphrase.

7. NEVER praise the product. Never say "we built something amazing." Let the evidence carry the weight.

Output STRICT JSON with this shape:
{
  "caption": "the caption body, no hashtags inside",
  "hashtags": ["medialiteracy", "newsmediabias", ...]
}

The body must end with the URL "void-news.pages.dev" unless the post type indicates otherwise."""


def _build_user_prompt(row: dict[str, Any]) -> str:
    pillar = row.get("pillar", "receipt")
    launch_slot = row.get("launch_slot")
    specs = row.get("slide_specs") or []
    spec_summary = json.dumps(specs[:4], indent=2)[:2000]

    if launch_slot == 1:
        intent = (
            "This is the launch opener. The caption should make a one-sentence promise: "
            "we're posting twice a week from here on, every post is evidence for the manifesto. "
            "Open with the manifesto line verbatim, follow with one sentence on what the algorithm "
            "did to news, close with the URL."
        )
    elif pillar == "receipt":
        intent = (
            "Receipt post: show the divergence between outlets without editorializing. "
            "Lead with the most striking score or quote. Name two outlets. Land on the "
            "per-article-not-per-outlet idea without using that exact phrase verbatim."
        )
    elif pillar == "method":
        intent = (
            "Methodology post: explain one axis or one design choice (like the unscored gate). "
            "Compare to AllSides/NewsGuard implicitly. Lead with 'AllSides won't show you the math' "
            "or similar concrete contrast. End on a first-principle, not a feature."
        )
    elif pillar == "history":
        intent = (
            "void --history post: drop the reader inside one fact about a historical event. "
            "Don't announce what the event is. Let the fact carry it. End with the void --history URL."
        )
    elif pillar == "brief":
        intent = (
            "Brief pull-quote post: the slide IS the quote. Caption is the context, "
            "no more than three sentences. Attribute to the daily brief. URL last."
        )
    elif pillar == "bts":
        intent = (
            "Pipeline behind-the-scenes post: one or two surprising numbers from the day's run. "
            "Build-in-public energy. No emojis. No corporate cheer."
        )
    elif pillar == "heatmap":
        intent = (
            "Heatmap post: name the topic and the two countries at the extreme ends. "
            "The data does the work. URL last."
        )
    else:
        intent = "Standard void --news post. Follow the voice rules."

    pool = (
        "niche: " + ", ".join(HASHTAG_POOL["niche"]) + "\n"
        "domain: " + ", ".join(HASHTAG_POOL["domain"]) + "\n"
        "owned: " + ", ".join(HASHTAG_POOL["owned"])
    )

    return f"""POST PILLAR: {pillar}
POST INTENT: {intent}

SLIDE CONTENT (first 4 slides, JSON):
{spec_summary}

APPROVED HASHTAG POOL (lead with niche; include at least 1 owned):
{pool}

Write the caption now. Return STRICT JSON only."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(caption: str, hashtags: list[str]) -> tuple[bool, str]:
    if not caption or not isinstance(caption, str):
        return False, "empty caption"
    if EM_DASH_RE.search(caption):
        return False, "contains em/en dash"

    lower = caption.lower()
    for banned in BANNED_PHRASES:
        if banned in lower:
            return False, f"banned phrase: {banned}"

    word_count = len(re.findall(r"\b\w+\b", caption))
    if word_count < WORD_MIN:
        return False, f"too short ({word_count} words, min {WORD_MIN})"
    if word_count > WORD_MAX:
        return False, f"too long ({word_count} words, max {WORD_MAX})"

    if HASHTAG_RE.search(caption):
        return False, "hashtags inside caption body (must be on separate line)"

    if not isinstance(hashtags, list) or len(hashtags) < 6 or len(hashtags) > 8:
        return False, f"wrong hashtag count ({len(hashtags) if isinstance(hashtags, list) else 'n/a'}; need 6-8)"

    all_allowed = set(HASHTAG_POOL["niche"] + HASHTAG_POOL["domain"] + HASHTAG_POOL["owned"])
    cleaned = [h.lstrip("#").strip() for h in hashtags]
    for h in cleaned:
        if h not in all_allowed:
            return False, f"hashtag not in approved stack: {h}"

    total_len = len(caption) + sum(len(h) + 2 for h in cleaned)
    if total_len > IG_MAX_CAPTION_CHARS:
        return False, f"total length exceeds IG limit ({total_len} > {IG_MAX_CAPTION_CHARS})"

    return True, "ok"


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def caption_for_post(row: dict[str, Any], max_retries: int = 3) -> tuple[str | None, list[str] | None, str | None]:
    """Returns (caption, hashtags, error). Error is None on success."""
    if generate_json is None or not claude_available():
        return None, None, "Claude not available (missing ANTHROPIC_API_KEY?)"

    prompt = _build_user_prompt(row)

    last_err = "unknown"
    for attempt in range(max_retries):
        result = generate_json(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
            max_retries=0,  # we handle retries ourselves so we can adjust prompt
            count_call=True,
            max_output_tokens=1024,
        )
        if not result:
            last_err = "Claude returned no JSON"
            continue

        caption_raw = (result.get("caption") or "").strip()
        hashtags_raw = result.get("hashtags") or []
        if isinstance(hashtags_raw, str):
            hashtags_raw = [h.strip() for h in re.split(r"[,\s]+", hashtags_raw) if h.strip()]
        hashtags = [h.lstrip("#").strip() for h in hashtags_raw if isinstance(h, str)]

        ok, msg = _validate(caption_raw, hashtags)
        if ok:
            return caption_raw, hashtags, None

        last_err = msg
        # Tighten prompt for next try
        prompt = (
            _build_user_prompt(row)
            + f"\n\nPREVIOUS ATTEMPT FAILED: {msg}. Fix it. Return STRICT JSON only."
        )

    return None, None, last_err


def _set_state(post_id: str, state: str, error: str | None = None) -> None:
    payload: dict[str, Any] = {"state": state}
    if error is not None:
        payload["error"] = error[:1000]
    try:
        supabase.table("ig_posts").update(payload).eq("id", post_id).execute()
    except Exception as e:
        print(f"  [error] state update {post_id} → {state}: {e}")


def _write_caption(post_id: str, caption: str, hashtags: list[str]) -> None:
    try:
        supabase.table("ig_posts").update({
            "caption": caption,
            "hashtags": hashtags,
        }).eq("id", post_id).execute()
    except Exception as e:
        print(f"  [error] caption write {post_id}: {e}")


def _fetch_targets(post_id: str | None) -> list[dict]:
    q = supabase.table("ig_posts").select("id, slide_specs, pillar, launch_slot, caption, state")
    if post_id:
        q = q.eq("id", post_id)
    else:
        # Caption rows that have rendered images but no caption yet.
        q = q.in_("state", ["draft"]).is_("caption", "null")
    return (q.order("scheduled_for", desc=False).limit(50).execute().data) or []


def caption_all(post_id: str | None = None) -> int:
    rows = _fetch_targets(post_id)
    if not rows:
        print("  [caption] nothing to do")
        return 0

    done = 0
    for row in rows:
        pid = row["id"]
        _set_state(pid, "captioning")
        cap, tags, err = caption_for_post(row)
        if cap and tags is not None:
            _write_caption(pid, cap, tags)
            # leave state at 'draft' so the admin picks it up; the captioning
            # state is a transient lock so concurrent runs don't collide
            _set_state(pid, "draft")
            print(f"  [caption] {pid} ok ({len(cap)} chars, {len(tags)} tags)")
            done += 1
        else:
            _set_state(pid, "caption_review", err or "validation failed")
            print(f"  [caption] {pid} → caption_review: {err}")
    return done


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", default=None, help="caption a single post")
    args = parser.parse_args()
    n = caption_all(post_id=args.post_id)
    print(f"  [caption] done. {n} caption(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
