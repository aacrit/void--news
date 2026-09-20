"""The pure core of void --weekly: parsing, week math, row assembly.

No DB, no LLM, no network, and no third-party import.

WHY THIS MODULE EXISTS
----------------------
`weekly_digest_generator` imports `utils.supabase_client`, which raises
`EnvironmentError` at import time unless `VOID_SQLITE_PATH` or `SUPABASE_*` is
set. So the generator module cannot be imported in CI *at all*, and every pure
function inside it was untestable. That import wall, not neglect, is why the
weekly had zero tests while the `week_offset` sign bug served Issue #23 for
three weeks.

Everything here imports `re` and `datetime` and nothing else, so
`tests/test_weekly.py` can exercise it with no key, no database and no network.

THE HEADLINE GUARD
------------------
`_parse_essay` took the first non-empty LINE as the headline with no sanity
check. `COVER_SYSTEM` does explicitly demand "Line 1: the headline only", but a
model is free to ignore an instruction, and on Issue #26 it did: the second
cover feature opened straight into prose, so its entire 698-character lede
became `cover_text[1].headline` and the essay LOST that paragraph. The page
then set it as a display-size red <h2> and as coverline #1 on the cover.

`looks_like_headline` is the fix. A line that could be a paragraph is not
accepted as a title, and the parser falls back to the single-block branch that
already existed: `headline = ""`, the prose stays whole in the body. Every
consumer already guards `headline?.trim()`, so no new failure mode.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

# A headline is short and is one utterance. These are deliberately loose: the
# job is to reject a PARAGRAPH, not to police house style. The live defect was
# 698 characters and 110 words, an order of magnitude past either bound.
MAX_HEADLINE_CHARS = 120
MAX_HEADLINE_WORDS = 18

# A sentence boundary with more text after it. A trailing period is fine (a
# headline may end in one); an INTERIOR boundary means the line is prose.
_INTERIOR_SENTENCE_END = re.compile(r"[.!?][\"')\]]?\s+\S")


def looks_like_headline(line: str) -> bool:
    """True when a line could be a title rather than a paragraph."""
    s = (line or "").strip()
    if not s:
        return False
    if len(s) > MAX_HEADLINE_CHARS:
        return False
    if len(s.split()) > MAX_HEADLINE_WORDS:
        return False
    if _INTERIOR_SENTENCE_END.search(s):
        return False
    return True


def clean_headline(line):
    """Strip an optional 'HEADLINE:'/'TITLE:' label and Markdown chars off a line.

    The label is only stripped when followed by a colon, so a real headline that
    happens to start with the word "Headline" (e.g. "Headline inflation") is kept.
    """
    line = re.sub(r"^\s*#{0,3}\s*(?:HEADLINE|TITLE)\s*:\s*", "", line, flags=re.IGNORECASE)
    return line.strip().strip("*_#").strip()


def parse_essay(raw, want_numbers=False):
    """Parse a plain-text essay into {headline, text[, numbers]} or None.

    Layout: first non-empty line is the headline, the rest is the body. If
    want_numbers, a trailing line "NUMBERS" splits off a block of
    "value | context" lines parsed into [{"stat", "context"}].

    A first line that does not pass `looks_like_headline` is treated as body:
    the essay keeps its lede and the caller supplies a headline from the
    cluster title instead of printing a paragraph at display size.
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    numbers = []
    if want_numbers:
        parts = re.split(r"\n\s*#{0,3}\s*NUMBERS\s*:?\s*\n", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            text, num_block = parts[0].strip(), parts[1]
            for ln in num_block.splitlines():
                ln = ln.strip().lstrip("-*•").strip()
                if "|" not in ln:
                    continue
                value, _, context = ln.partition("|")
                value = value.strip()
                if value:
                    numbers.append({"stat": value, "context": context.strip()})

    lines = text.splitlines()
    idx = next((k for k, ln in enumerate(lines) if ln.strip()), None)
    if idx is None:
        return None
    headline = clean_headline(lines[idx])
    body = "\n".join(lines[idx + 1:]).strip()
    if not body:
        # Single-block output: no separable headline; keep it all as text.
        body, headline = headline, ""
    elif not looks_like_headline(headline):
        # Line 1 is prose. Keep the essay whole rather than eating its lede.
        body = (headline + "\n" + body).strip()
        headline = ""
    result = {"headline": headline, "text": body}
    if want_numbers:
        result["numbers"] = numbers
    return result


def parse_recap(raw):
    """Parse a plain-text recap batch into {stories: [{headline, summary}]}.

    Stories are separated by a line that is just "###" (optionally "### STORY").
    Within each block, the first non-empty line is the headline, the rest is the
    summary. Returns None if nothing parseable.
    """
    if not raw or not raw.strip():
        return None
    blocks = re.split(r"\n\s*#{2,}(?:\s*STORY\s*\d*)?\s*\n", "\n" + raw.strip())
    stories = []
    for block in blocks:
        lines = block.strip().splitlines()
        idx = next((k for k, ln in enumerate(lines) if ln.strip()), None)
        if idx is None:
            continue
        headline = clean_headline(lines[idx])
        summary = " ".join(ln.strip() for ln in lines[idx + 1:] if ln.strip()).strip()
        if not summary:
            summary, headline = headline, ""
        elif not looks_like_headline(headline):
            summary = (headline + " " + summary).strip()
            headline = ""
        if headline or summary:
            stories.append({"headline": headline, "summary": summary})
    return {"stories": stories} if stories else None


# ---------------------------------------------------------------------------
# Week window
# ---------------------------------------------------------------------------

# Issue #1 is the week beginning Sunday 2026-03-22.
ISSUE_EPOCH = datetime(2026, 3, 22, tzinfo=timezone.utc)


def weekly_window(now, week_offset=0):
    """-> (week_start, week_end, issue_number) for a Monday-to-Sunday week.

    `week_offset` counts weeks BACK from the most recently COMPLETED week: 0 is
    the week that just ended, 1 the week before it, and -1 the current
    in-progress week (partial data, for a mid-week refresh).

    `now` is injected rather than read from the clock precisely because this
    sign was inverted until 2026-09-19 and could only be caught in production:
    offset 0 resolved to the week CONTAINING today, so the Monday 12:00 UTC
    cron generated the week that had just STARTED. Issue #23 (week of
    2026-08-24, generated 2026-08-24 12:48) is the last one that shipped so.
    """
    week_end = now - timedelta(days=now.weekday() + 1 + (week_offset * 7))
    week_start = week_end - timedelta(days=6)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=0)
    issue_number = max(1, int((week_start - ISSUE_EPOCH).days / 7) + 1)
    return week_start, week_end, issue_number


