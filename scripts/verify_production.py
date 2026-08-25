#!/usr/bin/env python3
"""Production output verification gate for Void News.

Fetch-and-assert on what the LIVE site actually SERVES, not on a diff. This is
the check that was missing: correctness was being judged against the code change
instead of against the rendered HTML, so regressions that only appear in the
served output (a doubled Top story badge, sitewide "U. S." corruption) shipped
while every unit gate stayed green.

Usage:
    python verify_production.py <html_file> [--url <origin>]

Exit code 0 => all hard checks pass. Exit code 1 => at least one failed; every
failure prints the offending string with surrounding context so the operator can
act without re-fetching. This script does exactly ZERO network I/O — the wrapper
verify-production.sh curls the URL and hands the file in, so the same logic runs
identically in CI, locally, and against a Pages preview URL.

Parsing is deliberately regex-over-rendered-DOM (stdlib only, no bs4): the story
text is server-rendered into `story-card__summary` / `lead-summary` nodes, so we
verify precisely the bytes a reader receives.
"""

from __future__ import annotations

import argparse
import html as _html
import re
import sys

# ---------------------------------------------------------------------------
# Tunables calibrated against a correct render. A check that would fire on a
# KNOWN-GOOD page is a false gate; each constant here is set so the gate passes
# on a clean fixture and fails only on real corruption.
# ---------------------------------------------------------------------------
MIN_SUMMARY_CHARS = 40
DUP_STEM_OVERLAP = 4          # >= this many shared title stems => same story
WORDMARK_MAX = 3             # header + footer + one mobile-nav variant
DATELINE_MAX = 2             # nav + footer

# ---------------------------------------------------------------------------
# Title stemming — VENDORED from pipeline/clustering/story_cluster.py so the gate
# and the ranker agree on what "same story" means. KEEP _TITLE_STOPWORDS in sync
# with that file (currently story_cluster.py:2420). Porter stem via nltk when
# available (the ranker's primary path); a light suffix stripper otherwise so the
# gate never hard-depends on nltk being installed.
# ---------------------------------------------------------------------------
_TITLE_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "its", "it", "as", "after", "over", "up", "that",
    "this", "not", "no", "says", "said", "new", "amid", "more", "than",
    "about", "how", "what", "why", "who", "when", "where", "which",
    "will", "would", "could", "should", "may", "might", "can",
    "reports", "report", "sources", "according", "also", "first",
    "two", "one", "three", "us", "announces", "while",
})

try:
    from nltk.stem import PorterStemmer  # type: ignore
    _STEMMER = PorterStemmer()

    def _stem(w: str) -> str:
        try:
            return _STEMMER.stem(w)
        except Exception:
            return w
except Exception:  # pragma: no cover - nltk missing
    def _stem(w: str) -> str:
        for suf in ("ations", "ation", "ing", "ies", "edly", "ed", "es", "s"):
            if len(w) > len(suf) + 2 and w.endswith(suf):
                return w[: -len(suf)]
        return w


def _title_word_stems(title: str) -> set[str]:
    """Tokenise + stopword-filter + Porter-stem a title's content words. Mirrors
    clustering/story_cluster.py::_title_word_stems (minus the wire-prefix cleaner,
    which does not change stem OVERLAP for feed headlines)."""
    words = re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", (title or "").lower())
    out: set[str] = set()
    for w in words:
        if w in _TITLE_STOPWORDS or len(w) < 2:
            continue
        out.add(_stem(w))
    return out


# ---------------------------------------------------------------------------
# DOM extraction
# ---------------------------------------------------------------------------
def _decode(s: str) -> str:
    return _html.unescape(s or "").strip()


# Document-order scan of the four feed text classes (both lead + card variants),
# used to pair each headline with its own summary (Page.card_pairs).
_PAIR_SCAN_RE = re.compile(
    r'class="(lead-headline__text|story-card__headline-text|lead-summary|story-card__summary)"[^>]*>([^<]*)<'
)


def _extract(pattern: str, doc: str) -> list[str]:
    return [_decode(m) for m in re.findall(pattern, doc, re.DOTALL)]


