"""Export the live top-50 feed exactly as the dashboard renders it, plus the
articles linked to each cluster, for offline multi-perspective review."""
import json
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

ENRICHED = ("id,title,summary,category,section,sections,importance_score,"
            "source_count,first_published,last_updated,divergence_score,"
            "headline_rank,coverage_velocity,bias_diversity,consensus_points,"
            "divergence_points,rank_world,claim_consensus,cached_image_url,"
            "is_international,is_headline,headline_confidence,summary_tier,"
            "mega_cluster_capped")

res = (sb.table("story_clusters")
       .select(ENRICHED)
       .contains("sections", ["world"])
       .order("rank_world", desc=True)
       .limit(100)
       .execute())
clusters = res.data or []
top = clusters[:50]
print(f"fetched {len(clusters)} clusters; taking top {len(top)}", file=sys.stderr)

out = []
for rank, c in enumerate(top, 1):
    cid = c["id"]
    # linked articles
    links = (sb.table("cluster_articles")
             .select("article_id")
             .eq("cluster_id", cid)
             .execute()).data or []
    aids = [l["article_id"] for l in links]
    arts = []
    if aids:
        # chunk to avoid URL length limits
        for i in range(0, len(aids), 50):
            chunk = aids[i:i+50]
            a = (sb.table("articles")
                 .select("id,title,url,source_id,published_at,word_count")
                 .in_("id", chunk)
                 .execute()).data or []
            arts.extend(a)
    c["_display_rank"] = rank
    c["_articles"] = arts
    c["_article_count_actual"] = len(arts)
    out.append(c)

with open("scripts/top50_export.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)
print(f"wrote scripts/top50_export.json with {len(out)} clusters", file=sys.stderr)

# compact human-readable index
for c in out:
    print(f'#{c["_display_rank"]:>2} rank={c.get("rank_world"):.4f} '
          f'src={c.get("source_count")}/{c["_article_count_actual"]} '
          f'cat={c.get("category")} tier={c.get("summary_tier")} '
          f'| {c.get("title","")[:80]}', file=sys.stderr)
