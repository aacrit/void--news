"""Pure parsing and date helpers for void --weekly. No DB, no LLM, no network.

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
