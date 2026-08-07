"""Deterministic feed-quality checks for the Void News evaluation system (v1).

Pure functions. No DB writes, no LLM calls, no network. Each check ingests the
already-fetched displayed top-50 clusters (with member article titles attached)
and returns a list of `Finding` objects carrying a grade, a red-flag code, a
priority, human-readable evidence, and — for judge candidates — the exact payload
a Claude agent needs to confirm the finding.

REUSE POLICY
------------
Every check prefers the real repo helper and only falls back to a local
equivalent when the heavy dependency (spaCy / nltk / sklearn / google-genai)
cannot be imported (e.g. in a hermetic offline smoke test). Each fallback is
noted inline. The production CI job installs the pipeline deps, so the real
helpers are used there.

Helpers reused (when importable):
  - summarizer.cluster_summarizer._SHOW_DONT_TELL_PATTERN
        _detect_show_dont_tell_violations, _META_BRACKET_RE, _META_SENT_RE,
        _ontopic_title_tokens  (dominant-topic / on-topic vote)
  - ranker.feed_ranker._specific_title_stems, _contest_anchor_conflict,
        _GENERIC_EVENT_WORDS, _COMMON_ACTION_WORDS, and the NEAR_DUP_* constants
  - clustering.story_cluster._title_word_stems, _cluster_cohesion,
        MEGA_OVERMERGE_ENTITY_CONV_FLOOR, MEGA_OVERMERGE_TITLE_JACCARD_FLOOR
  - categorizer.newsworthiness.newsworthiness

Reimplemented (no importable source):
  - isRawExcerpt  (ported from frontend/app/lib/summaryHygiene.ts — TypeScript)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Grade + red-flag vocabulary
# ---------------------------------------------------------------------------

GRADES = ("CORRECT", "ACCEPTABLE", "WRONG", "CATASTROPHIC")

# Numeric penalty per grade, used by score_findings.
_GRADE_PENALTY = {
    "CORRECT": 0,
    "ACCEPTABLE": 4,
    "WRONG": 16,
    "CATASTROPHIC": 45,
}

# Red-flag catalog: code -> (dimension, human label).
RED_FLAGS: dict[str, tuple[str, str]] = {
    "RF-1": ("contamination", "Summary describes a different event than the cluster"),
    "RF-3": ("agreement", "Headline and summary share no specific content"),
    "RF-4": ("coverage", "Displayed card has no usable summary"),
    "RF-5": ("cohesion", "Incoherent / mis-titled cluster bag"),
    "RF-6": ("duplication", "Two clusters are the same story (near-duplicate)"),
    "RF-7": ("junk", "Evergreen / junk item in the feed"),
    "RF-11": ("hygiene", "Editorial hygiene violation (em dash / show-don't-tell / meta)"),
}

# The dimensions rolled up into the Feed Score, in report order.
DIMENSIONS = ("coverage", "contamination", "agreement", "duplication",
              "junk", "cohesion", "hygiene")

# Tunables (documented where they mirror a repo constant).
TOP10 = 10                       # front-page band; findings here escalate to P0
MIN_COHESION_MEMBERS = 8         # cohesion RF-5 only judged on clusters this big
_FALLBACK_ENTITY_CONV_FLOOR = 0.40   # mirrors MEGA_OVERMERGE_ENTITY_CONV_FLOOR
_FALLBACK_TITLE_JACCARD_FLOOR = 0.12  # mirrors MEGA_OVERMERGE_TITLE_JACCARD_FLOOR


# ---------------------------------------------------------------------------
# Finding + score data models
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    """One red-flag finding against one (or a pair of) displayed cluster(s)."""
    code: str                      # RF-1 ... RF-11
    grade: str                     # one of GRADES
    priority: str                  # "P0" | "P1" | "P2"
    dimension: str                 # RED_FLAGS[code][0]
    cluster_id: str
    cluster_title: str
    position: int                  # 1-based display rank (0 if N/A)
    message: str                   # short human-readable evidence line
    is_candidate: bool = False     # True => needs the Claude judge to confirm
    evidence: dict[str, Any] = field(default_factory=dict)
    judge_payload: dict[str, Any] | None = None  # exact data an agent needs

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def sort_key(self) -> tuple:
        prio = {"P0": 0, "P1": 1, "P2": 2}.get(self.priority, 3)
        grade = {"CATASTROPHIC": 0, "WRONG": 1, "ACCEPTABLE": 2, "CORRECT": 3}.get(
            self.grade, 4)
        return (prio, grade, self.position or 999)


@dataclass
class ScoreReport:
    feed_score: int
    dimension_scores: dict[str, int]
    counts_by_grade: dict[str, int]
    counts_by_priority: dict[str, int]
    n_findings: int
    n_candidates: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Lazy, dependency-tolerant helper accessors
# ---------------------------------------------------------------------------

_UNSET = object()
_CACHE: dict[str, Any] = {}


def _cached(key: str, loader: Callable[[], Any]) -> Any:
    if key not in _CACHE:
        try:
            _CACHE[key] = loader()
        except Exception:
            _CACHE[key] = None
    return _CACHE[key]


# --- title tokenizer / stemmer ---------------------------------------------

_LOCAL_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "over", "after", "before",
    "under", "about", "amid", "amidst", "says", "said", "will", "would",
    "could", "should", "has", "have", "had", "are", "was", "were", "been",
    "its", "his", "her", "their", "new", "how", "why", "what", "when",
    "where", "who", "this", "that", "these", "those", "than", "then",
    "live", "update", "updates", "report", "reports", "amp", "news", "but",
    "not", "you", "your", "out", "off", "per", "via", "amid",
})


def _local_stem(word: str) -> str:
    """Very light suffix stripper (fallback only; real path uses Porter)."""
    w = word.lower()
    for suf in ("ational", "iness", "ingly", "edly", "ing", "ies", "ied",
                "ers", "er", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _local_title_stems(title: str) -> set[str]:
    words = re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", (title or "").lower())
    out: set[str] = set()
    for w in words:
        if len(w) < 3 or w in _LOCAL_STOPWORDS:
            continue
        out.add(_local_stem(w))
    return out


def _title_stems(title: str) -> set[str]:
    """Content-token stem set of a title. Prefers clustering's Porter stemmer
    (matches the upstream clusterer); falls back to a local stemmer offline."""
    fn = _cached("title_word_stems",
                 lambda: __import__(
                     "clustering.story_cluster", fromlist=["_title_word_stems"]
                 )._title_word_stems)
    if fn is not None:
        try:
            toks = fn(title or "")
            if toks:
                return set(toks)
        except Exception:
            pass
    return _local_title_stems(title or "")


def _ontopic_tokens(title: str) -> set[str]:
    """On-topic content tokens of a title, reusing the summarizer's exact
    on-topic vote helper when importable (the same lens RF-1 uses upstream)."""
    fn = _cached("ontopic_title_tokens",
                 lambda: __import__(
                     "summarizer.cluster_summarizer",
                     fromlist=["_ontopic_title_tokens"]
                 )._ontopic_title_tokens)
    if fn is not None:
        try:
            toks = fn(title or "")
            if toks:
                return set(toks)
        except Exception:
            pass
    return _local_title_stems(title or "")


# --- specific (high-IDF) stems ---------------------------------------------

def _feed_ranker():
    return _cached("feed_ranker",
                   lambda: __import__("ranker.feed_ranker",
                                      fromlist=["_specific_title_stems"]))


def _specific_stems(title: str) -> set[str]:
    """Distinctive (high-IDF) title stems: reuses feed_ranker._specific_title_stems
    when the clustering stemmer is available; otherwise computes locally as
    (title stems - generic geopolitical/role/wire words - common action verbs)
    using feed_ranker's own frozensets (which import with no heavy deps)."""
    fr = _feed_ranker()
    if fr is not None:
        try:
            toks = fr._specific_title_stems(title or "")
            if toks:
                return set(toks)
        except Exception:
            pass
    # Local fallback using feed_ranker's word lists (import-light constants).
    generic: frozenset = frozenset()
    action: frozenset = frozenset()
    if fr is not None:
        generic = getattr(fr, "_GENERIC_EVENT_WORDS", frozenset())
        action = getattr(fr, "_COMMON_ACTION_WORDS", frozenset())
    banned = {_local_stem(w) for w in (generic | action)} | (generic | action)
    return {s for s in _title_stems(title) if len(s) >= 3 and s not in banned}


