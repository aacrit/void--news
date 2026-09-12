"""Stage 2: the expensive, narrow half of the pipeline.

Stage 1 is cheap and broad. It fetches ~1,000 feeds, scrapes, scores six bias
axes and clusters the whole corpus, and it does that work on everything because
it has to: you cannot know which stories matter until you have them all.

Stage 2 is the opposite. It runs over ONE explicit set of clusters, chosen once
at step 8c.5, and every pass in it costs something a per-story pass should only
pay for a story that can still reach the page: an LLM summary, a second model
reading that summary, a validator sweep, a regeneration.

    8c.5  bench      the candidates, chosen once
    8d    summarize  every cache miss, on flash, in graduated batches
    8d.1  titles     normalize headlines before the ordering guards read them
    8d.2  critique   a second model reads each card against its articles
    8d.3  validate   deterministic rules; regenerate once; drop on a second fail
    8d.5  order      the final feed ordering, over the bench, lifted clear
    8d.6  floor      last resort, so no displayed card is ever a raw excerpt
    8f    print      the permanent archive of what was published

Before this module the sequence existed TWICE, in run_pipeline and in
run_editorial_stage, and the copies had already drifted: the standalone path
ordered the top 80 with its own limit, printed with a null run id and skipped
the near-duplicate log. One sequence, two callers.

The order is not arbitrary. Titles are cleaned before ordering because the
near-duplicate guard reads titles. Validation runs before ordering because a
drop must not leave a hole in the published feed. The floor runs after ordering
because it exists to cover a card the ordering PROMOTED into view.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, Optional

from utils.feed_config import ARCHIVE_CAP, CANDIDATES, DISPLAYED, POOL
from utils.display_window import (
    fetch_cluster_membership,
    fetch_display_pool,
    select_candidates,
)
from editorial import standard as std


# ---------------------------------------------------------------------------
# 8c.5: the bench
# ---------------------------------------------------------------------------

def select_bench(supabase, verbose: bool = True) -> list[str]:
    """The candidate ids, in rank order.

    A candidate is NOT a displayable card: a candidate has no summary yet, which
    is the whole point of Stage 2, so the display predicate's summary and tier
    tests would reject every one of them. The bench is the cheap half of that
    predicate (enough sources, not a ghost) applied to the post-rerank order.

    CANDIDATES exceeds DISPLAYED so the losses between here and the page (near
    duplicates, merges, validator drops) come out of the bench and not out of
    the reader's feed. Returns [] on failure, which every caller reads as "fall
    back to deriving your own window".
    """
    try:
        pool = fetch_display_pool(supabase, edition="world", pool=POOL)
        have_links = fetch_cluster_membership(supabase, [r["id"] for r in pool])
        bench = select_candidates(pool, CANDIDATES, have_links)
        ids = [r["id"] for r in bench]
        if verbose:
            print(f"\n[8c.5] Candidate bench: {len(ids)} of {len(pool)} pooled "
                  f"clusters (top {CANDIDATES} with >= 3 sources) for "
                  f"{DISPLAYED} display slots.")
            if len(ids) < DISPLAYED:
                print(f"  [warn] only {len(ids)} candidates for {DISPLAYED} "
                      f"slots: the feed will be short unless the floor "
                      f"rescues them")
        return ids
    except Exception as e:
        print(f"\n[8c.5] [warn] candidate selection failed, falling back to "
              f"per-pass windows: {e}")
        return []


# ---------------------------------------------------------------------------
# 8d.2 + 8d.3: critique, validate, regenerate once, drop
# ---------------------------------------------------------------------------

def _fetch_cards(supabase, cluster_ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(cluster_ids), 100):
        try:
            res = supabase.table("story_clusters").select(
                "id,title,summary,summary_tier,source_count,content_type"
            ).in_("id", cluster_ids[i:i + 100]).execute()
            for r in (res.data or []):
                out[r["id"]] = r
        except Exception as e:
            print(f"  [warn] editorial: card fetch failed: {e}")
    return out


def _fetch_articles_for(supabase, cluster_ids: list[str]) -> dict[str, list[dict]]:
    """Member articles per cluster, enriched with source name / tier / lean.

    Mirrors the enrichment the summarizer does, because the critique prompt
    names outlets and the regeneration path re-selects articles by lean spread.
    """
    links: dict[str, list[str]] = {}
    for i in range(0, len(cluster_ids), 100):
        try:
            res = supabase.table("cluster_articles").select(
                "cluster_id,article_id").in_(
                "cluster_id", cluster_ids[i:i + 100]).execute()
            for r in (res.data or []):
                links.setdefault(r["cluster_id"], []).append(r["article_id"])
        except Exception as e:
            print(f"  [warn] editorial: membership fetch failed: {e}")
            return {}
    all_ids = sorted({a for ids in links.values() for a in ids})
    by_id: dict[str, dict] = {}
    for i in range(0, len(all_ids), 200):
        try:
            res = supabase.table("articles").select(
                "id,title,summary,full_text,source_id,published_at,url"
            ).in_("id", all_ids[i:i + 200]).execute()
            for a in (res.data or []):
                by_id[a["id"]] = a
        except Exception as e:
            print(f"  [warn] editorial: article fetch failed: {e}")
            continue
    src_ids = sorted({a.get("source_id") for a in by_id.values() if a.get("source_id")})
    srcs: dict[str, dict] = {}
    for i in range(0, len(src_ids), 200):
        try:
            res = supabase.table("sources").select(
                "id,name,tier,political_lean_baseline"
            ).in_("id", src_ids[i:i + 200]).execute()
            for s in (res.data or []):
                srcs[s["id"]] = s
        except Exception as e:
            print(f"  [warn] editorial: source fetch failed: {e}")
            continue
    for a in by_id.values():
        s = srcs.get(a.get("source_id") or "", {})
        a.setdefault("source_name", s.get("name", ""))
        a.setdefault("tier", s.get("tier", ""))
        a.setdefault("source_lean_baseline", s.get("political_lean_baseline", ""))
    return {cid: [by_id[aid] for aid in aids if aid in by_id]
            for cid, aids in links.items()}


def _note(finding) -> str:
    return f"{finding.id}: {finding.message}"


def review_bench(supabase, candidate_ids: list[str],
                 run_critique: bool = True,
                 prefer_provider: str | None = "gemini") -> dict:
    """Steps 8d.2 and 8d.3 over the bench.

    Every candidate is read twice: by the deterministic validators in
    editorial.standard, and (budget permitting) by a second model checking the
    finished card against its own source articles. A card that fails either gets
    ONE regeneration that is TOLD what was wrong. A card that fails again is
    dropped from the bench, which is why the bench is larger than the feed.

    An ADVISORY finding is recorded and never causes a regeneration or a drop:
    the rules whose precision is not yet proven do not get to delete a story.

    Returns {survivors, dropped, regenerated, passed, candidates, by_id, worst}.
    """
    out = {"survivors": list(candidate_ids), "dropped": [], "regenerated": 0,
           "passed": 0, "candidates": len(candidate_ids), "by_id": {},
           "critiqued": 0}
    if not candidate_ids:
        return out

    from summarizer.cluster_summarizer import (  # heavy, pipeline-only
        _store_cluster_summary,
        critique_cards,
        summarize_cluster,
        is_available as llm_available,
    )

    cards = _fetch_cards(supabase, candidate_ids)
    articles = _fetch_articles_for(supabase, candidate_ids)

    # 8d.2: the second reader.
    critique: dict[str, list[tuple[str, str]]] = {}
    if run_critique and llm_available():
        print("\n[8d.2] Critique pass (a second model reads every card)...")
        recs = [{"cid": cid, "title": (cards.get(cid) or {}).get("title"),
                 "summary": (cards.get(cid) or {}).get("summary"),
                 "articles": articles.get(cid) or []}
                for cid in candidate_ids
                if (cards.get(cid) or {}).get("summary")]
        try:
            critique = critique_cards(recs, prefer_provider=prefer_provider)
            out["critiqued"] = len(recs)
            print(f"  Critique: {len(recs)} cards read, "
                  f"{len(critique)} carried a finding")
        except Exception as e:
            print(f"  [warn] critique pass failed (cards treated as clean): {e}")
    elif run_critique:
        print("\n[8d.2] Critique pass skipped (no LLM available).")

    # 8d.3: the deterministic rules, then one regeneration, then the drop.
    print("\n[8d.3] Editorial validation (regenerate once, then drop)...")
    all_findings: list = []
    survivors: list[str] = []
    dropped: list[tuple[str, str]] = []
    regenerated = 0
    for cid in candidate_ids:
        card = cards.get(cid)
        if not card:
            survivors.append(cid)
            continue
        findings = std.validate_candidate(card)
        all_findings.extend(findings)
        blocking = [f for f in findings
                    if std.VALIDATORS_BY_ID.get(f.id)
                    and std.VALIDATORS_BY_ID[f.id].status == std.ENFORCED]
        notes = [_note(f) for f in blocking]
        notes += [f"{rid}: {detail}" for rid, detail in critique.get(cid, [])]
        if not notes:
            survivors.append(cid)
            out["passed"] += 1
            continue

        arts = articles.get(cid) or []
        title = (card.get("title") or "")[:60]
        print(f"  [editorial] {cid[:8]} \"{title}\": "
              f"{', '.join(n.split(':')[0] for n in notes)}")
        if len(arts) < 3 or not llm_available():
            # Nothing to regenerate FROM. Keep the card: a thin cluster with a
            # flawed summary is still better than a hole, and the floor pass
            # will replace a summary that is actually unusable.
            survivors.append(cid)
            continue
        result = None
        try:
            result = summarize_cluster(arts, prefer_provider=prefer_provider,
                                       cluster_title=card.get("title"),
                                       revision_notes=notes)
        except Exception as e:
            print(f"    [warn] regeneration raised: {e}")
        if not result:
            survivors.append(cid)   # the model could not answer; not the card's fault
            continue
        recheck = std.validate_candidate(
            {"title": result.get("headline"), "summary": result.get("summary")})
        still = [f for f in recheck
                 if std.VALIDATORS_BY_ID.get(f.id)
                 and std.VALIDATORS_BY_ID[f.id].status == std.ENFORCED]
        if still:
            dropped.append((cid, still[0].id))
            print(f"    dropped: still fails {', '.join(f.id for f in still)}")
            continue
        try:
            from summarizer.cluster_summarizer import _content_hash
            # _store_cluster_summary records into `metrics`, including a
            # "failed" bump on its own exception path, so the dict has to carry
            # every key it touches.
            _store_cluster_summary(supabase, cid, result, _content_hash(arts),
                                   {"summarized": 0, "failed": 0,
                                    "updated_ids": [], "updated_summaries": {}})
            regenerated += 1
            survivors.append(cid)
            print("    regenerated, clean")
        except Exception as e:
            print(f"    [warn] regenerated summary write failed: {e}")
            survivors.append(cid)

    out["survivors"] = survivors
    out["dropped"] = [cid for cid, _ in dropped]
    out["regenerated"] = regenerated
    out["by_id"] = std.summarize(all_findings)
    out["worst"] = sorted(out["by_id"].items(), key=lambda kv: -kv[1])[:5]
    rate = (out["passed"] / out["candidates"] * 100) if out["candidates"] else 0.0
    worst = ", ".join(
        f"{k} x{v}" + (" (advisory)"
                       if (std.VALIDATORS_BY_ID.get(k)
                           and std.VALIDATORS_BY_ID[k].status == std.ADVISORY)
                       else "")
        for k, v in out["worst"]) or "none"
    print(f"  Editorial: {out['passed']}/{out['candidates']} candidates clean "
          f"({rate:.1f}%) | {regenerated} regenerated, {len(dropped)} dropped "
          f"| worst: {worst}")
    return out


# ---------------------------------------------------------------------------
# 8d.5: the final ordering, over the bench
# ---------------------------------------------------------------------------

def order_feed(supabase, sources, survivors: list[str], verbose: bool = True) -> int:
    """Re-run the feed ordering over the survivors and lift them clear.

    The gates here can demote a candidate. Before the bench existed, a demoted
    card simply swapped places with whatever sat at rank 36 in the raw pool: a
    cluster that was never summarized, never critiqued and never validated,
    walking into the displayed feed. Ordering the survivors and then lifting the
    whole set above every non-candidate makes "displayed is a subset of what
    Stage 2 examined" true by construction, not by hoping the gates stay gentle.
    """
    from ranker.feed_ranker import apply_feed_ordering

    res = supabase.table("story_clusters").select(
        "id,title,headline_rank,rank_world,content_type,category,source_count,"
        "sections,first_published,coverage_velocity,disaster_severity"
    ).contains("sections", ["world"]).order(
        "rank_world", desc=True).limit(POOL).execute()
    pool = res.data or []
    keep = set(survivors)
    rows = [r for r in pool if r["id"] in keep] if keep else pool
    others = [r for r in pool if r["id"] not in keep] if keep else []
    if not rows:
        return 0
    old = {r["id"]: r.get("rank_world") for r in rows}
    apply_feed_ordering(rows, sources)
    if keep and others:
        # A near-duplicate the guard just removed carries NEAR_DUP_REMOVED_RANK,
        # a NEGATIVE sentinel chosen so it sorts below every genuine rank and
        # falls out of the top-N cut. It must be excluded from the lift on both
        # sides, and the reason is arithmetic rather than tidiness.
        #
        # On 2026-09-09 it was not, and the sentinel became the minimum: floor
        # 46.04, low -1.0, so lift = 48.04 instead of the intended 0.32. Adding
        # 48.04 to a -1.0 sentinel produces +47.04, which puts the cluster the
        # guard had just REMOVED above all 65 non-candidates and ships it into
        # feed.json as row 35. The lift is meant to preserve an invariant and
        # instead it inverted one.
        removed = [r for r in rows if r.get("_near_dup_removed")
                   or (r.get("rank_world") or 0) < 0]
        genuine = [r for r in rows if r not in removed]
        if genuine:
            floor = max((r.get("rank_world") or 0) for r in others)
            low = min((r.get("rank_world") or 0) for r in genuine)
            lift = (floor + 1.0) - low
            if lift > 0:
                for r in genuine:
                    r["rank_world"] = round((r.get("rank_world") or 0) + lift, 2)
                if verbose:
                    print(f"  Bench lifted {lift:.1f} points clear of "
                          f"{len(others)} non-candidates (highest {floor:.1f})"
                          + (f"; {len(removed)} near-duplicate(s) left at their "
                             f"sentinel" if removed else ""))
    changed = 0
    for r in rows:
        new = r.get("rank_world", 0)
        if abs(new - (old.get(r["id"]) or 0)) > 0.01:
            supabase.table("story_clusters").update(
                {"rank_world": new}).eq("id", r["id"]).execute()
            changed += 1
    rows.sort(key=lambda r: r.get("rank_world", 0), reverse=True)
    if verbose:
        print(f"  Final ordering: {len(rows)} candidates, {changed} rank_world "
              f"updates. New top 5:")
        for i, r in enumerate(rows[:5], 1):
            dup = " [near-dup demoted]" if r.get("_near_dup_of") else ""
            print(f"   {i}. [{r.get('rank_world', 0):5.1f}] "
                  f"src={r.get('source_count', 0):3} "
                  f"{r.get('title', '')[:60]}{dup}")
        for r in [r for r in rows if r.get("_near_dup_of")][:5]:
            print(f"  [near-dup] demoted \"{r.get('title', '')[:55]}\" -> "
                  f"kept \"{r['_near_dup_of'][:55]}\"")
    return changed


# ---------------------------------------------------------------------------
# The sequence
# ---------------------------------------------------------------------------

def run_stage2(supabase, sources, *,
               run_id: Optional[str] = None,
               force_resummarize: bool = False,
               run_critique: bool = True,
               on_summaries: Optional[Callable[[dict], None]] = None) -> dict:
    """8c.5 through 8f. Returns the metrics the run summary reports.

    `on_summaries` receives summarize_top50_after_rerank's updated_summaries so
    the full pipeline can sync its in-memory cluster list; the standalone
    editorial path passes nothing.
    """
    from summarizer.cluster_summarizer import (
        ensure_top50_summary_floor,
        summarize_top50_after_rerank,
        is_available as llm_available,
        calls_remaining,
    )

    started = time.time()
    metrics: dict = {"summary": {}, "editorial": {}, "printed": 0}
    candidate_ids = select_bench(supabase)

    # 8c.6: candidate coherence. It runs BEFORE the merge, not after. Run the
    # other way round, the merge widens a cluster on purpose and the coherence
    # pass then judges the widened cluster against a modal vocabulary the
    # smaller half cannot reach: merging the Hegseth purge cluster into the
    # Pentagon polygraph cluster took it to 19 sources and the coherence pass
    # immediately removed 6 of the 8 it had just absorbed. Clean each cluster on
    # its own terms first, then decide which clean clusters are one event.
    if candidate_ids:
        print("\n[8c.6] Candidate coherence (members that share no vocabulary)...")
        try:
            from editorial.same_event import split_incoherent_candidates
            cm = split_incoherent_candidates(supabase, candidate_ids)
            metrics["coherence"] = cm
            print(f"  Trimmed {cm['trimmed']} cluster(s), {cm['removed']} members "
                  f"removed; {cm['reported']} reported not trimmed; "
                  f"{cm['abstained']} had no vocabulary to judge by")
        except Exception as e:
            print(f"  [warn] Coherence pass failed (bench unchanged): {e}")

    bench = candidate_ids or None

    # 8d: the one and only LLM summarization pass.
    if llm_available() and calls_remaining() > 0:
        print("\n[8d] Candidate summarization (batched, flash)...")
        try:
            sm = summarize_top50_after_rerank(
                supabase, edition="world", limit=CANDIDATES,
                prefer_provider="gemini", force_resummarize=force_resummarize,
                candidate_ids=bench)
            metrics["summary"] = sm
            print(f"  Candidates: {sm['summarized']} summarized, "
                  f"{sm['cached']} cache hits "
                  f"({sm.get('trimmed_cached', 0)} over-cap cached summaries "
                  f"trimmed in place), {sm['skipped']} skipped (op-ed / "
                  f"<3 sources), {sm['failed']} failed")
            if on_summaries:
                on_summaries(sm.get("updated_summaries", {}) or {})
        except Exception as e:
            print(f"  [warn] Candidate summarization failed: {e}")
    else:
        print("\n[8d] Candidate summarization skipped (no LLM budget).")

    # 8d.1: headlines, before the ordering guards read them.
    print("\n[8d.1] Pre-order title clean (null-tier candidates)...")
    try:
        tc = ensure_top50_summary_floor(
            supabase, edition="world", limit=CANDIDATES, title_only=True,
            candidate_ids=bench)
        print(f"  Title clean: {tc['checked']} null-tier cards, "
              f"{tc['titles_cleaned']} titles normalized")
    except Exception as e:
        print(f"  [warn] Pre-order title clean failed: {e}")

    # 8d.15: same-event merge, AFTER the titles are normalized.
    #
    # It used to run at 8c.7, before summarization, on whichever outlet headline
    # the cluster happened to carry. Step 8d then overwrites every title with
    # the LLM headline, so the gate was judging one set of words while the
    # near-duplicate guard at 8d.5 and the reader saw another.
    #
    # On 2026-09-09 that cost the feed its only real duplicate pair. The gate
    # saw "Republicans kick off a 'Trumpapalooza' of a midterm convention" and
    # rejected it; replaying the SAME gate over all 595 bench pairs using the
    # 8d titles yields exactly one merge and zero false positives, and it is
    # that pair: "Republicans Kick Off First Midterm Convention in Dallas,
    # Texas" (17 sources) and "Republicans Gather in Dallas for Trump-Centered
    # Midterm Convention" (9 sources), which share no outlet at all. Instead of
    # uniting 26 sources the near-dup guard demoted one and threw its nine away.
    #
    # The gate function is unchanged. It was never too strict; it was reading
    # the wrong input.
    if candidate_ids:
        print("\n[8d.15] Same-event merge (over the normalized headlines)...")
        try:
            from editorial.same_event import merge_candidates
            mm = merge_candidates(supabase, candidate_ids)
            metrics["merge"] = mm
            if mm["merged"]:
                absorbed = set(mm["absorbed"])
                candidate_ids = [c for c in candidate_ids if c not in absorbed]
                bench = candidate_ids or None
                # Refill the bench from the pool so a merge does not cost the
                # page a story: two cards became one, and the next-ranked
                # cluster takes the freed slot.
                for cid in select_bench(supabase, verbose=False):
                    if len(candidate_ids) >= CANDIDATES:
                        break
                    if cid not in candidate_ids and cid not in absorbed:
                        candidate_ids.append(cid)
                bench = candidate_ids or None
            print(f"  Merged {mm['merged']} pair(s) of {mm['examined']} examined; "
                  f"{mm['rejected']} near miss(es) logged; bench now "
                  f"{len(candidate_ids)}")
        except Exception as e:
            print(f"  [warn] Same-event merge failed (bench unchanged): {e}")

    # 8d.2 + 8d.3.
    survivors = list(candidate_ids)
    try:
        review = review_bench(supabase, candidate_ids, run_critique=run_critique)
        metrics["editorial"] = {k: v for k, v in review.items()
                                if k != "survivors"}
        survivors = review["survivors"]
    except Exception as e:
        print(f"  [warn] Editorial review failed (bench kept whole): {e}")

    # 8d.5.
    try:
        print("\n[8d.5] Final feed ordering (over the candidate bench)...")
        order_feed(supabase, sources, survivors)
    except Exception as e:
        print(f"  [warn] Final feed ordering failed (keeping 8c order): {e}")

    # 8d.6: the last resort.
    print("\n[8d.6] Final-order summary floor...")
    try:
        floor = ensure_top50_summary_floor(
            supabase, edition="world", limit=CANDIDATES,
            prefer_provider="gemini",
            candidate_ids=survivors or bench)
        metrics["floor"] = floor
        print(f"  Summary floor: {floor['checked']} cards needed a summary "
              f"(null OR raw excerpt) -> {floor['resummarized']} re-summarized "
              f"(LLM), {floor['sanitized']} cleaned (rule-based), "
              f"{floor.get('raw_excerpts_replaced', 0)} raw excerpts replaced, "
              f"{floor['still_null']} still without a summary")
    except Exception as e:
        print(f"  [warn] Final-order summary floor failed: {e}")

    # 8f: the record.
    try:
        print(f"\n[8f] Printing the record (permanent top-{ARCHIVE_CAP} archive)...")
        from archive.print_archive import archive_printed_edition
        by_id = {s.get("db_id"): s for s in sources if s.get("db_id")}
        pa = archive_printed_edition(
            supabase, sources_by_id=by_id,
            edition_date=datetime.now(timezone.utc).date(),
            pipeline_run_id=run_id)
        metrics["printed"] = pa.get("stories", 0)
        print(f"  Printed {pa['stories']} stories "
              f"({pa.get('threads_continued', 0)} continuing, "
              f"{pa.get('threads_new', 0)} new threads); archive "
              f"{pa.get('stats', {}).get('total_mb')} MB, "
              f"{pa.get('stats', {}).get('kb_per_day')} KB/day")
    except Exception as e:
        print(f"  [warn] Print archive failed (non-fatal): {e}")

    metrics["seconds"] = round(time.time() - started, 1)
    return metrics
