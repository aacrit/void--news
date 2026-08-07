"""Canonical Python port of frontend/app/lib/summaryHygiene.ts.

Single source of truth for raw-excerpt detection across the pipeline. The
frontend's `summaryHygiene.ts` is the last line of defence on the client: if a
displayed top-50 card's summary still looks like a raw scraped excerpt (CMS
artifacts, a photo/byline credit, a trailing "- outlet.com" suffix, or
run-together words from a bad extraction), the client BLANKS it and the card
falls back to its neutral "N sources reporting" pending line.

The problem that made that guard fire on production: a card can carry a
`summary_tier` stamped by an earlier pipeline step (7b / 8d) AND still hold a
raw scraped excerpt as its `summary`, so the summary floor's "no tier => needs a
summary" test skipped it, and the frontend then blanked it → an empty card.

This module lets the pipeline detect and repair exactly what the frontend would
blank, so a raw-excerpt summary never survives the floor and no displayed card
ever ships blank.

`is_raw_excerpt` / `clean_feed_summary` mirror the TS `isRawExcerpt` /
`cleanFeedSummary` 1:1 (same patterns, same camel-boundary and long-token
heuristics). Keep the two files in lock-step when either changes.

No heavy dependencies — safe to import anywhere in the pipeline.
"""

from __future__ import annotations

import re

# Obvious CMS / newsroom-scaffolding + syndication artifacts that never belong
# in an editorial summary. Kept conservative to avoid false positives on real
# prose. Ported 1:1 from summaryHygiene.ts RAW_EXCERPT_PATTERNS.
_RAW_EXCERPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bWhy it matters:", re.I),
    re.compile(r"\bthe big picture:", re.I),
    re.compile(r"\bgo deeper:", re.I),
    re.compile(r"\bread more:", re.I),
    re.compile(r"\bkeep reading:", re.I),
    re.compile(r"\bsign up for", re.I),
    re.compile(r"\bsubscribe to", re.I),
    re.compile(r"\badvertisement\b", re.I),
    re.compile(r"\bphoto(?:graph)?:\s", re.I),
    re.compile(r"\bimage caption\b", re.I),
    re.compile(r"\bgetty images\b", re.I),
    # Photo/byline credit like "(John Smith/AFP)" or "(AP Photo/...)".
    re.compile(r"\([^)]*/\s*(?:AFP|AP|Reuters|Getty|EPA|Bloomberg|Anadolu|Xinhua|AAP)\b", re.I),
    # Trailing outlet-domain suffix like " - reuters.com" / " - bbc.co.uk".
    re.compile(r"[\s\-–—]+[a-z0-9-]+\.(?:com|org|net|gov|co\.[a-z]{2})\s*$", re.I),
]


def is_raw_excerpt(summary: str) -> bool:
    """True when a non-empty summary looks like a raw scraped excerpt, not prose.

    Deterministic Python port of summaryHygiene.ts isRawExcerpt(). Empty input
    returns False (nothing to flag — that is the coverage/null case, handled
    separately).
    """
    s = (summary or "").strip()
    if not s:
        return False

    for rx in _RAW_EXCERPT_PATTERNS:
        if rx.search(s):
            return True

    # Run-together words from a broken extraction ("reportingThe minister said").
    # Require several lowercase->uppercase transitions to avoid flagging the rare
    # legitimate camel token (iPhone, eBay, McDonald's).
    camel_boundaries = len(re.findall(r"[a-z][A-Z]", s))
    if camel_boundaries >= 3:
        return True

    # A single absurdly long token is almost always concatenated words / a URL
    # slug that survived extraction.
    if re.search(r"\S{40,}", s):
        return True

    return False


def clean_feed_summary(summary: str, _title: str | None = None) -> str:
    """Return a display-safe summary.

    Empty or raw-excerpt input yields "" (so the client renders its neutral
    "N sources reporting" pending line). Clean prose passes through untouched.
    Mirrors summaryHygiene.ts cleanFeedSummary().
    """
    s = (summary or "").strip()
    if not s:
        return ""
    if is_raw_excerpt(s):
        return ""
    return summary