# --- raw-excerpt detector (ported from summaryHygiene.ts) ------------------

# Ported 1:1 from frontend/app/lib/summaryHygiene.ts (RAW_EXCERPT_PATTERNS).
_RAW_EXCERPT_PATTERNS = [
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
    re.compile(r"\([^)]*/\s*(?:AFP|AP|Reuters|Getty|EPA|Bloomberg|Anadolu|Xinhua|AAP)\b", re.I),
    re.compile(r"[\s\-–—]+[a-z0-9-]+\.(?:com|org|net|gov|co\.[a-z]{2})\s*$", re.I),
]


def is_raw_excerpt(summary: str) -> bool:
    """True when a non-empty summary looks like a raw scraped excerpt, not prose.
    Deterministic Python port of summaryHygiene.ts isRawExcerpt()."""
    s = (summary or "").strip()
    if not s:
        return False
    for rx in _RAW_EXCERPT_PATTERNS:
        if rx.search(s):
            return True
    # Run-together words from a broken extraction ("reportingThe minister said").
    camel = len(re.findall(r"[a-z][A-Z]", s))
    if camel >= 3:
        return True
    # A single absurdly long token is almost always concatenated words / a slug.
    if re.search(r"\S{40,}", s):
        return True
    return False


# --- show-don't-tell / meta hygiene ----------------------------------------