# ---------------------------------------------------------------------------
# Row assembly — pure, so the persistence contract is testable without a key
#
# This was 60 lines of dict literal inline in generate_weekly_digest, which is
# why nothing ever noticed that `tech` and `sports` were generated every week
# and then dropped: the row had a comment where the write should have been.
# ---------------------------------------------------------------------------

# Front-of-book order. A magazine's running order is editorial data, so it
# lives in a list rather than being implied by the order of column
# declarations in whatever renders it.
DEPARTMENTS = (
    ("tech", "Technology"),
    ("sports", "Sports & Culture"),
)


def _department_item(slug, label, essay):
    """One front-of-book department, or None when the week had no such story."""
    if not essay or not isinstance(essay, dict):
        return None
    text = (essay.get("text") or "").strip()
    if not text:
        return None
    return {
        "slug": slug,
        "label": label,
        "headline": (essay.get("headline") or "").strip(),
        "text": text,
        "cluster_id": essay.get("cluster_id"),
        "image_url": essay.get("image_url"),
        "image_attribution": essay.get("image_attribution"),
        "image_caption": essay.get("image_caption"),
    }


def _opinion_items(opinions, issue_number):
    """The flat opinion array, with the dialectic made explicit.

    `_generate_opinions` writes a deliberate structure: the first two essays
    argue the SAME cover story from left and right, each told the other exists.
    That structure survived only as an array index, and the three lean buckets
    destroyed it outright — center-left, center and center-right all land in
    `opinion_center`, and the page then read `[0]` of each bucket and dropped
    two essays on the floor. `pair_id` states it instead of implying it: two
    entries sharing one are a head-to-head on a single story.
    """
    items = []
    for i, o in enumerate(opinions or []):
        item = {
            "headline": (o.get("headline") or "").strip(),
            "text": (o.get("text") or "").strip(),
            "lean": o.get("lean", ""),
            "topic": o.get("topic", ""),
            "cluster_id": o.get("cluster_id"),
            "paired": bool(o.get("paired")),
            "position": i,
        }
        if item["paired"]:
            item["pair_id"] = f"w{issue_number}-{o.get('cluster_id') or 'lead'}"
        items.append(item)
    return items


