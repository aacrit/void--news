"""
News-worthiness / evergreen-junk filter for the void --news pipeline.

Drops non-news content — evergreen guides, product/loyalty promo pages, live
market-ticker/index pages, and recurring undated filler (horoscopes, puzzle
answers, TV schedules) — BEFORE it is scraped, clustered, and ranked.

Motivation (2026-08-06): the feed surfaced two non-stories at story rank:
  - "United MileagePlus: Guide to earning and redeeming miles, elite status
     and more"                                        (evergreen loyalty guide)
  - "Latest Stock and Share Market News, Sensex, Nifty, NSE, BSE Live News"
                                                       (live market-ticker page)
Neither is a dated news event. Both are structurally detectable from the title.

Motivation (2026-08-10): the Nature journal RSS feed (nature.rss mixes research
papers + corrections with actual Nature journalism) leaked academic errata into
the feed. In the 2026-08-10 run seven Nature items ("Author Correction: ...",
"Publisher Correction: ...", "Editorial Expression of Concern: ...") were
ingested as news and landed in a story cluster. A journal correction / erratum /
retraction notice is never a news event. These are matched as TITLE PREFIXES
only, so a real news story that merely contains the word "correction" /
"retraction" is NOT dropped: Retraction Watch's "...anesthesiologists earning
retractions..." and "Police issue correction to earlier statement" both survive
(the marker is not at the start of the title).

Design principles
-----------------
* Rule-based, deterministic, $0 (no LLM, no network).
* SCORED heuristic, not a hard blocklist — a single keyword never drops an
  article; dropping requires multiple independent evergreen signals OR one
  unambiguous non-news marker (horoscope/Wordle/lottery-results).
* HIGH PRECISION over recall. A borderline item STAYS. A hard news-event
  signal in the title (casualty numbers, breaking-news verbs) raises the drop
  bar sharply, so a real story that merely contains an evergreen keyword — a
  market CRASH, an airline-safety event, a policy fight — is never dropped.

Public API
----------
    newsworthiness(article) -> dict         # {score, threshold, signals, is_junk, ...}
    is_evergreen_junk(article) -> bool
    drop_evergreen_junk(articles, verbose=True) -> list   # returns KEPT articles

The article dict is read with the same keys RSS ingestion already provides:
title, summary, section, url, published_at. Only `title` is required; the
rest are optional supporting signals.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
# An article is dropped when its summed evergreen score reaches DROP_THRESHOLD.
# When the title ALSO carries a hard news-event signal (casualty count,
# breaking-news verb), the bar is raised to VETO_THRESHOLD so only an
# overwhelmingly evergreen page (multiple strong markers) can still be dropped.
DROP_THRESHOLD = 3
VETO_THRESHOLD = 6

# ---------------------------------------------------------------------------
# Signal patterns.  Each entry: (compiled_regex, reason_label, weight)
# Weights: 4 = unambiguous non-news (drops alone); 2 = moderate evergreen
# marker (needs a second signal); 1 = weak/supporting.
# Reason labels are unique so the same reason is never double-counted.
# ---------------------------------------------------------------------------

# -- Unambiguous recurring non-news (weight 4: drops on its own) -------------
_STRONG_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bhoroscope\b", re.I), "horoscope"),
    (re.compile(r"\b(?:zodiac|astrolog\w*)\b", re.I), "astrology"),
    (re.compile(r"\bwordle\b", re.I), "wordle"),
    (re.compile(r"\b(?:quordle|nyt connections|connections hint\w*|"
                r"strands hint\w*|spelling bee answer\w*)\b", re.I), "puzzle-game"),
    (re.compile(r"\b(?:crossword|sudoku|jumble)\b.{0,20}?"
                r"(?:answer\w*|clue\w*|solution\w*|hint\w*)", re.I), "puzzle-answers"),
    (re.compile(r"\b(?:lottery|lotto|powerball|mega\s?millions|euromillions)\b"
                r".{0,25}?(?:result\w*|number\w*|winning|draw)", re.I), "lottery-results"),
    (re.compile(r"\b(?:winning numbers|lucky numbers)\b", re.I), "lottery-numbers"),
    (re.compile(r"\bdaily horoscope\b", re.I), "daily-horoscope"),
]

# -- Academic-journal artifacts (DECISIVE, prefix-anchored) -----------------
# Journal corrections / errata / retraction notices / peer-review byproducts are
# never news. They are matched ONLY as a title PREFIX (optionally after a bracket
# or quote), so a real news story that merely CONTAINS "correction"/"retraction"
# mid-title survives:
#   DROP  "Author Correction: Nucleolar URB1 ensures ..."      (Nature erratum)
#   DROP  "Publisher Correction: Progressive plasticity ..."   (Nature erratum)
#   DROP  "Editorial Expression of Concern: Tumour exosome ..."
#   KEEP  "High-profile anesthesiologists earning retractions for data ..."
#   KEEP  "JU forms probe body over research paper retractions"
#   KEEP  "Police issue correction to earlier statement"
# This is a decisive, veto-proof drop: a title starting with one of these markers
# is an academic artifact regardless of any news-verb elsewhere in the title.
_ACADEMIC_ARTIFACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^[\[\('\"\s]*author\s+correction\b", re.I),
     "author-correction"),
    (re.compile(r"^[\[\('\"\s]*publisher\s+correction\b", re.I),
     "publisher-correction"),
    (re.compile(r"^[\[\('\"\s]*(?:editorial\s+)?expression\s+of\s+concern\b",
                re.I), "expression-of-concern"),
    # Single-word decisive markers require a following colon / whitespace / end
    # (NOT a hyphen), so "Erratum-free reporting ..." is not caught.
    (re.compile(r"^[\[\('\"\s]*erratum(?=[:\s]|$)", re.I), "erratum"),
    (re.compile(r"^[\[\('\"\s]*corrigend(?:um|a)(?=[:\s]|$)", re.I),
     "corrigendum"),
    # "Retraction:" / "Retraction of ..." / "Retraction Note" / "Retracted
    # Article" — but NOT "Retraction Watch" or a headline that merely opens with
    # the word (guarded by the required following token).
    (re.compile(r"^[\[\('\"\s]*retraction\s*(?::|of\b|note\b)", re.I),
     "retraction-notice"),
    (re.compile(r"^[\[\('\"\s]*retracted\s+article\b", re.I),
     "retracted-article"),
    (re.compile(r"^[\[\('\"\s]*author\s+response\s+to\b", re.I),
     "author-response"),
    (re.compile(r"^[\[\('\"\s]*reviewer\s+acknowledge?ments?\b", re.I),
     "reviewer-acknowledgements"),
    (re.compile(r"^[\[\('\"\s]*matters\s+arising\b", re.I), "matters-arising"),
    # Bare "Correction:" prefix (a stand-alone correction notice). Requires the
    # colon so "Correction to X" news phrasing mid-sentence never matches, and
    # the prefix anchor keeps "issue a correction" out.
    (re.compile(r"^[\[\('\"\s]*correction\s*:", re.I), "correction-prefix"),
]


def _academic_artifact_signal(title: str) -> str | None:
    """Return the reason label if the title is a journal correction/erratum.

    Prefix-anchored and decisive: a matching title is dropped regardless of the
    news-event veto (an "Author Correction: ..." is never a news event).
    Returns None when no academic-artifact prefix is present.
    """
    for pat, reason in _ACADEMIC_ARTIFACT_PATTERNS:
        if pat.search(title):
            return reason
    return None


# -- Guides / how-to / evergreen explainer (weight 2) -----------------------
_GUIDE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # "guide to ...", "a complete/ultimate/beginner's guide", "... : a guide"
    (re.compile(r"\b(?:complete|ultimate|comprehensive|beginner'?s?|"
                r"definitive|essential|step[-\s]by[-\s]step)\s+guide\b", re.I),
     "complete-guide"),
    (re.compile(r"\bguide\s+to\s+\w+", re.I), "guide-to"),
    (re.compile(r":\s*(?:a|the|your)\s+guide\b", re.I), "colon-guide"),
    (re.compile(r"\beverything you (?:need|wanted) to know\b", re.I),
     "everything-you-need-to-know"),
    # "how to <verb>" — restricted to instructional verbs so news headlines
    # like "How the Fed decided ..." (not "how to") never match.
    (re.compile(r"\bhow to\s+(?:earn|redeem|get|save|buy|choose|pick|make|use|"
                r"find|book|apply|invest|start|set\s?up|build|download|install|"
                r"stream|watch|activate|maximi[sz]e|cancel|claim)\b", re.I),
     "how-to"),
    (re.compile(r"\btips (?:and|&) tricks\b", re.I), "tips-and-tricks"),
    (re.compile(r"\b(?:explained|explainer)\b", re.I), "explainer"),  # weak; see WEAK set
    (re.compile(r"\bwhat you need to know about\b", re.I), "what-you-need-to-know"),
    # 2026-09-09: the rank-17 card was a five-member cluster joined on the word
    # "hair", built from a Daily Mail service guide ("The dos and don'ts of body
    # hair: Experts reveal how to flaunt your fuzz"), an NBC Select affiliate
    # commerce page, and a Page Six photo gallery. Its summary quoted an
    # aesthetician and a cosmetic-clinic director advising the reader how to
    # groom. None of the four scored as junk at ingestion.
    (re.compile(r"\bdos and don'?ts\b", re.I), "dos-and-donts"),
    (re.compile(r"\bhow to\s+(?:flaunt|style|wear|pull off|rock|dress)\b", re.I),
     "how-to-style"),
    (re.compile(r"\bhere'?s why (?:it|this|that|they|your)\b", re.I), "heres-why-service"),
    (re.compile(r"\bstar snaps\b", re.I), "star-snaps-gallery"),
]

# Affiliate-commerce and gallery URL sections. A path segment is a publisher's
# own declaration of what a page is for, and it is far more reliable than the
# headline: NBC Select lives at /select/shopping/ and sells things.
_COMMERCE_URL = re.compile(
    r"/(?:select/shopping|shop(?:ping)?/deals|affiliate|commerce|"
    r"best-deals|product-reviews)/", re.I)
# "explainer" alone is common in real news framing; demote it to weight 1.
_WEAK_REASONS = {"explainer"}

# -- Listicle titles --------------------------------------------------------
# A title that LEADS with a number + listicle noun ("10 Best Ways to ...") is
# almost never hard news, so it is decisive on its own (weight 3). The other,
# looser listicle markers stay at weight 2 (need corroboration).
_LISTICLE_LEAD = re.compile(
    r"^\s*\d{1,3}\s+(?:best|top|worst|ways|things|reasons|tips|"
    r"tricks|facts|hacks|ideas|must[-\s]\w+|essential|cheapest|"
    r"greatest|coolest|surprising)\b", re.I)
_LISTICLE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\btop\s+\d{1,3}\b", re.I), "top-N"),
    (re.compile(r"\b(?:best|cheapest)\s+\w+\s+(?:of|for|in)\s+20\d\d\b", re.I),
     "best-of-year"),
]

# -- Loyalty / product-promo (weight 2 each, contribution capped) -----------
_LOYALTY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bmileage\s?plus\b", re.I), "mileageplus"),
    (re.compile(r"\b(?:frequent[-\s]?flyer|frequent[-\s]?flier)\b", re.I),
     "frequent-flyer"),
    (re.compile(r"\b(?:rewards?|loyalty)\s+program\b", re.I), "rewards-program"),
    (re.compile(r"\belite status\b", re.I), "elite-status"),
    (re.compile(r"\b(?:earning and redeeming|redeeming and earning|"
                r"earn and redeem|points and miles|miles and points)\b", re.I),
     "earn-redeem-miles"),
    (re.compile(r"\b(?:best credit cards?|credit card rewards?|cash[-\s]?back)\b",
                re.I), "credit-card-rewards"),
    (re.compile(r"\b(?:reward points|bonus points|airline miles|air miles)\b",
                re.I), "reward-points"),
]
_LOYALTY_CAP = 4  # cap total loyalty contribution so runaway keyword pages ~= 4

# -- Live market-ticker / index pages (weight 2) ----------------------------
# Individual index names are NEVER a signal by themselves (a real story about
# the Sensex crashing must survive). The signal is an index name COMBINED with
# generic ticker-page framing ("live news", "live updates", "today").
_TICKER_LIVE = re.compile(
    r"\b(?:live\s+(?:news|updates?|blog|coverage)|market\s+live|"
    r"live\s+market|latest\s+(?:stock|share|market)\s+news)\b", re.I)
_TICKER_TODAY = re.compile(
    r"\b(?:share price|stock price|sensex|nifty|gold rate|silver rate|"
    r"petrol price|diesel price|fuel price)\s+today\b", re.I)
_INDEX_NAMES = re.compile(
    r"\b(?:sensex|nifty|nse|bse|dow jones|nasdaq|s&p 500|ftse|nikkei|"
    r"hang seng|dax|cac 40)\b", re.I)
_TICKER_GENERIC = re.compile(
    r"\b(?:stock (?:and share )?market news|share market news|"
    r"market news|stocks? to (?:buy|watch)|market wrap|closing bell)\b", re.I)

# -- Other recurring undated filler (weight 2/3) ----------------------------
_FILLER_PATTERNS: list[tuple[re.Pattern, str, int]] = [
    (re.compile(r"\b(?:weather (?:today|forecast)|today'?s weather|"
                r"weather (?:report|outlook))\b", re.I), "weather-page", 3),
    (re.compile(r"\b(?:tv (?:schedule|guide|listings)|what to watch|"
                r"streaming (?:guide|this week)|how to watch)\b", re.I),
     "tv-schedule", 2),
    (re.compile(r"\b(?:what'?s (?:on|new) (?:on|this)|coming to)\s+"
                r"(?:netflix|hulu|disney\+?|max|prime video|apple tv)\b", re.I),
     "streaming-schedule", 2),
]

# ---------------------------------------------------------------------------
# News-event veto signals — raise the drop bar when the title reads like a
# dated event, protecting real stories that merely contain an evergreen word.
# ---------------------------------------------------------------------------
_NEWS_VERB = re.compile(
    r"\b(?:kill\w*|dead|dies|died|injur\w*|wound\w*|"
    r"announce\w*|say\w*|said|warn\w*|resign\w*|arrest\w*|charg\w*|"
    r"convict\w*|win\w*|won|defeat\w*|elect\w*|unveil\w*|launch\w*|"
    r"sign\w*|approv\w*|reject\w*|pass\w*|vote\w*|sue\w*|ban\w*|"
    r"fire\w*|fired|strike\w*|attack\w*|crash\w*|erupt\w*|surg\w*|"
    r"plung\w*|soar\w*|jump\w*|tumbl\w*|slump\w*|rally\w*|"
    r"cut\w*|hike\w*|rais\w*|meet\w*|met|accus\w*|deni\w*|"
    r"quit\w*|ousts?|ousted|indict\w*|sentenc\w*|kidnap\w*|"
    r"invad\w*|bomb\w*|shell\w*|evacuat\w*|rescu\w*|collaps\w*)\b", re.I)
_CASUALTY_NUM = re.compile(
    r"\b(?:kill\w*|dead|dies|died|injur\w*|wound\w*|toll)\b\D{0,12}\d",
    re.I)


def _news_event_signal(title: str) -> bool:
    """True when the title carries a dated news-event marker."""
    return bool(_NEWS_VERB.search(title) or _CASUALTY_NUM.search(title))


# ---------------------------------------------------------------------------
# Desk furniture (2026-09-07)
# ---------------------------------------------------------------------------
# A newsroom's own scaffolding: the morning recap, the day's final word, the TV
# listings. These carry no event, so a clusterer has nothing to place them by
# and they land wherever the TF-IDF noise points. On 2026-09-06 "Morning recap"
# shipped inside the Trump / Pickaxe Mountain cluster, "Saturday's Final Word"
# inside a murder trial, and a local paper's TV-and-radio listing inside a BYU
# football card. Dropping them at ingestion costs nothing and touches no
# clustering threshold.
#
# Deliberately narrow. "Iran war latest: Iranian oil tanker targeted in US
# strike" is a real story with a real headline after the colon, so the
# furniture pattern must MATCH THE START of a SHORT title, not appear anywhere
# in a long one. Measured against the 1,237 article titles of the 09-06 feed:
# 3 matches, all three genuine furniture.
# 2026-09-09: the first list named only saturday and sunday, so Monday through
# Friday furniture sailed straight through. "Tuesday's Final Word" reached the
# Iran strike cluster on the 09-09 feed and the coherence pass had to remove it.
_FURNITURE_TITLE = re.compile(
    r"^(?:the\s+)?(?:morning|evening|weekend|daily|weekly|nightly|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tonight)?(?:'?s)?\s*"
    r"(?:news\s+)?(?:recap|roundup|round-?up|briefing|digest|rundown|"
    r"final\s+word|top\s+stories|headlines|newsletter|open\s+thread)\b", re.I)
_FURNITURE_MAX_WORDS = 6

_LISTING_TITLE = re.compile(
    r"\b(?:on\s+the\s+air|what'?s\s+on\s+tv|tv\s+and\s+radio|"
    r"here'?s\s+what\s+games|photos?\s+of\s+the\s+(?:day|week)|"
    r"in\s+pictures|your\s+(?:morning|evening)\s+briefing|"
    r"the\s+week\s+ahead|what\s+to\s+watch\s+(?:today|this\s+week|on\s+tv)|"
    # "Today in Germany: A roundup of the latest news on Wednesday" reached a
    # cluster on 09-09. The phrase is distinctive enough to match anywhere in
    # the title; a real story does not describe itself as a roundup of news.
    r"a\s+round-?up\s+of\s+the\s+latest|"
    r"round-?up\s+of\s+(?:the\s+)?(?:latest|today'?s?|this\s+week'?s?)\s+news)\b", re.I)


def _furniture_signals(title: str) -> list[tuple[str, int]]:
    """Newsroom scaffolding with no event in it. Weight 3: a hard drop on its
    own, and still under the raised bar a real news verb would set."""
    t = (title or "").strip()
    if not t:
        return []
    if _FURNITURE_TITLE.match(t) and len(t.split()) <= _FURNITURE_MAX_WORDS:
        return [("desk-furniture", 3)]
    if _LISTING_TITLE.search(t):
        return [("listing-page", 3)]
    return []


def _ticker_signals(title: str, url: str) -> list[tuple[str, int]]:
    """Collect live-ticker / index-page signals (weight 2 each)."""
    out: list[tuple[str, int]] = []
    has_index = bool(_INDEX_NAMES.search(title))
    has_live = bool(_TICKER_LIVE.search(title))
    has_today = bool(_TICKER_TODAY.search(title))
    has_generic = bool(_TICKER_GENERIC.search(title))

    if has_today:
        out.append(("ticker-price-today", 3))
    if has_live and (has_index or has_generic):
        out.append(("ticker-live-index", 3))
    elif has_live and not has_today:
        # "Live news" without an index/market anchor is a weaker signal; a real
        # "live blog" of a news event should not be dropped on this alone.
        out.append(("live-page", 1))
    # A title that names >=2 distinct indices AND uses generic market framing
    # (no specific move) is an index catalog page.
    if len(set(m.group(0).lower() for m in _INDEX_NAMES.finditer(title))) >= 2 \
            and (has_generic or has_live):
        out.append(("multi-index-catalog", 2))
    if _COMMERCE_URL.search(url or ""):
        out.append(("commerce-url-section", 3))
    if "/markets/live" in url.lower() or "/market-live" in url.lower():
        out.append(("url-market-live", 1))
    return out


# An agency dateline. AFP, Reuters and AP prefix copy with "PARIS, Sept 8, 2026
# (AFP) - " and some feeds leave it in the title, which is three commas before
# the headline even begins.
_AGENCY_DATELINE = re.compile(
    r"^[^,]{2,40}(?:,\s*[^,]{2,40}){0,2},\s*"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s*"
    r"\d{4}\s*\((?:AFP|AP|Reuters|PTI|IANS|ANI|dpa|EFE|Xinhua|Yonhap|Kyodo|"
    r"Bernama|TASS|Anadolu|Sputnik)\)\s*[-\u2013\u2014:]?\s*", re.I)


def _comma_catalog_signal(title: str) -> list[tuple[str, int]]:
    """A comma-separated keyword list with no verb is a catalog/index title.

    e.g. 'Latest Stock and Share Market News, Sensex, Nifty, NSE, BSE Live News'
    (4 commas, no sentence verb). Requires >=3 commas to avoid catching a
    normal headline with a couple of appositive commas.

    An agency dateline is stripped first. It is three commas of pure metadata,
    so without this a real AFP story counts as a catalog on its provenance
    alone: "Washington, United States, Sept 8, 2026 (AFP) - Smithsonian
    secretary to retire as Trump..." was one of exactly two false positives
    when this filter was swept over the 955 article titles behind the
    2026-09-09 feed.
    """
    body = _AGENCY_DATELINE.sub("", title or "", count=1)
    if body.count(",") >= 3 and not _NEWS_VERB.search(body):
        return [("comma-catalog", 2)]
    return []


def _recency_signal(published_at) -> list[tuple[str, int]]:
    """Weak supporting signal: a missing or very stale publish date.

    Only ever contributes alongside a title signal (see newsworthiness()),
    so a legit dateless feed item is never dropped on this alone.
    """
    if not published_at:
        return [("no-date", 1)]
    try:
        if isinstance(published_at, str):
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        else:
            dt = published_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt < datetime.now(timezone.utc) - timedelta(days=30):
            return [("stale-date", 1)]
    except (ValueError, TypeError):
        return [("no-date", 1)]
    return []


def newsworthiness(article: dict) -> dict:
    """Score an article's evergreen-junk signals.

    Returns a dict:
        score      -> summed weight of distinct evergreen signals
        threshold  -> the drop threshold applied (higher when a news-event
                      signal is present)
        news_event -> whether a dated news-event marker was found
        signals    -> list of (reason, weight) that fired
        is_junk    -> score >= threshold
    """
    title = (article.get("title") or "").strip()
    url = article.get("url") or ""
    if not title:
        # No title to judge; never drop (fail-open, conservative).
        return {"score": 0, "threshold": DROP_THRESHOLD, "news_event": False,
                "signals": [], "is_junk": False}

    # Academic-journal artifact (correction/erratum/retraction notice) — a
    # decisive, veto-proof drop. Checked FIRST so a correction whose title also
    # contains a news verb (e.g. "Author Correction: ... shows durable
    # response ...") is still dropped.
    artifact = _academic_artifact_signal(title)
    if artifact:
        return {"score": VETO_THRESHOLD, "threshold": DROP_THRESHOLD,
                "news_event": False, "academic_artifact": True,
                "signals": [(artifact, VETO_THRESHOLD)], "is_junk": True}

    signals: dict[str, int] = {}

    def add(reason: str, weight: int) -> None:
        # Keep the max weight seen for a reason; never double-count a reason.
        if weight > signals.get(reason, 0):
            signals[reason] = weight

    # Strong unambiguous non-news markers.
    for pat, reason in _STRONG_PATTERNS:
        if pat.search(title):
            add(reason, 4)

    # Guides / how-to / evergreen explainers.
    for pat, reason in _GUIDE_PATTERNS:
        if pat.search(title):
            add(reason, 1 if reason in _WEAK_REASONS else 2)

    # Listicles.
    if _LISTICLE_LEAD.search(title):
        add("listicle-lead", 3)
    for pat, reason in _LISTICLE_PATTERNS:
        if pat.search(title):
            add(reason, 2)

    # Loyalty / product promo (contribution capped).
    loyalty_total = 0
    for pat, reason in _LOYALTY_PATTERNS:
        if pat.search(title):
            add(reason, 2)
            loyalty_total += 2
    if loyalty_total > _LOYALTY_CAP:
        # Trim: drop lowest-value loyalty reasons down to the cap.
        overflow = loyalty_total - _LOYALTY_CAP
        for reason in list(signals):
            if overflow <= 0:
                break
            if reason in {p[1] for p in _LOYALTY_PATTERNS}:
                take = min(signals[reason], overflow)
                signals[reason] -= take
                overflow -= take
                if signals[reason] <= 0:
                    del signals[reason]

    # Newsroom scaffolding: recaps, final words, TV listings.
    for reason, weight in _furniture_signals(title):
        add(reason, weight)

    # Live market-ticker / index pages.
    for reason, weight in _ticker_signals(title, url):
        add(reason, weight)

    # Comma-separated catalog/index title.
    for reason, weight in _comma_catalog_signal(title):
        add(reason, weight)

    # Other recurring undated filler.
    for pat, reason, weight in _FILLER_PATTERNS:
        if pat.search(title):
            add(reason, weight)

    title_signal_score = sum(signals.values())

    # Weak recency signal only counts when a title signal already fired.
    if title_signal_score > 0:
        for reason, weight in _recency_signal(article.get("published_at")):
            add(reason, weight)

    score = sum(signals.values())
    news_event = _news_event_signal(title)
    threshold = VETO_THRESHOLD if news_event else DROP_THRESHOLD
    is_junk = score >= threshold

    return {
        "score": score,
        "threshold": threshold,
        "news_event": news_event,
        "academic_artifact": False,
        "signals": sorted(signals.items(), key=lambda kv: -kv[1]),
        "is_junk": is_junk,
    }


def is_evergreen_junk(article: dict) -> bool:
    """True when the article should be dropped as evergreen / non-news."""
    return newsworthiness(article)["is_junk"]


def drop_evergreen_junk(articles: list[dict], *, verbose: bool = True) -> list[dict]:
    """Filter evergreen/non-news items out of an article list.

    Returns the KEPT articles. Logs a one-line summary plus up to 15 dropped
    titles with their firing signals, so a pipeline run shows exactly what the
    filter removed (and lets a reviewer catch any false positive).
    """
    if not articles:
        return articles
    kept: list[dict] = []
    dropped: list[tuple[str, dict]] = []
    for art in articles:
        verdict = newsworthiness(art)
        if verdict["is_junk"]:
            dropped.append(((art.get("title") or "").strip(), verdict))
        else:
            kept.append(art)

    if verbose:
        n = len(dropped)
        print(f"  [newsworthiness] Dropped {n} evergreen/non-news item(s) of "
              f"{len(articles)} ({len(kept)} kept).")
        for title, verdict in dropped[:15]:
            sig = ", ".join(f"{r}={w}" for r, w in verdict["signals"])
            print(f"    - drop (score {verdict['score']}/{verdict['threshold']}): "
                  f"{title[:90]!r} [{sig}]")
        if n > 15:
            print(f"    ... and {n - 15} more.")
    return kept
