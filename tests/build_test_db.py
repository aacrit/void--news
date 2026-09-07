#!/usr/bin/env python3
"""Build a realistic pipeline state DB from the committed feed snapshots.

The repo has never had a way to run the editorial half of the pipeline offline.
Every change to main.py's step ordering, the summary window, the print archive
or the static export has therefore been compile-checked and then shipped
straight into the 11:00 UTC production run, which is how a dead re-rank went
unnoticed for weeks and a permalink gap shipped for six consecutive editions.

This builds `pipeline_state.db` from data already in git: `feed.json` supplies
story_clusters, `public/data/deepdive/<id>.json` supplies articles, sources and
bias_scores, and the printed edition in `archive.json` supplies printed_stories.
With it:

    python tests/build_test_db.py --out /tmp/state.db
    VOID_SQLITE_PATH=/tmp/state.db DISABLE_ANTHROPIC=1 \
        python pipeline/main.py --editorial-only        # no GEMINI_API_KEY: no LLM calls
    VOID_SQLITE_PATH=/tmp/state.db python pipeline/export_static.py

Read-only with respect to the repo: it reads committed JSON and writes only the
DB path given.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "migration" / "schema_pipeline.sql"


def _read(path: str, commit: str | None) -> str:
    if commit:
        return subprocess.check_output(["git", "show", f"{commit}:{path}"],
                                       text=True, cwd=ROOT)
    return (ROOT / path).read_text()


def _deepdive(cluster_id: str, commit: str | None) -> list[dict]:
    rel = f"frontend/public/data/deepdive/{cluster_id}.json"
    try:
        return json.loads(_read(rel, commit))
    except Exception:
        return []


def build(out: Path, commit: str | None = None, clusters_limit: int = 100) -> dict:
    if out.exists():
        out.unlink()
    conn = sqlite3.connect(out)
    conn.executescript(SCHEMA.read_text())
    conn.execute("PRAGMA foreign_keys = ON")

    feed = json.loads(_read("frontend/build-data/feed.json", commit))
    clusters = feed["clusters"][:clusters_limit]
    built_at = feed.get("builtAt")

    cluster_cols = {r[1] for r in conn.execute("PRAGMA table_info(story_clusters)")}
    stats = {"clusters": 0, "articles": 0, "sources": 0, "bias": 0, "links": 0,
             "printed": 0}
    seen_sources: dict[str, str] = {}
    seen_articles: set[str] = set()

    for c in clusters:
        row = {k: v for k, v in c.items() if k in cluster_cols}
        row["sections"] = "{world}"          # pg array literal, as the shim expects
        row.setdefault("section", "world")
        for k in ("bias_diversity", "consensus_points", "divergence_points",
                  "claim_consensus"):
            if isinstance(row.get(k), (dict, list)):
                row[k] = json.dumps(row[k])
        row.setdefault("content_type", "reporting")
        row.setdefault("last_updated", built_at)
        cols = ",".join(f'"{k}"' for k in row)
        conn.execute(f"INSERT INTO story_clusters ({cols}) VALUES "
                     f"({','.join('?' for _ in row)})", list(row.values()))
        stats["clusters"] += 1

        for entry in _deepdive(c["id"], commit):
            art = entry.get("article") or {}
            aid = art.get("id")
            if not aid:
                continue
            src = art.get("source") or {}
            sname = src.get("name") or "Unknown"
            if sname not in seen_sources:
                sid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"source:{sname}"))
                slug = (sname.lower().replace(" ", "-").replace("(", "")
                        .replace(")", "").replace("'", "")[:60] or "unknown")
                tier = src.get("tier") or "independent"
                if tier not in ("us_major", "international", "independent"):
                    tier = "independent"
                conn.execute(
                    "INSERT OR IGNORE INTO sources "
                    "(id, slug, name, url, tier, country, type, political_lean_baseline) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (sid, slug, sname, src.get("url") or f"https://{slug}.example",
                     tier, "unknown", "news", "center"))
                seen_sources[sname] = sid
                stats["sources"] += 1
            sid = seen_sources[sname]

            if aid not in seen_articles:
                conn.execute(
                    "INSERT INTO articles (id, source_id, url, title, summary, "
                    "full_text, published_at, section, image_url) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (aid, sid, art.get("url") or f"https://example.invalid/{aid}",
                     art.get("title") or "Untitled", art.get("summary"),
                     art.get("summary"), art.get("published_at"), "world",
                     art.get("image_url")))
                seen_articles.add(aid)
                stats["articles"] += 1
                scores = (art.get("bias_scores") or [None])[0]
                if scores:
                    rationale = scores.get("rationale")
                    conn.execute(
                        "INSERT INTO bias_scores (id, article_id, political_lean, "
                        "sensationalism, opinion_fact, factual_rigor, framing, "
                        "confidence, rationale) VALUES (?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), aid, scores.get("political_lean"),
                         scores.get("sensationalism"), scores.get("opinion_fact"),
                         scores.get("factual_rigor"), scores.get("framing"),
                         scores.get("confidence") or 0.5,
                         json.dumps(rationale) if isinstance(rationale, (dict, list))
                         else (rationale or "{}")))
                    stats["bias"] += 1
            conn.execute("INSERT OR IGNORE INTO cluster_articles VALUES (?,?)",
                         (c["id"], aid))
            stats["links"] += 1

    # printed_stories for the latest edition, so the archive and permalink map
    # have a prior day to reconcile against.
    try:
        archive = json.loads(_read("frontend/build-data/archive.json", commit))
        printed_cols = {r[1] for r in conn.execute("PRAGMA table_info(printed_stories)")}
        days = sorted({r["printed_on"] for r in archive}, reverse=True)[:2]
        # printed_stories.printed_on is an FK to printed_days, so the day rows
        # go in FIRST. (source_cluster_id has no FK: an archived edition
        # legitimately references clusters retention has since deleted.)
        for d in days:
            conn.execute("INSERT OR IGNORE INTO printed_days (printed_on) VALUES (?)", (d,))
        loaded = {r.get("id") for r in archive if r.get("printed_on") in days}
        # continues_printed_id is a self-FK. Rows arrive in edition order, so a
        # forward reference would fail the constraint on insert; insert every
        # row with the link null and set the links that stay inside the loaded
        # window in a second pass. Chains reaching further back stay null.
        chains = []
        for r in archive:
            if r.get("printed_on") not in days:
                continue
            row = {k: v for k, v in r.items() if k in printed_cols}
            cont = row.get("continues_printed_id")
            row["continues_printed_id"] = None
            for k, v in list(row.items()):
                if isinstance(v, (dict, list)):
                    row[k] = json.dumps(v)
            cols = ",".join(f'"{k}"' for k in row)
            try:
                conn.execute(f"INSERT INTO printed_stories ({cols}) VALUES "
                             f"({','.join('?' for _ in row)})", list(row.values()))
                stats["printed"] += 1
                if cont in loaded:
                    chains.append((cont, r["id"]))
            except sqlite3.Error as e:
                print(f"  [warn] printed row skipped: {e}")
        for cont, rid in chains:
            conn.execute("UPDATE printed_stories SET continues_printed_id = ? "
                         "WHERE id = ?", (cont, rid))
    except Exception as e:
        print(f"  [warn] printed_stories not loaded: {e}")

    conn.execute(
        "INSERT INTO pipeline_runs (id, status, completed_at, started_at) VALUES (?,?,?,?)",
        (str(uuid.uuid4()), "completed", built_at, built_at))
    conn.commit()
    conn.close()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/void_state_test.db")
    ap.add_argument("--commit", default=None,
                    help="build from a past snapshot (git commit-ish)")
    ap.add_argument("--clusters", type=int, default=100)
    args = ap.parse_args()
    out = Path(args.out)
    stats = build(out, args.commit, args.clusters)
    print(f"built {out} ({out.stat().st_size // 1024} KB)")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats["clusters"] < 20 or stats["articles"] < 50:
        print("FAIL: snapshot too thin to be a useful harness")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