class Page:
    def __init__(self, doc: str):
        self.raw = doc
        # Rendered story text nodes (text-only until the closing tag).
        self.card_summaries = _extract(r'class="story-card__summary"[^>]*>([^<]*)<', doc)
        self.lead_summaries = _extract(r'class="lead-summary"[^>]*>([^<]*)<', doc)
        self.card_headlines = _extract(r'class="story-card__headline-text"[^>]*>([^<]*)<', doc)
        # The real lead headline text is in the __text span; the lead-headline
        # element itself opens with an sr-only "Top story." span we must skip.
        self.lead_headlines = _extract(r'class="lead-headline__text"[^>]*>([^<]*)<', doc)
        self.summaries = self.lead_summaries + self.card_summaries
        self.headlines = self.lead_headlines + self.card_headlines

    def card_pairs(self) -> list[tuple[str, str]]:
        """(headline, summary) pairs in document order. Each card renders its
        headline-text span first, then (past the Sigil) its summary span, so we
        walk the four text classes in DOM order and pair every headline with the
        NEXT summary. Pairing by position (not parallel-list index) survives a
        card that is missing one element, so a title never gets matched to the
        WRONG card's summary. Used by the title<->summary consistency check."""
        pairs: list[tuple[str, str]] = []
        pending: str | None = None
        for m in _PAIR_SCAN_RE.finditer(self.raw):
            cls, text = m.group(1), _decode(m.group(2))
            if "headline" in cls:
                pending = text
            elif "summary" in cls and pending is not None:
                pairs.append((pending, text))
                pending = None
        return pairs

    @property
    def header_story_count(self) -> int | None:
        m = re.search(r'(\d+)\s+stories\s+loaded', self.raw)
        return int(m.group(1)) if m else None

    @property
    def rendered_card_count(self) -> int:
        return len(self.headlines)

    def top_story_badges(self) -> int:
        return len(re.findall(r'sr-only">Top story', self.raw))

    def wordmark_count(self) -> int:
        return len(re.findall(r'aria-label="VOID NEWS"', self.raw))

    def dateline_count(self) -> int:
        return len(re.findall(r'class="nav-dateline-line"', self.raw))

    def h1_count(self) -> int:
        return len(re.findall(r'<h1[\s>]', self.raw))

    def footer_wordmark_count(self) -> int:
        m = re.search(r'<footer[^>]*class="[^"]*site-footer[^"]*"[^>]*>(.*?)</footer>',
                      self.raw, re.DOTALL)
        seg = m.group(1) if m else ""
        return len(re.findall(r'aria-label="VOID NEWS"', seg))


# ---------------------------------------------------------------------------
# Checks — each returns list[str] of failure messages (empty => pass)
# ---------------------------------------------------------------------------
def _ctx(text: str, needle: str, pad: int = 45) -> str:
    i = text.find(needle)
    if i < 0:
        return needle
    a = max(0, i - pad)
    b = min(len(text), i + len(needle) + pad)
    return ("..." if a else "") + text[a:b].replace("\n", " ") + ("..." if b < len(text) else "")


# --- structural -------------------------------------------------------------
def check_top_story(p: Page) -> list[str]:
    n = p.top_story_badges()
    return [] if n <= 1 else [f'"Top story" badge appears {n} times (max 1). Two lead cards rendered.']


def check_wordmark(p: Page) -> list[str]:
    n = p.wordmark_count()
    if n == 0:
        return ['wordmark aria-label="VOID NEWS" not found (expected header + footer)']
    if n > WORDMARK_MAX:
        return [f'wordmark appears {n} times (max {WORDMARK_MAX}) — likely doubled']
    return []


def check_footer_wordmark(p: Page) -> list[str]:
    n = p.footer_wordmark_count()
    if n == 1:
        return []
    return [f'footer wordmark appears {n} times (expected exactly 1)']


def check_dateline(p: Page) -> list[str]:
    n = p.dateline_count()
    return [] if 1 <= n <= DATELINE_MAX else [f'dateline appears {n} times (expected 1..{DATELINE_MAX})']


def check_h1(p: Page) -> list[str]:
    n = p.h1_count()
    return [] if n == 1 else [f'<h1> appears {n} times (expected exactly 1)']


# --- text corruption --------------------------------------------------------
# Space injected after a period inside an abbreviation / decimal / before a
# closing quote. "E. Jean" and "St. Louis" are legitimate and deliberately NOT
# matched (only the known broken initialisms + decimals + quote-hugging period).
_ABBREV_RE = re.compile(r'\bU\. S\.|\bU\. K\.|\bU\. N\.|\bE\. U\.')
_DECIMAL_RE = re.compile(r'\d\. \d')
# Space between a sentence period and a CLOSING curly quote ("hear. ”") is the
# P0-1 splitter corruption. Only closing curly quotes are flagged: a straight "
# or an opening curly “ after ". " is legitimately a new sentence that opens on a
# quotation ('politician. "The Houses of Ireland" ...'), so those must NOT fire.
_QUOTE_PERIOD_RE = re.compile(r'\. [”’]')
_DIGIT_WORD_RE = re.compile(r'\d=[A-Za-z]')
# Missing-space concatenation: lowercase directly fused to Uppercase. Allowlist
# the handful of legitimate intercaps that appear in news copy.
_CONCAT_ALLOW = {
    "iphone", "ipad", "youtube", "openai", "mcdonald", "mcdonalds", "mckinsey",
    "macbook", "deepmind", "wework", "tiktok", "tiktok", "linkedin", "playstation",
    "ebay", "paypal", "airbnb", "spacex", "biontech", "msnow", "msnbc", "foxnews",
}
_CONCAT_RE = re.compile(r'\b([a-z]{3,})([A-Z][a-z]{2,})\b')
_KNOWN_CONCATS = ("Israelisettler", "Senateconfirmed", "policeofficer", "primeminister")


