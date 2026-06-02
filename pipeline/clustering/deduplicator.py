"""
Phase 0 wire-aware fingerprinting for the void --news pipeline.

This module REPLACES the prior content-deduplication step. Instead of
removing near-duplicate articles, it TAGS each one with wire-syndication
metadata so downstream clustering and ranking can credit a wire-amplified
story to its true distinct-voice count rather than its raw article count.

Public API: `deduplicate_articles(articles)` is preserved (caller in
pipeline/main.py is unchanged) but its semantics have shifted:
  - INPUT length == OUTPUT length (no removal)
  - Each article in the output may gain three new fields:
        article["wire_group_id"]            -- str | None
        article["is_wire_copy"]              -- bool
        article["wire_origin_publisher_id"] -- str | None

Detection algorithm:
  1. Strip wire prefixes from `full_text` (UPDATE/CORRECTED/(LEAD)/ etc.)
  2. Take the first WIRE_HASH_FINGERPRINT_BYTES (800) characters of the
     normalised body, lowercased, whitespace-collapsed.
  3. SHA1 the result. Collision groups are candidate wire syndicates.
  4. For each candidate group of size >= 2, confirm with a lead-paragraph
     cosine similarity check (>= WIRE_LEAD_COSINE = 0.92) on the first
     ~400 characters using TF-IDF. This guards against accidental hash
     collisions on very short bodies.
  5. The "wire origin" within a confirmed group is chosen by:
        a) explicit `tier == "wire"`
        b) source slug in CANONICAL_WIRE_SLUGS (ap-news, reuters, ...)
        c) earliest published_at
        d) first article in the group (deterministic fallback)

No LLM API calls -- scikit-learn TF-IDF, SHA1, and a small wire-prefix
regex only.
"""

from __future__ import annotations

import hashlib
import re
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------------
# Calibrated constants
# ---------------------------------------------------------------------------
WIRE_HASH_FINGERPRINT_BYTES = 800       # chars of normalised lead used in SHA1
WIRE_LEAD_COSINE = 0.92                 # cosine threshold to confirm collision
WIRE_LEAD_COSINE_CHARS = 400            # cosine vector built on first N chars

# Canonical wire-service slugs. Used (a) to bias which article in a
# confirmed wire group is chosen as the "origin", and (b) ALSO as a
# direct-tag heuristic for groups that share a wire origin slug even when
# their body bytes diverge slightly (rewritten leads, location inserts).
CANONICAL_WIRE_SLUGS = frozenset({
    "ap", "ap-news", "associated-press",
    "reuters",
    "afp",
    "dpa",
    "kyodo",
    "bloomberg-wire",
    "upi",
    "pa-media", "press-association",
    "anadolu",
    "tass",
    "xinhua",
    "ians",
    "pti",
    "epa-efe",
})

# Mirror of the wire-prefix regex used by story_cluster.py — kept inline
# here so the deduplicator does not import from clustering during pipeline
# bootstrap (avoids circular imports during partial loads).
_WIRE_PREFIX_RE = re.compile(
    r"^\s*(?:\((?:LEAD|URGENT|CORRECTED|UPDATE(?:\s*\d*)?|RECASTS?|ADDS?|"
    r"WRAPUP|NEWSALERT|\d+(?:st|nd|rd|th)\s+LD)\)\s*)"
    r"|^\s*(?:WATCH\s*LIVE\s*:|WATCH\s*:|BREAKING\s*:|UPDATE\s*:|EXCLUSIVE\s*:)"
    r"\s*",
    re.IGNORECASE,
)