# Local mirrors of the summarizer regexes (used only if the import fails).
_LOCAL_SDT = re.compile(
    r"\b(notable|notably|significant(ly)?|crucial(ly)?|interesting(ly)?|"
    r"it should be noted|it is worth noting|worth noting|"
    r"importantly|remarkably|strikingly)\b", re.I)
_LOCAL_META_BRACKET = re.compile(
    r"\s*\[[^\]]*?(?:cut[s]?\s+off|provided\s+(?:text|articles?)|"
    r"not\s+(?:available|provided|detailed|specified|clear))[^\]]*?\]", re.I)


def _sdt_pattern():
    return _cached("sdt_pattern", lambda: __import__(
        "summarizer.cluster_summarizer",
        fromlist=["_SHOW_DONT_TELL_PATTERN"])._SHOW_DONT_TELL_PATTERN) or _LOCAL_SDT


def _meta_bracket():
    return _cached("meta_bracket", lambda: __import__(
        "summarizer.cluster_summarizer",
        fromlist=["_META_BRACKET_RE"])._META_BRACKET_RE) or _LOCAL_META_BRACKET


def _meta_sent():
    return _cached("meta_sent", lambda: __import__(
        "summarizer.cluster_summarizer",
        fromlist=["_META_SENT_RE"])._META_SENT_RE)


# --- newsworthiness --------------------------------------------------------

def _newsworthiness():
    return _cached("newsworthiness", lambda: __import__(
        "categorizer.newsworthiness",
        fromlist=["newsworthiness"]).newsworthiness)


# --- cohesion --------------------------------------------------------------

def _cluster_cohesion_fn():
    return _cached("cluster_cohesion", lambda: __import__(
        "clustering.story_cluster",
        fromlist=["_cluster_cohesion"])._cluster_cohesion)


# ---------------------------------------------------------------------------
# Small text utilities
# ---------------------------------------------------------------------------

_DASH_RE = re.compile(r"[—–]")  # em dash / en dash


def _as_list(v: Any) -> list[str]:
    if not v:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x]
    return []


def _priority(base_p1: bool, position: int, both_positions: list[int] | None = None) -> str:
    """P0 when the finding touches the front page (top-10), else P1/P2."""
    positions = both_positions if both_positions is not None else [position]
    in_top10 = any(0 < p <= TOP10 for p in positions)
    if in_top10:
        return "P0"
    return "P1" if base_p1 else "P2"


# ---------------------------------------------------------------------------
# Checks — each returns list[Finding]
# ---------------------------------------------------------------------------

