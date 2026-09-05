"""
Story clustering engine for the void --news pipeline.

Rule-based phases. PRODUCTION runs 1 → 2 → 3 → 4 → 5 (see
cluster_stories); the historical 2.5/2.55/2.6 passes are parked:

    Phase 1:   TF-IDF + agglomerative clustering on (title + first 500 words)
               at distance threshold 1 - STORY_TFIDF_THRESHOLD.
    Phase 2:   IDF-weighted entity-overlap merge — pairs of clusters
               accumulate sum-of-IDF over shared named entities, merging
               when the score crosses ENTITY_MERGE_IDF_THRESHOLD.
    Phase 3:   Stem-aware title Jaccard merge — Porter-stemmed title-word
               sets that cross TITLE_JACCARD_THRESHOLD merge.
    Phase 4:   Garbage-title force-split — when the title-generator
               produces a "X Spans Y, Z, and W" signature it has been
               forced to mash up unrelated sub-events; we re-cluster the
               articles at a stricter TF-IDF + IDF gate.
    Phase 5:   Mega-cluster soft cap + over-merge flag (no force-split
               since the 2026-05-31 revert).

    PARKED (not wired into cluster_stories — kept for possible revival):
    Phase 2.5  merge_canonical_pairs (_SUMMIT_PAIRS editorial override —
               NOTE: its Trump+Xi fragmentation protection has NO
               replacement in the live path; _SYNONYM_NORMALISATION in
               _build_document only canonicalises name variants).
    Phase 2.55 merge_synonym_pairs — geographic aliases folded into
               _build_document's _SYNONYM_NORMALISATION (2026-05-31).
    Phase 2.6  merge_anchor_entities — behind enable_anchor_merge=False;
               no production caller passes the flag.

Wire-amplification is handled OUTSIDE the cluster topology: every article
arriving here may carry `is_wire_copy` / `wire_origin_publisher_id`
fields set by `deduplicator.deduplicate_articles()`. The final
`source_count` collapses wire copies to their origin publisher and a
companion `wire_amplification` metric (= total_articles / source_count)
records the syndication ratio for downstream ranking.

Uses scikit-learn (TF-IDF, AgglomerativeClustering, cosine_similarity),
spaCy NER (via utils.nlp_shared), and nltk PorterStemmer (with a spaCy
lemma fallback). No LLM API calls.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.nlp_shared import get_nlp

try:
    from utils.prohibited_terms import sanitize_editorial_text as _sanitize_editorial
except ImportError:  # utils not on path (e.g. isolated unit test)
    def _sanitize_editorial(text):
        return text

# text_sanitizer adds what _sanitize_editorial (em-dash / significance / HTML
# entities) does not cover (2026-07-01 top-50 review): normalize_headline strips
# source-name suffixes the O6 whitelist misses (Euractiv, Focus Taiwan, Cyrillic
# outlets), editorial prefixes (INSIGHT:/Exclusive,) and tabloid epithet leads
# (Devastating:/Unbothered King:); sanitize_summary strips CMS/RSS scaffolding
# ("appeared first on", "Submitted by ... <date>", twitter embeds) and repairs
# mid-word "..." truncation on the un-summarized null-tier tail.
try:
    from utils.text_sanitizer import normalize_headline, sanitize_summary
except ImportError:  # pragma: no cover
    def normalize_headline(t):
        return t

    def sanitize_summary(t):
        return t


# ---------------------------------------------------------------------------
# Calibrated thresholds — single source of truth for clustering signal
# sensitivity. Tuned 2026-05-15 against the 21-fixture clustering suite.
# ---------------------------------------------------------------------------
STORY_TFIDF_THRESHOLD       = 0.24   # Phase 1 agglomerative cosine cut (2026-06-28 O1: 0.18->0.24, tighter to curb over-merge chaining)
ENTITY_MERGE_IDF_THRESHOLD  = 2.0    # legacy — unused after 2026-05-31 simplification
TITLE_JACCARD_THRESHOLD     = 0.22   # Phase 3: stemmed title Jaccard
                                     # 0.27 → 0.22 on 2026-05-31 to align with
                                     # ANCHOR_TITLE_JACCARD_FLOOR + rescue
                                     # multi-desk title diversity cases like
                                     # Trump-Iran where each desk picks a
                                     # different secondary detail.
MAX_AGE_SPREAD_HOURS        = 48.0   # Time gate (kept for both merge passes)
WIRE_HASH_FINGERPRINT_BYTES = 800    # Phase 0 (in deduplicator): chars hashed
WIRE_LEAD_COSINE            = 0.92   # Phase 0 (in deduplicator): confirm threshold


# ---------------------------------------------------------------------------
# Title cleanup
# ---------------------------------------------------------------------------
# Wire service prefixes: (LEAD), (URGENT), BREAKING:, (3rd LD), etc.
_WIRE_PREFIX_RE = re.compile(
    r"^\s*(?:\((?:LEAD|URGENT|CORRECTED|UPDATE(?:\s*\d*)?|RECASTS?|ADDS?|"
    r"WRAPUP|NEWSALERT|\d+(?:st|nd|rd|th)\s+LD)\)\s*)"
    r"|^\s*(?:WATCH\s*LIVE\s*:|WATCH\s*:|BREAKING\s*:|UPDATE\s*:|EXCLUSIVE\s*:)"
    r"\s*",
    re.IGNORECASE,
)
# Source attribution at end: " - Reuters", " | BBC News", " -- AP", etc.
_ATTRIBUTION_SUFFIX_RE = re.compile(
    r"\s*[-–—|]+\s*"
    r"(?:Reuters|AP\s*News?|Associated\s*Press|CNN|BBC(?:\s*News)?|NPR|PBS"
    r"|Fox\s*News|The\s+[A-Z]\w+(?:\s+[A-Z]\w+)?|[A-Z]\w+\s+News"
    r"|Al\s+Jazeera|Bloomberg|CNBC|ABC\s*News|CBS\s*News|NBC\s*News"
    r"|The\s+Guardian|Washington\s+Post|New\s+York\s+Times|Wall\s+Street\s+Journal"
    r"|Chicago\s+Tribune|UPI|NHK\s+WORLD(?:-JAPAN)?|NHK\s+World"
    r"|Nikkei|Haaretz|South\s+China\s+Morning\s+Post)"
    r"\s*$",
    re.IGNORECASE,
)
_DOMAIN_SUFFIX_RE = re.compile(
    r"\s*[-–—|]+\s*\w+\.(?:com|org|net|co\.uk|or\.jp|co\.jp)\s*$",
    re.IGNORECASE,
)
# Outlet-suffix shapes the explicit wire allow-list above misses (2026-06-28,
# O6). Case-sensitive so a leading word must be capitalised (a proper noun),
# which keeps ordinary trailing clauses intact. Each strips one trailing tag:
#   all-caps wire/outlet acronyms  ("- WSJ", "| UPI", "- NHK", "- TheCab"→no)
#   single-token CamelCase outlets ("- TheCable", "- TheBlaze")
#   multi-word names ending in an outlet-type word ("- Just The News")
_ACRONYM_SUFFIX_RE = re.compile(r"\s*[-–—|]+\s*[A-Z]{2,6}\s*$")
_CAMEL_OUTLET_SUFFIX_RE = re.compile(r"\s*[-–—|]+\s*The[A-Z][a-zA-Z]+\s*$")
_OUTLET_WORD_SUFFIX_RE = re.compile(
    r"\s*[-–—|]+\s*(?:[A-Z][\w.&'’-]*\s+){0,3}"
    r"(?:News|Times|Post|Herald|Journal|Tribune|Cable|Wire|Bulletin|Observer|"
    r"Gazette|Globe|Sun|Star|Mail|Express|Telegraph|Independent|Standard|"
    r"Chronicle|Review|Today|Press|Agency|Daily|Weekly|Monitor|Dispatch|"
    r"Pioneer|Examiner|Sentinel|Ledger|Recorder|Courier|Beacon|Network)\s*$"
)


def _clean_title(title: str) -> str:
    """Strip wire prefixes, source attribution, and junk from a title."""
    title = _WIRE_PREFIX_RE.sub("", title).strip()
    for _ in range(2):
        title = _ATTRIBUTION_SUFFIX_RE.sub("", title).strip()
        title = _OUTLET_WORD_SUFFIX_RE.sub("", title).strip()
        title = _CAMEL_OUTLET_SUFFIX_RE.sub("", title).strip()
        title = _ACRONYM_SUFFIX_RE.sub("", title).strip()
        title = _DOMAIN_SUFFIX_RE.sub("", title).strip()
    title = title.strip(" \t\n\r-–—|")
    # Final deterministic pass for the suffix/prefix/epithet shapes the O6
    # whitelist above misses (Euractiv, Focus Taiwan, Cyrillic outlets,
    # INSIGHT:/Exclusive,/Devastating:/epithet leads). Idempotent.
    return normalize_headline(title)


def _mostly_ascii(text: str, threshold: float = 0.7) -> bool:
    """True if >= threshold of the alphabetic chars are ASCII (Latin script).

    Used to prefer an English-language headline over a co-clustered foreign
    one when both are present (the English feed should not surface an
    untranslated Spanish/Arabic headline)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    ascii_letters = sum(1 for c in letters if ord(c) < 128)
    return ascii_letters / len(letters) >= threshold


# Content-word stopwords for headline-keyword overlap (O4 on-topic summary
# selection + O9 cluster coherence). Kept local and lightweight (no spaCy).
# NOTE: named distinctly from Phase 3's _TITLE_STOPWORDS — a previous same-name
# redefinition further down silently clobbered this set at call time, letting
# filler words ("latest", "world", "update") count as content keywords.
_HEADLINE_CONTENT_STOPWORDS = frozenset("""the a an of in on at to for and or but with from by as is are was were be
been this that these those it its their his her our your my we they you he she them us i over under after
before during into out up down off about above below between through against amid new news say says said
will would could should may might can has have had do does did not no nor so than then here there what
which who whom whose when where why how all any both each few more most other some such only own same too
very just also back even still way get got make made latest live update updates day days week year years
world cup over into onto amid says said report reports""".split())


def _title_keywords(text: str) -> set[str]:
    """Lowercased content-word tokens (length >= 4, minus stopwords) from a
    headline. Used to decide whether two headlines are about the same story."""
    toks = re.findall(r"[A-Za-z][A-Za-z']{3,}", (text or "").lower())
    return {t for t in toks if t not in _HEADLINE_CONTENT_STOPWORDS}


def topic_coherence(title: str, articles: list[dict]) -> float:
    """Fraction of member-article titles that share a content keyword with the
    cluster headline. 1.0 = every member on-topic, low = over-merged bag.

    Stored on the cluster and read by the ranker (O9) to discount the source
    count of incoherent clusters. Returns 1.0 for clusters too small/title-less
    to assess (no penalty)."""
    kw = _title_keywords(title)
    if not kw or not articles:
        return 1.0
    on = sum(1 for a in articles if kw & _title_keywords(a.get("title", "") or ""))
    return on / len(articles)


def _build_document(article: dict) -> str:
    """Build a TF-IDF document from title + first 500 words of full_text.

    2026-05-31 — synonym aliases (DRC↔Congo, UK↔Britain, "Donald Trump"↔Trump)
    are normalised here, before TF-IDF vectorisation. This subsumes the
    old Phase 2.55 merge pass: TF-IDF cosine similarity between a "DRC"
    article and a "Congo" article rises automatically because both
    documents now share the same canonical token.
    """
    title = article.get("title", "") or ""
    full_text = article.get("full_text", "") or ""
    words = full_text.split()[:500]
    body_snippet = " ".join(words)
    doc = f"{title} {body_snippet}".strip().lower()
    # Apply synonym normalisation in the order longest-first so that
    # multi-word phrases ("democratic republic of congo") match before
    # their single-token aliases ("congo").
    for surface, canonical in _SYNONYM_NORMALISATION:
        doc = doc.replace(surface, canonical)
    return doc


# Canonical-form mapping derived from the old Phase 2.55 SYNONYM_PAIRS list.
# Tuples are (surface, canonical) and applied in document order via simple
# substring replacement on the lowercased document text. Order matters:
# longer surface forms must be listed BEFORE their shorter aliases so a
# multi-word match doesn't get fragmented by an earlier single-token rule.
_SYNONYM_NORMALISATION: list[tuple[str, str]] = [
    # Multi-word geographic / political phrases (must come first)
    ("democratic republic of congo", "drc"),
    ("united kingdom", "uk"),
    ("united states", "us"),
    ("north korea", "north-korea"),
    ("south korea", "south-korea"),
    # Single-token aliases
    ("congo", "drc"),
    ("burma", "myanmar"),
    ("britain", "uk"),
    ("emirates", "uae"),
    ("dprk", "north-korea"),
    ("rok", "south-korea"),
    # Name variants — full name → surname so TF-IDF tokenisation aligns
    ("donald trump", "trump"),
    ("joe biden", "biden"),
    ("vladimir putin", "putin"),
    ("xi jinping", "xi"),
]


# ---------------------------------------------------------------------------
# Cluster title / summary generation
# ---------------------------------------------------------------------------

# P0-6 (2026-08-11) — contested-policy headline neutrality. The cluster title is
# EXTRACTIVE: _generate_cluster_title picks the best member headline. On
# contested-policy stories (abortion, immigration, gun policy, gender-related
# legislation) member outlets phrase the SAME procedural event with opposed
# advocacy framing ("Allows Abortion Through All Nine Months of Pregnancy" vs
# the neutral "Removes 24-Week Gestational Limit"). When the topic is contested,
# candidate headlines carrying a loaded/advocacy construction are PENALISED and
# ones using neutral procedural/legal construction are PREFERRED, so the feed
# surfaces the least-loaded existing headline. This only RE-RANKS the extractive
# candidates; it never fabricates a headline. The lexicon is deliberately
# SYMMETRIC — it neutralises both left-loaded and right-loaded phrasings.
_CONTESTED_POLICY_TOPICS = (
    "abortion", "reproductive", "immigration", "immigrant", "migrant",
    "deportation", "deport", "asylum", "border",
    "gun", "firearm", "assault weapon", "second amendment",
    "transgender", "trans ", "gender-affirming", "gender affirming",
    "gender identity", "puberty blocker",
)
# Loaded / advocacy phrasings, both directions. Substring-matched on the
# lowercased headline (all entries are specific enough that they only appear in
# an advocacy frame). Right-loaded and left-loaded terms are BOTH listed so the
# penalty is symmetric.
_LOADED_HEADLINE_PHRASES = (
    # abortion — right-loaded
    "through all nine months", "all nine months", "nine months of pregnancy",
    "partial-birth", "partial birth", "born alive", "born-alive",
    "baby killing", "baby-killing", "kill babies", "abortion on demand",
    "abortion up to birth", "up to birth", "dismemberment abortion",
    # abortion — left-loaded
    "forced birth", "forced-birth", "forced pregnancy", "forced-pregnancy",
    "war on women", "handmaid", "reproductive slavery", "abortion ban zealots",
    # immigration — right-loaded
    "illegals", "illegal aliens", "amnesty", "open borders", "open-borders",
    "anchor baby", "anchor babies", "invasion", "criminal aliens", "invaders",
    # immigration — left-loaded
    "kids in cages", "caged children", "concentration camp", "kidnapping migrants",
    "ethnic cleansing", "mass deportation machine",
    # guns — right-loaded
    "gun grab", "gun-grab", "confiscation", "tyranny", "jackbooted",
    # guns — left-loaded
    "weapons of war", "weapon of war", "gun lobby bloodbath", "blood money",
    "child killing machine",
    # gender — right-loaded
    "mutilation", "genital mutilation", "chemical castration", "castrate",
    "grooming", "groomers", "sterilizing children", "trans agenda",
    # gender — left-loaded
    "erasing trans", "trans genocide", "eradicate transgender", "hateful ban",
)
# Neutral procedural / legal construction cues — PREFERRED on contested topics.
# Word-boundary matched.
_PROCEDURAL_HEADLINE_CUES = (
    "removes", "remove", "repeals", "repeal", "amends", "amend", "amended",
    "legalizes", "legalize", "legalise", "legalises", "bans", "ban", "banned",
    "restricts", "restrict", "restricted", "limit", "limits", "gestational",
    "lifts", "lift", "overturns", "overturn", "strikes down", "struck down",
    "enacts", "enact", "passes", "passed", "signs", "signed", "vetoes", "vetoed",
    "expands", "expand", "narrows", "narrow", "codifies", "codify", "rules",
    "upholds", "uphold", "blocks", "block", "approves", "approve", "authorizes",
    "authorize", "prohibits", "prohibit", "requires", "require",
)
_CONTESTED_LOADED_PENALTY = 4.0   # per loaded phrase present
_CONTESTED_PROCEDURAL_BONUS = 2.0  # per procedural cue (capped at 2)