_WHITESPACE_RE = re.compile(r"\s+")
# Common wire byline tags that pollute the lead ("AP exclusive.",
# "Reuters reports", "(Reuters) -"); strip so the first 800 normalised
# chars line up across syndicated copies.
_BYLINE_TAG_RE = re.compile(
    r"\(\s*(?:reuters|ap|afp|bloomberg|dpa|kyodo|upi|xinhua|tass|anadolu)"
    r"\s*\)\s*[-–—:]?\s*",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_lead(text: str) -> str:
    """Lowercase, strip wire prefixes + bylines, collapse whitespace."""
    if not text:
        return ""
    cleaned = _WIRE_PREFIX_RE.sub("", text)
    cleaned = _BYLINE_TAG_RE.sub("", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip().lower()
    return cleaned


def _fingerprint_hash(article: dict) -> str:
    """SHA1 of the first WIRE_HASH_FINGERPRINT_BYTES of the normalised body.

    Returns "" when the article has no usable body — those articles are
    skipped (passed through untagged).
    """
    body = article.get("full_text", "") or ""
    norm = _normalise_lead(body)
    if len(norm) < 80:  # too short to fingerprint meaningfully
        return ""
    head = norm[:WIRE_HASH_FINGERPRINT_BYTES]
    return hashlib.sha1(head.encode("utf-8")).hexdigest()


def _lead_text(article: dict) -> str:
    """Normalised lead used for the cosine confirmation check."""
    body = article.get("full_text", "") or ""
    return _normalise_lead(body)[:WIRE_LEAD_COSINE_CHARS]


def _confirm_wire_group(group_articles: list[dict]) -> bool:
    """Return True when the lead-text TF-IDF cosine across ALL members
    is >= WIRE_LEAD_COSINE.

    Uses pairwise minimum: a single divergent member sinks the group.
    Single-member groups never reach this function.
    """
    leads = [_lead_text(a) for a in group_articles]
    if any(len(t) < 60 for t in leads):
        return False
    try:
        vec = TfidfVectorizer(
            max_features=2000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=1.0,
        )
        mat = vec.fit_transform(leads)
    except ValueError:
        return False
    sims = cosine_similarity(mat)
    n = len(leads)
    # Pairwise minimum off-diagonal
    min_sim = 1.0
    for i in range(n):
        for j in range(i + 1, n):
            if sims[i, j] < min_sim:
                min_sim = float(sims[i, j])
    return min_sim >= WIRE_LEAD_COSINE


def _pick_origin(group_articles: list[dict]) -> dict:
    """Pick the origin article for a confirmed wire group.

    Priority:
      1. tier == "wire"
      2. slug in CANONICAL_WIRE_SLUGS
      3. earliest published_at (lexicographic on ISO timestamps is fine)
      4. first item (deterministic)
    """
    def _key(a: dict) -> tuple[int, int, str, int]:
        tier = (a.get("tier") or "").lower()
        slug = (a.get("source_id") or "").lower()
        pub = a.get("published_at") or ""
        # Tuple ordered so SMALLER is BETTER → we use min().
        # tier_rank: wire=0, anything else=1
        tier_rank = 0 if tier in ("wire", "wire-service") else 1
        # slug_rank: canonical wire=0 else 1
        slug_rank = 0 if slug in CANONICAL_WIRE_SLUGS else 1
        # group_articles is small (<= ~30); index acts as deterministic tiebreaker
        return (tier_rank, slug_rank, pub or "~", group_articles.index(a))

    return min(group_articles, key=_key)


# ---------------------------------------------------------------------------
# Tag pass
# ---------------------------------------------------------------------------

def _tag_chunk(articles: list[dict]) -> None:
    """Mutate `articles` in place, attaching wire-group metadata.

    Articles that don't belong to any wire group still receive default
    None/False values so downstream code can rely on the keys existing.
    """
    # Default-initialise every article so callers can rely on the fields
    for a in articles:
        a.setdefault("wire_group_id", None)
        a.setdefault("is_wire_copy", False)
        a.setdefault("wire_origin_publisher_id", None)

    if len(articles) < 2:
        return

    # Hash each article (skip those with no usable body)
    hashes: list[str] = [_fingerprint_hash(a) for a in articles]

    # Bucket indices by hash
    buckets: dict[str, list[int]] = {}
    for i, h in enumerate(hashes):
        if not h:
            continue
        buckets.setdefault(h, []).append(i)

    for h, members in buckets.items():
        if len(members) < 2:
            continue

        group = [articles[i] for i in members]
        if not _confirm_wire_group(group):
            continue

        origin = _pick_origin(group)
        origin_slug = (origin.get("source_id") or "").lower() or None

        for art in group:
            art["wire_group_id"] = h
            art["wire_origin_publisher_id"] = origin_slug
            # Mark every NON-origin article as a wire copy. The origin
            # itself keeps its own source_id contribution to source_count.
            art["is_wire_copy"] = (art is not origin)


# ---------------------------------------------------------------------------
# Public API (unchanged signature)
# ---------------------------------------------------------------------------

def deduplicate_articles(
    articles: list[dict],
    similarity_threshold: float = 0.80,  # accepted for API compat; ignored
) -> list[dict]:
    """Tag wire-syndicated articles in place; return the SAME list length.

    The historical name and signature are preserved so the pipeline caller
    in `pipeline/main.py` does not need to change. The semantics, however,
    have shifted: this function NO LONGER REMOVES articles. It only
    annotates them with wire-fingerprint metadata so downstream clustering
    and ranking can apply the wire-amplification dampener.

    Args:
        articles: List of article dicts. May contain `full_text`,
            `source_id`, `tier`, `published_at`. Mutated in place.
        similarity_threshold: Accepted for backward compatibility. The
            wire-confirmation cosine threshold is governed internally by
            WIRE_LEAD_COSINE. This parameter is intentionally ignored.

    Returns:
        The same list (also returned for caller convenience). Length is
        guaranteed equal to the input length.
    """
    if not articles:
        return articles

    # Single in-memory pass. Wire-fingerprinting is O(N + buckets * cosine)
    # which is far cheaper than the previous O(N^2) cross-chunk dedup.
    _tag_chunk(articles)
    return articles


# ---------------------------------------------------------------------------
# Convenience helpers exposed for tests / downstream consumers
# ---------------------------------------------------------------------------

def is_wire_copy(article: dict) -> bool:
    """True when an article was tagged as a non-origin wire reprint."""
    return bool(article.get("is_wire_copy", False))


def wire_origin_publisher_id(article: dict) -> str | None:
    """Origin publisher slug for a tagged wire copy (or its own slug for
    an origin article)."""
    return article.get("wire_origin_publisher_id")


def voice_id(article: dict) -> str:
    """Return the publisher slug that should count as one "voice" for
    source_count math: the wire origin if the article is a wire copy,
    else the article's own source_id."""
    if article.get("is_wire_copy"):
        return article.get("wire_origin_publisher_id") or article.get("source_id", "")
    return article.get("source_id", "")
