"""Deterministic ($0) headline + summary hygiene for void --news.

The daily feed ships 50 clusters. Only ~20 of them get an LLM-written headline
and summary; the rest (the "null-tier tail") fall back to the raw
clustering-generated title (the best member headline) and the raw longest
member-article summary. Those raw strings leak:

  * source-name suffixes ("... - Euractiv", "... - Focus Taiwan", Cyrillic
    outlet names),
  * CMS / RSS scaffolding ("appeared first on X", "Continue reading",
    "Submitted by <name> on <date>", "pic.twitter.com/..."),
  * tabloid / banned-adjective clickbait ("Devastating:", "Unbothered King:",
    scare-quote roast verbs),
  * mid-word "..." truncation.

This module cleans all of that with pure regex — no LLM, no network. It is
applied at cluster-title/-summary generation (future runs) and by the
offline backfill script (current feed), so hygiene ships regardless of LLM
availability.

Reviewed 2026-07-01 (top-50 multi-perspective review, waves CQ-1/CQ-2/CQ-3).
"""

from __future__ import annotations

import re
import json
import os
from functools import lru_cache


# ---------------------------------------------------------------------------
# Publisher-name list (for suffix stripping). Loaded once from sources.json.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _publisher_names() -> frozenset[str]:
    """Lowercased outlet names from data/sources.json, plus common variants."""
    names: set[str] = set()
    # data/sources.json lives two dirs up from pipeline/utils/
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "..", "data", "sources.json"),
        os.path.join(os.getcwd(), "data", "sources.json"),
    ]
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            rows = data if isinstance(data, list) else data.get("sources", [])
            for r in rows:
                nm = (r.get("name") or "").strip().lower()
                if nm:
                    names.add(nm)
                    # "The Guardian" -> also match "guardian"
                    if nm.startswith("the "):
                        names.add(nm[4:])
            break
        except Exception:
            continue
    # Common outlets / aggregator tags that leak as suffixes but may not be a
    # primary source-list name.
    names.update({
        "huffpost", "euractiv", "i24news", "focus taiwan", "telegraph india",
        "new haven register", "mediaite", "the daily beast", "rt", "axios",
        "politico", "the hill", "newsweek", "salon", "vox", "the daily wire",
        "breitbart", "the national pulse", "western journal", "raw story",
        "the namibian", "asia times", "egypt independent", "scmp",
    })
    return frozenset(names)


# ---------------------------------------------------------------------------
# Headline normalization
# ---------------------------------------------------------------------------

# Editorial / wire prefixes that should never lead a neutral headline.
_EDITORIAL_PREFIX_RE = re.compile(
    r"^\s*(?:"
    r"INSIGHT|ANALYSIS|OPINION|EXCLUSIVE|EXCLUSIVELY|COMMENT|EDITORIAL|"
    r"WATCH|LIVE|UPDATE|BREAKING|DEVELOPING|SPECIAL REPORT|FACT CHECK|"
    r"EXPLAINER|PROFILE|FEATURE|RECAP|REVEALED"
    r")\s*[:,\-–—]\s*",
    re.IGNORECASE,
)

# Banned-adjective / tabloid lead words that mark clickbait framing when they
# open a headline as an emphatic label ("Devastating: ...", "Shocking: ...").
_CLICKBAIT_LEAD_LABEL_RE = re.compile(
    r"^\s*(?:"
    r"Devastating|Shocking|Stunning|Explosive|Bombshell|Horrifying|Tragic|"
    r"Outrageous|Unbelievable|Jaw-dropping|Heartbreaking|Chaos|Chaotic"
    r")\s*[:!\-–—]\s*",
    re.IGNORECASE,
)

# Nickname/epithet label leads that read as tabloid framing:
# "Unbothered King: Justice Clarence Thomas ..." -> keep the substantive clause.
_EPITHET_LEAD_RE = re.compile(
    r"^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\s*:\s*(?=[A-Z])"
)

_DELIMS = ("-", "–", "—", "|")


def _looks_like_source_suffix(seg: str) -> bool:
    """True if a trailing segment (after a delimiter) is a source attribution,
    a date stamp, or a non-Latin fragment rather than real headline content."""
    seg = seg.strip()
    if not seg:
        return False
    low = seg.lower()
    # Known publisher / aggregator name
    if low in _publisher_names():
        return True
    # Any publisher name as a whole-segment match (e.g. "South African News
    # Briefs - June 30, 2026" -> the "June 30, 2026" tail is a date stamp)
    if re.fullmatch(r"[A-Z][a-z]+ \d{1,2},? \d{4}", seg):
        return True
    # Predominantly non-Latin (Cyrillic, CJK, Arabic, etc.) short fragment
    non_latin = sum(1 for ch in seg if ord(ch) > 0x24F and not ch.isspace())
    letters = sum(1 for ch in seg if ch.isalpha())
    if letters and non_latin / letters > 0.5:
        return True
    # Short Title-Case fragment with no sentence punctuation and <= 5 words:
    # very likely an outlet name that isn't in sources.json.
    words = seg.split()
    if 1 <= len(words) <= 5 and not re.search(r"[.?!]", seg):
        capish = sum(1 for w in words if w[:1].isupper())
        if capish >= max(1, len(words) - 1):
            return True
    return False