def check_coverage(clusters: list[dict]) -> list[Finding]:
    """RF-4: every displayed top-50 card must carry a non-empty summary AND a
    non-null summary_tier. A null/empty summary is CATASTROPHIC. A present but
    raw-excerpt-looking summary is WRONG (the frontend hygiene guard would blank
    it, leaving the card on its neutral pending line)."""
    out: list[Finding] = []
    for c in clusters:
        # Op-eds preserve original article text by design (no LLM summary tier).
        if (c.get("content_type") or "").lower() == "opinion":
            continue
        pos = c["position"]
        summary = (c.get("summary") or "").strip()
        tier = (c.get("summary_tier") or "").strip()
        if not summary or not tier:
            out.append(Finding(
                code="RF-4", grade="CATASTROPHIC",
                priority=_priority(True, pos), dimension="coverage",
                cluster_id=c["id"], cluster_title=c.get("title", ""),
                position=pos,
                message=(f"no usable summary (summary={'empty' if not summary else 'present'}, "
                         f"tier={tier or 'NULL'})"),
                evidence={"summary_present": bool(summary),
                          "summary_tier": tier or None},
            ))
        elif is_raw_excerpt(summary):
            out.append(Finding(
                code="RF-4", grade="WRONG",
                priority=_priority(True, pos), dimension="coverage",
                cluster_id=c["id"], cluster_title=c.get("title", ""),
                position=pos,
                message="summary looks like a raw scraped excerpt (would be blanked on the card)",
                evidence={"summary": summary[:280], "summary_tier": tier},
            ))
    return out


def check_hygiene(clusters: list[dict]) -> list[Finding]:
    """RF-11: scan summary/title/consensus/divergence for em/en dashes and
    show-don't-tell / source-meta patterns. Reuses the summarizer's own regexes.
    Graded ACCEPTABLE (P2) — an editorial tell, not a correctness failure."""
    out: list[Finding] = []
    sdt = _sdt_pattern()
    meta_bracket = _meta_bracket()
    meta_sent = _meta_sent()
    for c in clusters:
        pos = c["position"]
        title = c.get("title", "") or ""
        summary = c.get("summary", "") or ""
        consensus = _as_list(c.get("consensus_points"))
        divergence = _as_list(c.get("divergence_points"))
        blob = " ".join([title, summary, *consensus, *divergence])

        problems: list[str] = []
        # Em/en dashes are banned in all written editorial output (audio exempt,
        # not scanned here).
        if _DASH_RE.search(title):
            problems.append("em/en dash in title")
        if _DASH_RE.search(summary):
            problems.append("em/en dash in summary")
        if any(_DASH_RE.search(x) for x in consensus + divergence):
            problems.append("em/en dash in consensus/divergence")
        # Show-don't-tell asserted-significance words.
        sdt_hits = sorted({m.group(0).lower() for m in sdt.finditer(blob)})
        if sdt_hits:
            problems.append("show-don't-tell: " + ", ".join(sdt_hits))
        # Source-meta commentary leaking into the summary.
        if meta_bracket.search(summary) or (meta_sent and meta_sent.search(summary)):
            problems.append("source-meta commentary in summary")

        if problems:
            out.append(Finding(
                code="RF-11", grade="ACCEPTABLE",
                priority=_priority(False, pos), dimension="hygiene",
                cluster_id=c["id"], cluster_title=title, position=pos,
                message="; ".join(problems),
                evidence={"problems": problems},
            ))
    return out


def check_headline_summary_agreement(clusters: list[dict]) -> list[Finding]:
    """RF-3: stemmed SPECIFIC-token overlap between title and summary. A title
    with distinctive stems whose summary shares NONE of them is a candidate for
    the judge (emit both texts). Distinct from RF-1: this compares title vs
    summary directly; RF-1 compares summary vs the member-title topic."""
    out: list[Finding] = []
    for c in clusters:
        if (c.get("content_type") or "").lower() == "opinion":
            continue
        pos = c["position"]
        title = c.get("title", "") or ""
        summary = (c.get("summary") or "").strip()
        tier = (c.get("summary_tier") or "").strip()
        if not summary or not tier:
            continue  # coverage check owns the missing-summary case
        if is_raw_excerpt(summary):
            continue  # coverage check owns the raw-excerpt case
        title_specific = _specific_stems(title)
        if len(title_specific) < 2:
            continue  # too few distinctive stems to judge overlap meaningfully
        summary_stems = _title_stems(summary)
        overlap = title_specific & summary_stems
        if not overlap:
            out.append(Finding(
                code="RF-3", grade="WRONG", is_candidate=True,
                priority=_priority(True, pos), dimension="agreement",
                cluster_id=c["id"], cluster_title=title, position=pos,
                message=(f"summary shares 0 of {len(title_specific)} specific "
                         f"title stems ({', '.join(sorted(title_specific))})"),
                evidence={"title_specific_stems": sorted(title_specific)},
                judge_payload={
                    "question": "Does the summary describe the same story as the headline?",
                    "cluster_id": c["id"], "title": title, "summary": summary,
                },
            ))
    return out