def _generate_cluster_title(articles: list[dict]) -> str:
    """Pick the most representative headline across articles in a cluster."""
    raw_titles = [a.get("title", "") or "" for a in articles]
    cleaned_titles = [_clean_title(t) for t in raw_titles]
    valid_titles = [t for t in cleaned_titles if len(t) >= 15]

    if not valid_titles:
        nlp = get_nlp()
        ent_counter: Counter = Counter()
        for article in articles[:20]:
            t = article.get("title", "") or ""
            s = article.get("summary", "") or ""
            doc = nlp(f"{t} {s}"[:5000])
            for ent in doc.ents:
                if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT"):
                    ent_counter[ent.text] += 1
        top = [name for name, _ in ent_counter.most_common(3)]
        return ", ".join(top) if top else "Developing Story"

    if len(valid_titles) == 1:
        return _sanitize_editorial(valid_titles[0])

    # Score titles by entity coverage + length sweet spot
    nlp = get_nlp()
    ent_counter: Counter = Counter()
    for article in articles[:20]:
        doc = nlp(article.get("title", "") or "")
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "NORP"):
                ent_counter[ent.text.lower()] += 1
    top_entities = (
        {name for name, c in ent_counter.most_common(5) if c >= 2}
        if ent_counter else set()
    )

    # P0-6: is this a contested-policy story? Detected once over the pooled
    # candidate headlines (word-boundary), then used to gate the loaded-phrase
    # penalty / procedural-cue bonus below.
    _pooled_lower = " ".join(valid_titles).lower()
    _contested_policy = any(
        re.search(rf"\b{re.escape(kw.strip())}", _pooled_lower)
        for kw in _CONTESTED_POLICY_TOPICS
    )

    def _score(title: str) -> float:
        score = 0.0
        length = len(title)
        if 40 <= length <= 120:
            score += 3.0
        elif 20 <= length < 40:
            score += 1.5
        elif 120 < length <= 160:
            score += 2.0
        elif length < 20:
            score += 0.5
        if top_entities:
            tl = title.lower()
            score += sum(1 for e in top_entities if e in tl) * 2.0
        if title.endswith("?"):
            score -= 1.0
        if title.isupper():
            score -= 2.0
        if any(w in title.lower() for w in (
                "you won't believe", "shocking", "this is why", "here's what")):
            score -= 1.5
        if ": " in title or " - " in title:
            score += 0.5
        # P0-6: on contested-policy topics, penalise advocacy/loaded phrasing
        # and prefer neutral procedural/legal construction. Only re-ranks the
        # existing extractive candidates; never fabricates a headline.
        if _contested_policy:
            tl2 = title.lower()
            loaded_hits = sum(1 for p in _LOADED_HEADLINE_PHRASES if p in tl2)
            score -= _CONTESTED_LOADED_PENALTY * loaded_hits
            proc_hits = sum(
                1 for p in _PROCEDURAL_HEADLINE_CUES
                if re.search(rf"\b{re.escape(p)}", tl2)
            )
            score += _CONTESTED_PROCEDURAL_BONUS * min(proc_hits, 2)
        return score

    scored = [(t, _score(t)) for t in valid_titles]
    scored.sort(key=lambda x: x[1], reverse=True)
    # Prefer the highest-scoring English (Latin-script) headline so the feed
    # never surfaces an untranslated foreign-language title when an English
    # member exists; fall back to the top score if all are non-Latin. (O6)
    best = next((t for t, _ in scored if _mostly_ascii(t)), scored[0][0])
    return _sanitize_editorial(best)


def _generate_cluster_summary(articles: list[dict], title: str = "") -> str:
    """Pick the longest substantive member summary, preferring members that are
    on-topic with the cluster headline.

    On an over-merged cluster the longest member excerpt is frequently from an
    off-topic article (headline says "heatwave", the longest summary is about an
    archaeology dig). Restricting the candidate pool to members whose own title
    shares a content keyword with the cluster title keeps the rule-based summary
    on-topic; it widens to all members only when none qualify (or no title is
    given), preserving prior behavior for small/coherent clusters.
    (2026-06-28, Wave 2 / O4)
    """
    keywords = _title_keywords(title) if title else set()

    def _on_topic(a: dict) -> bool:
        if not keywords:
            return True
        return bool(keywords & _title_keywords(a.get("title", "") or ""))

    def _collect(min_len: int, on_topic_only: bool) -> list[str]:
        out = []
        for a in articles:
            if on_topic_only and not _on_topic(a):
                continue
            s = (a.get("summary", "") or "").strip()
            if s and len(s) >= min_len:
                out.append(s)
        return out

    # On-topic members first; widen to all members only if none qualify.
    summaries = (
        _collect(40, True) or _collect(40, False)
        or _collect(15, True) or _collect(15, False)
    )
    if summaries:
        summaries.sort(key=len, reverse=True)
        # sanitize_summary strips CMS/RSS scaffolding + mid-word truncation the
        # raw member excerpt carries (the null-tier tail ships this verbatim);
        # _sanitize_editorial then enforces the em-dash / significance rules.
        for s in summaries:
            cleaned = sanitize_summary(s)
            if len(cleaned) >= 40:
                return _sanitize_editorial(cleaned)
        return _sanitize_editorial(sanitize_summary(summaries[0]))
    # No usable summary — fall back to an on-topic title, then any title.
    for on_topic_only in (True, False):
        for a in articles:
            if on_topic_only and not _on_topic(a):
                continue
            t = (a.get("title", "") or "").strip()
            if t:
                return _sanitize_editorial(sanitize_summary(t) or t)
    return ""


# ---------------------------------------------------------------------------
# Section markers (US vs world fallback for downstream tagging)
# ---------------------------------------------------------------------------
US_MARKERS = {
    "congress", "house of representatives", "white house",
    "capitol hill", "pentagon", "state department",
    "fbi", "cia", "dhs", "fema", "epa", "fda", "sec",
    "federal reserve", "wall street", "medicare", "medicaid",
    "gop", "dnc", "rnc",
    "trump", "biden", "desantis", "pelosi", "mcconnell",
}
INTL_MARKERS = {
    "ukraine", "russia", "china", "eu ", "european union", "nato",
    "middle east", "gaza", "israel", "iran", "north korea", "un ",
    "united nations", "world bank", "imf", "brics",
    "africa", "asia", "latin america", "pacific",
    "india", "japan", "south korea", "taiwan", "syria",
    "saudi arabia", "turkey", "brazil", "mexico",
    "minister", "parliament", "european", "beijing", "moscow",
    "kiev", "kyiv", "jerusalem", "tehran", "kabul",
    "g7", "g20", "world cup", "olympics",
    "prime minister", "chancellor", "monarchy",
    "hong kong", "myanmar", "afghanistan", "iraq", "yemen",
    "sudan", "somalia", "ethiopia", "nigeria", "kenya",
    "australia", "new zealand", "philippines", "indonesia",
    "pakistan", "bangladesh", "sri lanka", "vietnam",
}


def _determine_section(articles: list[dict], cluster_title: str = "",
                       cluster_summary: str = "") -> str:
    """Always return "world" (2026-06-02 collapse-editions).

    void --news ships a single daily feed. The section field is preserved
    as a constant string for downstream defensive code that still reads
    `cluster.section` or filters `sections @> ['world']`, but it no longer
    has discriminative meaning. The args are accepted to keep the existing
    call-site signatures stable.
    """
    return "world"


# ---------------------------------------------------------------------------
# Phase 2: IDF-weighted entity merge
# ---------------------------------------------------------------------------

# Tokens spaCy emits as entities that carry no merge signal. Kept tight —
# the IDF math is the primary defence against generic-entity over-merging.
# Anything that survives both this stop-set AND a meaningful IDF score is
# considered a strong signal.
# Tokens spaCy emits as entities that carry no merge signal. Kept tight —
# the IDF math is the primary defence against generic-entity over-merging.
# Anything that survives both this stop-set AND a meaningful IDF score is
# considered a strong signal.
_ENTITY_STOP_TOKENS = frozenset({
    "us", "u.s.", "u.s",
    "the", "an", "a",
    "today", "yesterday", "tomorrow", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    # 2026-05-24 production audit — publisher-name token bridge bug.
    # Cluster a61aa38d ("News Outlets Cover Local Business...") merged
    # 80 articles from 7 sources (Oman Observer, Samoa Observer, Raleigh
    # News & Observer, Kashmir Observer, Charlotte Observer, Fayetteville
    # Observer) because spaCy NER picked up "Observer" from article bylines
    # / breadcrumb URLs / footer copyright lines and treated it as a high-
    # IDF anchor entity. The token appears in 30+ publisher names across
    # data/sources.json. Same risk: "Times", "Post", "Herald", "Tribune",
    # "Journal", "Gazette", "Telegraph", "Chronicle", "Mail", "Express",
    # "Daily", "Sun", "Globe", "Monitor", "Bulletin", "Register", "News".
    # Excluding these from anchor entity candidacy kills the 80-article
    # false-merge without affecting genuine event names (Hagibis, Silina,
    # Ouagadougou, etc. — those are PERSON / GPE proper nouns spaCy still
    # extracts cleanly).
    "observer", "times", "post", "herald", "tribune", "journal", "gazette",
    "telegraph", "chronicle", "mail", "express", "daily", "sun", "globe",
    "monitor", "bulletin", "register", "news", "media", "broadcasting",
    "wire", "newswire", "press", "report", "review", "weekly", "today",
    "online", "digital", "edition", "network", "channel",
    # 2026-08-05 production audit — masthead-name token bridges (same class
    # as "Observer" above). A "The Virginian-Pilot - The Virginian-Pilot"
    # doubled-masthead cluster (pos 52, 49 arts) formed because spaCy tagged
    # the masthead as an ORG anchor across every article that carried the
    # publisher's name in a byline / breadcrumb / footer. These words appear
    # in dozens of US/regional publisher names in data/sources.json and are
    # never a distinguishing event entity.
    "virginian-pilot", "virginian", "pilot", "sentinel", "dispatch",
    "courier", "advertiser", "ledger", "enquirer", "examiner",
    "standard", "record", "star", "beacon", "inquirer", "picayune",
    "clarion", "advocate",
    # Often-occurring source-byline / copyright phrases
    "staff", "writer", "correspondent", "reporter", "editor",
    # 2026-05-31 simplification — moved here from _LOW_SPECIFICITY_ENTITIES
    # (which was deleted with the Phase 2 revert). Generic government
    # VENUES and AGENCIES appear in many unrelated political stories and
    # would over-merge under the simple set-intersection rule:
    # us-1a (Trump rally) shares {White House, Treasury, Bessent} with
    # us-3a (Fed Chair Warsh) and us-5a (NYC mayor budget) even though
    # those are three unrelated stories. Stop-list these venues so they
    # never count toward the 3-entity gate. Country names and politician
    # names are NOT stop-listed — they ARE distinguishing when shared
    # across multi-desk coverage of one event (Trump-Iran consolidation).
    "white house", "kremlin", "downing street", "elysee",
    "congress", "senate", "house", "parliament", "supreme court",
    "treasury", "us treasury", "pentagon", "state department",
    "fbi", "cia", "doj", "justice department",
    "fed", "federal reserve", "wall street",
    "european commission", "european council", "european union",
    "nato", "un", "united nations",
    # Wire-service names — appear as bylines / "Reuters reported" stubs
    # across many unrelated stories. Filtering as stop tokens prevents
    # cross-story bridges via shared wire attribution.
    "reuters", "ap", "associated press", "bloomberg", "afp", "dpa",
    "bbc", "cnn", "fox news", "wall street journal", "nytimes",
    "the new york times", "washington post", "guardian",
    # Generic stub words
    "newsmax",
})

# Entities that appear in such a high baseline rate across world-news
# coverage that their per-fixture IDF over-states their distinguishing
# power. They get a weight multiplier of 0.4 in the merge score, so an
# overlap of {trump, white house, treasury, senate} no longer triggers
# a same-story merge between unrelated US-government clusters. The list
# is intentionally focused — only entities we've seen cause cross-story
# bridges in the validation suite.
_LOW_SPECIFICITY_ENTITIES = frozenset({
    # Heads of major governments — appear in dozens of unrelated stories
    "trump", "biden", "obama", "harris", "vance",
    "putin", "xi jinping", "xi", "modi", "starmer", "macron",
    "scholz", "merz", "netanyahu", "lula",
    # Geopolitical hot-spot countries — appear in many unrelated stories
    # via wire desk reactions ("Iran said...", "China called for...") and
    # cause transitive bridges between unrelated regional events.
    "iran", "iranian", "tehran",
    "china", "chinese", "beijing",
    "russia", "russian", "moscow", "kremlin",
    "ukraine", "ukrainian", "kyiv",
    "israel", "israeli", "jerusalem",
    "india", "indian", "new delhi",
    "brazil", "brazilian", "sao paulo",
    "japan", "japanese", "tokyo",
    "germany", "german", "berlin",
    "france", "french", "paris",
    "uk", "u.k.", "united kingdom", "britain", "british", "london",
    "europe", "european",
    "africa", "african",
    # Generic government / institution shells
    "white house", "kremlin", "downing street", "elysee",
    "congress", "senate", "house", "parliament", "supreme court",
    "treasury", "us treasury", "pentagon", "state department",
    "fbi", "cia", "doj", "justice department",
    "fed", "federal reserve", "wall street",
    "european commission", "european council", "european union",
    "nato", "un ", "united nations",
    # Wire-service self-references (always appear, never distinguishing)
    "reuters", "ap", "associated press", "bloomberg", "afp", "dpa",
    "bbc", "cnn", "fox news", "wall street journal", "nytimes",
    "the new york times", "washington post", "guardian",
})
_LOW_SPECIFICITY_WEIGHT = 0.4

# Phase 2 distinguishing-shared gate. After the total entity-overlap gate
# passes, the shared set must still contain >= this many SPECIFIC entities
# once generic ones (_LOW_SPECIFICITY_ENTITIES + _ENTITY_STOP_TOKENS) are
# removed. Generic entities alone (e.g. {obama, court, ruling, washington}
# bridging an unrelated SCOTUS story and an Obama story) must not trigger a
# merge. Set-membership only — NOT the IDF-math scheme reverted 2026-05-31.
# 2026-06-28 (Wave 3 / O2 evaluated, REVERTED): raising this to 2 rejected
# one-entity coincidental bridges but also broke a legitimate loose-window merge
# (trump-xi-loose fixture: Trump-Xi summit articles share one strong entity).
# The Phase-1 tightening (O1) already curbs the over-merge, so this stays at 1.
MIN_DISTINGUISHING_SHARED = 1

# Phase 2 cross-topic sanity floor (2026-08-04). merge_related_clusters unions
# purely on entity overlap with NO content-similarity requirement — the only
# main-path merge that lacks the stemmed-title-Jaccard guard that Phases 2.55
# and 2.6 both carry. A SINGLE coincidental or roundup-bridged entity (e.g. a
# "news in brief" member article injecting "Flagstar"/"Senate" into a Korea
# heatwave cluster's entity set) can therefore union two topically-disjoint
# stories. 2026-08-04 production: a "South Korea Heatwave Deaths Rise to 19"
# cluster absorbed a Flagstar Bank 2021 data-breach story AND a US Senate-panel
# story, all three stitched into one summary.
#
# Guard: EVERY entity-overlap merge must clear a MINIMAL stemmed-title overlap
# (the two clusters must name the same story). The floor is deliberately far
# below Phase 3's TITLE_JACCARD_THRESHOLD (0.22) so genuine multi-desk title
# diversity is not refused — it only rejects the near-zero overlap of a
# genuinely cross-topic bridge.
#
# 2026-08-10 (editorial-audit 1b): PHASE2_STRONG_DISTINGUISHING (the old
# "2+ shared distinguishing entities waive the title check" bypass) is RETIRED.
# It was the specific hole that let two GPEs bridge unrelated same-region events
# (two Assam stories, two Trump items) straight past the only content check.
# The title floor now applies to all bridges with no exception, so the constant
# is no longer read anywhere; it is kept defined at its historical value purely
# so any external import does not break.
PHASE2_STRONG_DISTINGUISHING = 2      # RETIRED 2026-08-10 (no longer read; see note)
PHASE2_TITLE_SANITY_FLOOR = 0.08      # every entity bridge must clear this

# Data-driven common-word over-merge guard (2026-08-07, CEO-directed). A shared
# entity may only DRIVE a Phase-2 merge when it is DISCRIMINATIVE: its document-
# frequency across the day's post-Phase-1 clusters is low. A generic word (an
# institution like "military" / "supreme court", a bare country/nationality
# name, or ANY future high-frequency term such as "summit" / "election" /
# "festival") has high df BY DEFINITION and therefore can never be the sole
# merge driver — no hand-maintained stop-list required.
#
# 2026-08-10 (SCALE-STABLE FIX, editorial-audit 1b). The prior bound was
# `max(5, int(n * 0.05))`. At production scale (n ~= 1,945 post-Phase-1
# clusters on the 2026-08-10 run) that collapsed to `max(5, 97) = 97`, so an
# entity counted as discriminative unless it appeared in >97 clusters. Ordinary
# GPEs that HOST several distinct same-region stories then qualified as rare
# anchors and bridged unrelated events: Assam (df 5: a border-firing AND a
# flood AND state politics), Kazakhstan (df 6: Comic Con AND finance AND a
# tiger release), South Africa (df 10, the Cape Town bag), Hong Kong (df 10).
# The measured df split is unambiguous: genuinely story-specific anchors on the
# same run sit at df 2-3 (Nizhnekamsk 2, Tatarstan 3, Rezaei 3, Kumamoto 3,
# Banerjee 2, Andhra 2) while multi-story GPEs sit at df 5-10. A story-specific
# named entity appears only in the handful of clusters covering its one event,
# so its ABSOLUTE df stays small (2-4) at ANY corpus size; a region/institution
# that hosts many stories has df that grows with news volume. A FIXED small df
# cap is therefore genuinely scale-stable, whereas the old `n * 0.05` term made
# "discriminative" mean "in up to 5% of all clusters" (~97 at scale).
#
# IDF (log(N/df)) was considered and REJECTED: on this corpus the contaminating
# GPEs (df 5-10 of N=1,945) score IDF 5.3-6.0 — HIGH IDF — so an IDF threshold
# would still admit them. Corpus-rarity is the wrong axis; absolute df is right,
# because the defect is entities shared across a FEW distinct stories, not
# entities that are globally common. Hence a fixed absolute df cap.
PHASE2_ANCHOR_DF_ABS = 3              # discriminative iff df <= this (fixed, scale-stable)


# ---------------------------------------------------------------------------
# Canonical summit / known co-occurrence pairs
# ---------------------------------------------------------------------------
# Editorial override for known high-frequency political pair-events that
# the IDF formula systematically under-weights (each name appears in many
# unrelated clusters individually, deflating their idf). When two clusters
# both carry BOTH names from a pair AND fall within the merge time window,
# they are the same story by editorial fiat.
#
# Production failures motivating this list (audit 2026-05-15):
#   - Trump-Xi summit fragmented into 4 clusters (#5/#15/#17/#43)
#   - Starmer + Streeting fragmented into 2 clusters (#6 + #44)
#
# Keep the list short and intentional. Each entry must be a known
# bilateral / governance pair where every appearance in production news
# refers to the same underlying event-stream.
_SUMMIT_PAIRS = frozenset({
    # Heads-of-state diplomatic pairs (G2 / G7 / bilateral)
    frozenset({"trump", "xi"}),
    frozenset({"trump", "putin"}),
    frozenset({"trump", "modi"}),
    frozenset({"trump", "netanyahu"}),
    frozenset({"trump", "zelensky"}),
    frozenset({"biden", "xi"}),
    frozenset({"biden", "putin"}),
    frozenset({"biden", "netanyahu"}),
    frozenset({"biden", "zelensky"}),
    frozenset({"xi", "putin"}),
    # UK government internal — known fragmenters in 2026-05 audit
    frozenset({"starmer", "streeting"}),
    frozenset({"starmer", "reeves"}),
    # Israel / regional pairs
    frozenset({"netanyahu", "putin"}),
    # Ukraine / Russia
    frozenset({"zelensky", "putin"}),
})


