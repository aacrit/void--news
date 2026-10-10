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

# ---------------------------------------------------------------------------
# Tabloid shout-headline neutralization (2026-08-03)
#
# Source headlines like  "Drama With the CDC? WHOA: Fauci's 2021 Diary Entry ...
# Paints the Most EVIL Picture of All"  shipped verbatim on null-tier cards:
# all-caps emphatic shout words + clickbait "?:" teasers straight from the
# source. This pass detects those markers and rewrites to a neutral factual
# headline; if nothing substantive survives it returns "" so the caller falls
# back to another member headline.
#
# Detection is a CURATED shout vocabulary (all-caps, case-sensitive) so genuine
# acronyms (NATO, SCOTUS, COVID, NASA, OPEC) are never touched.
# ---------------------------------------------------------------------------
_SHOUT_WORDS = frozenset({
    "WHOA", "OMG", "WOW", "LOL", "LMAO", "WTF", "OUCH", "YIKES", "BOOM",
    "EVIL", "INSANE", "CRAZY", "SHOCKING", "BRUTAL", "SAVAGE", "EPIC", "VIRAL",
    "MELTDOWN", "SLAMMED", "DESTROYED", "OWNED", "BUSTED", "EXPOSED", "BOMBSHELL",
    "UNREAL", "OUTRAGEOUS", "DISGUSTING", "SHOOK", "SMACKDOWN", "CLAPBACK",
})
_SHOUT_ALT = "|".join(sorted(_SHOUT_WORDS, key=len, reverse=True))
# A shout word used as a label ("WHOA:", "BOOM!").
_SHOUT_LABEL_RE = re.compile(r"\b(?:" + _SHOUT_ALT + r")\b\s*[:!]+\s*")
# A shout word anywhere (case-sensitive all-caps).
_SHOUT_WORD_RE = re.compile(r"\b(" + _SHOUT_ALT + r")\b")
# Clickbait punctuation: "?:", "!?", "!!", "??".
_CLICKBAIT_PUNCT_RE = re.compile(r"\?\s*[:!]|!\s*\?|!{2,}|\?{2,}")


def _is_sensational_headline(title: str) -> bool:
    """True if a headline carries all-caps shout words or clickbait punctuation."""
    if not title:
        return False
    if _CLICKBAIT_PUNCT_RE.search(title):
        return True
    return bool(_SHOUT_WORD_RE.search(title))


def _desensationalize_headline(title: str) -> str:
    """Neutralize a shout/clickbait headline deterministically ($0). Drops a
    leading teaser question and shout labels, title-cases residual shout words,
    and removes clickbait punctuation. May return "" if nothing substantive
    remains (signals the caller to fall back to another headline)."""
    t = title
    # Drop a leading teaser question that precedes a shout label:
    # "Drama With the CDC? WHOA: ..." -> "WHOA: ..."
    if _SHOUT_LABEL_RE.search(t):
        t = re.sub(
            r"^[^?]{0,80}\?\s+(?=\b(?:" + _SHOUT_ALT + r")\b)", "", t
        ).strip()
    # Remove shout labels ("WHOA:", "BOOM!").
    t = _SHOUT_LABEL_RE.sub("", t).strip()
    # Title-case residual mid-sentence shout words ("EVIL" -> "Evil").
    t = _SHOUT_WORD_RE.sub(lambda m: m.group(1).capitalize(), t)
    # Neutralize clickbait punctuation.
    t = re.sub(r"\?\s*[:!]", ". ", t)
    t = re.sub(r"!\s*\?", "?", t)
    t = re.sub(r"!+", "", t)
    t = re.sub(r"\?{2,}", "?", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" :-–—.")
    return t


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

    t = t.strip(" \t\r\n-–—|,").strip()

    # Tabloid shout-headline neutralization (all-caps shout words + clickbait
    # "?:"). A no-op on ordinary/LLM headlines. If nothing substantive survives
    # the rewrite, return "" so the caller falls back to another member title.
    if _is_sensational_headline(t):
        cleaned = _desensationalize_headline(t)
        t = cleaned if len(cleaned) >= 15 else ""

    return t.strip()


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