def check_cross_contamination(clusters: list[dict]) -> list[Finding]:
    """RF-1 (PRIMARY): build the cluster's dominant-topic token set from its
    member article titles (the same on-topic vote the summarizer uses), then
    compare the summary's tokens against it. When the summary's tokens are
    DISJOINT from the dominant topic, the summary is likely describing a
    different event => candidate for the judge (emit summary + member titles)."""
    out: list[Finding] = []
    for c in clusters:
        if (c.get("content_type") or "").lower() == "opinion":
            continue
        pos = c["position"]
        summary = (c.get("summary") or "").strip()
        tier = (c.get("summary_tier") or "").strip()
        member_titles = c.get("member_titles") or []
        if not summary or not tier or is_raw_excerpt(summary):
            continue  # coverage owns these
        if len(member_titles) < 2:
            continue  # need a member-title vote to define the topic

        # Dominant topic = title tokens UNION tokens shared by >= 2 members
        # (mirrors cluster_summarizer._filter_ontopic_articles' core).
        from collections import Counter
        freq: Counter = Counter()
        for mt in member_titles:
            freq.update(_ontopic_tokens(mt))
        shared = {t for t, n in freq.items() if n >= 2}
        core = _ontopic_tokens(c.get("title", "") or "") | shared
        if not core:
            continue  # no reliable topic signal — do not flag

        summary_tokens = _ontopic_tokens(summary)
        if summary_tokens and not (summary_tokens & core):
            out.append(Finding(
                code="RF-1", grade="WRONG", is_candidate=True,
                priority=_priority(True, pos), dimension="contamination",
                cluster_id=c["id"], cluster_title=c.get("title", ""),
                position=pos,
                message=("summary tokens are disjoint from the cluster's "
                         "dominant topic (possible cross-contamination)"),
                evidence={
                    "dominant_topic": sorted(core)[:12],
                    "summary_tokens": sorted(summary_tokens)[:12],
                },
                judge_payload={
                    "question": ("Same event? Which event does the summary "
                                 "describe vs. the member headlines?"),
                    "cluster_id": c["id"],
                    "title": c.get("title", ""),
                    "summary": summary,
                    "member_titles": list(member_titles),
                },
            ))
    return out


def check_near_duplicates(clusters: list[dict]) -> list[Finding]:
    """RF-6: re-run feed_ranker's near-dup rules over the stored top-50 titles.
    Any surviving same-story pair is WRONG (P1; P0 if both in the top-10). Keeps
    the higher-sourced telling as the canonical one, mirroring the ranker."""
    fr = _feed_ranker()
    # Constants (mirror feed_ranker; fall back to its documented defaults).
    HARD = getattr(fr, "NEAR_DUP_SHARED_HARD", 4)
    SOFT = getattr(fr, "NEAR_DUP_SHARED_SOFT", 3)
    CONTAIN = getattr(fr, "NEAR_DUP_CONTAINMENT", 0.65)
    SPEC_MIN = getattr(fr, "NEAR_DUP_SPECIFIC_MIN", 2)
    contest_conflict = getattr(fr, "_contest_anchor_conflict", None)

    out: list[Finding] = []
    n = len(clusters)
    stem_sets = [_title_stems(c.get("title", "") or "") for c in clusters]
    spec_sets = [_specific_stems(c.get("title", "") or "") for c in clusters]
    flagged: set[int] = set()

    for i in range(n):
        if i in flagged or len(stem_sets[i]) < 3:
            continue
        for j in range(i + 1, n):
            if j in flagged or len(stem_sets[j]) < 3:
                continue
            shared = len(stem_sets[i] & stem_sets[j])
            smaller = min(len(stem_sets[i]), len(stem_sets[j])) or 1
            shared_specific = len(spec_sets[i] & spec_sets[j])
            conflict = bool(contest_conflict and contest_conflict(stem_sets[i], stem_sets[j]))
            specific_match = (shared >= SOFT and shared_specific >= SPEC_MIN
                              and not conflict)
            if (shared >= HARD or specific_match
                    or (shared >= SOFT and shared / smaller >= CONTAIN)):
                a, b = clusters[i], clusters[j]
                # Keep the higher-sourced telling; the other is the duplicate.
                keep, drop = (a, b) if (a.get("source_count", 0)
                                        >= b.get("source_count", 0)) else (b, a)
                positions = [a["position"], b["position"]]
                out.append(Finding(
                    code="RF-6", grade="WRONG",
                    priority=_priority(True, drop["position"], positions),
                    dimension="duplication",
                    cluster_id=drop["id"], cluster_title=drop.get("title", ""),
                    position=drop["position"],
                    message=(f"#{drop['position']} duplicates #{keep['position']} "
                             f"'{(keep.get('title') or '')[:60]}' "
                             f"({shared} shared stems, {shared_specific} specific)"),
                    evidence={
                        "kept_cluster_id": keep["id"],
                        "kept_title": keep.get("title", ""),
                        "kept_position": keep["position"],
                        "dup_title": drop.get("title", ""),
                        "shared_stems": sorted(stem_sets[i] & stem_sets[j]),
                        "shared_specific": sorted(spec_sets[i] & spec_sets[j]),
                    },
                ))
                flagged.add(j)  # don't re-pair the demoted one
    return out