def normalize_headline(title: str) -> str:
    """Strip source-name suffixes, editorial prefixes, and tabloid label leads
    from a cluster headline. Deterministic, idempotent, $0.

    Safe to apply to LLM-written headlines (they have no suffixes/prefixes, so
    it is a no-op) and to raw member headlines (the common case for null-tier
    clusters)."""
    if not title:
        return title or ""
    t = title.strip()

    # Editorial / tabloid label leads.
    for _ in range(2):
        new = _EDITORIAL_PREFIX_RE.sub("", t)
        new = _CLICKBAIT_LEAD_LABEL_RE.sub("", new)
        new = _EPITHET_LEAD_RE.sub("", new)
        if new == t:
            break
        t = new.strip()

    # Trailing source / date / non-Latin suffixes, delimiter by delimiter.
    for _ in range(3):
        stripped = False
        for d in _DELIMS:
            idx = t.rfind(f" {d} ")
            if idx == -1:
                continue
            head, tail = t[:idx], t[idx + 3:]
            if len(head) >= 20 and _looks_like_source_suffix(tail):
                t = head.strip()
                stripped = True
        if not stripped:
            break

    return t.strip(" \t\r\n-–—|,").strip()


# ---------------------------------------------------------------------------
# Summary sanitization
# ---------------------------------------------------------------------------

# CMS / RSS scaffolding, in application order. Each removes boilerplate that a
# scraper left in article body text.
_BOILERPLATE_RES = [
    # "The post/article <...> appeared first on <Outlet>." (with or without
    # spaces around the join — scrapers often drop the space)
    re.compile(r"\s*The (?:post|article)\b.*?appeared first on.*?$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\s*(?:This (?:post|article)|It)?\s*(?:first )?appeared (?:first )?on\s*[A-Z][^.]*\.?\s*$", re.IGNORECASE),
    # "Read more at <Outlet>." / "Continue reading ..." / "Read the full story"
    re.compile(r"\s*Read (?:more|the full (?:story|article))\b.*$", re.IGNORECASE | re.DOTALL),
    re.compile(r"\s*Continue reading\b.*$", re.IGNORECASE | re.DOTALL),
    # Drupal/CMS byline scaffolding: "Submitted by <Name> on <Day, MM/DD/YYYY
    # - HH:MM>". The real article body follows the timestamp, so bound the
    # match to the time and do NOT run to end-of-string.
    re.compile(r"\s*Submitted by\b.*?\d{1,2}:\d{2}\s*", re.IGNORECASE),
    re.compile(r"\s*Submitted by\b.*?\d{1,2},?\s*\d{4}\s*", re.IGNORECASE),
    # Twitter/X embeds and pic links
    re.compile(r"\s*pic\.twitter\.com/\S+", re.IGNORECASE),
    re.compile(r"\s*https?://\S+", re.IGNORECASE),
    # Social share tails: "... news magazineonLinkedIn", "onFacebook", "onX"
    re.compile(r"\s*on(?:LinkedIn|Facebook|Twitter|X|Instagram|Telegram|WhatsApp)\b.*$"),
    # Trailing "(Reuters)" / "(AP)" wire tags at the very end
    re.compile(r"\s*\((?:Reuters|AP|AFP|UPI|Bloomberg|Xinhua|Reporting by[^)]*)\)\s*$", re.IGNORECASE),
]

# BREAKING rendered in Unicode math-alphanumeric styling and other zero-width /
# control junk that scrapers pull from styled source headlines.
_UNICODE_JUNK_RE = re.compile(r"[​-‏‪-‮﻿]")


def _fix_missing_spaces(text: str) -> str:
    """Insert a space at obvious lowercase|Uppercase and word|date joins that
    scrapers produce when stripping HTML ('lostSubmitted', 'magazineonLinkedIn',
    'firstThe')."""
    # letter followed by capital that starts a new word run
    text = re.sub(r"(?<=[a-z])(?=[A-Z][a-z])", " ", text)
    return text


def _trim_to_sentence(text: str, max_chars: int = 600) -> str:
    """Cut trailing mid-word '...' truncation and end on a complete sentence."""
    text = text.strip()
    # Kill a trailing ellipsis/truncation marker and any partial final word.
    text = re.sub(r"\s*(?:\.\.\.|…|…)\s*$", "", text)
    if len(text) > max_chars:
        text = text[:max_chars]
    # Prefer ending on the last sentence terminator if we have enough body.
    m = list(re.finditer(r"[.!?][\"')\]]?(?:\s|$)", text))
    if m:
        end = m[-1].end()
        if end >= min(80, len(text) // 2):
            text = text[:end]
    else:
        # No sentence end at all -> we likely truncated mid-word; drop the
        # dangling partial token.
        text = re.sub(r"\s+\S{1,20}$", "", text) if " " in text else text
    return text.strip()


def sanitize_summary(text: str) -> str:
    """Strip CMS/RSS boilerplate, embeds, byline scaffolding, and mid-word
    truncation from a raw article summary. Deterministic, $0.

    Returns cleaned text; may return "" if nothing substantive remains."""
    if not text:
        return ""
    t = _UNICODE_JUNK_RE.sub("", text).strip()
    t = _fix_missing_spaces(t)
    for rx in _BOILERPLATE_RES:
        t = rx.sub("", t).strip()
    t = re.sub(r"\s{2,}", " ", t)
    t = _trim_to_sentence(t)
    return t.strip()