def _repair_runons(text: str) -> str:
    """Insert missing spaces at glued sentence/word joins that HTML stripping
    produces in raw article excerpts:
        'friendship.The'  -> 'friendship. The'   (period glued to a Cap word)
        'Wednesday.In'    -> 'Wednesday. In'
        'KokSINGAPORE'    -> 'Kok SINGAPORE'     (byline glued to a DATELINE)

    Never splits a dotted abbreviation ('U.S.') — the punct rule only fires
    when the char BEFORE the punctuation is a lowercase letter.
    """
    if not text:
        return text
    # sentence/clause punctuation glued directly to a following capitalized
    # letter, only when preceded by a lowercase letter (protects 'U.S.').
    text = re.sub(r"(?<=[a-z])([.!?,;])(?=[A-Z])", r"\1 ", text)
    # a lowercase run glued directly to an ALL-CAPS run (byline|DATELINE). Two
    # leading lowercase letters required so 'iOS'/'eBay' are left intact.
    text = re.sub(r"(?<=[a-z][a-z])(?=[A-Z]{2,}\b)", " ", text)
    return text


# ---------------------------------------------------------------------------
# Leading byline / dateline / outlet-slug / photo-credit stripping (2026-08-03)
#
# The un-summarized ("null-tier") fallback ships the raw member excerpt. Those
# excerpts routinely open with wire scaffolding that leaks onto the card:
#   dateline    "SINGAPORE, Aug 3 (Reuters) - ..."   / "WASHINGTON — ..."
#   byline      "By Xinghui Kok ..."
#   outlet slug "ALBAWABA - ..."
#   photo credit "... via Getty Images"  / "(Photo by ...)"
# Each strip is applied only when a substantial body (>= 40 chars) survives, so
# a real headline that merely resembles one of these shapes is never gutted.
# ---------------------------------------------------------------------------
# Byline: Title-cased name tokens only (so an all-caps DATELINE that follows a
# byline is NOT swallowed as a name).
_BYLINE_RE = re.compile(
    r"^\s*By\s+[A-Z][a-z][\w.'\-]*(?:\s+(?:and\s+|& )?[A-Z][a-z][\w.'\-]*){0,3}"
    r"\s*[.,;:\-–—]?\s+"
)
# Strong dateline: requires an (agency) parenthetical before the dash.
_DATELINE_STRONG_RE = re.compile(
    r"^\s*[A-Z][A-Z.'\-]+(?:\s+[A-Z][A-Z.'\-]+){0,3}\s*"
    r"(?:,\s*[A-Z][a-z]{2,8}\.?\s+\d{1,2}(?:\s*,\s*\d{4})?\s*)?"
    r"\([^)]{1,40}\)\s*[-–—]\s+"
)
# Date dateline: requires a ", <Month> <Day>" before the dash.
_DATELINE_DATE_RE = re.compile(
    r"^\s*[A-Z][A-Z.'\-]+(?:\s+[A-Z][A-Z.'\-]+){0,3}\s*,\s*"
    r"[A-Z][a-z]{2,8}\.?\s+\d{1,2}(?:\s*,\s*\d{4})?\s*"
    r"(?:\([^)]{1,40}\))?\s*[-–—]\s+"
)
# Em/en-dash dateline: "WASHINGTON — ..." (em/en dash only; a plain hyphen is
# skipped so "US - China trade" is never mistaken for a dateline).
_DATELINE_EMDASH_RE = re.compile(
    r"^\s*[A-Z][A-Z.'\-]{3,}(?:\s+[A-Z][A-Z.'\-]+){0,3}\s*[–—]\s+"
)
# Outlet slug: a single all-caps token (>= 5 chars, so US/USA/AFP are safe) then
# " - ".
_OUTLET_SLUG_RE = re.compile(r"^\s*[A-Z][A-Z0-9.&'\-]{4,20}\s+[-–—]\s+")
# Photo credit fragment ending in an agency tag.
_PHOTO_CREDIT_RE = re.compile(
    r"^\s*(?:"
    r"\(?\s*(?:Photo|Image|Picture|File Photo|Credit|Pictured)\b[^.)\n]{0,120}?\)?[.:]?\s+"
    r"|[^.\n]{0,140}?\b(?:via\s+Getty Images|Getty Images|AP Photo|"
    r"/\s*(?:AFP|AP|Reuters|Getty|EPA|Bloomberg|Xinhua))\b[^.\n]{0,60}?[.\n]\s*"
    r")",
    re.IGNORECASE,
)