def check_junk(clusters: list[dict]) -> list[Finding]:
    """RF-7: run the newsworthiness junk detector over the 50 titles. Any
    is_junk item is WRONG (P0 if in the top-10)."""
    nw = _newsworthiness()
    if nw is None:
        return []  # detector unavailable (heavy import failed) — skip silently
    out: list[Finding] = []
    for c in clusters:
        pos = c["position"]
        try:
            verdict = nw({"title": c.get("title", ""), "url": c.get("url", "")})
        except Exception:
            continue
        if verdict.get("is_junk"):
            out.append(Finding(
                code="RF-7", grade="WRONG",
                priority=_priority(True, pos), dimension="junk",
                cluster_id=c["id"], cluster_title=c.get("title", ""),
                position=pos,
                message=(f"evergreen/junk (score {verdict.get('score')} "
                         f">= {verdict.get('threshold')})"),
                evidence={"signals": verdict.get("signals"),
                          "score": verdict.get("score"),
                          "threshold": verdict.get("threshold")},
            ))
    return out


def _local_avg_title_jaccard(titles: list[str]) -> float:
    stems = [_title_stems(t) for t in titles]
    stems = [s for s in stems if s]
    if len(stems) < 2:
        return 1.0
    total, pairs = 0.0, 0
    for i in range(len(stems)):
        for j in range(i + 1, len(stems)):
            union = stems[i] | stems[j]
            if not union:
                continue
            total += len(stems[i] & stems[j]) / len(union)
            pairs += 1
    return (total / pairs) if pairs else 0.0


def _local_entity_convergence(titles: list[str]) -> float:
    """Fallback convergence proxy (no NER): coverage of the single most common
    specific title stem across member titles."""
    from collections import Counter
    freq: Counter = Counter()
    per_title = [_specific_stems(t) for t in titles]
    for s in per_title:
        freq.update(s)
    if not freq:
        return 0.0
    top = freq.most_common(1)[0][0]
    hits = sum(1 for s in per_title if top in s)
    return hits / len(titles) if titles else 0.0


