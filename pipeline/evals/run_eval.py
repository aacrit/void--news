"""Entry point for the Void News evaluation system (v1).

Fetches the DISPLAYED top-50 of the most recent daily run from Supabase
(read-only), runs every deterministic check, rolls the findings into a scored
report, and writes BOTH:

  - eval_report.json  — structured scores + findings + per-candidate judge payloads
  - eval_report.md    — a human-readable Feed Score + dimension scores + ranked
                        red-flag list (also printed to stdout)

Run:
    python -m pipeline.evals.run_eval

Read-only. No DB writes. No LLM calls. $0.

The LLM "judge" layer that confirms the CANDIDATE findings is intentionally OUT
of scope here — it runs separately as Claude agents over eval_report.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Mirror main.py's import bootstrap: put the pipeline dir on sys.path so the
# reused helpers can resolve their own `from clustering...`, `from ranker...`,
# `from summarizer...`, `from categorizer...` imports.
_PIPELINE_DIR = Path(__file__).resolve().parent.parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from evals import checks  # noqa: E402  (after sys.path bootstrap)

# Homepage window constants (mirror HomeContent + ensure_top50_summary_floor).
FETCH_LIMIT = 100      # HomeContent.FETCH_LIMIT
EDITION_FEED_SIZE = 50  # HomeContent.EDITION_FEED_SIZE (displayed top-50)
MIN_SOURCE_COUNT = 3    # only source_count>=3 rows occupy display slots
EDITION = "world"       # single daily feed

# Columns to pull for the clusters. Kept to known-present story_clusters columns
# (see HomeContent enrichedFields + insert_cluster).
_CLUSTER_COLS = (
    "id,title,summary,summary_tier,content_type,category,source_count,"
    "rank_world,headline_rank,consensus_points,divergence_points,sections"
)


# ---------------------------------------------------------------------------
# Data fetch (read-only)
# ---------------------------------------------------------------------------

def _fetch_displayed_top50(supabase) -> list[dict]:
    """Fetch the displayed top-50 exactly as the homepage renders it: order by
    rank_world desc, take up to FETCH_LIMIT, keep source_count>=3, first 50."""
    res = (
        supabase.table("story_clusters")
        .select(_CLUSTER_COLS)
        .contains("sections", [EDITION])
        .order("rank_world", desc=True)
        .limit(FETCH_LIMIT)
        .execute()
    )
    rows = res.data or []
    displayed: list[dict] = []
    for row in rows:
        if (row.get("source_count") or 0) < MIN_SOURCE_COUNT:
            continue
        row["position"] = len(displayed) + 1
        displayed.append(row)
        if len(displayed) >= EDITION_FEED_SIZE:
            break
    return displayed


def _paginated_in(supabase, table: str, cols: str, key: str,
                  ids: list[str], page: int = 1000) -> list[dict]:
    """Fetch rows where `key` IN ids, paginating past PostgREST's 1000-row cap
    via .range(). ids are chunked so each IN clause stays small."""
    out: list[dict] = []
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        start = 0
        while True:
            res = (
                supabase.table(table)
                .select(cols)
                .in_(key, chunk)
                .range(start, start + page - 1)
                .execute()
            )
            batch = res.data or []
            out.extend(batch)
            if len(batch) < page:
                break
            start += page
    return out


def _attach_member_titles(supabase, clusters: list[dict]) -> None:
    """Attach `member_titles` (list[str]) and `member_articles` (list[dict] with
    title + source_id) to each cluster, in-place. Several checks need them."""
    cluster_ids = [c["id"] for c in clusters]
    if not cluster_ids:
        return

    links = _paginated_in(
        supabase, "cluster_articles", "cluster_id,article_id",
        "cluster_id", cluster_ids)
    by_cluster: dict[str, list[str]] = {}
    for link in links:
        by_cluster.setdefault(link["cluster_id"], []).append(link["article_id"])

    all_article_ids = sorted({aid for ids in by_cluster.values() for aid in ids})
    articles = _paginated_in(
        supabase, "articles", "id,title,source_id",
        "id", all_article_ids)
    articles_by_id = {a["id"]: a for a in articles}

    for c in clusters:
        member_articles = [
            articles_by_id[aid]
            for aid in by_cluster.get(c["id"], [])
            if aid in articles_by_id
        ]
        c["member_articles"] = member_articles
        c["member_titles"] = [a.get("title", "") for a in member_articles
                              if a.get("title")]


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def build_json_report(clusters, findings, score) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "edition": EDITION,
        "clusters_evaluated": len(clusters),
        "feed_score": score.feed_score,
        "dimension_scores": score.dimension_scores,
        "counts_by_grade": score.counts_by_grade,
        "counts_by_priority": score.counts_by_priority,
        "n_findings": score.n_findings,
        "n_candidates": score.n_candidates,
        "red_flag_legend": {code: label for code, (_, label)
                            in checks.RED_FLAGS.items()},
        "findings": [f.to_dict() for f in findings],
        # Judge candidates broken out for the Claude-agent resolution layer.
        "judge_candidates": [
            {"code": f.code, "cluster_id": f.cluster_id,
             "position": f.position, **(f.judge_payload or {})}
            for f in findings if f.is_candidate
        ],
    }


def build_markdown_report(clusters, findings, score) -> str:
    lines: list[str] = []
    lines.append("# Void News - Feed Evaluation")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}  ")
    lines.append(f"Clusters evaluated: **{len(clusters)}** (displayed top-50, "
                 f"source_count >= {MIN_SOURCE_COUNT})")
    lines.append("")
    lines.append(f"## Feed Score: {score.feed_score} / 100")
    lines.append("")

    # Grade + priority summary.
    g = score.counts_by_grade
    p = score.counts_by_priority
    lines.append(f"- Findings: **{score.n_findings}** "
                 f"(judge candidates: {score.n_candidates})")
    lines.append(f"- By grade: CATASTROPHIC {g.get('CATASTROPHIC', 0)}, "
                 f"WRONG {g.get('WRONG', 0)}, ACCEPTABLE {g.get('ACCEPTABLE', 0)}")
    lines.append(f"- By priority: P0 {p.get('P0', 0)}, P1 {p.get('P1', 0)}, "
                 f"P2 {p.get('P2', 0)}")
    lines.append("")

    # Dimension scores table.
    lines.append("## Dimension scores")
    lines.append("")
    lines.append("| Dimension | Score |")
    lines.append("|---|---|")
    for dim in checks.DIMENSIONS:
        lines.append(f"| {dim} | {score.dimension_scores.get(dim, 100)} |")
    lines.append("")

    # Ranked red-flag list.
    lines.append("## Red flags (P0 > P1 > P2)")
    lines.append("")
    if not findings:
        lines.append("No red flags detected. Clean feed.")
    else:
        for f in findings:
            cand = " _(judge candidate)_" if f.is_candidate else ""
            title = (f.cluster_title or "").strip()
            pos = f"#{f.position}" if f.position else "—"
            lines.append(
                f"- **[{f.priority}] {f.code} · {f.grade}** {pos} "
                f"“{title[:80]}”{cand}  ")
            lines.append(f"  {f.message}")
    lines.append("")
    lines.append("---")
    lines.append("*Deterministic rule layer only. Judge/resolution is a "
                 "separate Claude-agent pass over `eval_report.json` "
                 "(`judge_candidates`).*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    out_dir = Path(os.environ.get("EVAL_OUT_DIR", ".")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from utils.supabase_client import supabase
    except Exception as e:
        print(f"[eval] FATAL: could not init Supabase client: {e}")
        return 2

    print("[eval] fetching displayed top-50 ...")
    clusters = _fetch_displayed_top50(supabase)
    print(f"[eval] {len(clusters)} clusters in the displayed window")
    _attach_member_titles(supabase, clusters)

    print("[eval] running checks ...")
    findings = checks.run_all_checks(clusters)
    score = checks.score_findings(findings)

    json_report = build_json_report(clusters, findings, score)
    md_report = build_markdown_report(clusters, findings, score)

    json_path = out_dir / "eval_report.json"
    md_path = out_dir / "eval_report.md"
    json_path.write_text(json.dumps(json_report, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    md_path.write_text(md_report, encoding="utf-8")

    print("\n" + md_report + "\n")
    print(f"[eval] wrote {json_path}")
    print(f"[eval] wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
