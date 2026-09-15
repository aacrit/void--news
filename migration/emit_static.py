"""Emit the static-JSON snapshots the frontend reads, from the staging SQLite.

Outputs (into OUT dir, later copied to frontend/public/data/):
  feed.json                {clusters:[...top-100 world by rank_world...], builtAt}
  brief.json               latest daily_briefs row (world), JSONB/array parsed
  weekly.json              latest weekly_digests row, JSONB parsed
  archive.json             all printed_stories rows (permalinks + /story pages)
  archiveMap.json          {cluster_id: "/story/<printed_id>/"} latest edition
  methodology.json         10 recent articles w/ bias (sources methodology)
  deepdive/<cluster>.json  per displayed cluster: fetchDeepDiveData shape

Shapes mirror exactly what PostgREST returned so the frontend mapping is unchanged.
"""
import json
import os
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "void_local.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data_out"
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "deepdive"), exist_ok=True)

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row


def pbool(v):
    if v is None:
        return None
    return v == "t" or v is True


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
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return None


def parr(v):
    """Parse a pg array literal like {a,b,"c d"} into a list of strings."""
    if v is None or v == "":
        return []
    s = v.strip()
    if not (s.startswith("{") and s.endswith("}")):
        # maybe JSON array
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
    return [x for x in out]


# ---- feed.json ----
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
    d = {k: r[k] for k in FEED_COLS if k in r.keys()}
    for k in ("importance_score", "source_count", "divergence_score",
              "headline_rank", "coverage_velocity", "rank_world",
              "headline_confidence"):
        d[k] = pnum(r[k])
    d["is_international"] = pbool(r["is_international"])
    d["is_headline"] = pbool(r["is_headline"])
    d["sections"] = parr(r["sections"])
    d["bias_diversity"] = pjson(r["bias_diversity"])
    d["consensus_points"] = pjson(r["consensus_points"]) or []
    d["divergence_points"] = pjson(r["divergence_points"]) or []
    d["claim_consensus"] = pjson(r["claim_consensus"])
    clusters.append(d)

built = c.execute(
    "SELECT completed_at FROM pipeline_runs WHERE status='completed' "
    "AND completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 1"
).fetchone()
built_at = built["completed_at"] if built else None
if built_at:
    # normalize to ISO-8601 T + Z so new Date() parses on the client
    built_at = built_at.replace(" ", "T")
    if "+" in built_at:
        built_at = built_at.split("+")[0] + "Z"