def check_cohesion(clusters: list[dict]) -> list[Finding]:
    """RF-5: recompute cohesion signals from the stored members. A top-50
    cluster whose entity_convergence < floor AND avg_title_jaccard < floor is a
    candidate mis-titled bag (the MEGA_OVERMERGE_* over-merge condition). Uses
    story_cluster._cluster_cohesion when importable, else a local approximation
    (title-jaccard exact; entity_convergence approximated without NER)."""
    cohesion_fn = _cluster_cohesion_fn()
    sc_mod = _cached("story_cluster_mod", lambda: __import__(
        "clustering.story_cluster",
        fromlist=["MEGA_OVERMERGE_ENTITY_CONV_FLOOR"]))
    ent_floor = getattr(sc_mod, "MEGA_OVERMERGE_ENTITY_CONV_FLOOR",
                        _FALLBACK_ENTITY_CONV_FLOOR)
    jac_floor = getattr(sc_mod, "MEGA_OVERMERGE_TITLE_JACCARD_FLOOR",
                       _FALLBACK_TITLE_JACCARD_FLOOR)

    out: list[Finding] = []
    for c in clusters:
        members = c.get("member_articles") or []
        titles = [m.get("title", "") for m in members if m.get("title")]
        if len(titles) < MIN_COHESION_MEMBERS:
            continue

        approximated = False
        entity_conv = jaccard = None
        if cohesion_fn is not None:
            try:
                coh = cohesion_fn({"articles": members,
                                   "source_count": c.get("source_count", 0)})
                entity_conv = coh.get("entity_convergence")
                jaccard = coh.get("avg_title_jaccard")
            except Exception:
                entity_conv = jaccard = None
        if entity_conv is None or jaccard is None:
            approximated = True
            jaccard = _local_avg_title_jaccard(titles)
            entity_conv = _local_entity_convergence(titles)

        if entity_conv < ent_floor and jaccard < jac_floor:
            pos = c["position"]
            out.append(Finding(
                code="RF-5", grade="WRONG", is_candidate=True,
                priority=_priority(True, pos), dimension="cohesion",
                cluster_id=c["id"], cluster_title=c.get("title", ""),
                position=pos,
                message=(f"incoherent bag: entity_convergence={entity_conv:.2f} "
                         f"(<{ent_floor}) AND avg_title_jaccard={jaccard:.2f} "
                         f"(<{jac_floor}){' [approx]' if approximated else ''} "
                         f"over {len(titles)} members"),
                evidence={"entity_convergence": round(float(entity_conv), 3),
                          "avg_title_jaccard": round(float(jaccard), 3),
                          "n_members": len(titles),
                          "approximated": approximated},
                judge_payload={
                    "question": "Are these member headlines one event or a mis-merged bag?",
                    "cluster_id": c["id"],
                    "title": c.get("title", ""),
                    "member_titles": titles[:40],
                },
            ))
    return out


# ---------------------------------------------------------------------------
# Orchestration + scoring
# ---------------------------------------------------------------------------

_ALL_CHECKS: list[Callable[[list[dict]], list[Finding]]] = [
    check_coverage,
    check_cross_contamination,
    check_headline_summary_agreement,
    check_near_duplicates,
    check_junk,
    check_cohesion,
    check_hygiene,
]


def run_all_checks(clusters: list[dict]) -> list[Finding]:
    """Run every check over the displayed top-50 and return findings sorted
    P0 > P1 > P2 (then by grade severity, then display position)."""
    findings: list[Finding] = []
    for check in _ALL_CHECKS:
        try:
            findings.extend(check(clusters))
        except Exception as e:  # a broken check must never abort the eval
            print(f"  [warn] check {check.__name__} raised: {e}")
    findings.sort(key=lambda f: f.sort_key())
    return findings


def score_findings(findings: list[Finding]) -> ScoreReport:
    """Roll findings up into per-dimension scores (0-100) and an overall Feed
    Score. Each dimension starts at 100 and loses points per finding by grade;
    the Feed Score is the mean of the dimension scores, capped when any
    CATASTROPHIC finding exists (a single blanked card is a launch-blocker)."""
    dim_scores = {d: 100 for d in DIMENSIONS}
    counts_by_grade = {g: 0 for g in GRADES}
    counts_by_priority = {"P0": 0, "P1": 0, "P2": 0}
    n_candidates = 0

    has_catastrophic = False
    for f in findings:
        counts_by_grade[f.grade] = counts_by_grade.get(f.grade, 0) + 1
        counts_by_priority[f.priority] = counts_by_priority.get(f.priority, 0) + 1
        if f.is_candidate:
            n_candidates += 1
        if f.grade == "CATASTROPHIC":
            has_catastrophic = True
        dim = f.dimension if f.dimension in dim_scores else None
        if dim is not None:
            dim_scores[dim] = max(0, dim_scores[dim] - _GRADE_PENALTY.get(f.grade, 0))

    feed_score = round(sum(dim_scores.values()) / len(dim_scores))
    if has_catastrophic:
        feed_score = min(feed_score, 40)

    return ScoreReport(
        feed_score=feed_score,
        dimension_scores=dim_scores,
        counts_by_grade=counts_by_grade,
        counts_by_priority=counts_by_priority,
        n_findings=len(findings),
        n_candidates=n_candidates,
    )