# ---------------------------------------------------------------------------
# Phase 2.55: Synonym-pair merge (DRC↔Congo, UK↔Britain, etc.)
# ---------------------------------------------------------------------------
# Geographic + name aliases that must collapse to one cluster when both
# surface forms reference the same place / person. Each tuple is a
# symmetric pair: if cluster A's surface set contains entity X AND cluster
# B's set contains entity Y AND (X, Y) in SYNONYM_PAIRS, the clusters
# reference the same underlying entity.
#
# Production failures motivating this list (audit 2026-05-15):
#   - "Africa CDC Confirms Ebola Outbreak in DRC" (9 src) NOT merged with
#     "Africa CDC Confirms Ebola Outbreak in Congo" (7 src) — same event.
#
# A safety guard (stemmed-title Jaccard ≥ SYNONYM_TITLE_JACCARD_FLOOR)
# is applied alongside the surface match so that two unrelated stories
# both mentioning {DRC, Congo} with no other story-similarity (e.g.,
# "DRC mining sector" vs "Congo Brazzaville politics") stay split.
SYNONYM_PAIRS = frozenset({
    # Country / region aliases
    ("drc", "congo"), ("drc", "democratic republic of congo"),
    ("myanmar", "burma"),
    ("uk", "britain"), ("uk", "united kingdom"),
    ("us", "america"), ("us", "united states"),
    ("uae", "emirates"),
    ("north korea", "dprk"),
    ("south korea", "rok"),
    # Common name variants
    ("biden", "joe biden"),
    ("trump", "donald trump"),
    ("putin", "vladimir putin"),
    ("xi", "xi jinping"),
})
SYNONYM_TITLE_JACCARD_FLOOR = 0.20


# ---------------------------------------------------------------------------
# Phase 2.6: Anchor-entity merge (high-IDF rare proper nouns)
# ---------------------------------------------------------------------------
# A high-IDF rare proper noun (e.g., "Evika Siliņa", "Ouagadougou", a
# specific MP name) shared across two clusters within the merge time
# window is strong enough merge evidence on its own — even when the
# canonical/synonym pair lists don't enumerate the entity and the IDF
# sum doesn't cross ENTITY_MERGE_IDF_THRESHOLD.
#
# Production failure motivating this pass (audit 2026-05-15):
#   - Latvian PM resignation (30+ LSM articles) fragmented into 5
#     single-source clusters, none cracking top 50. All clusters share
#     the rare entity "Siliņa" — this pass collapses them.
#
# Tunables:
#   ANCHOR_IDF_FRACTION_OF_MAX  — entity must score ≥ this fraction of
#                                 the corpus max IDF to qualify as anchor.
#                                 0.60 picks up entities that appear in 5-10
#                                 clusters out of 200 in production (Silina
#                                 case) while still excluding common bridges.
#   ANCHOR_MAX_DOC_FREQ_FLOOR   — absolute df cap (≤3 clusters always
#                                 qualifies regardless of corpus size).
#   ANCHOR_MAX_DOC_FREQ_PCT     — relative df cap (≤ this fraction of
#                                 corpus). The OR of the two caps is the
#                                 effective gate, so small corpora use the
#                                 absolute floor and large corpora use the
#                                 percentage gate.
#   ANCHOR_MIN_SHARED           — minimum number of shared anchor entities
#                                 required to fire the merge. ≥2 blocks
#                                 single-bridge merges (e.g. Warsh+Trump-Xi
#                                 sharing only "Bessent") while still
#                                 surfacing Silina (which shares both
#                                 "silina" and "latvian"/"riga"/"saeima").
#   ANCHOR_TITLE_JACCARD_FLOOR  — stemmed-title Jaccard floor on the
#                                 candidate pair (safety vs. accidental
#                                 entity collisions like "Boryspil"-the-
#                                 airport vs "Boryspil"-the-football-match)
# 2026-05-17 retune for production scale (N≈200 clusters/day). The
# original constants were validated against the 21-fixture synthetic
# suite (N≤6 per fixture). At production scale, `df ≤ max(3, 0.05·N)
# = 10` was too permissive: any entity appearing in 10 of 200 clusters
# (e.g. "regulation", "policy", "AI deployment") qualified as a rare
# anchor and bridged unrelated stories via union-find transitive closure.
# Result: 217-source AI-deployment mega-cluster. New constants tighten:
#   • require stronger IDF (0.70 of corpus max, was 0.60)
#   • require rarer entity (≤2.5% of corpus, was 5%)
#   • require stronger title agreement (Jaccard 0.22, was 0.15)
ANCHOR_IDF_FRACTION_OF_MAX = 0.70
ANCHOR_MAX_DOC_FREQ_FLOOR = 3
ANCHOR_MAX_DOC_FREQ_PCT = 0.025  # ≤ 2.5% of corpus (5 clusters at N=200)
ANCHOR_MIN_SHARED = 2            # require ≥2 shared anchors to merge
ANCHOR_TITLE_JACCARD_FLOOR = 0.22
# 2026-05-25 — DO NOT lower this without a compensating gate. Lowering
# to 0.18 chained transitively across unrelated stories: a 362-source
# / 3,217-article cluster bundled Nigeria politics + Spain courts +
# Scottish level crossings + Pakistan + Israel + Senegal PM + Ebola +
# Toronto biz + Delhi exams + Smithfield Times into one bucket because
# the lower floor allowed Phase 2.6 anchor matches with weak title
# overlap, then transitive closure across many such hops aggregated
# entire continents of news. The 0.22 floor is the floor — if you need
# to merge a wire-style scatter (e.g., Pakistan train bombing in 5
# clusters), add it to _CANONICAL_PAIRS / _SYNONYM_ALIASES instead.

# Garbage cluster-title signatures (Fix 2 — over-merge force-split).
# When the title-generator emits one of these, the cluster has aggregated
# unrelated sub-events sharing a single GPE or NORP, and we must split it.
# Each pattern targets a real production failure mode:
#   - "X Spans <list> and Y" — multi-event mash-up under one entity
#   - "Diplomatic ... Activity Spans" — UK celeb / Italy umbrella over-merge
#   - "Cluster Spans" — the title-generator literally writes "Cluster"
_GARBAGE_TITLE_PATTERNS = [
    # "Spans Deaths, Weddings, and Bond Casting" / "Spans Four Continents"
    # Separator accepts ", and " (Oxford comma) so 3-item Spans-lists match.
    re.compile(
        r"\bSpans\s+(?:[A-Z][A-Za-z]+(?:,\s*(?:and\s+)?|\s+and\s+)){2,}[A-Z][A-Za-z]+",
    ),
    # "Italy Diplomatic Activity Spans..." / "Diplomatic and Cultural Activity Spans..."
    re.compile(
        r"\b(?:Diplomatic|Cultural|Political|Economic)\s+"
        r"(?:and\s+\w+\s+)?Activity\s+Spans\b",
        re.IGNORECASE,
    ),
    # Explicit "Cluster Spans" — title-generator gave up
    re.compile(r"\bCluster\s+Spans\b", re.IGNORECASE),
    # "News Cluster Spans" / "Coverage Spans Multiple"
    re.compile(r"\b(?:News\s+)?Cluster\s+Spans\b", re.IGNORECASE),
    re.compile(r"\bCoverage\s+Spans\s+(?:Multiple|Many|Several)\b", re.IGNORECASE),
    # New 2026-05-15 production-audit signatures:
    # "Three Unrelated Crime Stories Span UK, Canada, Cambodia"
    # — explicit self-admission of garbage.
    re.compile(r"\b(?:Two|Three|Four|Five|\d+)\s+Unrelated\b", re.IGNORECASE),
    # Title joined by semicolon — two clauses describing different events.
    # Safety: split is force-discarded if stricter re-cluster collapses to 1
    # (already handled by _force_split_cluster's final guard).
    re.compile(r"^[^;]{20,}\s*;\s*[A-Z][^;]{20,}$"),
    # "Stories Span" / "Reports Span" / "Events Span" — variant of "Spans X"
    re.compile(
        r"\b(?:Stories|Reports|Events|News|Cases|Incidents)\s+Span\b",
        re.IGNORECASE,
    ),
    # Mega-cluster signatures from "AI Deployment Expands Across Industries
    # Amid Legal and Reliability Debates" (267-source bucket, 2026-05-15
    # CEO-spotted at homepage #2).
    # "Expands Across Industries" / "Spreads Across Continents"
    re.compile(
        r"\b(?:Expands|Spreads)\s+Across\s+"
        r"(?:Industries|Sectors|Continents|Regions|Borders)\b",
        re.IGNORECASE,
    ),
    # "Amid Legal and Reliability Debates" / "Amid Political and Economic Concerns"
    re.compile(
        r"\bAmid\s+(?:Legal|Regulatory|Political|Economic)\s+and\s+\w+\s+"
        r"(?:Debates|Concerns|Tensions|Questions)\b",
        re.IGNORECASE,
    ),
    # 2026-05-24 production audit — broadened from semicolon-only to
    # catch additional self-admitting "this is a mash-up" patterns that
    # the Gemini fallback title-generator produces when handed an over-
    # merged cluster.
    #
    # Today's top-10 false-merge titles that the existing patterns missed:
    #   - "Multiple Car Crashes Across Regions Cause Injuries and One Fatality"
    #   - "Arms Recovered in Chhattisgarh; Wildlife Smugglers Arrested; Oregon Police Kill Bear"
    #   - "News Outlets Cover Local Business, Sports, Weather, and Diplomacy"
    #   - "The Spectator Publishes Diverse Commentary on Politics, Culture, and Society"
    #   - "HuffPost Publishes Lifestyle Advice; Economist Critiques Western Statue"
    re.compile(
        r"^(?:Multiple|Various|Several|Numerous|Different)\s+\w+\s+"
        r"(?:Across|Reported|Cause|Strike|Hit|Occur|Reveal|Show|Spread)",
        re.IGNORECASE,
    ),
    re.compile(r"\bAcross\s+(?:Regions|Continents|Borders|Countries|Sectors)\b", re.IGNORECASE),
    re.compile(
        r"\bNews\s+Outlets?\s+(?:Cover|Report|Publish|Discuss|Address|Examine)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:Publishes|Covers|Reports|Discusses)\s+"
        r"(?:Diverse|Various|Multiple|Wide-Ranging)\s+\w+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bCommentary\s+on\s+\w+,\s*\w+,?\s*(?:and\s+)?\w+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:Lifestyle\s+Advice|Lifestyle\s+Tips|Various\s+Topics)\b",
        re.IGNORECASE,
    ),
    # Three-clause titles joined by commas where the clauses describe
    # unrelated topics. Conservative: requires 4+ comma-separated capitalized
    # phrases. "Business, Sports, Weather, and Diplomacy". Matches 4+ item
    # capitalized lists ("X, Y, Z, [and] W"). Requires {3,} comma-separated
    # items before the final one: at {2,} this matched routine 3-item news
    # headlines ("Britain, France, Germany Trigger Sanctions...",
    # "Trump, Putin, and Zelensky to Meet...") and force-split real clusters.
    re.compile(
        r"\b([A-Z][a-z]+,\s+){3,}(?:and\s+)?[A-Z][a-z]+\b",
    ),
    # 2026-08-05 production audit — doubled-masthead title. When a cluster is
    # a publisher-name-bridged bag with no real story to headline, the title-
    # generator falls back to the masthead and emits it TWICE across a dash:
    # "The Virginian-Pilot - The Virginian-Pilot" (pos 52, 49 arts). The two
    # halves are byte-identical around the separator — a signature no genuine
    # headline produces. Backreference-anchored so only a true repeat matches.
    re.compile(
        r"^\s*(.{4,}?)\s*[-–—|]\s*\1\s*$",
    ),
]


# ---------------------------------------------------------------------------
# Phase 5: Mega-cluster soft cap (force-split + display cap)
# ---------------------------------------------------------------------------
# A cluster with source_count above MEGA_CLUSTER_THRESHOLD is suspect
# regardless of title. At production N=200+, "AI" / "Trump" / "Russia"
# have near-zero IDF and Phase 2 can bundle every tangentially-related
# story into one mega-bucket (267-source "AI Deployment Expands Across
# Industries..." 2026-05-15).
#
# Two-step response:
#   1. Force-split at AGGRESSIVE thresholds (1.8x baseline TFIDF, 2.0x
#      baseline IDF) — strictly more cautious than Phase 4's force-split.
#   2. If the stricter pass still produces 1 sub-cluster (genuine
#      breaking news mega-event), KEEP it but cap the displayed
#      source_count at MEGA_CLUSTER_THRESHOLD and stamp
#      `mega_cluster_capped=True` so the ranker can deprioritize.
MEGA_CLUSTER_THRESHOLD = 75
MEGA_SPLIT_TFIDF = 0.32   # 1.78x baseline (STORY_TFIDF_THRESHOLD = 0.18)
MEGA_SPLIT_IDF = 4.0      # 2.0x baseline (ENTITY_MERGE_IDF_THRESHOLD = 2.0)

# 2026-05-24 v2 — article-count cap REPLACED by cohesion-gated Phase 5.
# Constants live near the cohesion scorer (search MEGA_COHESION_FLOOR).
# The legacy MEGA_CLUSTER_THRESHOLD (source_count >= 75) remains as a
# hard ceiling for the rare 200+ source breaking-news case.

# Hard merge ceiling — refuse any merge that would produce a cluster
# larger than this. Phase 5 can still cap legitimate breaking-news
# mega-events that arrive large from Phase 1, but no merge phase
# should ever ADD to a 100-source cluster. Set above MEGA_CLUSTER_THRESHOLD
# so we don't fight Phase 5; below the 200+ pathology we're preventing.
MERGE_HARD_CEILING = 120


def _merge_load(c: dict) -> int:
    """Conservative size estimate for the merge ceiling.

    Source_count may be stale during early merge phases (before
    `_apply_wire_aware_source_count` runs), so use the larger of the
    stored count and the article count. Intentionally pessimistic — we'd
    rather miss a few legitimate merges than create a mega-cluster.
    """
    stored = int(c.get("source_count", 0) or 0)
    arts = c.get("articles", []) or []
    return max(stored, len(arts))


def _would_exceed_ceiling(a: dict, b: dict) -> bool:
    """Pairwise ceiling check on two cluster dicts.

    NOTE: NOT transitive on its own — cluster dicts are never updated on
    union(), so chained merges slip past it. The merge phases use
    _ceiling_union_find() below, which tracks accumulated load at each
    union-find root. Kept for direct two-cluster checks.
    """
    return (_merge_load(a) + _merge_load(b)) > MERGE_HARD_CEILING


def _ceiling_union_find(clusters: list[dict]):
    """Union-find whose MERGE_HARD_CEILING gate is TRANSITIVE.

    The old per-pair gate read source_count off the two ROOT CLUSTER
    DICTS, which no merge phase updates on union() — so two 60-source
    groups could chain through a third cluster and sail past the 120
    ceiling unseen. Track accumulated load at each root instead (the
    same defence merge_related_clusters applies via group_size).

    Returns (parent, find, union, would_exceed) where would_exceed(i, j)
    gates on the CURRENT accumulated group loads of i's and j's roots.
    """
    parent = list(range(len(clusters)))
    load = [_merge_load(c) for c in clusters]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            load[rb] += load[ra]

    def would_exceed(i: int, j: int) -> bool:
        return (load[find(i)] + load[find(j)]) > MERGE_HARD_CEILING

    return parent, find, union, would_exceed


_ENTITY_QUALIFIER_PREFIXES = (
    "the ", "a ", "an ",
    "president ", "vice president ", "prime minister ", "pm ",
    "chancellor ", "chairman ", "chairwoman ", "chair ",
    "secretary ", "minister ", "mr. ", "mrs. ", "ms. ", "dr. ",
    "sir ", "lord ", "lady ",
    "super ", "tropical ", "category 1 ", "category 2 ", "category 3 ",
    "category 4 ", "category 5 ",
    "former ", "ex-",
)


def _normalise_entity(text: str) -> str:
    """Lowercase + strip honorifics/qualifiers + possessive + punctuation.

    The qualifier strip aligns variants like:
        "President Trump"        -> "trump"
        "Super Typhoon Hagibis"  -> "typhoon hagibis"
        "Prime Minister Modi"    -> "modi"
    so that two articles using different honorifics land on the same key.
    """
    s = text.lower().strip()
    # Repeat once more to handle stacked qualifiers ("the former president ...")
    for _ in range(2):
        for pfx in _ENTITY_QUALIFIER_PREFIXES:
            if s.startswith(pfx):
                s = s[len(pfx):]
                break
    if s.endswith("'s") or s.endswith("’s"):
        s = s[:-2]
    return s.strip(" '\"‘’“”.,;:!?")


def _extract_cluster_entities(articles: list[dict]) -> dict[str, int]:
    """Return entity -> count from title + summary + first 1500 chars of body.

    Body inclusion (vs. title+summary alone) is what surfaces the
    distinguishing entities — Klitschko, Zelensky, Marcos, Cagayan,
    Hagibis, Fadnavis — that anchor a same-story merge. Without body,
    only generic GPEs/NORPs (Russia, Ukraine, Russian) appear and the
    IDF score collapses. The 1500-char cap balances NER cost against
    coverage: most named actors appear in the first 3-4 sentences.
    """
    nlp = get_nlp()
    counts: Counter = Counter()
    # Cap at first 10 articles to bound spaCy cost on giant clusters
    for article in articles[:10]:
        title = article.get("title", "") or ""
        summary = article.get("summary", "") or ""
        body = article.get("full_text", "") or ""
        # Body is sliced before concatenation so the title is always seen
        text = f"{title} {summary} {body[:1500]}"[:3000]
        if not text.strip():
            continue
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "NORP", "EVENT", "FAC", "LOC"):
                norm = _normalise_entity(ent.text)
                if len(norm) < 3:
                    continue
                if norm in _ENTITY_STOP_TOKENS:
                    continue
                counts[norm] += 1
    return dict(counts)