_LEADING_CREDIT_RES = [
    _BYLINE_RE, _PHOTO_CREDIT_RE,
    _DATELINE_STRONG_RE, _DATELINE_DATE_RE, _DATELINE_EMDASH_RE,
    _OUTLET_SLUG_RE,
]


def _strip_leading_credits(text: str) -> str:
    """Strip leading bylines, datelines, outlet slugs, and photo credits, keeping
    a strip only when >= 40 chars of body remain."""
    t = text
    for _ in range(3):
        changed = False
        for rx in _LEADING_CREDIT_RES:
            m = rx.match(t)
            if not m:
                continue
            candidate = t[m.end():].lstrip()
            if len(candidate) >= 40:
                t = candidate
                changed = True
        if not changed:
            break
    return t


# Abbreviations whose trailing period is NOT a sentence end. Used so a hard
# truncation like "...post-Oct." or "...the Rev." is not mistaken for a
# complete sentence.
_ABBREV_END = frozenset({
    "oct", "sept", "sep", "nov", "dec", "jan", "feb", "mar", "apr", "jun",
    "jul", "aug", "mr", "mrs", "ms", "dr", "prof", "st", "sen", "rep", "gov",
    "gen", "lt", "col", "sgt", "capt", "jr", "sr", "inc", "ltd", "co", "corp",
    "vs", "etc", "no", "dept", "est", "approx", "gmt", "rev", "hon", "adm",
})


def _ends_in_abbrev(chunk: str) -> bool:
    """True if `chunk` ends on an abbreviation period ('post-Oct.', '9 a.m.',
    'the Rev.') rather than a genuine sentence terminator."""
    m = re.search(r"([A-Za-z](?:[A-Za-z.'\-]*[A-Za-z])?)\.[\"')\]]?\s*$", chunk)
    if not m:
        return False
    word = m.group(1).lower()
    tail = word.rsplit("-", 1)[-1].rsplit(".", 1)[-1]  # "post-oct" -> "oct"
    if tail in _ABBREV_END or word in _ABBREV_END:
        return True
    # dotted abbreviation ("a.m", "u.s") or single-letter initial.
    if re.fullmatch(r"[a-z](?:\.[a-z])*", word):
        return True
    return False


def _trim_to_sentence(text: str, max_chars: int = 600) -> str:
    """End on the last COMPLETE sentence; never cut mid-word or mid-sentence.

    Trailing '...' truncation is removed. Terminators that are actually
    abbreviation periods ('...post-Oct.') are not treated as sentence ends, so
    a hard-truncated fragment is dropped rather than shipped verbatim.
    """
    text = text.strip()
    # Kill a trailing ellipsis/truncation marker and any partial final word.
    text = re.sub(r"\s*(?:\.\.\.|…)\s*$", "", text)
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    ends = list(re.finditer(r"[.!?][\"')\]]?(?=\s|$)", text))
    real_ends = [m.end() for m in ends if not _ends_in_abbrev(text[:m.end()])]
    if real_ends:
        good = [e for e in real_ends if e >= min(80, len(text) // 2)]
        end = max(good) if good else max(real_ends)
        return text[:end].strip()
    # No complete sentence available. Never leave a mid-word cut: if we
    # truncated, drop the dangling final partial token.
    if truncated and " " in text:
        text = re.sub(r"\s+\S+$", "", text)
    return text.strip()


def sanitize_summary(text: str) -> str:
    """Strip CMS/RSS boilerplate, embeds, byline scaffolding, and mid-word
    truncation from a raw article summary. Deterministic, $0.

    Returns cleaned text; may return "" if nothing substantive remains."""
    if not text:
        return ""
    t = _UNICODE_JUNK_RE.sub("", text).strip()
    # Repair glued run-ons BEFORE credit stripping so a byline glued to a
    # dateline ('KokSINGAPORE') separates and both can be recognized.
    t = _repair_runons(t)
    t = _fix_missing_spaces(t)
    # Strip leading byline / dateline / outlet-slug / photo-credit scaffolding.
    t = _strip_leading_credits(t)
    for rx in _BOILERPLATE_RES:
        t = rx.sub("", t).strip()
    t = re.sub(r"\s{2,}", " ", t)
    t = _trim_to_sentence(t)
    return t.strip()