def _corruption_hits(regex: re.Pattern, texts: list[str], label: str, limit: int = 6) -> list[str]:
    hits: list[str] = []
    for t in texts:
        for m in regex.finditer(t):
            hits.append(f'{label}: "{_ctx(t, m.group(0))}"')
            if len(hits) >= limit:
                return hits
    return hits


def check_abbrev(p: Page) -> list[str]:
    texts = p.summaries + p.headlines
    return (_corruption_hits(_ABBREV_RE, texts, "broken abbreviation")
            + _corruption_hits(_QUOTE_PERIOD_RE, texts, "space before closing quote"))


def check_decimal(p: Page) -> list[str]:
    return _corruption_hits(_DECIMAL_RE, p.summaries + p.headlines, "broken decimal")


def check_digit_word(p: Page) -> list[str]:
    return _corruption_hits(_DIGIT_WORD_RE, p.summaries + p.headlines, "digit=word artifact")


def check_concatenation(p: Page) -> list[str]:
    texts = p.summaries + p.headlines
    hits: list[str] = []
    for known in _KNOWN_CONCATS:
        for t in texts:
            if known.lower() in t.lower():
                hits.append(f'known concatenation "{known}": "{_ctx(t, known)}"')
    for t in texts:
        for m in _CONCAT_RE.finditer(t):
            whole = (m.group(1) + m.group(2)).lower()
            if whole in _CONCAT_ALLOW:
                continue
            hits.append(f'missing-space seam "{m.group(0)}": "{_ctx(t, m.group(0))}"')
            if len(hits) >= 6:
                return hits
    return hits


# --- summary integrity ------------------------------------------------------
_TERMINAL = tuple('.!?”"’\')')


def check_summary_terminal(p: Page) -> list[str]:
    out = []
    for s in p.summaries:
        if s and not s.endswith(_TERMINAL):
            out.append(f'summary not terminated: "...{s[-60:]}"')
    return out[:6]


def check_summary_length(p: Page) -> list[str]:
    out = []
    for s in p.summaries:
        if 0 < len(s) < MIN_SUMMARY_CHARS:
            out.append(f'summary under {MIN_SUMMARY_CHARS} chars ({len(s)}): "{s}"')
    return out[:6]