json.dump({"clusters": clusters, "builtAt": built_at},
          open(os.path.join(OUT, "feed.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"feed.json: {len(clusters)} clusters, builtAt={built_at}")

# ---- brief.json ----
b = c.execute(
    "SELECT * FROM daily_briefs WHERE edition='world' "
    "ORDER BY created_at DESC LIMIT 1"
).fetchone()
if not b:
    b = c.execute("SELECT * FROM daily_briefs ORDER BY created_at DESC LIMIT 1").fetchone()
brief = None
if b:
    brief = {k: b[k] for k in b.keys()}
    for k in ("audio_duration_seconds", "opinion_start_seconds"):
        if k in brief:
            brief[k] = pnum(b[k])
    if "top_cluster_ids" in brief:
        brief["top_cluster_ids"] = parr(b["top_cluster_ids"])
json.dump(brief, open(os.path.join(OUT, "brief.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"brief.json: {'ok' if brief else 'MISSING'}  headline={brief.get('tldr_headline','')[:50] if brief else ''}")

# ---- weekly.json ----
w = c.execute(
    "SELECT * FROM weekly_digests ORDER BY created_at DESC LIMIT 1"
).fetchone()
weekly = None
if w:
    weekly = {k: w[k] for k in w.keys()}
    for k in ("cover_text", "recap_stories", "opinion_left", "opinion_center",
              "opinion_right", "opinion_headlines", "bias_report_data"):
        if k in weekly:
            weekly[k] = pjson(w[k])
    for k in ("audio_duration_seconds", "opinion_start_seconds",
              "issue_number", "total_articles", "total_clusters"):
        if k in weekly:
            weekly[k] = pnum(w[k])
json.dump(weekly, open(os.path.join(OUT, "weekly.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"weekly.json: {'ok' if weekly else 'MISSING'}")

# ---- archive.json (printed_stories) + archiveMap.json ----
prows = c.execute("SELECT * FROM printed_stories ORDER BY printed_on DESC, "
                  "CAST(edition_position AS INT) ASC").fetchall()
archive = []
for r in prows:
    d = {k: r[k] for k in r.keys()}
    for k in ("consensus_points", "divergence_points", "claim_consensus",
              "bias_diversity", "members", "title_keywords", "search_terms"):
        if k in d:
            d[k] = pjson(r[k]) if (r[k] and str(r[k]).lstrip().startswith(("{", "["))) else r[k]
    for k in ("edition_position", "editorial_importance", "rank_world",
              "headline_rank", "source_count", "divergence_score",
              "mean_lean", "polarization", "lean_spread",
              "aggregate_confidence", "member_count"):
        if k in d:
            d[k] = pnum(r[k])
    archive.append(d)
json.dump(archive, open(os.path.join(OUT, "archive.json"), "w", encoding="utf-8"),
          ensure_ascii=False)

# latest printed edition -> permalink map keyed by source_cluster_id
latest_day = c.execute("SELECT printed_on FROM printed_stories ORDER BY printed_on DESC LIMIT 1").fetchone()
amap = {}
if latest_day:
    lp = c.execute("SELECT id, source_cluster_id FROM printed_stories WHERE printed_on = ?",
                   (latest_day["printed_on"],)).fetchall()
    for r in lp:
        if r["source_cluster_id"]:
            amap[r["source_cluster_id"]] = f"/story/{r['id']}/"
json.dump(amap, open(os.path.join(OUT, "archiveMap.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"archive.json: {len(archive)} printed rows;  archiveMap.json: {len(amap)} permalinks")

# ---- deepdive/<cluster>.json (fetchDeepDiveData shape) for displayed clusters ----
disp_ids = [d["id"] for d in clusters]
dd_count = 0
for cid in disp_ids:
    links = c.execute("SELECT article_id FROM cluster_articles WHERE cluster_id = ?", (cid,)).fetchall()
    out_rows = []
    for lk in links:
        aid = lk["article_id"]
        a = c.execute("SELECT id,title,url,summary,published_at,image_url,source_id FROM articles WHERE id = ?", (aid,)).fetchone()
        if not a:
            continue
        src = None
        if a["source_id"]:
            s = c.execute("SELECT name,tier,url FROM sources WHERE id = ?", (a["source_id"],)).fetchone()
            if s:
                src = {"name": s["name"], "tier": s["tier"], "url": s["url"]}
        bs = c.execute("SELECT political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence,rationale FROM bias_scores WHERE article_id = ?", (aid,)).fetchone()
        bias = None
        if bs:
            bias = {
                "political_lean": pnum(bs["political_lean"]),
                "sensationalism": pnum(bs["sensationalism"]),
                "opinion_fact": pnum(bs["opinion_fact"]),
                "factual_rigor": pnum(bs["factual_rigor"]),
                "framing": pnum(bs["framing"]),
                "confidence": pnum(bs["confidence"]),
                "rationale": pjson(bs["rationale"]) if (bs["rationale"] and str(bs["rationale"]).lstrip().startswith("{")) else bs["rationale"],
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
        json.dump(out_rows, open(os.path.join(OUT, "deepdive", f"{cid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
        dd_count += 1
print(f"deepdive/: {dd_count} cluster files")

# ---- methodology.json (10 recent articles w/ bias) ----
meth = []
mrows = c.execute(
    "SELECT a.id,a.title,a.published_at,a.summary,a.source_id "
    "FROM articles a JOIN bias_scores b ON b.article_id=a.id "
    "ORDER BY a.published_at DESC LIMIT 10"
).fetchall()
for a in mrows:
    s = c.execute("SELECT name,slug,url FROM sources WHERE id=?", (a["source_id"],)).fetchone() if a["source_id"] else None
    bs = c.execute("SELECT political_lean,sensationalism,opinion_fact,factual_rigor,framing,rationale FROM bias_scores WHERE article_id=? LIMIT 1", (a["id"],)).fetchone()
    meth.append({
        "id": a["id"], "title": a["title"], "published_at": a["published_at"],
        "summary": a["summary"],
        "source": {"name": s["name"], "slug": s["slug"], "url": s["url"]} if s else None,
        "bias_scores": [{
            "political_lean": pnum(bs["political_lean"]), "sensationalism": pnum(bs["sensationalism"]),
            "opinion_fact": pnum(bs["opinion_fact"]), "factual_rigor": pnum(bs["factual_rigor"]),
            "framing": pnum(bs["framing"]),
            "rationale": pjson(bs["rationale"]) if (bs["rationale"] and str(bs["rationale"]).lstrip().startswith("{")) else bs["rationale"],
        }] if bs else [],
    })
json.dump(meth, open(os.path.join(OUT, "methodology.json"), "w", encoding="utf-8"), ensure_ascii=False)
print(f"methodology.json: {len(meth)} articles")

# size report
total = 0
for root, _, files in os.walk(OUT):
    for f in files:
        total += os.path.getsize(os.path.join(root, f))
print(f"\nTotal static payload: {total/1e6:.2f} MB across {sum(len(f) for _,_,f in os.walk(OUT))} files")
c.close()