def _compute_global_idf(cluster_entities: list[dict[str, int]]) -> dict[str, float]:
    """Compute idf(e) = log(N_eff / df(e)) with corpus-prior smoothing.

    Pure within-fixture IDF collapses when an entity appears in every
    cluster of a small fixture (df = N -> log(1) = 0). To keep the
    signal stable across both fixture-scale (N ~ 6) and production-scale
    runs (N ~ 2000), we use:
        N_eff = max(N, 30)        — virtual corpus floor
        df_eff = df + ceil(N/4)   — additive smoothing
    The smoothing replaces the prior hard df_floor: every entity gets a
    prior count proportional to N/4, which damps the spread between
    truly-rare and merely-uncommon entities while preserving the
    ordering. Net effect for fixtures: an entity in 6/6 clusters gets
    idf ~ log(30/(6+2)) = 1.32 (was 0.05 with the old formula); an
    entity in 1/6 clusters gets idf ~ log(30/(1+2)) = 2.30. The signal
    is now stable enough to drive merge decisions on small N.
    """
    n = max(1, len(cluster_entities))
    n_eff = max(n, 30)
    smoothing = max(1, (n + 3) // 4)  # ~N/4 rounded up

    df: Counter = Counter()
    for ents in cluster_entities:
        for e in ents:
            df[e] += 1

    idf: dict[str, float] = {}
    for e, raw_df in df.items():
        df_eff = raw_df + smoothing
        idf[e] = max(0.05, math.log(n_eff / df_eff))
    return idf


def _parse_first_pub(cluster: dict) -> datetime | None:
    fp = cluster.get("first_published", "") or ""
    if not fp:
        return None
    try:
        dt = datetime.fromisoformat(fp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def merge_related_clusters(
    clusters: list[dict],
    min_shared_entities: int = 3,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
    max_cluster_articles: int = 50,
) -> list[dict]:
    """Phase 2: entity-overlap merge — simple set-intersection.

    REVERTED 2026-05-31 to the 2026-03-28 design (commit 5402f7d). The
    May 15 rewrite layered IDF-weighting, _LOW_SPECIFICITY_ENTITIES
    downweighting, and a distinguishing_shared >= 1 gate on top of the
    simple set-intersection. Those gates correctly prevent the 233-source
    AI-deployment chain merge but incorrectly prevent every legitimate
    Trump-X / Iran-X / China-X consolidation where the shared entities
    happen to be geopolitical hot-spots. The May 30 production case:
    Trump-Iran deal story fragmented across 5 sibling clusters of
    sc=6/4/4/3/2.

    The structural defence against chain-merges is the size cap
    `max_cluster_articles=50` on union-find, with proper size tracking
    via `group_size[rb] += group_size[ra]` on every union. That defence
    blocks the 233-source AI mega-cluster before transitive closure can
    form it, and it does so without sacrificing legitimate consolidations.

    Algorithm:
      1. For each cluster, extract its named-entity set.
      2. For each pair (i, j): if they share >= min_shared_entities AND
         their first_published timestamps are within max_age_spread_hours
         AND their accumulated group size would stay under
         max_cluster_articles, union them.
      3. Repeat over all pairs (deterministic order). Return merged.
    """
    if len(clusters) <= 1:
        return clusters

    cluster_entities: list[set[str]] = [
        set(_extract_cluster_entities(c.get("articles", [])).keys())
        for c in clusters
    ]
    timestamps = [_parse_first_pub(c) for c in clusters]
    titles = [c.get("title", "") or "" for c in clusters]

    n = len(clusters)

    # Document-frequency of every entity across the day's clusters — the
    # data-driven discriminativeness signal (see PHASE2_ANCHOR_DF_*). A
    # generic term appears in many clusters (high df); a specific named
    # entity appears in only the few that actually cover its story.
    entity_df: Counter = Counter()
    for ents in cluster_entities:
        for e in ents:
            entity_df[e] += 1
    # SCALE-STABLE: a fixed absolute df cap, independent of n (see
    # PHASE2_ANCHOR_DF_ABS note). Does not grow with corpus size, so ordinary
    # multi-story GPEs never sneak in as "rare" anchors on a busy news day.
    phase2_max_df = PHASE2_ANCHOR_DF_ABS

    parent = list(range(n))
    group_size = [len(c.get("articles", []) or []) for c in clusters]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            group_size[rb] += group_size[ra]

    for i in range(n):
        ents_i = cluster_entities[i]
        if not ents_i:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            ents_j = cluster_entities[j]
            if not ents_j:
                continue

            # Entity-overlap gate
            shared = ents_i & ents_j
            if len(shared) < min_shared_entities:
                continue

            # Distinguishing-shared gate — generic entities (world leaders,
            # hot-spot countries, institution shells) alone must not bridge two
            # stories. Require >= MIN_DISTINGUISHING_SHARED specific entities in
            # the overlap once generic ones are removed. Legitimate Trump-X /
            # Iran-X consolidations share a concrete entity (a person, place, or
            # org named in the event), so they still merge; an unrelated SCOTUS
            # and Obama cluster sharing only {obama, court, ...} does not.
            distinguishing = shared - _LOW_SPECIFICITY_ENTITIES - _ENTITY_STOP_TOKENS
            if len(distinguishing) < MIN_DISTINGUISHING_SHARED:
                continue

            # Discriminative-anchor gate (PRIMARY common-word over-merge guard,
            # data-driven). The merge must be driven by at least one
            # DISCRIMINATIVE shared entity — one whose corpus document-frequency
            # is low (high IDF). A generic institutional word, a bare country
            # name, or any future high-df term is filtered out here automatically
            # with zero hand-listing: it appears across too many clusters to be
            # the sole bridge. This is what keeps the "military" / "supreme court"
            # / "Nigeria" bags from forming.
            discriminative = {
                e for e in distinguishing
                if entity_df.get(e, 0) <= phase2_max_df
            }
            if not discriminative:
                continue

            # Cross-topic sanity floor — EVERY entity bridge must be confirmed by
            # a minimal stemmed-title overlap so a coincidental / roundup-injected
            # entity cannot union two disjoint stories.
            #
            # 2026-08-10 (editorial-audit 1b): the old code WAIVED this title
            # check whenever two or more discriminative entities were shared
            # (PHASE2_STRONG_DISTINGUISHING = 2), on the theory that two shared
            # anchors prove a same-event merge. With the loose df bound that was
            # the specific hole that bridged unrelated events: two different
            # Assam stories, or two Trump items, routinely co-share a secondary
            # named entity, so a 2-entity overlap skipped straight past the only
            # content check and merged. The bypass is removed: an entity bridge
            # NEVER substitutes for title agreement. The floor is deliberately
            # low (0.08, far below Phase 3's 0.22 TITLE_JACCARD_THRESHOLD), so a
            # genuine multi-desk consolidation — whose sibling titles still share
            # the event's core noun (e.g. "Iran"/"Hormuz", "Pentagon"/"weapons")
            # — clears it easily, while a cross-topic bridge sharing ~0 title
            # stems is refused. The df cap now doing the heavy lifting means the
            # surviving bridges are already strong; the title floor is the
            # content backstop that must always hold.
            if _stemmed_title_jaccard(titles[i], titles[j]) < PHASE2_TITLE_SANITY_FLOOR:
                continue

            # Time gate — don't merge stories far apart in time.
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            # Size gate — the structural defence against transitive
            # chain-merges. Reads accumulated group_size at each root
            # so the check sees the CURRENT merged size, not just the
            # pair members. union() maintains the invariant via
            # group_size[rb] += group_size[ra].
            if group_size[find(i)] + group_size[find(j)] > max_cluster_articles:
                continue

            union(i, j)

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Phase 2.5: Canonical-pair merge (editorial override)
# ---------------------------------------------------------------------------

def _cluster_entity_surface_set(cluster: dict) -> set[str]:
    """Lowercased, qualifier-stripped entity-surface set for one cluster.

    Used by the canonical-pair pass — we look for surface-form matches like
    "trump" / "xi" / "starmer" / "streeting" regardless of how the entity
    appears (title-cased, with title prefixes, possessive, hyphenated, etc).

    Splits on whitespace, hyphens, slashes, parentheses, and most punctuation
    so that headlines like "Trump-Xi summit" yield {trump, xi}, not
    {trump-xi}. Two-letter surnames (Xi) are intentionally allowed.

    Body cap: 3000 chars per article (loosened from 1500 on 2026-05-15 after
    Trump-Xi-Iran summit fragmented because "Xi" appeared after the lead in
    "Trump Warns Iran of Annihilation as Xi Raises Taiwan in Beijing Talks").
    Cheap regex tokenisation; no NER cost on the wider window.
    """
    surfaces: set[str] = set()
    for art in (cluster.get("articles") or [])[:10]:
        title = art.get("title", "") or ""
        summary = art.get("summary", "") or ""
        body = (art.get("full_text", "") or "")[:3000]
        text = f"{title} {summary} {body}".lower()
        # Split on any non-letter character (covers hyphens, slashes, dots,
        # quotes, punctuation, whitespace). Keep apostrophes inside words
        # but not as separators.
        for tok in re.findall(r"[a-z]+(?:'[a-z]+)?", text):
            if 2 <= len(tok) <= 20:
                surfaces.add(tok)
    return surfaces


def _cluster_surface_phrases(cluster: dict) -> set[str]:
    """Multi-word surface phrases from title + summary + body (first 3000 chars).

    Companion to `_cluster_entity_surface_set` for the synonym-pair pass:
    pair entries like ("democratic republic of congo", "drc") need a way
    to detect the full multi-word form. We scan up to 4-word lowercase
    phrases (joined on whitespace, punctuation-stripped) so that
    "Democratic Republic of Congo" yields the phrase
    "democratic republic of congo".
    """
    phrases: set[str] = set()
    for art in (cluster.get("articles") or [])[:10]:
        title = art.get("title", "") or ""
        summary = art.get("summary", "") or ""
        body = (art.get("full_text", "") or "")[:3000]
        text = f"{title} {summary} {body}".lower()
        # Strip non-letter/space, then split into tokens
        cleaned = re.sub(r"[^a-z\s]+", " ", text)
        toks = cleaned.split()
        n = len(toks)
        # Single token + 2-4-word windows
        for i, t in enumerate(toks):
            if 2 <= len(t) <= 20:
                phrases.add(t)
            for k in (2, 3, 4):
                if i + k <= n:
                    phr = " ".join(toks[i:i + k])
                    if 5 <= len(phr) <= 40:
                        phrases.add(phr)
    return phrases


def merge_canonical_pairs(
    clusters: list[dict],
    pair_set: frozenset = _SUMMIT_PAIRS,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 2.5: editorial pair-merge.

    For each known co-occurrence pair (e.g. {trump, xi}, {starmer, streeting}),
    if cluster A and cluster B BOTH contain BOTH names from the pair AND
    fall within the same time window, union them. This is intentionally
    NOT IDF-based — it's an editorial override for political pair-events
    whose individual entity counts are too high for IDF to surface.
    """
    if len(clusters) <= 1 or not pair_set:
        return clusters

    n = len(clusters)
    surface_sets = [_cluster_entity_surface_set(c) for c in clusters]
    timestamps = [_parse_first_pub(c) for c in clusters]

    parent, find, union, _uf_exceeds = _ceiling_union_find(clusters)

    for i in range(n):
        if not surface_sets[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not surface_sets[j]:
                continue

            # Time gate (same as Phase 2)
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            # Both clusters must carry BOTH names from at least one pair
            for pair in pair_set:
                # pair is a frozenset of two names
                if pair.issubset(surface_sets[i]) and pair.issubset(surface_sets[j]):
                    # Hard ceiling — transitive via accumulated root loads
                    if _uf_exceeds(i, j):
                        break
                    union(i, j)
                    break

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Phase 2.55: Synonym-pair merge (geographic + name aliases)
# ---------------------------------------------------------------------------

def _stemmed_title_jaccard(title_a: str, title_b: str) -> float:
    """Stemmed-title Jaccard. Used by Phase 2.55 + 2.6 as a safety guard.

    Reuses the Phase-3 _title_word_stems() so the same stopword + Porter-stem
    pipeline is applied. Returns 0.0 on either-side-empty.
    """
    a = _title_word_stems(title_a)
    b = _title_word_stems(title_b)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return (inter / uni) if uni > 0 else 0.0


def merge_synonym_pairs(
    clusters: list[dict],
    pair_set: frozenset = SYNONYM_PAIRS,
    title_jaccard_floor: float = SYNONYM_TITLE_JACCARD_FLOOR,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 2.55: synonym-pair (alias) merge.

    Differs from Phase 2.5 (canonical pairs):
      - Phase 2.5 wants BOTH names from a pair in BOTH clusters
        (e.g., {trump, xi} ⊆ A and {trump, xi} ⊆ B).
      - Phase 2.55 wants ONE alias from a pair in cluster A and the OTHER
        alias in cluster B (e.g., "drc" ∈ A, "congo" ∈ B). The two
        clusters reference the SAME entity via different surface forms.

    Safety guard: stemmed-title Jaccard ≥ title_jaccard_floor (default
    0.20) ensures the two clusters genuinely share story content. Without
    this guard, "DRC mining sector unrest" + "Congo Brazzaville politics"
    would merge purely on the alias hit. With it, the pair must also pass
    a content-similarity floor.

    Pair entries can be single-word ("drc"/"congo") or multi-word
    ("democratic republic of congo"). Multi-word matching uses the
    `_cluster_surface_phrases` helper (2-4-word windows).
    """
    if len(clusters) <= 1 or not pair_set:
        return clusters

    n = len(clusters)
    # Collect both single tokens AND multi-word phrases per cluster
    surface_sets = [_cluster_entity_surface_set(c) for c in clusters]
    # Lazy multi-word phrase set: only build when at least one pair entry
    # contains a space (cost-saver for runs where all aliases are single-word)
    needs_phrases = any(" " in a or " " in b for a, b in pair_set)
    phrase_sets: list[set[str]] = (
        [_cluster_surface_phrases(c) for c in clusters]
        if needs_phrases else [set()] * n
    )
    timestamps = [_parse_first_pub(c) for c in clusters]
    titles = [c.get("title", "") or "" for c in clusters]

    parent, find, union, _uf_exceeds = _ceiling_union_find(clusters)

    def cluster_has(idx: int, term: str) -> bool:
        """True if cluster idx contains term in surface set or phrase set."""
        if " " in term:
            return term in phrase_sets[idx]
        return term in surface_sets[idx]

    for i in range(n):
        if not surface_sets[i] and not phrase_sets[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not surface_sets[j] and not phrase_sets[j]:
                continue

            # Time gate
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            # Look for ANY (a, b) pair where a ∈ A and b ∈ B (or vice versa)
            alias_hit = False
            for a, b in pair_set:
                if (cluster_has(i, a) and cluster_has(j, b)) or \
                   (cluster_has(i, b) and cluster_has(j, a)):
                    alias_hit = True
                    break
            if not alias_hit:
                continue

            # Safety: title-stem Jaccard floor
            if _stemmed_title_jaccard(titles[i], titles[j]) < title_jaccard_floor:
                continue

            # Hard ceiling — transitive via accumulated root loads
            if _uf_exceeds(i, j):
                continue

            union(i, j)

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Phase 2.6: Anchor-entity merge (high-IDF rare proper nouns)
# ---------------------------------------------------------------------------

def _expand_entities_with_tokens(entity_counts: dict[str, int]) -> dict[str, int]:
    """Expand a {entity: count} dict with single-token sub-entities.

    spaCy's en_core_web_sm is small and produces inconsistent NER chunks
    across re-writes of the same story. "Evika Silina" might emerge as
    one entity in cluster A and "silina cabinet wraps final session"
    in cluster B (with the chunk boundary mis-set). Both should
    contribute "silina" as a normalized rare-anchor candidate.

    For each multi-word entity, we also record each constituent token
    that's alphabetic, ≥4 chars, and not in the entity stop set as a
    standalone candidate. The token's count carries through.

    NB: We deliberately do NOT explode every entity (too noisy). This
    function is called only by the anchor-entity pass to widen the
    overlap surface. The base IDF math in Phase 2 is unchanged.
    """
    expanded = dict(entity_counts)
    for ent, cnt in list(entity_counts.items()):
        if " " not in ent:
            continue
        for tok in ent.split():
            tok = tok.strip(" '\"‘’“”.,;:!?-")
            if not tok.isalpha() or len(tok) < 4:
                continue
            if tok in _ENTITY_STOP_TOKENS:
                continue
            if tok in _LOW_SPECIFICITY_ENTITIES:
                continue
            # Add but don't overwrite if the token already had a higher count
            expanded[tok] = max(expanded.get(tok, 0), cnt)
    return expanded


def merge_anchor_entities(
    clusters: list[dict],
    idf_fraction_of_max: float = ANCHOR_IDF_FRACTION_OF_MAX,
    max_doc_freq_floor: int = ANCHOR_MAX_DOC_FREQ_FLOOR,
    max_doc_freq_pct: float = ANCHOR_MAX_DOC_FREQ_PCT,
    min_shared: int = ANCHOR_MIN_SHARED,
    title_jaccard_floor: float = ANCHOR_TITLE_JACCARD_FLOOR,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 2.6: shared rare-anchor-entity merge.

    Algorithm:
      1. Re-extract per-cluster entity sets (Phase 2's data was discarded
         on rebuild). Expand each entity with its constituent tokens to
         work around spaCy's inconsistent NER-chunk boundaries (so that
         "Evika Silina" in cluster A and "silina cabinet" in cluster B
         both register "silina" as a shared anchor candidate).
      2. Compute global IDF over the post-Phase-2.55 cluster population.
      3. Identify "anchor" entities: those whose IDF ≥ idf_fraction_of_max
         × global_max_idf AND that appear in ≤ max_doc_freq clusters total.
         These are rare, distinguishing proper nouns (e.g., specific
         minister names, small-town place names, less-covered organisations).
      4. For each cluster pair within the time window:
         - If they share at least one anchor entity AND
         - stemmed-title Jaccard ≥ title_jaccard_floor: union.

    The Jaccard floor is the safety: even if two unrelated stories happen
    to share a rare entity (e.g., the same surname referring to two
    different MPs in different countries), the title overlap requirement
    prevents a spurious merge.

    This is the lever that surfaces under-covered international stories
    (Latvian PM Siliņa, Burkinabé politician, regional disasters) where
    each cluster only has 1-3 sources but they all anchor on the same
    rare proper noun.
    """
    if len(clusters) <= 1:
        return clusters

    n = len(clusters)
    # Re-extract entities AFTER Phase 2 + 2.5 + 2.55 merges. The IDF map
    # over the smaller post-merge cluster set is more discriminating than
    # the pre-Phase-2 IDF map (df is now over coalesced stories).
    cluster_entities_raw: list[dict[str, int]] = [
        _extract_cluster_entities(c.get("articles", [])) for c in clusters
    ]
    if not any(cluster_entities_raw):
        return clusters

    # Expand with single-token sub-entities to work around inconsistent
    # NER chunk boundaries (Silina vs Evika Silina vs Silina Cabinet).
    cluster_entities = [_expand_entities_with_tokens(e) for e in cluster_entities_raw]

    idf = _compute_global_idf(cluster_entities)
    if not idf:
        return clusters

    # Doc-frequency for the rare-entity gate
    df: Counter = Counter()
    for ents in cluster_entities:
        for e in ents:
            df[e] += 1

    max_idf = max(idf.values())
    idf_floor = idf_fraction_of_max * max_idf
    # Adaptive doc-freq cap: take the LARGER of the absolute floor (≤3
    # clusters always qualifies — picks up rare entities in small corpora)
    # and the percentage cap (≤5% of corpus — picks up entities in 5-10
    # clusters out of 200 in production).
    max_doc_freq = max(max_doc_freq_floor, int(n * max_doc_freq_pct))

    # Anchor set: rare AND high-IDF, NOT in the low-specificity blacklist
    # (which contains entities like "trump" / "iran" / "white house" that
    # appear in many unrelated stories — never anchors no matter the IDF).
    anchor_entities = {
        e for e, score in idf.items()
        if score >= idf_floor
        and df[e] <= max_doc_freq
        and e not in _LOW_SPECIFICITY_ENTITIES
        and e not in _ENTITY_STOP_TOKENS
        and len(e) >= 4   # avoid 2-3-letter spaCy noise like "ai"/"un"
    }

    if not anchor_entities:
        return clusters

    timestamps = [_parse_first_pub(c) for c in clusters]
    titles = [c.get("title", "") or "" for c in clusters]

    # Pre-compute per-cluster anchor-entity intersection (cheap: just
    # restrict the entity dict to anchor_entities)
    cluster_anchors: list[set[str]] = [
        set(ents.keys()) & anchor_entities for ents in cluster_entities
    ]

    parent, find, union, _uf_exceeds = _ceiling_union_find(clusters)

    for i in range(n):
        if not cluster_anchors[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not cluster_anchors[j]:
                continue

            # Time gate
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            # Must share ≥ min_shared anchor entities (default 2). The
            # 1-anchor case caused over-merge in 2026-05-15 audit:
            # Warsh + Trump-Xi share only "Bessent" but their stories
            # are unrelated. Two-anchor requirement excludes single-bridge
            # cases while still firing on truly fragmented stories where
            # the anchor entity appears across multiple distinct
            # surface forms (Silina + Latvian + Riga + Saeima).
            shared = cluster_anchors[i] & cluster_anchors[j]
            if len(shared) < min_shared:
                continue

            # Safety: title-stem Jaccard floor
            if _stemmed_title_jaccard(titles[i], titles[j]) < title_jaccard_floor:
                continue

            # Hard ceiling — Phase 2.6 is the most aggressive merger;
            # it must be the most conservative about creating mega-clusters.
            # Transitive via accumulated root loads.
            if _uf_exceeds(i, j):
                continue

            union(i, j)

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Phase 4: "Spans X" garbage-title force-split
# ---------------------------------------------------------------------------

def _title_is_garbage(title: str) -> bool:
    """Return True if the cluster title matches a known over-merge signature."""
    if not title:
        return False
    return any(p.search(title) for p in _GARBAGE_TITLE_PATTERNS)


def _cluster_carries_garbage(cluster: dict) -> bool:
    """Return True if the cluster's chosen title OR any source-article title
    matches a garbage signature.

    Phase 2.6 anchor-entity merge can pull in a "Three Unrelated Stories
    Span..." aggregator article whose title is the smoking gun, but the
    title-generator picks the longest non-garbage real title and the
    aggregator's signature gets buried. This helper widens the check to
    all article titles so the aggregator-driven over-merge still trips
    Phase 4's force-split.
    """
    if _title_is_garbage(cluster.get("title", "") or ""):
        return True
    for art in (cluster.get("articles") or [])[:30]:
        t = (art.get("title", "") or "").strip()
        if t and _title_is_garbage(t):
            return True
    return False


def _force_split_cluster(
    cluster: dict,
    tighter_threshold: float = STORY_TFIDF_THRESHOLD * 1.5,
    tighter_idf_threshold: float = ENTITY_MERGE_IDF_THRESHOLD * 1.5,
) -> list[dict]:
    """Re-cluster a single over-merged cluster's articles with stricter gates.

    Runs a mini Phase 1 + Phase 2 on JUST this cluster's articles. Used by
    the garbage-title force-split pass when the title-generator emits a
    "Spans X, Y, and Z" signature that proves the cluster has aggregated
    unrelated sub-events under a single shared entity (usually a GPE).

    Pre-step: aggregator/garbage-titled articles are EXCLUDED from the
    re-cluster. They contain content from multiple unrelated stories
    (high TF-IDF similarity to all of them), so leaving them in re-merges
    everything back together. Each garbage article emerges as its own
    singleton sub-cluster.
    """
    articles = cluster.get("articles") or []
    if len(articles) < 2:
        return [cluster]

    # Separate garbage-titled articles from real ones
    garbage_articles: list[dict] = []
    real_articles: list[dict] = []
    for a in articles:
        if _title_is_garbage(a.get("title", "") or ""):
            garbage_articles.append(a)
        else:
            real_articles.append(a)

    # If after removing garbage we have <2 real articles, keep cluster as-is
    if len(real_articles) < 2:
        return [cluster]

    # Mini Phase 1: stricter TF-IDF cosine on the REAL articles only
    documents = [_build_document(a) for a in real_articles]
    valid_indices = [i for i, d in enumerate(documents) if d.strip()]
    if len(valid_indices) < 2:
        return [cluster]

    valid_docs = [documents[i] for i in valid_indices]
    valid_articles = [real_articles[i] for i in valid_indices]

    try:
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )
        tfidf_matrix = vectorizer.fit_transform(valid_docs)
        sim_matrix = cosine_similarity(tfidf_matrix)
        distance_matrix = np.clip(1.0 - sim_matrix, 0.0, 2.0)
        distance_threshold = 1.0 - tighter_threshold
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(distance_matrix)
    except Exception:
        # If anything goes wrong, return the original cluster unchanged
        return [cluster]

    # Group by label
    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(label, []).append(idx)

    # If still only one sub-cluster after stricter gating, give up the split
    if len(cluster_map) <= 1:
        return [cluster]

    sub_clusters: list[dict] = []
    for label, indices in sorted(cluster_map.items()):
        carts = [valid_articles[i] for i in indices]
        article_ids = [a.get("id", "") for a in carts]
        source_ids = list({a.get("source_id", "") for a in carts if a.get("source_id")})
        pub_dates = [a.get("published_at", "") for a in carts if a.get("published_at")]
        first_published = min(pub_dates) if pub_dates else ""
        sub_title = _generate_cluster_title(carts)
        sub_summary = _generate_cluster_summary(carts, sub_title)
        sub_clusters.append({
            "title": sub_title,
            "summary": sub_summary,
            "article_ids": article_ids,
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "section": _determine_section(carts, sub_title, sub_summary),
            "first_published": first_published,
            "articles": carts,
        })

    # Mini Phase 2: stricter merge so we don't immediately re-merge.
    # Uses set-intersection like main Phase 2 but with a tighter
    # min_shared_entities (5 instead of 3) for sub-cluster confidence.
    if len(sub_clusters) > 1:
        sub_clusters = merge_related_clusters(
            sub_clusters,
            min_shared_entities=5,
        )

    # Final guard: if the stricter pass collapsed everything back to 1
    # (real same-story content) AND we had no garbage articles to peel
    # off, keep the original anchor cluster unchanged.
    if len(sub_clusters) == 1 and not garbage_articles:
        return [cluster]

    # Re-attach the garbage articles as singleton sub-clusters so they
    # don't disappear entirely. Each becomes its own one-article cluster
    # (they're aggregator/rollup articles by definition; keeping them
    # separate prevents them from re-poisoning a real story cluster).
    for ga in garbage_articles:
        sub_clusters.append({
            "title": (ga.get("title", "") or "Aggregator Story")[:200],
            "summary": (ga.get("summary", "") or "")[:1000],
            "article_ids": [ga.get("id", "")],
            "source_ids": [ga.get("source_id", "")] if ga.get("source_id") else [],
            "source_count": 1 if ga.get("source_id") else 0,
            "section": _determine_section([ga], ga.get("title", ""), ga.get("summary", "")),
            "first_published": ga.get("published_at", "") or "",
            "articles": [ga],
        })

    return sub_clusters


def split_garbage_clusters(clusters: list[dict]) -> list[dict]:
    """Phase 4: scan cluster titles for over-merge signatures, force-split.

    The cluster title is the symptom. When the title-generator emits a
    "Spans X, Y, and Z" signature, it has been forced to manufacture a
    mash-up because no single headline covers the cluster's articles —
    proof of over-merge. Re-cluster those articles at a stricter
    threshold and replace the original with the resulting sub-clusters.

    Checks ALL article titles in the cluster, not just the chosen
    representative title. Phase 2.6 anchor-entity merge can pull in an
    aggregator article whose "Three Unrelated Stories Span..." title is
    the smoking gun, but the title-generator hides it by picking the
    longest non-garbage real title. The widened scan catches both cases.
    """
    if not clusters:
        return clusters

    out: list[dict] = []
    for c in clusters:
        if _cluster_carries_garbage(c):
            sub = _force_split_cluster(c)
            out.extend(sub)
        else:
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Phase 5: Mega-cluster soft cap
# ---------------------------------------------------------------------------

# O3 (2026-06-28): an article pile this large that did NOT reach the 75-source
# mega threshold is a candidate over-merge. If it is ALSO internally incoherent
# (cohesion < MEGA_COHESION_FLOOR), flag it so the ranker's 0.65x mega penalty
# deprioritizes it. A genuine big story scores high cohesion and is exempt.
# O5 (2026-08-06): lowered 45 -> 30 so single-source feed-dump piles that sit
# just under the old ceiling (e.g. a 33-article Kyiv-Independent feed) become
# eligible. Size alone NEVER splits a cluster — every trigger below is
# coherence-gated, so a genuine 30-article single-event story is untouched.
MEGA_OVERMERGE_ARTICLE_FLOOR = 30

# Small-bag over-merge catch-all (2026-08-07, CEO-directed). Today's grab-bags
# were n=3-14 — below MEGA_OVERMERGE_ARTICLE_FLOOR(30) — so they slipped Phase 5
# entirely. Extend the GROSS-incoherence force-split down to small clusters: a
# pile whose members share almost no entities AND almost no title words is a bag
# at ANY size, independent of the specific words that bridged it. ONLY the gross
# AND-gate (entity_convergence AND avg_title_jaccard BOTH far below floor) is
# applied here — the riskier title-minority / feed-dump triggers stay gated at
# the 30-article floor where their statistics are reliable — so a small COHERENT
# story (high entity_convergence) is never fragmented. A cheap title-jaccard
# prefilter keeps the spaCy cohesion cost off the coherent majority (only piles
# whose headlines barely overlap pay for NER).
MEGA_OVERMERGE_SMALLBAG_ARTICLE_FLOOR = 3

# ...but the GROSS trigger specifically needs more members than that before its
# statistics mean anything, because entity_convergence is a COARSE RATIO k/n.
# At n=3 it can only be 0.33, 0.67 or 1.0 against a 0.40 floor, so a genuinely
# coherent 3-article story is force-split the moment spaCy NER misses the shared
# entity in 2 of its 3 members — which is NER noise, not evidence of a bag.
#
# Measured on the 2026-08-13 run, which force-split 289 clusters:
#     115 gross splits, 103 of them on clusters with >=3 SOURCES (i.e. stories
#     that met the frontend's display threshold and were destroyed anyway);
#     52 of the 115 had entity_conv of exactly 0.33 (the n=3 quantization) and
#     23 more had exactly 0.25 (the n=4 case); 32 splits were on n=3 alone.
# The ranked feed that run came out with 1src on nearly every top entry.
#
# Gate the gross AND-gate at 8 members, where the floor corresponds to "top
# entity absent from more than half the pile" rather than to a single NER miss.
# The exact-shape triggers keep the lower floor: single-publisher reads
# dominant_publisher_share, which is counted from publisher slugs (no NER, no
# quantization problem), and it splits genuine one-outlet feed dumps -- of its
# 169 splits that run, only 14 touched a cluster with >=3 sources.
MEGA_OVERMERGE_GROSS_ARTICLE_FLOOR = 8

# O4 (2026-08-05): over-merge FORCE-SPLIT gate. The 2026-06-28 O3 path only
# FLAGGED (rank penalty) and only fired when source_count >= 40 — so the
# wire-collapsed "desk bag" over-merges live in production (16-38 source, ~50-
# article Phase-2 accretions that grow to the max_cluster_articles=50 ceiling
# and then borrow a title from one stray member) were NEVER caught: their
# source_count sits below 40, and even when a bigger one tripped the flag the
# mismatched title still shipped. This gate is INDEPENDENT of source_count and
# FORCE-SPLITS the pile back into its real sub-stories.
#
# It keys on the only two cohesion signals that actually separate a grab-bag
# from a real story: how many of the articles share the cluster's top entities
# (entity_convergence) and how much their titles overlap (avg_title_jaccard).
# The wire-amp / tier / publisher-spread signals are deliberately IGNORED here
# because a 50-article/38-source grab-bag looks *healthily diverse* on them
# (measured 2026-08-05: desk bag entity_conv=0.13 / title_jac=0.07 / cohesion=35;
# a coherent 100+-article Iran-Hormuz mega-event entity_conv~1.0 / title_jac~0.8
# / cohesion~73). The gate is an AND of both floors, so a genuine mega-event
# must fail BOTH to be touched — and _force_split_cluster's own collapse-to-1
# guard is a second net that returns the pile unchanged if a stricter re-cluster
# proves it coherent. Per the launch constraint, this is cohesion-gated, NOT a
# naive article-count cap: a clean Phase-1 mega-story is never fragmented.
MEGA_OVERMERGE_ENTITY_CONV_FLOOR = 0.40   # top-entity coverage below this AND
MEGA_OVERMERGE_TITLE_JACCARD_FLOOR = 0.12  # stemmed-title overlap below this

# O5 (2026-08-06): the O4 gross-garbage AND-gate above cleared the obvious
# wire-desk bags, but two SUBTLER over-merge classes still reached the top-50:
#
#   (a) Entity-anchored regional bags. A recurring GPE/actor (EU, Iran) keeps
#       entity_convergence >= 0.40, so the O4 floor never fires — yet the
#       cluster TITLE describes a MINORITY of members (measured: "EU Urges
#       Caribbean Nations..." on-topic for 0/7 sampled; a Europe/Morocco
#       grab-bag). topic_coherence(title, articles) — already computed for the
#       ranker — measures exactly this title-vs-content coverage and is
#       INDEPENDENT of entity_convergence, so it catches them.
#
#   (b) Single-source feed dumps. One publisher's RSS feed collapses into one
#       cluster that then borrows one item's headline ("Ukraine hits 2 Russian
#       oil refineries", 33 art / 12 src, a Kyiv-Independent feed padded with a
#       Sweden-residency item + a house ad). The tell is publisher dominance
#       (dominant_publisher_share high, or source_count/n_articles low) plus low
#       internal coherence.
#
# CRITICAL CONSTRAINT: coherent large single-event clusters (a 192-article
# El-Sayed Michigan story, a 52-article Ukraine-war story) MUST stay whole.
# They score HIGH on BOTH entity_convergence AND title coverage, so:
#   1. the coherent-override below exempts any entity-saturated + title-
#      representative cluster outright, and
#   2. every trigger is coherence-gated (never size-alone), and
#   3. _force_split_cluster's stricter-TF-IDF collapse-to-1 guard is the final
#      net — a pile that re-clusters back to one story is returned unchanged.
#
# Title-vs-content coverage (Fix 1): title on-topic for < half the members, and
# NOT entity-saturated (an entity-saturated cluster is a coherent single-actor
# story regardless of headline wording).
MEGA_OVERMERGE_TITLE_COVERAGE_FLOOR = 0.50
MEGA_OVERMERGE_TITLE_COVERAGE_ENTITY_CEIL = 0.85
# Single-source feed dump (Fix 2): one publisher dominates OR the wire-amp ratio
# is high, AND the pile is internally incoherent (low title coverage OR low
# pairwise title overlap — distinct feed items barely share headlines, whereas a
# single outlet covering ONE event intensely shares heavy headline vocabulary).
MEGA_OVERMERGE_PUB_SHARE_FLOOR = 0.50
MEGA_OVERMERGE_SRC_RATIO_FLOOR = 0.40
MEGA_OVERMERGE_FEED_DUMP_COVERAGE_FLOOR = 0.60
MEGA_OVERMERGE_FEED_DUMP_JACCARD_FLOOR = 0.15
# Coherent single-event override (the CRITICAL protection): entity-saturated AND
# title-representative => one real story; skip every split trigger. El-Sayed /
# Ukraine-war clear both; the bags fail title coverage (their title matches a
# minority) so they are never exempted.
MEGA_OVERMERGE_COHERENT_ENTITY_FLOOR = 0.80
MEGA_OVERMERGE_COHERENT_COVERAGE_FLOOR = 0.50

# O6 (2026-08-10, CEO-directed): two residual over-merge classes verified on a
# live run and SEPARATE from the Branch-B Phase-2/3 df-gate work (those only
# guard the entity / title MERGE paths; a bag that forms in Phase 1 TF-IDF never
# reaches them). Both bags survive every existing split trigger because
# topic_coherence is BLIND to them (it reported 1.00 on a genuinely 0.25-coherent
# live bag), so the coherent-override exempts them. NEITHER new rule reads
# topic_coherence for its decision; both lean on entity_convergence (NER-based,
# reliable) and title agreement, and every split is still confirmed by
# _force_split_cluster's collapse-to-1 guard.
#
# RULE A - single-publisher feed dump (the live "Will Scharf" bag). One outlet's
# feed of DISTINCT stories about a recurring subject (a person / org named in
# every item) collapses into one cluster: entity_convergence is high (the subject
# recurs) so the coherent-override would exempt it, yet the headlines barely
# agree (distinct events). The tell is single-publisher dominance PLUS low title
# agreement. A genuine well-covered event is carried by MANY outlets
# (dom_pub_share low) OR its sibling headlines repeat the event's vocabulary
# (title_jac high), so neither floor is met. Checked BEFORE the coherent-override
# because such a pile can be entity-saturated. Measured margins: every genuine
# good-merge reference sits at dom_pub_share <= 0.33; the bag at 1.00.
SINGLE_PUB_DOMINANCE_FLOOR = 0.80
SINGLE_PUB_TITLE_JAC_CEIL = 0.25
# RULE B - generic-topic-token bridge (the live "Supreme Court" bag). Two
# genuinely distinct events (a mail-in-ballot plea and a redistricting-map
# ruling) merge on shared GENERIC institutional / procedural HEADLINE vocabulary
# ("Supreme Court Weighs Emergency Application ...") while their bodies name
# entirely different actors (Pennsylvania / ballots vs Louisiana / gerrymander).
# The signature is a HIGH title-Jaccard (generic headlines strongly overlap) with
# NO single dominant actor unifying the pile. entity_convergence (any-of-top-3)
# is USELESS here: each sub-event contributes a top-3 entity, so every article
# matches at least one and entity_conv pins to ~1.0. entity_dominant_share (the
# SINGLE most-common entity's coverage) is the honest signal: a real event names
# one actor across most members (measured: every genuine good-merge reference
# >= 0.60), a two-topic bag's top entity only spans its own half (the SCOTUS bag
# at 0.50). The high title-Jaccard floor is the second guard: no genuine
# good-merge reference reaches 0.45, the bag sits at 0.64. Checked BEFORE the
# coherent-override (which entity_conv=1.0 would otherwise satisfy). A genuine
# event fails BOTH floors, and _force_split_cluster's collapse-to-1 is the net.
GENERIC_BRIDGE_TITLE_JAC_FLOOR = 0.45    # generic headlines strongly overlap
GENERIC_BRIDGE_DOMINANT_CEIL = 0.60      # no single actor covers most members


def _overmerge_split_reason(
    entity_conv: float,
    title_jac: float,
    title_cov: float,
    dom_pub_share: float,
    src_ratio: float,
    entity_dominant_share: float = 1.0,
) -> str | None:
    """Decide whether an over-size cluster should be force-split, and why.

    Pure/deterministic so it is unit-testable without building real clusters.
    Returns the trigger name ('single-publisher' | 'generic-bridge' | 'gross' |
    'title-minority' | 'feed-dump') or None.

    All triggers are coherence-gated; the coherent-override short-circuits any
    entity-saturated + title-representative (i.e. genuinely coherent) pile so a
    real large single-event story can never match a trigger. The exceptions are
    the O6 rules (single-publisher, generic-bridge), checked FIRST because both
    bag shapes pin entity_conv to ~1.0 and would otherwise be wrongly exempted.
    """
    # (O6 RULE A) single-publisher feed dump: one outlet dominates AND the
    # headlines barely agree => a feed of DISTINCT stories about a recurring
    # subject, not one event. Checked BEFORE the coherent-override because such a
    # pile is often entity-saturated (the subject recurs) and would otherwise be
    # wrongly exempted. A genuine well-covered event has many voices
    # (dom_pub_share low) OR high title agreement, so neither floor is met.
    if (
        dom_pub_share >= SINGLE_PUB_DOMINANCE_FLOOR
        and title_jac < SINGLE_PUB_TITLE_JAC_CEIL
    ):
        return "single-publisher"

    # (O6 RULE B) generic-topic-token bridge: generic headlines strongly overlap
    # (title_jac high) but NO single actor unifies the pile
    # (entity_dominant_share low) => two distinct events bridged on institutional
    # headline vocabulary. Checked BEFORE the coherent-override because
    # entity_conv (any-of-top-3) pins to ~1.0 when each sub-event contributes a
    # top entity. A real event names one actor across most members (high
    # dominant share) AND does not reach the high title-Jaccard floor, so it
    # fails both.
    if (
        title_jac >= GENERIC_BRIDGE_TITLE_JAC_FLOOR
        and entity_dominant_share < GENERIC_BRIDGE_DOMINANT_CEIL
    ):
        return "generic-bridge"

    # Coherent single-event: entity-saturated AND title represents the members.
    if (
        entity_conv >= MEGA_OVERMERGE_COHERENT_ENTITY_FLOOR
        and title_cov >= MEGA_OVERMERGE_COHERENT_COVERAGE_FLOOR
    ):
        return None

    # (existing) gross garbage: near-zero shared entities AND near-zero titles.
    if (
        entity_conv < MEGA_OVERMERGE_ENTITY_CONV_FLOOR
        and title_jac < MEGA_OVERMERGE_TITLE_JACCARD_FLOOR
    ):
        return "gross"

    # (new) entity-anchored title-minority bag: the headline is on-topic for a
    # minority of members, and the cluster is not entity-saturated.
    if (
        title_cov < MEGA_OVERMERGE_TITLE_COVERAGE_FLOOR
        and entity_conv < MEGA_OVERMERGE_TITLE_COVERAGE_ENTITY_CEIL
    ):
        return "title-minority"

    # (new) single-source feed dump: one publisher dominates OR wire-amp is
    # high, AND the pile is internally incoherent.
    if (
        dom_pub_share >= MEGA_OVERMERGE_PUB_SHARE_FLOOR
        or src_ratio <= MEGA_OVERMERGE_SRC_RATIO_FLOOR
    ) and (
        title_cov < MEGA_OVERMERGE_FEED_DUMP_COVERAGE_FLOOR
        or title_jac < MEGA_OVERMERGE_FEED_DUMP_JACCARD_FLOOR
    ):
        return "feed-dump"

    return None


def _overmerge_split_reason_smallbag(
    entity_conv: float,
    title_jac: float,
    title_cov: float,
    dom_pub_share: float,
    entity_dominant_share: float,
    n_articles: int = 0,
) -> str | None:
    """Small-bag (n < MEGA_OVERMERGE_ARTICLE_FLOOR) split decision.

    Conservative subset of _overmerge_split_reason: only the three
    size-independent, topic_coherence-robust triggers -- single-publisher (O6
    RULE A), generic-topic-bridge (O6 RULE B), gross. The title-minority and
    feed-dump triggers are DELIBERATELY excluded here: both lean on
    topic_coherence / wire-amplification statistics that are noisy at small n,
    and the CEO audit flagged topic_coherence as blind to these bags. Every
    trigger below decides from entity signals (NER-based) and title agreement,
    and the split is still confirmed by _force_split_cluster.
    """
    # RULE A -- single-publisher feed dump. Checked first (see the >=30 twin).
    if (
        dom_pub_share >= SINGLE_PUB_DOMINANCE_FLOOR
        and title_jac < SINGLE_PUB_TITLE_JAC_CEIL
    ):
        return "single-publisher"
    # RULE B -- generic-topic-token bridge: generic headlines strongly overlap
    # but no single actor unifies the pile. Also before the coherent-override.
    if (
        title_jac >= GENERIC_BRIDGE_TITLE_JAC_FLOOR
        and entity_dominant_share < GENERIC_BRIDGE_DOMINANT_CEIL
    ):
        return "generic-bridge"
    # Coherent single-event override: entity-saturated AND title-representative.
    if (
        entity_conv >= MEGA_OVERMERGE_COHERENT_ENTITY_FLOOR
        and title_cov >= MEGA_OVERMERGE_COHERENT_COVERAGE_FLOOR
    ):
        return None
    # Gross garbage: near-zero shared entities AND near-zero titles. Gated at
    # MEGA_OVERMERGE_GROSS_ARTICLE_FLOOR because entity_conv is a coarse k/n
    # ratio: below that, one spaCy NER miss is indistinguishable from a real
    # grab-bag and the rule shreds coherent 3-6 article stories (see the
    # constant's note for the measured 2026-08-13 damage).
    if (
        n_articles >= MEGA_OVERMERGE_GROSS_ARTICLE_FLOOR
        and entity_conv < MEGA_OVERMERGE_ENTITY_CONV_FLOOR
        and title_jac < MEGA_OVERMERGE_TITLE_JACCARD_FLOOR
    ):
        return "gross"
    return None


def _cheap_dominant_publisher_share(articles: list[dict], sample_cap: int = 30) -> float:
    """Dominant publisher's share of the cluster's articles, with NO spaCy NER.

    A cheap prefilter twin to _cheap_avg_title_jaccard so the small-bag path can
    detect the single-publisher shape (O6 RULE A) before paying for full
    cohesion. Mirrors _cluster_cohesion's dominant_publisher_share exactly.
    Returns 1.0 when no publisher slugs are present (conservative: treated as a
    single-publisher candidate so the full cohesion pass makes the real call)."""
    arts = articles[:sample_cap]
    pub_counts: dict[str, int] = {}
    for a in arts:
        slug = a.get("source_slug") or a.get("source_id", "")
        if slug:
            pub_counts[slug] = pub_counts.get(slug, 0) + 1
    n = len(arts)
    if not pub_counts or n == 0:
        return 1.0
    return max(pub_counts.values()) / n


def _cheap_avg_title_jaccard(articles: list[dict], sample_cap: int = 20) -> float:
    """Pairwise stemmed-title Jaccard with NO spaCy NER — a cheap prefilter for
    the small-bag over-merge split so the expensive full cohesion (entity
    convergence) is only computed on clusters whose headlines barely overlap.

    Returns 1.0 (treated as coherent → skip split) when there are no scorable
    title pairs. Mirrors _cluster_cohesion's title-Jaccard math exactly."""
    arts = articles[:sample_cap]
    stems = [_title_word_stems(a.get("title", "") or "") for a in arts]
    pairs = 0
    total = 0.0
    for i in range(len(stems)):
        si = stems[i]
        if not si:
            continue
        for j in range(i + 1, len(stems)):
            sj = stems[j]
            if not sj:
                continue
            uni = si | sj
            if not uni:
                continue
            total += len(si & sj) / len(uni)
            pairs += 1
    return (total / pairs) if pairs else 1.0


def split_mega_clusters(
    clusters: list[dict],
    threshold: int = MEGA_CLUSTER_THRESHOLD,
    verbose: bool = True,
) -> list[dict]:
    """Phase 5: soft-cap clusters whose source_count exceeds the threshold.

    REVERTED 2026-05-31 to the simple soft-cap branch. The Phase 2
    50-article hard cap (in union-find via group_size accumulation)
    already prevents the chain-merge mega-clusters that motivated the
    Era 6/7 elaborations (cohesion-gated trip, force-split, recursive
    sub-cap, chain-merge-dissolve). Phase 5 now only fires on the rare
    genuine mega-event (a presidential inauguration, a 9/11-scale
    disaster). In that case we keep the cluster whole but cap
    source_count for display — no force-split, no cohesion gate.

    Logs each cap decision when verbose=True.
    """
    if not clusters:
        return clusters

    out: list[dict] = []
    for c in clusters:
        sc = int(c.get("source_count", 0) or 0)
        n_articles = len(c.get("articles") or [])
        if sc >= threshold:
            c["_mega_cluster_original_count"] = sc
            c["source_count"] = threshold
            c["mega_cluster_capped"] = True
            if verbose:
                print(
                    f"  [Phase5/mega-cap] '{c.get('title','')[:60]!r}' "
                    f"(src={sc}) kept whole, source_count capped at {threshold}"
                )
            out.append(c)
            continue

        if (
            n_articles >= MEGA_OVERMERGE_ARTICLE_FLOOR
            and not c.get("mega_cluster_capped")
        ):
            # O4/O5: over-size pile, source_count-independent. Measure the
            # coherence signals that separate a real story from a wire desk-bag /
            # entity-anchored regional bag / single-source feed dump. source_map
            # is threaded via the _source_map stash so the (unused-here) tier
            # signal stays consistent with the ranker.
            coh = _cluster_cohesion(c, source_map=c.get("_source_map"))
            entity_conv = coh.get("entity_convergence", 1.0)
            title_jac = coh.get("avg_title_jaccard", 1.0)
            cohesion = coh.get("cohesion_score", 100.0)
            dom_pub_share = coh.get("dominant_publisher_share", 1.0)
            entity_dominant_share = coh.get("entity_dominant_share", 1.0)
            # Title-vs-content coverage (Fix 1): computed over ALL members (not
            # the cohesion sample) since it is a cheap keyword-set operation.
            title_cov = topic_coherence(
                c.get("title", "") or "", c.get("articles") or []
            )
            src_ratio = (sc / n_articles) if n_articles else 1.0

            reason = _overmerge_split_reason(
                entity_conv=entity_conv,
                title_jac=title_jac,
                title_cov=title_cov,
                dom_pub_share=dom_pub_share,
                src_ratio=src_ratio,
                entity_dominant_share=entity_dominant_share,
            )

            if reason:
                sub = _force_split_cluster(c)
                if len(sub) > 1:
                    # Productive split: the bag dissolved into its real sub-
                    # stories (+ peeled aggregator singletons). The coherent-
                    # override + coherence gates in _overmerge_split_reason are
                    # the guarantee a real mega-event never reaches here (it is
                    # entity-saturated AND title-representative); _force_split_
                    # cluster's collapse-to-1 return is the additional backstop
                    # for a borderline pile that turns out cohesive at the
                    # stricter TF-IDF gate.
                    if verbose:
                        print(
                            f"  [Phase5/overmerge-split:{reason}] "
                            f"'{c.get('title','')[:55]!r}' (art={n_articles}, "
                            f"src={sc}, ent_conv={entity_conv:.2f}, "
                            f"title_jac={title_jac:.2f}, title_cov={title_cov:.2f}, "
                            f"pub_share={dom_pub_share:.2f}) force-split into "
                            f"{len(sub)} sub-clusters"
                        )
                    out.extend(sub)
                    continue
                # Split declined (coherent after all) — keep whole but flag for
                # the ranker penalty so a still-suspect pile is deprioritized.
                c["mega_cluster_capped"] = True
                if verbose:
                    print(
                        f"  [Phase5/overmerge-flag:{reason}] "
                        f"'{c.get('title','')[:55]!r}' "
                        f"(art={n_articles}, src={sc}) split declined; flagged"
                    )
            elif cohesion < MEGA_COHESION_FLOOR and sc >= MEGA_COHESION_MIN_SOURCES:
                # Legacy O3 flag preserved for the medium-incoherent case that
                # does not meet the stricter grab-bag split gate (e.g. a merged
                # pile that shares SOME entities/titles but still reads muddled).
                # The MEGA_COHESION_MIN_SOURCES floor keeps it off heavily
                # wire-amplified real stories (48 articles / 12 voices).
                c["mega_cluster_capped"] = True
                if verbose:
                    print(
                        f"  [Phase5/overmerge-flag] '{c.get('title','')[:55]!r}' "
                        f"(art={n_articles}, src={sc}, cohesion={cohesion:.0f}) "
                        f"flagged as over-merge"
                    )
        elif (
            n_articles >= MEGA_OVERMERGE_SMALLBAG_ARTICLE_FLOOR
            and not c.get("mega_cluster_capped")
        ):
            # Small-bag catch-all (Layer 2). A grab-bag is a grab-bag at ANY
            # size. Three shapes are caught here via the conservative
            # _overmerge_split_reason_smallbag: gross incoherence (historical),
            # single-publisher feed dump (O6 RULE A), and the generic-topic-token
            # bridge (O6 RULE B). Cheap NER-free prefilters gate the expensive
            # spaCy cohesion pass so a small COHERENT story never pays for NER:
            #   * cheap title-Jaccard < gross floor        -> gross candidate
            #   * cheap dom-publisher-share high + low tj   -> single-pub candidate
            #   * cheap title-Jaccard >= bridge floor       -> generic-bridge candidate
            # (the middle title-Jaccard band is a mildly-overlapping pile with no
            # clear bag signal; it is left untouched, as before.)
            arts = c.get("articles") or []
            cheap_tj = _cheap_avg_title_jaccard(arts)
            cheap_dom = _cheap_dominant_publisher_share(arts)
            admit = (
                # gross candidate — only worth NER above the gross floor, since
                # below it the gross trigger can no longer fire (coarse k/n).
                (n_articles >= MEGA_OVERMERGE_GROSS_ARTICLE_FLOOR
                 and cheap_tj < MEGA_OVERMERGE_TITLE_JACCARD_FLOOR)
                or (cheap_dom >= SINGLE_PUB_DOMINANCE_FLOOR
                    and cheap_tj < SINGLE_PUB_TITLE_JAC_CEIL)
                or cheap_tj >= GENERIC_BRIDGE_TITLE_JAC_FLOOR
            )
            if admit:
                coh = _cluster_cohesion(c, source_map=c.get("_source_map"))
                entity_conv = coh.get("entity_convergence", 1.0)
                title_jac = coh.get("avg_title_jaccard", 1.0)
                dom_pub_share = coh.get("dominant_publisher_share", 1.0)
                entity_dominant_share = coh.get("entity_dominant_share", 1.0)
                # title_cov feeds ONLY the coherent-override exemption (never a
                # positive split decision), so its known blindness cannot cause a
                # false split here -- at worst it fails to exempt, and the split
                # is still arbitrated by _force_split_cluster's collapse-to-1.
                title_cov = topic_coherence(
                    c.get("title", "") or "", arts
                )
                reason = _overmerge_split_reason_smallbag(
                    entity_conv=entity_conv,
                    title_jac=title_jac,
                    title_cov=title_cov,
                    dom_pub_share=dom_pub_share,
                    entity_dominant_share=entity_dominant_share,
                    n_articles=n_articles,
                )
                if reason:
                    sub = _force_split_cluster(c)
                    if len(sub) > 1:
                        if verbose:
                            print(
                                f"  [Phase5/smallbag-split:{reason}] "
                                f"'{c.get('title','')[:55]!r}' (art={n_articles}, "
                                f"src={sc}, ent_conv={entity_conv:.2f}, "
                                f"title_jac={title_jac:.2f}, "
                                f"pub_share={dom_pub_share:.2f}) force-split into "
                                f"{len(sub)} sub-clusters"
                            )
                        out.extend(sub)
                        continue
        out.append(c)
    return out


# ---------------------------------------------------------------------------
# Phase 3: Stem-aware title Jaccard merge
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

# Lazy stemmer — try nltk PorterStemmer; on import failure fall back to
# spaCy lemmatisation (slower per-call but always available since spaCy
# is a hard pipeline dependency).
_STEMMER = None
_USE_LEMMA_FALLBACK = False


def _get_stemmer():
    global _STEMMER, _USE_LEMMA_FALLBACK
    if _STEMMER is not None or _USE_LEMMA_FALLBACK:
        return _STEMMER
    try:
        from nltk.stem import PorterStemmer
        _STEMMER = PorterStemmer()
    except Exception:
        _USE_LEMMA_FALLBACK = True
        _STEMMER = None
    return _STEMMER


def _stem_word(word: str) -> str:
    stemmer = _get_stemmer()
    if stemmer is not None:
        try:
            return stemmer.stem(word)
        except Exception:
            pass
    # spaCy lemma fallback
    try:
        nlp = get_nlp()
        doc = nlp(word)
        if len(doc) > 0:
            return doc[0].lemma_.lower() or word
    except Exception:
        pass
    return word


def _title_word_stems(title: str) -> set[str]:
    """Tokenise + stopword-filter + Porter-stem a title's content words."""
    cleaned = _clean_title(title)
    words = re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", cleaned.lower())
    out: set[str] = set()
    for w in words:
        if w in _TITLE_STOPWORDS or len(w) < 2:
            continue
        out.add(_stem_word(w))
    return out


# ---------------------------------------------------------------------------
# Cluster cohesion scorer — distinguish real big stories from false-merges
# ---------------------------------------------------------------------------
# 2026-05-24 — replaces the band-aid article-count cap. A true top story
# with 30+ articles across 20+ sources, 3 tiers, and cross-spectrum lean
# scores ~70-90 here and passes through Phase 5 untouched. A false-merge
# (80 articles bridged by one common token like "Observer", single tier,
# single political lean, titles all over the map) scores < 20 and gets
# force-split.
#
# Weighted components, each 0..1:
#   avg_title_jaccard        — pairwise stemmed-title overlap, sample-capped.
#                              Real stories share entities + verbs;
#                              false-merges share generic nouns at best.
#   entity_convergence       — fraction of articles containing the top-3
#                              most-common entities. Real stories have one
#                              dominant set; bridge-merges have unique
#                              entity sets per article.
#   inv_wire_amp             — 1 / (1 + amp_ratio - 1). Penalises clusters
#                              where article_count >> source_count. Real
#                              wire stories: amp_ratio ~ 2-4 → score ~0.5.
#                              Bridge piles: amp_ratio > 8 → score < 0.2.
#   inv_tier_concentration   — 1 - (dominant_tier_share). Penalises
#                              single-tier piles. Multi-tier stories
#                              score 0.5-0.7.
#   inv_publisher_concentration — 1 - (dominant_publisher_share).
#                              Penalises one-publisher verticals.
#
# Weights chosen so a healthy mid-coverage story (4 sources, 2 tiers,
# moderate Jaccard) lands around 50, leaving room for genuine top
# stories (8+ sources, 3 tiers, high Jaccard) to clear 65 for headline
# eligibility AND for false-merges (<30) to be force-split.
COHESION_WEIGHT_TITLE_JACCARD = 0.30
COHESION_WEIGHT_ENTITY_CONVERGENCE = 0.25
COHESION_WEIGHT_WIRE_AMP = 0.15
COHESION_WEIGHT_TIER_CONCENTRATION = 0.15
COHESION_WEIGHT_PUBLISHER_CONCENTRATION = 0.15
# Phase 5 cohesion gate. The cohesion-trip path was originally written to
# catch publisher-bridge false-merges (80 articles named "* Observer" piled
# into one cluster). It must ONLY apply to clusters that are actually
# suspiciously large — never to legitimate 12-25-source breaking news that
# happens to have multi-desk title diversity. Today's regression: a slow
# day produced 22-article real clusters with cohesion ~28 that got
# force-split into singletons because there was no source-count floor.
MEGA_COHESION_FLOOR = 30          # cohesion below this flags over-merge
                                  # (rank penalty; no force-split since the
                                  # 2026-05-31 Phase 5 revert)
MEGA_COHESION_MIN_ARTICLES = 20   # superseded by MEGA_OVERMERGE_ARTICLE_FLOOR
                                  # (=45) as the operative article floor
MEGA_COHESION_MIN_SOURCES = 40    # AND require source_count >= this so
                                  # cohesion-trip never fires on healthy
                                  # medium clusters (e.g. 12-source breaking
                                  # news with 22 multi-desk articles)


def _cluster_cohesion(
    cluster: dict,
    source_map: dict[str, dict] | None = None,
    sample_cap: int = 30,
) -> dict:
    """Score how internally coherent a cluster's articles are.

    Used by Phase 5 to gate the force-split decision AND by the ranker
    to compute is_headline. Rule-based, deterministic, ~5-10ms per
    cluster at sample_cap=30.

    Returns a dict with:
      avg_title_jaccard       0..1
      entity_convergence      0..1
      wire_amp_ratio          float (articles / max(sources, 1))
      tier_concentration      0..1
      dominant_publisher_share 0..1
      cohesion_score          0..100 — weighted blend, the headline gate
    """
    articles = (cluster.get("articles") or [])[:sample_cap]
    n = len(articles)
    if n == 0:
        return {
            "avg_title_jaccard": 0.0, "entity_convergence": 0.0,
            "entity_dominant_share": 0.0,
            "wire_amp_ratio": 0.0, "tier_concentration": 1.0,
            "dominant_publisher_share": 1.0, "cohesion_score": 0.0,
        }

    # ── title-Jaccard: average pairwise stemmed-word-set overlap ─────────
    stems = [_title_word_stems(a.get("title", "") or "") for a in articles]
    if n == 1:
        jaccard = 1.0  # singletons are trivially cohesive
    else:
        # Cap pairs at ~150 (matches sample_cap=30 → 435 pairs worst case
        # → cheap; faster than O(n^2) text similarity)
        pairs = 0
        total = 0.0
        for i in range(n):
            si = stems[i]
            if not si:
                continue
            for j in range(i + 1, n):
                sj = stems[j]
                if not sj:
                    continue
                union = si | sj
                if not union:
                    continue
                total += len(si & sj) / len(union)
                pairs += 1
        jaccard = (total / pairs) if pairs else 0.0

    # ── entity-convergence: share of articles containing top-3 entities ──
    # Reuses _extract_cluster_entities (already capped at 10 articles
    # internally for cost), then computes a separate per-article entity
    # set on the same sample.
    #
    # ALSO computes entity_dominant_share (O6): the coverage of the SINGLE most
    # common entity. entity_convergence (any-of-top-3) is fooled to ~1.0 by a
    # two-topic bag where each sub-event contributes a top-3 entity (every
    # article then matches at least one), so it cannot see a generic-topic
    # bridge of two entity-rich events. The dominant single entity's coverage
    # does: one real event has one actor named across most members (high share),
    # whereas a two-topic bag's top entity only covers its own half (~0.5).
    cluster_entities = _extract_cluster_entities(articles)
    if not cluster_entities:
        entity_conv = 0.0
        entity_dominant_share = 0.0
    else:
        top3 = sorted(cluster_entities.items(), key=lambda kv: -kv[1])[:3]
        top3_keys = {k for k, _ in top3}
        top1_key = top3[0][0]
        # Per-article entity sets via the SAME normalisation as cluster ents
        per_art_hits = 0
        top1_hits = 0
        for art in articles:
            ents = _extract_cluster_entities([art])
            if any(k in ents for k in top3_keys):
                per_art_hits += 1
            if top1_key in ents:
                top1_hits += 1
        entity_conv = per_art_hits / n
        entity_dominant_share = top1_hits / n

    # ── wire-amp ratio: articles / unique source voices ─────────────────
    sc = int(cluster.get("source_count", 0) or 0)
    if sc == 0:
        # Fall back to counting unique source_ids on the article dicts
        sc = len({a.get("source_id") for a in articles if a.get("source_id")})
    amp_ratio = n / max(sc, 1)
    inv_wire_amp = 1.0 / (1.0 + max(0.0, amp_ratio - 1.0))

    # ── tier concentration: dominant tier's share of articles ───────────
    tier_concentration = 0.0
    if source_map:
        tier_counts: dict[str, int] = {}
        for a in articles:
            slug = a.get("source_slug") or a.get("source_id", "")
            src = source_map.get(slug, {})
            tier = src.get("tier", "")
            if tier:
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
        if tier_counts:
            tier_concentration = max(tier_counts.values()) / n
        else:
            tier_concentration = 1.0  # unknown tiers → treat as concentrated
    else:
        tier_concentration = 1.0  # no map → can't measure → conservative

    # ── publisher concentration: dominant publisher's share ─────────────
    pub_counts: dict[str, int] = {}
    for a in articles:
        slug = a.get("source_slug") or a.get("source_id", "")
        if slug:
            pub_counts[slug] = pub_counts.get(slug, 0) + 1
    dom_pub_share = (max(pub_counts.values()) / n) if pub_counts else 1.0

    # ── weighted blend ─────────────────────────────────────────────────
    score_unit = (
        COHESION_WEIGHT_TITLE_JACCARD * jaccard
        + COHESION_WEIGHT_ENTITY_CONVERGENCE * entity_conv
        + COHESION_WEIGHT_WIRE_AMP * inv_wire_amp
        + COHESION_WEIGHT_TIER_CONCENTRATION * (1.0 - tier_concentration)
        + COHESION_WEIGHT_PUBLISHER_CONCENTRATION * (1.0 - dom_pub_share)
    )

    return {
        "avg_title_jaccard": round(jaccard, 3),
        "entity_convergence": round(entity_conv, 3),
        "entity_dominant_share": round(entity_dominant_share, 3),
        "wire_amp_ratio": round(amp_ratio, 2),
        "tier_concentration": round(tier_concentration, 3),
        "dominant_publisher_share": round(dom_pub_share, 3),
        "cohesion_score": round(score_unit * 100.0, 1),
    }


# Phase 3 discriminative-stem gate (2026-08-07, CEO-directed). A title-Jaccard
# merge must be driven by at least one DISCRIMINATIVE shared stem — one whose df
# across the day's cluster titles is low. Two clusters that share only generic
# headline stems ("suprem", "court", "militari", a country stem) never merge on
# that alone, no matter how high the raw Jaccard: those stems appear across many
# titles that day. This is the title-path analogue of the Phase-2 discriminative-
# anchor gate and directly kills the "Supreme Court" India-vs-US over-merge.
#
# 2026-08-10 (SCALE-STABLE FIX, editorial-audit 1b). Same defect as the Phase-2
# gate: the bound was `max(5, int(n * 0.08))`, which at production scale
# (n ~= 1,945) collapsed to `max(5, 155) = 155`, so a stem counted as
# discriminative unless it appeared in >155 cluster titles. Phase 3 then
# compounded Phase 2's contamination on the largest, entity-dense clusters
# (Netanyahu grew from 50 to 103 articles at Phase 3 in the audit replay). A
# story-specific title stem appears in only the few titles about that one event,
# so its ABSOLUTE df stays small at any corpus size; a generic headline word's
# df grows with the day's volume. A FIXED absolute df cap is therefore scale-
# stable. IDF rejected for the same reason as Phase 2.
#
# The cap is set to 5 (the historical FLOOR, one above the Phase-2 entity cap of
# 3). Two reasons the stem cap is looser than the entity cap: (a) titles are
# short, so a genuine event's own place/name stem legitimately recurs across a
# few more same-event sibling titles than a body-extracted entity does; the
# over-split guard fixture 041 (a real 8-outlet typhoon) merges on "Cebu" /
# "Philippines" which sit at title-df 5 there, and a cap of 4 fragments it. (b)
# Phase 3 also gates on the 0.22 raw title-Jaccard THRESHOLD, which is far higher
# than the Phase-2 title floor of 0.08, so two DIFFERENT same-region stories
# (e.g. an Assam firing vs an Assam flood, title-Jaccard ~0.11) are already
# refused by the Jaccard threshold and never reach this stem gate. The Phase-2
# entity df cap (3) is what blocks that cross-topic pair; the Phase-3 stem cap
# only needs to exclude genuinely GENERIC headline words (institutions, bare
# country names), whose title df runs into the dozens/hundreds at scale and is
# nowhere near 5.
PHASE3_STEM_DF_ABS = 5               # discriminative iff title-stem df <= this (fixed, scale-stable)


def merge_duplicate_title_clusters(
    clusters: list[dict],
    jaccard_threshold: float = TITLE_JACCARD_THRESHOLD,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 3: stem-aware title Jaccard merge.

    Single threshold. Porter-stemmed token overlap (e.g. "resign" /
    "resignation" both reduce to "resign"). Same time-spread gate as
    Phase 2 — different stories about the same entity at different times
    will not collapse.

    A merge additionally requires at least one DISCRIMINATIVE shared stem
    (df across the day's titles <= PHASE3_STEM_DF_*), so two clusters that
    overlap only on generic institutional/country headline words never
    merge on that alone.
    """
    if len(clusters) <= 1:
        return clusters

    n = len(clusters)
    title_stems = [_title_word_stems(c.get("title", "")) for c in clusters]
    timestamps = [_parse_first_pub(c) for c in clusters]

    # Document-frequency of each title stem across the day's clusters — the
    # data-driven discriminativeness signal for the title path.
    stem_df: Counter = Counter()
    for st in title_stems:
        for s in st:
            stem_df[s] += 1
    # SCALE-STABLE: fixed absolute df cap, independent of n (see
    # PHASE3_STEM_DF_ABS note). Does not grow with the day's title volume.
    phase3_max_df = PHASE3_STEM_DF_ABS

    parent, find, union, _uf_exceeds = _ceiling_union_find(clusters)

    for i in range(n):
        if not title_stems[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not title_stems[j]:
                continue

            shared_stems = title_stems[i] & title_stems[j]
            inter = len(shared_stems)
            uni = len(title_stems[i] | title_stems[j])
            if uni == 0:
                continue
            if (inter / uni) < jaccard_threshold:
                continue

            # Discriminative-stem gate: at least one shared stem must be rare
            # across the day's titles. Blocks generic-word-only title bridges.
            if not any(stem_df.get(s, 0) <= phase3_max_df for s in shared_stems):
                continue

            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            # Hard ceiling — transitive via accumulated root loads
            if _uf_exceeds(i, j):
                continue

            union(i, j)

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Shared rebuild helper for both merge phases
# ---------------------------------------------------------------------------

def _rebuild_merged(
    clusters: list[dict],
    parent: list[int],
    find,
) -> list[dict]:
    n = len(clusters)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    out: list[dict] = []
    for root, members in groups.items():
        if len(members) == 1:
            out.append(clusters[root])
            continue

        all_articles: list[dict] = []
        all_article_ids: list[str] = []
        all_source_ids: set[str] = set()
        all_pub_dates: list[str] = []

        for idx in members:
            c = clusters[idx]
            all_articles.extend(c.get("articles", []))
            all_article_ids.extend(c.get("article_ids", []))
            all_source_ids.update(c.get("source_ids", []))
            fp = c.get("first_published", "")
            if fp:
                all_pub_dates.append(fp)

        anchor_idx = max(members, key=lambda i: clusters[i].get("source_count", 0))
        anchor = clusters[anchor_idx]

        first_published = min(all_pub_dates) if all_pub_dates else ""
        merged_title = _generate_cluster_title(all_articles)
        merged_summary = _generate_cluster_summary(all_articles, merged_title)
        merged_section = _determine_section(all_articles, merged_title, merged_summary)

        out.append({
            "title": merged_title,
            "summary": merged_summary,
            "article_ids": all_article_ids,
            "source_ids": list(all_source_ids),
            "source_count": len(all_source_ids),
            "section": merged_section,
            "first_published": first_published,
            "articles": all_articles,
            **{
                k: v for k, v in anchor.items()
                if k not in (
                    "title", "summary", "article_ids", "source_ids",
                    "source_count", "section", "first_published", "articles",
                )
            },
        })
    return out


# ---------------------------------------------------------------------------
# Wire-amplification accounting (post-merge)
# ---------------------------------------------------------------------------

def _voice_id(article: dict) -> str:
    """Return the publisher slug that should count as one voice for
    source_count math. Wire copies collapse to their origin publisher.
    """
    if article.get("is_wire_copy"):
        return (
            article.get("wire_origin_publisher_id")
            or article.get("source_id", "")
            or ""
        )
    return article.get("source_id", "") or ""


def _apply_wire_aware_source_count(cluster: dict) -> None:
    """Mutate cluster in place: recompute source_count + source_ids using
    `_voice_id`, and add a `wire_amplification` ratio field."""
    arts = cluster.get("articles", []) or []
    voices = {_voice_id(a) for a in arts if _voice_id(a)}
    cluster["source_ids"] = list(voices)
    cluster["source_count"] = len(voices)
    total = len(arts)
    cluster["wire_amplification"] = (
        round(total / max(len(voices), 1), 3) if total else 0.0
    )


# ---------------------------------------------------------------------------
# Phase 6 — headline/body contamination guard (salient-coherence split)
# ---------------------------------------------------------------------------
# 2026-08-11 (P0-3). Phase 1 (TfidfVectorizer, ngram (1,2), cosine >=
# STORY_TFIDF_THRESHOLD) has NO domain stop-list and NO document-frequency gate,
# so high-frequency bridge bigrams ("supreme court", "extreme heat", "muslim",
# "army", "youth") survive TF-IDF and chain thin low-source articles that share
# nothing else. topic_coherence() is fooled because it rewards ANY shared word.
# Worst live offender: cluster 9673f352 ("Supreme Court ... Mail-In Ballot")
# fused five different countries' supreme courts into one #63.5 bag.
#
# Phase 6 runs LAST (after Phase 5). For each cluster it extracts the chosen
# headline's SALIENT anchors — title stems, minus the generic government /
# wire-service / hot-spot stop-vocabulary (_LOW_SPECIFICITY_ENTITIES +
# _ENTITY_STOP_TOKENS, stemmed), minus any stem whose document-frequency across
# the day's cluster titles is high (the same absolute-df discriminativeness
# signal Phases 2 and 3 use). That yields the low-df distinguishing anchors
# ({mail-in, ballot} NOT {supreme, court}). salient_coherence = fraction of
# members whose own title+lead carries >= 1 salient anchor. When that is < 0.5
# on a >= 3-member cluster the cluster is over-merged: the published cluster is
# rebuilt from ONLY the coherent core (so the summary is generated from members
# that actually match the headline), and the off-anchor members are re-clustered
# on their own (any coherent sub-story reforms; incoherent leftovers fall to
# low-source singletons that the feed naturally drops). Nothing is fabricated.
#
# A GENUINE multi-source event is untouched: it keeps a low-df person/place
# anchor that most members share, so salient_coherence stays high.
PHASE6_SALIENT_COHERENCE_FLOOR = 0.5   # flag below this (with >= 3 members)
PHASE6_MIN_MEMBERS = 3                  # only assess clusters this large
PHASE6_ANCHOR_DF_ABS = PHASE3_STEM_DF_ABS  # salient iff title-stem df <= this


@lru_cache(maxsize=1)
def _generic_anchor_stop_stems() -> frozenset[str]:
    """Porter-stems of every token in the generic government / wire-service /
    geopolitical-hotspot stop vocabularies. A salient headline anchor must not
    be one of these, so an institution ("supreme court") or a bare hot-spot
    country name can never count as a distinguishing anchor even when its
    corpus df happens to be low on a given day."""
    stems: set[str] = set()
    for phrase in (_LOW_SPECIFICITY_ENTITIES | _ENTITY_STOP_TOKENS):
        for tok in re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", phrase.lower()):
            if len(tok) < 2 or tok in _TITLE_STOPWORDS:
                continue
            stems.add(_stem_word(tok))
    return frozenset(stems)


def _reset_cluster_from_members(cluster: dict, members: list[dict]) -> None:
    """Rebuild a cluster's derived fields from a coherent subset of members.
    The extractive title is KEPT (it is the coherent core's headline); the
    summary is regenerated from the retained members only."""
    cluster["articles"] = members
    cluster["article_ids"] = [a.get("id", "") for a in members]
    src = list({a.get("source_id", "") for a in members if a.get("source_id")})
    cluster["source_ids"] = src
    cluster["source_count"] = len(src)
    pub = [a.get("published_at", "") for a in members if a.get("published_at")]
    if pub:
        cluster["first_published"] = min(pub)
    cluster["summary"] = _generate_cluster_summary(members, cluster.get("title", ""))
    _apply_wire_aware_source_count(cluster)


def split_incoherent_clusters(
    clusters: list[dict],
    coherence_floor: float = PHASE6_SALIENT_COHERENCE_FLOOR,
    source_map: dict[str, dict] | None = None,
) -> list[dict]:
    """Phase 6: salient-coherence contamination guard. See section header."""
    if not clusters:
        return clusters

    # Document-frequency of each title stem across the day's cluster titles —
    # the same absolute-df discriminativeness signal Phase 3 uses. A generic
    # institutional word ("supreme"/"court") recurs across many distinct
    # clusters' titles at production scale (high df); a story-specific anchor
    # ("mail-in"/"ballot") stays low-df.
    title_stems = [_title_word_stems(c.get("title", "")) for c in clusters]
    stem_df: Counter = Counter()
    for st in title_stems:
        for s in st:
            stem_df[s] += 1
    stop_stems = _generic_anchor_stop_stems()

    out: list[dict] = []
    for idx, c in enumerate(clusters):
        arts = c.get("articles", []) or []
        if len(arts) < PHASE6_MIN_MEMBERS:
            out.append(c)
            continue

        anchors = {
            s for s in title_stems[idx]
            if s not in stop_stems
            and stem_df.get(s, 0) <= PHASE6_ANCHOR_DF_ABS
        }
        if not anchors:
            # Headline carries no low-df distinguishing anchor — cannot assess
            # coherence, so leave the cluster whole (safe / no false split).
            out.append(c)
            continue

        def _carries_anchor(a: dict) -> bool:
            text = f"{a.get('title', '') or ''} {a.get('summary', '') or ''}"
            return bool(anchors & _title_word_stems(text))

        core = [a for a in arts if _carries_anchor(a)]
        off = [a for a in arts if not _carries_anchor(a)]
        coherence = len(core) / len(arts)

        if coherence >= coherence_floor or not core or not off:
            out.append(c)
            continue

        # FLAG: rebuild the published cluster from the coherent core so its
        # summary is generated only from members that match the headline.
        _reset_cluster_from_members(c, core)
        c["salient_coherence"] = round(coherence, 3)
        c["coherence_split"] = True
        out.append(c)

        # Re-cluster the off-anchor members on their own. apply_coherence_check
        # is False on the recursive call so Phase 6 cannot re-enter (no
        # unbounded recursion); a coherent off-story reforms, incoherent
        # leftovers fall to low-source singletons the feed naturally drops.
        # Belt-and-braces: this recursion re-enters the full phase stack on a
        # small, odd sub-corpus, which is exactly where the 2026-08-13 run blew
        # up ("After pruning, no terms remain" out of Phase 1's vectorizer).
        # That exception escaped cluster_stories and cost the whole day's
        # clustering -- main.py caught it with `clusters` still [], and the
        # orphan backstop wrapped every article as a 1-source cluster. Phase 6
        # is a refinement, so a failure here must degrade to "leave the
        # off-anchor members alone", never take the run's clustering with it.
        try:
            sub = cluster_stories(
                off,
                source_map=source_map,
                apply_coherence_check=False,
            )
        except Exception as exc:
            print(f"  [warn] Phase 6 re-cluster failed, keeping off-anchor "
                  f"members unsplit: {exc}")
            sub = []
            _reset_cluster_from_members(c, core + off)
        out.extend(sub)

    return out


# ---------------------------------------------------------------------------
# Main entry: cluster_stories
# ---------------------------------------------------------------------------

def cluster_stories(
    articles: list[dict],
    similarity_threshold: float = STORY_TFIDF_THRESHOLD,
    run_merge_pass: bool = True,
    source_map: dict[str, dict] | None = None,
    enable_anchor_merge: bool = False,
    apply_coherence_check: bool = True,
) -> list[dict]:
    """Group articles into story clusters.

    Pipeline (what actually runs; 2.5/2.55/2.6 are parked — see module
    docstring):
        Phase 1    — TF-IDF + agglomerative clustering at
                     `similarity_threshold` (default STORY_TFIDF_THRESHOLD).
                     Synonym aliases (DRC↔Congo, UK↔Britain) are
                     normalised inside _build_document, subsuming the old
                     Phase 2.55.
        Phase 2    — IDF-weighted entity-overlap merge
                     (merge_related_clusters).
        Phase 2.6  — Anchor-entity merge (merge_anchor_entities): ONLY
                     when enable_anchor_merge=True; no production caller
                     passes it today.
        Phase 3    — Stem-aware title-Jaccard merge
                     (merge_duplicate_title_clusters).
        Phase 4    — Garbage-title force-split (split_garbage_clusters):
                     re-clusters at stricter gates when the title-generator
                     produces a "Spans X, Y, and Z" mash-up signature.
        Phase 5    — Mega-cluster soft cap (split_mega_clusters):
                     clusters with source_count >= 75 are kept whole with
                     source_count capped at 75 for display; large
                     incoherent piles are flagged mega_cluster_capped for
                     the ranker penalty (no force-split since 2026-05-31).

    Wire-amplification: if articles arrive carrying `is_wire_copy` /
    `wire_origin_publisher_id` (set by deduplicator.deduplicate_articles),
    the final source_count collapses wire copies to their origin
    publisher and a `wire_amplification` ratio is recorded.

    Args:
        articles: List of article dicts. Each may carry the wire-fingerprint
            fields populated by Phase 0.
        similarity_threshold: Cosine similarity floor for Phase 1
            (override only for sub-cluster recursion or debugging).
        run_merge_pass: When False, skip Phases 2 and 3 (used by callers
            that want raw TF-IDF output for diagnostic purposes).

    Returns:
        List of cluster dicts with keys:
            title, summary, article_ids, source_ids, source_count,
            section, first_published, articles, wire_amplification.
    """
    if not articles:
        return []

    # Single-article fast path
    if len(articles) == 1:
        a = articles[0]
        c = {
            "title": a.get("title") or "Developing Story",
            "summary": _generate_cluster_summary([a]),
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", ""),
            "articles": [a],
        }
        _apply_wire_aware_source_count(c)
        return [c]

    # Build documents and split into vectorizable / empty
    documents = [_build_document(a) for a in articles]
    valid_indices = [i for i, d in enumerate(documents) if d.strip()]
    empty_indices = [i for i, d in enumerate(documents) if not d.strip()]

    empty_singletons: list[dict] = []
    for i in empty_indices:
        a = articles[i]
        c = {
            "title": a.get("title") or "Developing Story",
            "summary": a.get("summary", "") or (a.get("full_text", "") or "")[:500],
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", "") or "",
            "articles": [a],
        }
        _apply_wire_aware_source_count(c)
        empty_singletons.append(c)

    if not valid_indices:
        return empty_singletons

    valid_docs = [documents[i] for i in valid_indices]
    valid_articles = [articles[i] for i in valid_indices]

    if len(valid_docs) == 1:
        a = valid_articles[0]
        c = {
            "title": a.get("title") or "Developing Story",
            "summary": _generate_cluster_summary([a]),
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", ""),
            "articles": [a],
        }
        _apply_wire_aware_source_count(c)
        return [c] + empty_singletons

    # Phase 1: TF-IDF + agglomerative clustering.
    # min_df=2 on production-scale corpora suppresses single-document
    # boilerplate (nav/footer/byline tokens) that otherwise bridges one
    # publisher's unrelated articles into a grab-bag; kept at 1 for tiny
    # corpora (fixtures) where min_df=2 would empty the vocabulary.
    # (2026-06-28, Wave 3 / O1)
    _phase1_min_df = 2 if len(valid_docs) >= 30 else 1

    def _vectorize(min_df: int, max_df: float):
        return TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=min_df,
            max_df=max_df,
        ).fit_transform(valid_docs)

    # min_df/max_df pruning can empty the vocabulary outright on a degenerate
    # corpus ("After pruning, no terms remain"), and fit_transform RAISES rather
    # than returning an empty matrix. That escaped cluster_stories entirely on
    # 2026-08-13 and cost the whole day's clustering: main.py caught it with
    # `clusters` still [], the orphan backstop then wrapped every single article
    # as a 1-source cluster, and the ranked feed came out with 1src on nearly
    # every top entry. The trigger was Phase 6's recursive call re-entering here
    # with a small off-anchor sub-corpus.
    #
    # Degrade instead of raising: relax the pruning, then fall back to raw
    # counts. Only if even that yields nothing do we give up on Phase 1 and hand
    # the articles back as singletons for the later phases to merge.
    tfidf_matrix = None
    for _min_df, _max_df in ((_phase1_min_df, 0.95), (1, 1.0)):
        try:
            tfidf_matrix = _vectorize(_min_df, _max_df)
            break
        except ValueError:
            continue

    if tfidf_matrix is not None and tfidf_matrix.shape[1] > 0:
        sim_matrix = cosine_similarity(tfidf_matrix)
        distance_matrix = np.clip(1.0 - sim_matrix, 0.0, 2.0)
        distance_threshold = 1.0 - similarity_threshold
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(distance_matrix)
    else:
        # No usable vocabulary even unpruned. Seed one label per article and let
        # the entity/title phases below do the merging, rather than raising out
        # of cluster_stories and losing the entire run's clustering.
        labels = list(range(len(valid_articles)))

    # Group articles by label
    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(label, []).append(idx)

    clusters: list[dict] = []
    for label, indices in sorted(cluster_map.items()):
        carts = [valid_articles[i] for i in indices]
        article_ids = [a.get("id", "") for a in carts]
        source_ids = list({a.get("source_id", "") for a in carts if a.get("source_id")})
        pub_dates = [a.get("published_at", "") for a in carts if a.get("published_at")]
        first_published = min(pub_dates) if pub_dates else ""
        cluster_title = _generate_cluster_title(carts)
        cluster_summary = _generate_cluster_summary(carts, cluster_title)
        clusters.append({
            "title": cluster_title,
            "summary": cluster_summary,
            "article_ids": article_ids,
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "section": _determine_section(carts, cluster_title, cluster_summary),
            "first_published": first_published,
            "articles": carts,
        })

    # Phases 2 + 2.5 + 2.55 + 2.6 + 3 + 4
    # 2026-05-28 — reverted the adaptive entity / anchor thresholds added on
    # 2026-05-26. They were meant to compensate for chain-merge bridges on
    # low-volume days, but in practice they starved merging across EVERY
    # slow day (e.g. 4,395-article corpus → entity threshold 3.0 + anchor
    # fraction 0.80 → Phase 2 + Phase 2.6 both effectively no-ops → real
    # top stories stay fragmented as 2-3-source siblings, never clearing
    # the coverage_ok gate (src>=5 AND tiers>=2) in the ranker. Restore the
    # static baselines that worked. The MERGE_HARD_CEILING already prevents
    # transitive mega-merges; IDF smoothing in _ent_idf_sum (n_eff = max(n,30),
    # df_eff = df + ceil(N/4)) already stabilises IDF across corpus sizes.
    # 2026-05-31 simplification — Phase 2 uses set-intersection + 50-article
    # cap, restored from the 2026-03-28 design. Phases 2.5 (canonical pairs)
    # and 2.55 (synonyms) deleted; synonyms now normalised inside Phase 1
    # _build_document(). Phase 2.6 (anchor merge) survives behind an
    # opt-in flag for diagnostic runs only — production cron leaves it OFF.
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_related_clusters(clusters)
    if run_merge_pass and len(clusters) > 1 and enable_anchor_merge:
        clusters = merge_anchor_entities(clusters, idf_fraction_of_max=ANCHOR_IDF_FRACTION_OF_MAX)
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_duplicate_title_clusters(clusters)
    # Phase 4 — garbage-title force-split (over-merge detector)
    if run_merge_pass and clusters:
        clusters = split_garbage_clusters(clusters)

    # Append empty-document singletons (they bypass merge passes since
    # there's no document to compare against).
    if empty_singletons:
        clusters.extend(empty_singletons)

    # Final pass: recompute source_count using the wire-aware voice
    # collapse, and stamp wire_amplification on every cluster.
    # NB: must run BEFORE Phase 5 because Phase 5's mega-threshold check
    # uses source_count after wire-collapse (one publisher = one voice).
    for c in clusters:
        _apply_wire_aware_source_count(c)

    # Phase 5 — mega-cluster soft cap (267-source "AI Deployment" mega
    # bucket motivated this pass). Force-split if possible; otherwise
    # keep whole but cap source_count at MEGA_CLUSTER_THRESHOLD.
    if run_merge_pass and clusters:
        # 2026-05-24 v2 — attach source_map to each cluster so the new
        # cohesion-gated Phase 5 can read tier info per article.
        if source_map:
            for _c in clusters:
                _c["_source_map"] = source_map
        clusters = split_mega_clusters(clusters)
        # Clean up the temporary stash so it doesn't get persisted.
        for _c in clusters:
            _c.pop("_source_map", None)
        # If Phase 5 produced new sub-clusters from a force-split, recompute
        # the wire-aware source_count for them. Capped clusters already
        # have their source_count rewritten by Phase 5 itself.
        for c in clusters:
            if not c.get("mega_cluster_capped"):
                _apply_wire_aware_source_count(c)

    # Phase 6 — headline/body contamination guard (salient-coherence split).
    # Runs LAST so it sees the final merged clusters. apply_coherence_check is
    # False on the recursive re-cluster of off-anchor members (no re-entry).
    if run_merge_pass and apply_coherence_check and clusters:
        clusters = split_incoherent_clusters(clusters, source_map=source_map)

    # Phase 7 — late-stage same-event merge (2026-08-22). Runs AFTER Phase 6's
    # split so it coalesces clean fragments, never contaminated ones. Top-N only,
    # conjunctive high-precision gate, uses the geopolitical common entities that
    # Phase 2 blacklists (safe at N=50). Gated to the top-level pass so Phase 6's
    # recursive re-cluster (apply_coherence_check=False) never re-enters it.
    if run_merge_pass and apply_coherence_check and len(clusters) > 1:
        from .same_event_merge import merge_same_event_clusters
        clusters = merge_same_event_clusters(clusters)

    return clusters