# Orphan subject-less numeric fragment: a sentence that opens on a bare figure and
# runs straight into a preposition / conjunction / dangling participle. Catches
# "375 million into Saddam-era Iraq and blacklisted over alleged ... ties." while
# leaving real leads ("54 people died in the quake") alone.
_ORPHAN_RE = re.compile(
    r'^\$?\d[\d,.]*\s*(?:million|billion|trillion|thousand|percent|%)?\s+'
    r'(?:into|over|and|for|to|with|by|from|blacklisted|accused|linked|tied|amid)\b',
    re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


# A summary sentence that opens on a lowercase subordinating conjunction is a
# dependent clause left standing by a truncation ("...PAC. when she won a seat").
_ORPHAN_SUBORDINATE_RE = re.compile(
    r'(?<=[.!?]\s)(?:when|where|which|who|whom|whose|that|because|although|'
    r'though|while|since|unless|whereas|after|before|if)\b', re.MULTILINE,
)


def check_orphan_subordinate(p: Page) -> list[str]:
    out = []
    for s in p.summaries:
        m = _ORPHAN_SUBORDINATE_RE.search(s)
        if m:
            out.append(f'orphan subordinate-clause sentence: "{_ctx(s, m.group(0))}"')
    return out[:6]


def _quote_orphans(text: str) -> bool:
    """True if `text` has an unpaired double quote (an orphan closer or an
    unclosed opener), using the same left-to-right pairing as the repair."""
    t = text.replace("“", '"').replace("”", '"')
    pending = False
    for i, ch in enumerate(t):
        if ch != '"':
            continue
        before = t[i - 1] if i > 0 else " "
        after = t[i + 1] if i + 1 < len(t) else " "
        looks_open = (not before.isalnum()) and after.strip() != ""
        if not pending:
            if looks_open:
                pending = True
            else:
                return True  # closer with no opener
        else:
            pending = False
    return pending  # unclosed opener


def check_quote_balance(p: Page) -> list[str]:
    out = []
    for s in p.summaries:
        if _quote_orphans(s):
            m = re.search(r'\S*"\S*', s)
            out.append(f'unbalanced quote (orphan): "{_ctx(s, m.group(0)) if m else s[:60]}"')
    return out[:6]


def check_orphan_numeral(p: Page) -> list[str]:
    out = []
    for s in p.summaries:
        for sent in _sentences(s):
            if _ORPHAN_RE.match(sent):
                out.append(f'orphan numeric fragment: "{sent[:110]}"')
                break
    return out[:6]


# --- duplication ------------------------------------------------------------
def check_duplicate_headlines(p: Page) -> list[str]:
    stems = [(_title_word_stems(h), h) for h in p.headlines]
    out = []
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            shared = stems[i][0] & stems[j][0]
            if len(shared) >= DUP_STEM_OVERLAP:
                out.append(
                    f'duplicate story ({len(shared)} shared stems '
                    f'{sorted(shared)}):\n      - "{stems[i][1]}"\n      - "{stems[j][1]}"'
                )
    return out[:8]


# --- consistency: a card's summary must be ABOUT its own headline -----------
# Backstop for a batched-summarizer cross-assignment (2026-08-24: the "Sailor's
# Father Detained" card shipped a summary entirely about the Paramount/Warner
# merger). A genuine feed summary restates its headline's subject, so it shares
# several salient stems with the title; a cross-assigned summary shares ~none.
# Fires ONLY on the egregious zero-overlap case, and only when both sides carry
# enough signal to judge (title >= 3 salient stems, summary >= 5), so a legit
# paraphrase or a thin headline never trips it. This complements the pipeline
# guard (_summary_matches_cluster) at the served-HTML layer, catching a mismatch
# from ANY source (batch, cache, future path), not just the batch prompt.
_TS_MIN_TITLE_STEMS = 3
_TS_MIN_SUMMARY_STEMS = 5


def check_title_summary_consistency(p: Page) -> list[str]:
    out: list[str] = []
    for title, summary in p.card_pairs():
        t = _title_word_stems(title)
        s = _title_word_stems(summary)
        if len(t) < _TS_MIN_TITLE_STEMS or len(s) < _TS_MIN_SUMMARY_STEMS:
            continue  # too little signal — fail open
        if not (t & s):
            out.append(
                f'summary shares NO salient word with its headline '
                f'(likely cross-assigned):\n      headline: "{title}"'
                f'\n      summary: "{summary[:130]}..."'
            )
    return out[:6]


# --- count ------------------------------------------------------------------
def check_count_match(p: Page) -> list[str]:
    hdr = p.header_story_count
    rendered = p.rendered_card_count
    if hdr is None:
        return ['could not find "N stories loaded" header count']
    if hdr != rendered:
        return [f'header says {hdr} stories but {rendered} cards rendered']
    return []


# The Sigil aria-label is the feed card's ONLY lean label ("Coverage tilt:
# <label> (<raw lean>). N sources."). Its extreme tiers must agree with the
# canonical raw-lean bands leanLabel/BiasSnapshot use elsewhere: "Far Right"
# requires raw >= 81, "Far Left" requires raw <= 20. A card that says "Far Right"
# for raw 73-80 while the Deep Dive says "Right" is the card-vs-Sigil split (P0-6).
_SIGIL_ARIA_RE = re.compile(r'aria-label="Coverage tilt:\s*([^"(]+?)\s*\((\d+)\)')


# Every story card's stretch-link must be a crawlable <a href>, never a bare
# <button> (2026-08-21: cards near the archive boundary rendered as buttons with
# no story URL, so no Deep Dive link, no share target, nothing to index).
_CARD_BUTTON_RE = re.compile(r'<button[^>]*class="[^"]*story-card__stretch-link')


def check_every_card_has_href(p: Page) -> list[str]:
    n = len(_CARD_BUTTON_RE.findall(p.raw))
    return [] if n == 0 else [f'{n} story card(s) render as a <button> with no href (must be <a href>)']


# Every story card link must be the canonical /story/<uuid>/ shape. A "/?story="
# link loads the homepage instead of the story page and is not indexable (P0-B):
# it means the card missed the print archive and fell back. Extract the stretch
# link hrefs and flag any that are not /story/<uuid>/.
_STRETCH_HREF_RE = re.compile(r'<a[^>]*class="[^"]*(?:story-card|lead)__stretch-link[^"]*"[^>]*href="([^"]+)"|<a[^>]*href="([^"]+)"[^>]*class="[^"]*(?:story-card|lead)__stretch-link')
_STORY_SHAPE_RE = re.compile(r'/story/[0-9a-f-]{36}/?$')


def check_href_shape(p: Page) -> list[str]:
    hrefs = [a or b for a, b in _STRETCH_HREF_RE.findall(p.raw)]
    out = []
    for h in hrefs:
        if not _STORY_SHAPE_RE.search(h):
            out.append(f'malformed story href (must be /story/<uuid>/): "{h}"')
    return out[:6]


# Regression lock for the aggregate_confidence read path. The real rev-49 formula
# (migration 076 RPC + main.py fallback) varies per cluster; the superseded proxy
# (migration 002's LEAST(1.0, COUNT/5.0)) pins every >=5-source cluster to exactly
# 1.0. If the feed's confidence values are ALL pinned high, the dead proxy path
# has leaked back in and rev-49 damping is off on the live site.
_CONF_RE = re.compile(r'\\?"aggregateConfidence\\?":([0-9.]+)')


def check_confidence_not_proxy(p: Page) -> list[str]:
    vals = [float(x) for x in _CONF_RE.findall(p.raw)]
    if len(vals) < 5:
        return []  # too few to judge
    if all(v >= 0.999 for v in vals):
        return [f'all {len(vals)} aggregateConfidence values are ~1.0 — the dead '
                f'COUNT/5 proxy (migration 002) has leaked back; rev-49 damping is off']
    return []


def check_card_sigil_label(p: Page) -> list[str]:
    out = []
    for m in _SIGIL_ARIA_RE.finditer(p.raw):
        label = m.group(1).strip()
        low = label.lower()
        val = int(m.group(2))
        if "far right" in low and val < 81:
            out.append(f'card/Sigil "{label}" but raw lean {val} is canonical Right (Far Right needs >= 81)')
        elif "far left" in low and val > 20:
            out.append(f'card/Sigil "{label}" but raw lean {val} is canonical Left (Far Left needs <= 20)')
    return out[:8]


CHECKS = [
    ("structural: single Top story", check_top_story),
    ("structural: wordmark not doubled", check_wordmark),
    ("structural: single dateline", check_dateline),
    ("structural: footer wordmark exactly once", check_footer_wordmark),
    ("structural: exactly one h1", check_h1),
    ("corruption: abbreviations / quotes", check_abbrev),
    ("corruption: decimals", check_decimal),
    ("corruption: digit=word", check_digit_word),
    ("corruption: missing-space concatenation", check_concatenation),
    ("integrity: summaries terminated", check_summary_terminal),
    ("integrity: summary min length", check_summary_length),
    ("integrity: no orphan numeric fragment", check_orphan_numeral),
    ("integrity: no orphan subordinate clause", check_orphan_subordinate),
    ("integrity: quotes are balanced", check_quote_balance),
    ("duplication: no duplicate headlines", check_duplicate_headlines),
    ("consistency: summary matches its headline", check_title_summary_consistency),
    ("count: header matches rendered", check_count_match),
    ("consistency: card lean label == canonical (Sigil)", check_card_sigil_label),
    ("structural: every card has an href", check_every_card_has_href),
    ("structural: story hrefs are /story/<uuid>/", check_href_shape),
    ("integrity: confidence is real (not COUNT/5 proxy)", check_confidence_not_proxy),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html_file")
    ap.add_argument("--url", default="(local file)")
    args = ap.parse_args()

    with open(args.html_file, encoding="utf-8", errors="replace") as fh:
        doc = fh.read()

    p = Page(doc)
    print(f"Verifying: {args.url}")
    print(f"  parsed {len(p.headlines)} headlines, {len(p.summaries)} summaries, "
          f"header count {p.header_story_count}\n")

    total_fail = 0
    for name, fn in CHECKS:
        try:
            failures = fn(p)
        except Exception as e:  # a check crashing must not mask a real problem
            failures = [f"check raised {type(e).__name__}: {e}"]
        if failures:
            total_fail += len(failures)
            print(f"[FAIL] {name}")
            for f in failures:
                print(f"    - {f}")
        else:
            print(f"[ ok ] {name}")

    print()
    if total_fail:
        print(f"GATE FAILED: {total_fail} issue(s) in served output at {args.url}")
        return 1
    print(f"GATE PASSED: served output at {args.url} clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
