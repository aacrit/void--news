"""Same-event merge, in Stage 2, over the candidate bench.

Two disjoint clusters covering one real event ship as two cards with two source
counts, two summaries and two bias labels. On 2026-09-06 the feed carried the
Nepal flood rescue at 46 sources (rank 18) and 9 sources (rank 27), spelling the
survivor's name two ways, and the Pentagon polygraph story at 12 sources (rank
20) and 8 (rank 48).

Why the existing Phase 7 pass did not catch them
------------------------------------------------
Phase 7 (clustering/same_event_merge.py, disabled 2026-09-06 after it fused
unrelated events) is not too strict for these pairs. Measured against the
stored membership, BOTH pairs pass all three of its conjuncts: Nepal shares 3
salient entities and 2 title stems and the clusters are 23 minutes apart;
Pentagon shares 2 entities and 2 stems and is 7 hours apart. The gate never
rejected them because the gate never saw them. Phase 7's candidate set is the
top 50 clusters by source_count out of the whole 36-hour corpus, and the
partners have 9 and 8 sources. Inside the 100 clusters that even reached the
feed pool, 37 already carry more than 9 sources and 44 more than 8; the corpus
is roughly twenty times that size. The window was full long before it reached
them.

That is why this pass lives here. The bench is 35 clusters chosen by RANK, not
by raw source count, so the small half of a duplicate pair is in it precisely
because the ranker already thinks it belongs on the page.

The Pentagon pair also shows why entity overlap cannot carry the gate alone:
its two "shared salient entities" are `new york` and `york`, the New York Times
masthead leaking out of article titles. Mastheads are excluded here.

The gate
--------
Conjunctive, and every conjunct has to be earned:

    the two titles share at least MERGE_MIN_SHARED_STEMS SPECIFIC stems
    AND the clusters are within MERGE_TEMPORAL_HOURS
    AND at least one of those shared stems survives as an ANCHOR

"Specific" excludes the vocabulary any two same-day news stories share: day,
kill, strike, order, official, and the prepositions the tokenizer keeps ("into"
is why a Tesla autonomy probe and the US Open tennis draw shared two stems).
An anchor additionally excludes outlet mastheads (the Pentagon pair's only
shared entities were `new york` and `york`, the New York Times) and words that
are proper nouns in one headline and common verbs in another (Regulators OPEN
a probe; Alcaraz into the US OPEN). Demonyms are normalized, so "Nepal" and
"Nepali" are one anchor; without that the Nepal pair shares one stem, not two.

Deliberately NOT in the gate:

  * a numeric branch ("both mention a death toll"). It was the primary
    contamination path when Phase 7 shipped with it: it merged any two same-day
    casualty stories.
  * article cosine. Cross-cluster article cosine saturates near 1.0 on shared
    wire reprints, so it separates nothing.
  * topic_coherence. It scores any shared word as on topic and reported 1.00 on
    the Assam cluster at a true precision of 0.25.

Merging is pairwise into the higher-sourced survivor, with no transitive chains
and a ceiling of MERGE_CEILING absorbed clusters, so this can never manufacture
a mega-cluster. Bias is NEVER averaged: the merge writes the unioned membership
and then re-runs the pipeline's own aggregation over the merged article set, so
a 55 and a 42 become one number computed from all the articles.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from typing import Callable, Optional

from editorial.standard import title_word_stems

MERGE_TEMPORAL_HOURS = 48
MERGE_MIN_SHARED_STEMS = 2
MERGE_CEILING = 3

# Vocabulary any two same-day news stories share. A stem in here can never be
# one of the two specific stems, and can never be the anchor.
GENERIC_STEMS = frozenset({
    "day", "week", "month", "year", "time", "hour", "new", "old", "top",
    "kill", "dead", "death", "die", "injur", "wound", "toll", "victim",
    "strike", "attack", "hit", "blast", "fire", "crash", "explos",
    "order", "call", "say", "said", "tell", "warn", "urg", "vow", "plan",
    "leader", "presid", "minist", "offici", "author", "govern", "state",
    "polic", "court", "judg", "case", "probe", "investig", "arrest",
    "man", "woman", "peopl", "famili", "home", "citi", "town", "villag",
    "found", "face", "over", "sourc", "live", "updat", "latest",
    "recap", "roundup",
    # Prepositions and connectives the tokenizer keeps. "into" is why a Tesla
    # autonomy probe and the US Open tennis draw shared two stems.
    "into", "onto", "upon", "amid", "across", "within", "without",
    "toward", "after", "befor", "dure", "against", "among",
})

# Words that are proper nouns in one headline and common verbs or nouns in
# another. "Federal Regulators OPEN Probe Into Tesla" and "Alcaraz into US
# OPEN last 16" share the stem and share nothing else. This is the same class
# of bug as the ranker's "pla" matching "downplays": a lexical hit that carries
# no meaning. An ambiguous word can never be the anchor.
AMBIGUOUS_ANCHORS = frozenset({
    "open", "close", "post", "mail", "sun", "star", "march", "may",
    "will", "union", "standard", "record", "journal", "age", "hill",
    "point", "mark", "green", "brown", "young", "west", "east", "north",
    "south", "general", "nation", "capit", "counter", "bank",
})

# Demonym and adjectival forms that must resolve to one anchor. Keyed by the
# STEM the tokenizer produces.
_DEMONYM = {
    "nepali": "nepal", "nepales": "nepal",
    "israeli": "israel", "palestinian": "palestin",
    "russian": "russia", "ukrainian": "ukrain", "ukrain": "ukrain",
    "chines": "china", "japanes": "japan", "indian": "india",
    "iranian": "iran", "iraqi": "iraq", "syrian": "syria",
    "german": "germani", "french": "franc", "spanish": "spain",
    "britain": "british", "uk": "british", "american": "usa", "us": "usa",
    "mexican": "mexico", "brazilian": "brazil", "turkish": "turkey",
    "pakistani": "pakistan", "afghan": "afghanistan", "egyptian": "egypt",
    "nigerian": "nigeria", "kenyan": "kenya", "sudanes": "sudan",
    "korean": "korea", "vietnames": "vietnam", "thai": "thailand",
    "greek": "greec", "polish": "poland", "swedish": "sweden",
    "danish": "denmark", "dutch": "netherland", "italian": "itali",
}


def _norm(stem: str) -> str:
    return _DEMONYM.get(stem, stem)


def specific_stems(title: str) -> set[str]:
    """Title stems that could identify a story, demonyms normalized.

    Hyphenated tokens are NOT split here. The merge gate's error preference is
    precision: splitting "Nepal-Tibet Flood" into nepal and flood is enough to
    merge a Singapore xenophobia story into the Nepal rescue. The coherence
    pass, whose error preference is the opposite, uses topic_stems instead.
    """
    return {_norm(x) for x in title_word_stems(title)
            if _norm(x) not in GENERIC_STEMS and len(x) > 2}


def topic_stems(title: str) -> set[str]:
    """Like specific_stems, but a hyphenated token also contributes its parts.

    For the coherence pass, where a false flag deletes real coverage: without
    this a Bloomberg headline almost word for word the cluster's own title
    ("Germany's Far Right Heads for Historic State Win" against a cluster
    titled "Germany's Far-Right AfD Poised for Historic State Election
    Victory") reads as off topic on a hyphen.
    """
    raw = set(title_word_stems(title))
    for part in re.split(r"[-\u2010-\u2015]", (title or "").lower()):
        raw |= title_word_stems(part)
    return {_norm(x) for x in raw if _norm(x) not in GENERIC_STEMS and len(x) > 2}


_PROPER = re.compile(r"\b[A-Z][a-zA-Z'’-]{2,}")


def title_anchors(title: str) -> set[str]:
    """Capitalized content stems in a headline.

    Worth being honest about what this can and cannot do: news headlines are
    title case, so capitalization does NOT identify proper nouns here. In
    "Rescuers Pull Two People Alive From Nepal Debris" every content word is
    capitalized. What makes an anchor an anchor is therefore not the capital
    letter but the three exclusions applied to it in should_merge: outlet
    mastheads, the generic same-day vocabulary, and the ambiguous words. This
    function supplies the pool; those filters do the work.
    """
    words = _PROPER.findall(title or "")
    out: set[str] = set()
    for w in words:
        for s in specific_stems(w):
            out.add(s)
    return out


def masthead_tokens(source_names: list[str]) -> set[str]:
    """Stems of the outlet names covering a cluster.

    The Pentagon pair's only shared entities were `new york` and `york`. An
    outlet name is evidence about who reported a story, never about what the
    story is, so it cannot anchor a merge.
    """
    out: set[str] = set()
    for name in source_names or []:
        out |= title_word_stems(name)
    return {_norm(s) for s in out}


def _bias_reaggregator():
    """main._enrich_cluster_fallback, resolved without importing main.

    `from main import ...` is wrong here. Under `python pipeline/main.py` the
    orchestrator is the module `__main__`, so importing `main` would load
    main.py a SECOND time under a different name and re-run its top level. Look
    it up in whichever module object is already loaded instead.

    Returns None when neither is present (a unit test importing this module on
    its own), and the caller then leaves the pre-merge bias in place rather
    than writing an average of two clusters, which is the one thing this pass
    must never do.
    """
    for name in ("main", "__main__"):
        mod = sys.modules.get(name)
        fn = getattr(mod, "_enrich_cluster_fallback", None)
        if callable(fn):
            return fn
    return None


def _parse_ts(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00").replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def should_merge(a: dict, b: dict) -> tuple[bool, str]:
    """The gate, as a pure function of two cluster dicts.

    Each dict needs: title, first_published, and optionally entities (a set of
    salient entity strings) and mastheads (a set of outlet-name stems). Returns
    (merge, reason); `reason` names the branch on a pass and the FAILING
    conjunct on a reject, which is what the run log records for every rejected
    pair that shared a stem.
    """
    stems_a = specific_stems(a.get("title") or "")
    stems_b = specific_stems(b.get("title") or "")
    shared_stems = stems_a & stems_b
    if len(shared_stems) < MERGE_MIN_SHARED_STEMS:
        return False, f"stems({len(shared_stems)}<{MERGE_MIN_SHARED_STEMS})"

    ts_a, ts_b = _parse_ts(a.get("first_published")), _parse_ts(b.get("first_published"))
    if ts_a and ts_b:
        hours = abs((ts_a - ts_b).total_seconds()) / 3600.0
        if hours > MERGE_TEMPORAL_HOURS:
            return False, f"temporal({hours:.0f}h>{MERGE_TEMPORAL_HOURS}h)"

    mast = (a.get("mastheads") or set()) | (b.get("mastheads") or set())
    anchors = ((title_anchors(a.get("title") or "") & title_anchors(b.get("title") or ""))
               | ({_norm(e) for e in (a.get("entities") or set())}
                  & {_norm(e) for e in (b.get("entities") or set())}))
    anchors = {x for x in anchors
               if x not in mast
               and x not in GENERIC_STEMS
               and x not in AMBIGUOUS_ANCHORS}
    if not anchors:
        return False, "anchor(none outside mastheads and ambiguous words)"
    # The two shared stems have to include the anchor. Two clusters that agree
    # on WHAT happened but not on WHO or WHERE are two stories.
    if not (anchors & shared_stems):
        return False, f"anchor({sorted(anchors)[:2]}) not among shared stems"

    return True, f"anchor({sorted(anchors)[:2]})+stems({sorted(shared_stems)[:3]})"


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------

def merge_candidates(supabase, candidate_ids: list[str],
                     log_fn: Optional[Callable[[str], None]] = None) -> dict:
    """Merge same-event fragments among the bench. Returns metrics.

    Writes: the survivor absorbs the other's cluster_articles links, the
    absorbed row is deleted, source_count is recomputed from the union of
    DISTINCT sources (never a sum, which double-counts a source present in
    both), and the survivor's bias is re-aggregated from the merged article set
    by the pipeline's own enrichment path. The survivor keeps its own title,
    which is the higher-sourced one.

    Never raises: on any unexpected failure it logs and leaves the bench alone.
    """
    log = log_fn or (lambda m: print(m))
    metrics = {"merged": 0, "absorbed": [], "examined": 0, "rejected": 0}
    if len(candidate_ids) < 2:
        return metrics
    try:
        rows: dict[str, dict] = {}
        for i in range(0, len(candidate_ids), 100):
            res = supabase.table("story_clusters").select(
                "id,title,source_count,first_published,bias_diversity"
            ).in_("id", candidate_ids[i:i + 100]).execute()
            for r in (res.data or []):
                rows[r["id"]] = r
        order = [cid for cid in candidate_ids if cid in rows]
        if len(order) < 2:
            return metrics

        # Membership and outlet names, for the source recount and the masthead
        # exclusion. One read each, not one per pair.
        links: dict[str, list[str]] = {}
        for i in range(0, len(order), 100):
            res = supabase.table("cluster_articles").select(
                "cluster_id,article_id").in_("cluster_id", order[i:i + 100]).execute()
            for r in (res.data or []):
                links.setdefault(r["cluster_id"], []).append(r["article_id"])
        all_arts = sorted({a for ids in links.values() for a in ids})
        art_src: dict[str, str] = {}
        for i in range(0, len(all_arts), 200):
            res = supabase.table("articles").select("id,source_id").in_(
                "id", all_arts[i:i + 200]).execute()
            for a in (res.data or []):
                art_src[a["id"]] = a.get("source_id") or ""
        src_ids = sorted({v for v in art_src.values() if v})
        src_name: dict[str, str] = {}
        for i in range(0, len(src_ids), 200):
            res = supabase.table("sources").select("id,name").in_(
                "id", src_ids[i:i + 200]).execute()
            for s in (res.data or []):
                src_name[s["id"]] = s.get("name") or ""

        info: dict[str, dict] = {}
        for cid in order:
            aids = links.get(cid, [])
            srcs = {art_src.get(a, "") for a in aids} - {""}
            info[cid] = {
                "title": rows[cid].get("title") or "",
                "first_published": rows[cid].get("first_published"),
                "source_count": rows[cid].get("source_count") or 0,
                "articles": set(aids),
                "sources": srcs,
                "mastheads": masthead_tokens([src_name.get(s, "") for s in srcs]),
                "entities": set(),
            }

        absorbed: set[str] = set()
        load: dict[str, int] = {cid: 1 for cid in order}
        for i, a in enumerate(order):
            if a in absorbed:
                continue
            for b in order[i + 1:]:
                if b in absorbed:
                    continue
                # Pairwise into the survivor only: no transitive chains, so a
                # merged cluster can never become the bridge between two
                # clusters that would never have merged with each other.
                if load[a] + 1 > MERGE_CEILING:
                    break
                ok, reason = should_merge(info[a], info[b])
                metrics["examined"] += 1
                if not ok:
                    # Only log a near miss: a pair with nothing in common is
                    # noise, a pair that shared a stem is a judgement call
                    # someone may want to review.
                    if reason.startswith("stems(0") or reason.startswith("stems(1"):
                        continue
                    metrics["rejected"] += 1
                    log(f"  [merge-reject] \"{info[a]['title'][:44]}\" vs "
                        f"\"{info[b]['title'][:44]}\": {reason}")
                    continue

                keep, drop = (a, b) if info[a]["source_count"] >= info[b]["source_count"] else (b, a)
                lean_k = (rows[keep].get("bias_diversity") or {}).get("avg_political_lean")
                lean_d = (rows[drop].get("bias_diversity") or {}).get("avg_political_lean")
                new_links = info[drop]["articles"] - info[keep]["articles"]
                try:
                    if new_links:
                        supabase.table("cluster_articles").upsert(
                            [{"cluster_id": keep, "article_id": aid}
                             for aid in sorted(new_links)],
                            on_conflict="cluster_id,article_id").execute()
                    supabase.table("cluster_articles").delete().eq(
                        "cluster_id", drop).execute()
                    merged_sources = info[keep]["sources"] | info[drop]["sources"]
                    supabase.table("story_clusters").update(
                        {"source_count": len(merged_sources)}).eq("id", keep).execute()
                    supabase.table("story_clusters").delete().eq("id", drop).execute()
                except Exception as e:
                    log(f"  [warn][merge] write failed, pair skipped: {e}")
                    continue

                info[keep]["articles"] |= info[drop]["articles"]
                info[keep]["sources"] = merged_sources
                info[keep]["source_count"] = len(merged_sources)
                info[keep]["mastheads"] |= info[drop]["mastheads"]
                load[keep] += load[drop]
                absorbed.add(drop)
                metrics["merged"] += 1
                metrics["absorbed"].append(drop)
                log(f"  [merge] KEEP[{rows[keep].get('source_count')}src lean={lean_k}] "
                    f"\"{info[keep]['title'][:44]}\" <- "
                    f"ABSORB[{rows[drop].get('source_count')}src lean={lean_d}] "
                    f"\"{info[drop]['title'][:44]}\" -> {len(merged_sources)} sources, "
                    f"{reason}")

        if absorbed:
            # Bias from the MERGED set, computed by the pipeline's own
            # aggregation. Never (55 + 42) / 2.
            enrich = _bias_reaggregator()
            for cid in {c for c in order if c not in absorbed and load[c] > 1}:
                if enrich is None:
                    log("  [warn][merge] bias re-aggregation unavailable; the "
                        "survivor keeps the pre-merge numbers until the next run")
                    break
                try:
                    enrich(cid, skip_text=False)
                    log(f"  [merge] re-aggregated bias for {cid[:8]} "
                        f"from {len(info[cid]['articles'])} merged articles")
                except Exception as e:
                    log(f"  [warn][merge] bias re-aggregation failed for {cid[:8]}: {e}")
        return metrics
    except Exception as e:
        log(f"  [warn][merge] pass skipped ({type(e).__name__}: {e})")
        return metrics


# ---------------------------------------------------------------------------
# Step 8c.7: candidate coherence
# ---------------------------------------------------------------------------
# Merging does not fix a contaminated cluster; it makes a bigger one. On
# 2026-09-06 the feed carried "Russia Loads First Crude Oil on Arctic Tanker"
# whose 6 members were 2 stories about the tanker and 4 about a NATO exercise,
# EU energy policy, an Arctic power struggle and sea-ice observation, joined by
# the single word "Arctic"; "Trump Threatens Iran's Pickaxe Mountain" carried a
# member titled "Morning recap"; and a local paper's whole Saturday output rode
# in on one BYU football card.
#
# The measure is the cluster's OWN modal vocabulary, not its title. Comparing
# each member to the title reads a differently-worded report of the same event
# as off topic: four members of the Putin ceasefire cluster say "Putin orders
# three-day halt to strikes on Kiev" where the title says "Suspends Kyiv
# Strikes for 72 Hours", and a title-based rule flags all four. Modal
# vocabulary (stems in at least MODAL_MIN of member headlines, minus the broad
# geographic terms that join anything) keeps them and still catches the tanker.
#
# topic_coherence is not used and never should be: it scores any shared word as
# on topic and reported 1.00 on the Assam cluster at a true precision of 0.25.

MODAL_MIN = 0.30          # a stem is modal at this share of member headlines
MODAL_MIN_STEMS = 3       # below this the cluster has no vocabulary to judge by.
                          # Three, not two: the 25-member Ukraine wire bag
                          # spanning Mykolaiv, Kherson, Dnipropetrovsk and
                          # Donetsk has a modal vocabulary of exactly {forces,
                          # region}, and trimming 8 of its members would pick an
                          # arbitrary half of a cluster that has no core at all.
                          # That is a clustering defect; this pass abstains.

# Regions and nationalities broad enough to join unrelated events. Kept small
# and geographic ON PURPOSE: an earlier draft also listed the topic words
# (strike, election, price, politics) and that flagged the Putin ceasefire
# reports, the AfD election coverage and two on-topic fuel-price stories.
BROAD_GEOGRAPHY = frozenset("""
arctic africa asia europ american usa uk british britain china chines
russia russian iran iranian israel israeli india indian pakistan japan japanes
korea german germani franc french spain spanish itali ukrain ukrainian
nato eu turkey turkish brazil mexico canada australia middl east west
""".split())


def modal_vocabulary(member_titles: list[str]) -> set[str]:
    """Stems carried by at least MODAL_MIN of the member headlines."""
    if not member_titles:
        return set()
    counts: dict[str, int] = {}
    for t in member_titles:
        for s in topic_stems(t):
            counts[s] = counts.get(s, 0) + 1
    n = len(member_titles)
    return {s for s, k in counts.items()
            if k / n >= MODAL_MIN and s not in BROAD_GEOGRAPHY}


def incoherent_members(member_titles: list[str]) -> tuple[list[int], set[str]]:
    """Indices of members sharing NO modal stem, plus the modal vocabulary.

    Returns ([], vocabulary) when the cluster has fewer than MODAL_MIN_STEMS
    modal stems: with no vocabulary of its own there is nothing to be off topic
    against, and guessing there would delete real coverage.
    """
    vocab = modal_vocabulary(member_titles)
    if len(vocab) < MODAL_MIN_STEMS:
        return [], vocab
    return [i for i, t in enumerate(member_titles)
            if not (topic_stems(t) & vocab)], vocab


MIN_MEMBERS_TO_TRIM = 6   # below this one removal is a large share of a small
                          # cluster, and the borderline calls (a wire stub with
                          # a generic headline) cost more than they fix.


def split_incoherent_candidates(supabase, candidate_ids: list[str],
                                log_fn: Optional[Callable[[str], None]] = None) -> dict:
    """Step 8c.7: remove members that share no vocabulary with their cluster.

    A trimmed cluster has its source_count recomputed from the DISTINCT sources
    that remain, its bias re-aggregated over the cleaned membership, and its
    summary cache INVALIDATED, so step 8d rewrites the headline and summary from
    what the cluster actually contains rather than serving yesterday's text
    about a membership that no longer exists.

    A removed article is only unlinked, never deleted. It stays in the 36-hour
    window and is re-clustered on the next run.

    Reports, but does not trim, when the cluster is small or when more than half
    its members are off vocabulary: at that point there is no core to keep and
    trimming would choose an arbitrary half.
    """
    log = log_fn or (lambda m: print(m))
    metrics = {"trimmed": 0, "removed": 0, "reported": 0, "abstained": 0}
    if not candidate_ids:
        return metrics
    try:
        links: dict[str, list[str]] = {}
        for i in range(0, len(candidate_ids), 100):
            res = supabase.table("cluster_articles").select(
                "cluster_id,article_id").in_(
                "cluster_id", candidate_ids[i:i + 100]).execute()
            for r in (res.data or []):
                links.setdefault(r["cluster_id"], []).append(r["article_id"])
        all_ids = sorted({a for v in links.values() for a in v})
        arts: dict[str, dict] = {}
        for i in range(0, len(all_ids), 200):
            res = supabase.table("articles").select("id,title,source_id").in_(
                "id", all_ids[i:i + 200]).execute()
            for a in (res.data or []):
                arts[a["id"]] = a
        titles_by_cluster: dict[str, dict] = {}
        for i in range(0, len(candidate_ids), 100):
            res = supabase.table("story_clusters").select("id,title").in_(
                "id", candidate_ids[i:i + 100]).execute()
            for r in (res.data or []):
                titles_by_cluster[r["id"]] = r.get("title") or ""

        for cid in candidate_ids:
            aids = [a for a in links.get(cid, []) if a in arts]
            if len(aids) < 3:
                continue
            member_titles = [arts[a].get("title") or "" for a in aids]
            idx, vocab = incoherent_members(member_titles)
            if len(vocab) < MODAL_MIN_STEMS:
                metrics["abstained"] += 1
                continue
            if not idx:
                continue
            head = titles_by_cluster.get(cid, "")[:44]
            if len(aids) < MIN_MEMBERS_TO_TRIM or len(idx) * 2 > len(aids):
                metrics["reported"] += 1
                log(f"  [coherence-report] \"{head}\": {len(idx)} of {len(aids)} "
                    f"members share none of {sorted(vocab)[:4]}, not trimmed "
                    f"({'too small' if len(aids) < MIN_MEMBERS_TO_TRIM else 'no core'})")
                continue

            drop = [aids[i] for i in idx]
            try:
                for aid in drop:
                    supabase.table("cluster_articles").delete().eq(
                        "cluster_id", cid).eq("article_id", aid).execute()
                keep = [a for a in aids if a not in set(drop)]
                srcs = {arts[a].get("source_id") for a in keep} - {None, ""}
                supabase.table("story_clusters").update({
                    "source_count": len(srcs),
                    # The stored summary was written from the contaminated
                    # membership. Clearing the cache key and the tier makes 8d
                    # treat this as a miss and rewrite the card.
                    "summary_tier": None,
                    "summary_article_hash": None,
                }).eq("id", cid).execute()
            except Exception as e:
                log(f"  [warn][coherence] write failed for {cid[:8]}: {e}")
                continue
            metrics["trimmed"] += 1
            metrics["removed"] += len(drop)
            for i in idx:
                log(f"  [coherence] \"{head}\" -> removed "
                    f"\"{member_titles[i][:58]}\"")
            log(f"  [coherence] \"{head}\": {len(keep)} members, "
                f"{len(srcs)} sources, summary invalidated")
            try:
                enrich = _bias_reaggregator()
                if enrich is not None:
                    enrich(cid, skip_text=False)
            except Exception as e:
                log(f"  [warn][coherence] bias re-aggregation failed for {cid[:8]}: {e}")
        return metrics
    except Exception as e:
        log(f"  [warn][coherence] pass skipped ({type(e).__name__}: {e})")
        return metrics