def build_weekly_row(*, edition, week_start, week_end, issue_number, cover_items,
                     opinions, tech, sports, recap_stories, bias_text, bias_data,
                     weekly_opinion, audio, cover_image, total_articles,
                     total_clusters, gemini_calls, elapsed, voice_pair=None):
    """Assemble the weekly_digests row. Pure: dict in, dict out.

    `cover_items` arrives with its images already resolved, so this function
    makes no network call and `tests/test_weekly.py` can assert the whole
    persistence contract against a fixture with no Gemini key.
    """
    audio = audio or {}
    weekly_opinion = weekly_opinion or {}
    audio_url = audio.get("audio_url")
    opinion_list = _opinion_items(opinions, issue_number)

    return {
        "edition": edition,
        "week_start": week_start,
        "week_end": week_end,
        "issue_number": issue_number,
        # Cover
        "cover_headline": cover_items[0].get("headline", "") if cover_items else "",
        "cover_text": json.dumps(cover_items),
        "cover_numbers": json.dumps(cover_items[0].get("numbers", []) if cover_items else []),
        "cover_timelines": json.dumps([
            {"story_index": i, "entries": c.get("timeline", [])}
            for i, c in enumerate(cover_items)
        ]),
        # Front-of-book departments. Generated since the section was written and
        # persisted by nothing until 2026-09-20.
        "departments": json.dumps([
            d for d in (
                _department_item("tech", "Technology", tech),
                _department_item("sports", "Sports & Culture", sports),
            ) if d
        ]),
        # Recap
        "recap_stories": json.dumps(recap_stories or []),
        # Opinions. The flat array is the real shape; the three lean buckets are
        # a lossy partition of it, kept so an already-deployed client and every
        # archived row still render.
        "opinions": json.dumps(opinion_list),
        "opinion_left": json.dumps([o for o in opinion_list if o["lean"] == "left"]),
        "opinion_center": json.dumps([o for o in opinion_list
                                      if o["lean"] in ("center", "center-left", "center-right")]),
        "opinion_right": json.dumps([o for o in opinion_list if o["lean"] == "right"]),
        "opinion_topic": ", ".join(o["topic"] for o in opinion_list[:3]),
        # Bias report
        "bias_report_text": bias_text,
        "bias_report_data": json.dumps(bias_data),
        # Audio (fixed weekly pair: Editor + Correspondent)
        "audio_script": audio.get("script"),
        "audio_url": audio_url,
        "audio_duration_seconds": audio.get("duration_seconds"),
        "audio_file_size": audio.get("file_size"),
        # Weekly editorial (one argued week-in-review column + monologue)
        "opinion_text": weekly_opinion.get("opinion_text"),
        "opinion_headline": weekly_opinion.get("opinion_headline"),
        "opinion_lean": weekly_opinion.get("opinion_lean"),
        "opinion_audio_script": weekly_opinion.get("opinion_audio_script"),
        "opinion_start_seconds": audio.get("opinion_start_seconds"),
        # Broadcast desk voices (news pair drives player host chips + label)
        "audio_voice": (
            f"{voice_pair['host_a']['id']}+{voice_pair['host_b']['id']}"
            if audio_url and voice_pair else None
        ),
        "audio_voice_label": (
            f"{voice_pair['host_a']['name']} & {voice_pair['host_b']['name']}"
            if audio_url and voice_pair else None
        ),
        # Cover image
        "cover_image_url": cover_image["url"] if cover_image else None,
        "cover_image_attribution": cover_image["attribution"] if cover_image else None,
        "cover_image_source": cover_image["source"] if cover_image else None,
        # Stats
        "total_articles": total_articles,
        "total_clusters": total_clusters,
        "generator": "gemini-flash",
        "gemini_calls_used": gemini_calls,
        "generation_duration_seconds": round(elapsed, 1),
    }
