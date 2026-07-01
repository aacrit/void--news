"""$0 / no-LLM backfill of headline + summary + category hygiene onto the LIVE
feed, using the exact production functions so results match the next pipeline
run. Dry-run by default; pass --apply to write.

Fixes applied to the current top-N world clusters:
  * headline  -> normalize_headline (strip source suffix / editorial prefix /
                 epithet leads the O6 whitelist misses)
  * summary   -> for null-tier (un-LLM-summarized) clusters only, regenerate an
                 on-topic, boilerplate-free summary via _generate_cluster_summary
                 (LLM-tiered summaries are preserved untouched)
  * category  -> O10 headline-primary desk via categorize_article
"""
import sys, os, json, argparse
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from dotenv import load_dotenv
from supabase import create_client
from clustering.story_cluster import _generate_cluster_summary
from categorizer.auto_categorize import categorize_article, map_to_desk
from utils.text_sanitizer import normalize_headline

load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true", help="write changes (default dry-run)")
ap.add_argument("--limit", type=int, default=100)
args = ap.parse_args()


def o10_category(title, articles):
    t = (title or "").strip()
    hc = categorize_article({"title": t, "summary": "", "full_text": ""}) if t else []
    if hc:
        return map_to_desk(hc[0])
    votes = {}
    for a in articles[:8]:
        for c in categorize_article(a):
            votes[c] = votes.get(c, 0) + 1
    return map_to_desk(max(votes, key=votes.get) if votes else "politics")


clusters = (sb.table("story_clusters")
            .select("id,title,summary,category,summary_tier,rank_world")
            .contains("sections", ["world"])
            .order("rank_world", desc=True)
            .limit(args.limit).execute()).data or []
print(f"fetched {len(clusters)} clusters (top {args.limit} by rank_world)")

n_title, n_summary, n_cat = 0, 0, 0
changes = []
for c in clusters:
    cid = c["id"]
    links = (sb.table("cluster_articles").select("article_id").eq("cluster_id", cid).execute()).data or []
    aids = [l["article_id"] for l in links]
    arts = []
    for i in range(0, len(aids), 50):
        arts.extend((sb.table("articles")
                     .select("id,title,summary,full_text")
                     .in_("id", aids[i:i+50]).execute()).data or [])

    old_title = c.get("title", "") or ""
    new_title = normalize_headline(old_title)

    payload = {}
    if new_title and new_title != old_title:
        payload["title"] = new_title
        n_title += 1

    # Regenerate summary ONLY for null-tier (never got an LLM summary).
    if c.get("summary_tier") is None and arts:
        new_summary = _generate_cluster_summary(arts, new_title or old_title)
        old_summary = c.get("summary", "") or ""
        if new_summary and new_summary != old_summary and len(new_summary) >= 40:
            payload["summary"] = new_summary
            n_summary += 1

    new_cat = o10_category(new_title or old_title, arts)
    if new_cat and new_cat != (c.get("category") or ""):
        payload["category"] = new_cat
        n_cat += 1

    if payload:
        changes.append((c.get("rank_world"), old_title[:55], payload))
        if args.apply:
            sb.table("story_clusters").update(payload).eq("id", cid).execute()

print(f"\n{'APPLIED' if args.apply else 'DRY-RUN'}: {len(changes)} clusters changed "
      f"(titles {n_title}, summaries {n_summary}, categories {n_cat})")
for rw, t, p in changes[:40]:
    keys = ",".join(p.keys())
    print(f"  rank={rw} [{keys}] {t}")
    if "category" in p:
        print(f"      cat -> {p['category']}")
    if "title" in p:
        print(f"      title -> {p['title'][:70]!r}")
