"""Emit the static-JSON snapshots the frontend reads, from the pipeline SQLite.

Runs at the END of a pipeline run (Cloudflare migration): the browser and the
`next build` never touch a database, they read these files. Splits output into:

  frontend/build-data/  (read via fs at build, NOT shipped to the client)
      feed.json         {clusters:[...top-100 world by rank_world...], builtAt}
      archive.json      all printed_stories rows (generateStaticParams + /story)
      archiveMap.json   {source_cluster_id: "/story/<id>/"} latest edition

  frontend/public/data/ (fetched by the browser from the CDN)
      brief.json        latest daily_briefs row (world)
      weekly.json       latest weekly_digests row
      methodology.json  10 recent bias-scored articles
      deepdive/<id>.json  per displayed cluster: fetchDeepDiveData shape

Shapes mirror exactly what PostgREST returned so the frontend mapping is
unchanged. Reads directly with sqlite3 (typed state DB from schema_pipeline.sql,
so JSONB columns are TEXT holding JSON, booleans are 1/0). Deterministic.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("VOID_SQLITE_PATH", str(REPO / "pipeline_state.db"))
)
BUILD_DIR = REPO / "frontend" / "build-data"
PUBLIC_DIR = REPO / "frontend" / "public" / "data"
BUILD_DIR.mkdir(parents=True, exist_ok=True)
_DD = PUBLIC_DIR / "deepdive"
_DD.mkdir(parents=True, exist_ok=True)
# Clear stale per-cluster deep-dive files first: each run's displayed clusters
# differ, so without this the directory accumulates yesterday's orphans forever.
for _f in _DD.glob("*.json"):
    _f.unlink()

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row


def pbool(v):
    if v is None:
        return None
    return v in (1, "1", "t", True)


def pnum(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (ValueError, TypeError):
        return None


def pjson(v):
    if v is None or v == "":
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return None


def parr(v):
    """Parse a pg array literal {a,b} OR a JSON array into a list of strings."""
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return v
    s = str(v).strip()
    if not (s.startswith("{") and s.endswith("}")):
        j = pjson(s)
        return j if isinstance(j, list) else []
    s = s[1:-1]
    if not s:
        return []
    out, cur, i, n, inq = [], [], 0, len(s), False
    while i < n:
        ch = s[i]
        if ch == '"':
            inq = not inq
        elif ch == "," and not inq:
            out.append("".join(cur))
            cur = []
        elif ch == "\\" and i + 1 < n:
            cur.append(s[i + 1])
            i += 2
            continue
        else:
            cur.append(ch)
        i += 1
    out.append("".join(cur))
    return out


def wj(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)


# ── feed.json ──
FEED_COLS = [
    "id", "title", "summary", "summary_tier", "category", "section",
    "importance_score", "source_count", "first_published", "last_updated",
    "divergence_score", "headline_rank", "coverage_velocity", "rank_world",
    "cached_image_url", "is_international", "is_headline", "headline_confidence",
]
rows = c.execute(
    "SELECT * FROM story_clusters WHERE sections LIKE '%world%' "
    "ORDER BY CAST(rank_world AS REAL) DESC LIMIT 100"
).fetchall()
clusters = []
for r in rows:
    keys = r.keys()
    d = {k: (r[k] if k in keys else None) for k in FEED_COLS}
    for k in ("importance_score", "source_count", "divergence_score",
              "headline_rank", "coverage_velocity", "rank_world",
              "headline_confidence"):
        d[k] = pnum(r[k]) if k in keys else None
    d["is_international"] = pbool(r["is_international"]) if "is_international" in keys else None
    d["is_headline"] = pbool(r["is_headline"]) if "is_headline" in keys else None
    d["sections"] = parr(r["sections"]) if "sections" in keys else ["world"]
    d["bias_diversity"] = pjson(r["bias_diversity"]) if "bias_diversity" in keys else None
    d["consensus_points"] = pjson(r["consensus_points"]) if "consensus_points" in keys else []
    d["consensus_points"] = d["consensus_points"] or []
    d["divergence_points"] = pjson(r["divergence_points"]) if "divergence_points" in keys else []
    d["divergence_points"] = d["divergence_points"] or []
    d["claim_consensus"] = pjson(r["claim_consensus"]) if "claim_consensus" in keys else None
    clusters.append(d)

built = c.execute(
    "SELECT completed_at FROM pipeline_runs WHERE status='completed' "
    "AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 1"
).fetchone()
built_at = built["completed_at"] if built else None
if built_at:
    built_at = str(built_at).replace(" ", "T")
    if "+" in built_at:
        built_at = built_at.split("+")[0] + "Z"
    elif not built_at.endswith("Z"):
        built_at = built_at + "Z"
wj(BUILD_DIR / "feed.json", {"clusters": clusters, "builtAt": built_at})
print(f"feed.json: {len(clusters)} clusters, builtAt={built_at}")

# ── brief.json ──
b = c.execute(
    "SELECT * FROM daily_briefs WHERE edition='world' ORDER BY created_at DESC LIMIT 1"
).fetchone() or c.execute(
    "SELECT * FROM daily_briefs ORDER BY created_at DESC LIMIT 1"
).fetchone()
brief = None
if b:
    brief = {k: b[k] for k in b.keys()}
    for k in ("audio_duration_seconds", "opinion_start_seconds"):
        if k in brief:
            brief[k] = pnum(b[k])
    if "top_cluster_ids" in brief:
        brief["top_cluster_ids"] = parr(b["top_cluster_ids"])
wj(PUBLIC_DIR / "brief.json", brief)
print(f"brief.json: {'ok' if brief else 'MISSING'}")

# ── weekly.json ──
w = c.execute("SELECT * FROM weekly_digests ORDER BY created_at DESC LIMIT 1").fetchone()
weekly = None
if w:
    weekly = {k: w[k] for k in w.keys()}
    for k in ("cover_text", "recap_stories", "opinion_left", "opinion_center",
              "opinion_right", "opinion_headlines", "bias_report_data"):
        if k in weekly:
            weekly[k] = pjson(w[k])
    for k in ("audio_duration_seconds", "opinion_start_seconds", "issue_number",
              "total_articles", "total_clusters"):
        if k in weekly:
            weekly[k] = pnum(w[k])
wj(PUBLIC_DIR / "weekly.json", weekly)
print(f"weekly.json: {'ok' if weekly else 'MISSING'}")

# ── archive.json + archiveMap.json ──
prows = c.execute(
    "SELECT * FROM printed_stories ORDER BY printed_on DESC, CAST(edition_position AS INT) ASC"
).fetchall()
archive = []
for r in prows:
    d = {k: r[k] for k in r.keys()}
    for k in ("consensus_points", "divergence_points", "claim_consensus",
              "bias_diversity", "members", "title_keywords", "search_terms"):
        if k in d and d[k] is not None and str(d[k]).lstrip()[:1] in ("{", "["):
            d[k] = pjson(r[k])
    for k in ("edition_position", "editorial_importance", "rank_world",
              "headline_rank", "source_count", "divergence_score", "mean_lean",
              "polarization", "lean_spread", "aggregate_confidence", "member_count"):
        if k in d:
            d[k] = pnum(r[k])
    archive.append(d)
wj(BUILD_DIR / "archive.json", archive)

latest = c.execute("SELECT printed_on FROM printed_stories ORDER BY printed_on DESC LIMIT 1").fetchone()
amap = {}
if latest:
    for r in c.execute(
        "SELECT id, source_cluster_id FROM printed_stories WHERE printed_on = ?",
        (latest["printed_on"],),
    ).fetchall():
        if r["source_cluster_id"] and r["source_cluster_id"] not in amap:
            amap[r["source_cluster_id"]] = f"/story/{r['id']}/"
wj(BUILD_DIR / "archiveMap.json", amap)
print(f"archive.json: {len(archive)} rows; archiveMap.json: {len(amap)} permalinks")

# ── deepdive/<cluster>.json for displayed clusters (typed DB is indexed -> fast) ──
dd = 0
for cid in [d["id"] for d in clusters]:
    links = c.execute("SELECT article_id FROM cluster_articles WHERE cluster_id=?", (cid,)).fetchall()
    out_rows = []
    for lk in links:
        a = c.execute(
            "SELECT id,title,url,summary,published_at,image_url,source_id FROM articles WHERE id=?",
            (lk["article_id"],),
        ).fetchone()
        if not a:
            continue
        src = None
        if a["source_id"]:
            s = c.execute("SELECT name,tier,url FROM sources WHERE id=?", (a["source_id"],)).fetchone()
            if s:
                src = {"name": s["name"], "tier": s["tier"], "url": s["url"]}
        bs = c.execute(
            "SELECT political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence,rationale "
            "FROM bias_scores WHERE article_id=?",
            (a["id"],),
        ).fetchone()
        bias = None
        if bs:
            bias = {
                "political_lean": pnum(bs["political_lean"]),
                "sensationalism": pnum(bs["sensationalism"]),
                "opinion_fact": pnum(bs["opinion_fact"]),
                "factual_rigor": pnum(bs["factual_rigor"]),
                "framing": pnum(bs["framing"]),
                "confidence": pnum(bs["confidence"]),
                "rationale": pjson(bs["rationale"]) if (bs["rationale"] and str(bs["rationale"]).lstrip()[:1] == "{") else bs["rationale"],
            }
        out_rows.append({
            "article": {
                "id": a["id"], "title": a["title"], "url": a["url"],
                "summary": a["summary"], "published_at": a["published_at"],
                "image_url": a["image_url"], "source": src,
                "bias_scores": [bias] if bias else [],
            }
        })
    if out_rows:
        wj(PUBLIC_DIR / "deepdive" / f"{cid}.json", out_rows)
        dd += 1
print(f"deepdive/: {dd} cluster files")

# ── methodology.json ──
meth = []
for a in c.execute(
    "SELECT a.id,a.title,a.published_at,a.summary,a.source_id FROM articles a "
    "JOIN bias_scores b ON b.article_id=a.id ORDER BY a.published_at DESC LIMIT 10"
).fetchall():
    s = c.execute("SELECT name,slug,url FROM sources WHERE id=?", (a["source_id"],)).fetchone() if a["source_id"] else None
    bs = c.execute(
        "SELECT political_lean,sensationalism,opinion_fact,factual_rigor,framing,rationale "
        "FROM bias_scores WHERE article_id=? LIMIT 1", (a["id"],)
    ).fetchone()
    meth.append({
        "id": a["id"], "title": a["title"], "published_at": a["published_at"], "summary": a["summary"],
        "source": {"name": s["name"], "slug": s["slug"], "url": s["url"]} if s else None,
        "bias_scores": [{
            "political_lean": pnum(bs["political_lean"]), "sensationalism": pnum(bs["sensationalism"]),
            "opinion_fact": pnum(bs["opinion_fact"]), "factual_rigor": pnum(bs["factual_rigor"]),
            "framing": pnum(bs["framing"]),
            "rationale": pjson(bs["rationale"]) if (bs["rationale"] and str(bs["rationale"]).lstrip()[:1] == "{") else bs["rationale"],
        }] if bs else [],
    })
wj(PUBLIC_DIR / "methodology.json", meth)
print(f"methodology.json: {len(meth)} articles")

# Fail loud if the feed is too thin to ship (mirrors serverFeed's guard).
displayable = sum(
    1 for d in clusters
    if (d.get("source_count") or 0) >= 3 and d.get("summary_tier")
)
print(f"displayable (>=3 sources, real summary): {displayable}")
if displayable < 30:
    print("WARNING: fewer than 30 displayable stories; serverFeed will fail the build.")
c.close()
