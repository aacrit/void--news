"""One-off: regenerate the CURRENT displayed top-50 cluster summaries in place.

The summary-quality fixes (feed full article bodies, 55-to-90 word target band,
temperature 0, 90-word hard cap) are merged but only take effect on the NEXT
daily pipeline run. This forces the SAME code to re-summarize today's live
top-50 so the feed reads well for a launch, without waiting for 11:00 UTC.

The content-hash cache would otherwise skip every already-summarized cluster, so
step 1 nulls `summary_article_hash` on the top window to force a clean miss; step
2 runs the production summarizer; step 3 prints word-count evidence.

Usage (from repo root, .env must carry SUPABASE_* + GEMINI_API_KEY):
    python pipeline/admin/revamp_top50_summaries.py
"""

import os
import sys

# Replicate main.py's run context (it is invoked as `python pipeline/main.py`,
# so pipeline/ is on sys.path and imports are `from utils...` / `from summarizer...`).
_PIPELINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PIPELINE_DIR not in sys.path:
    sys.path.insert(0, _PIPELINE_DIR)

from utils.supabase_client import supabase  # noqa: E402
from summarizer.cluster_summarizer import (  # noqa: E402
    summarize_top50_after_rerank,
    reconcile_flash_top10,
)

EDITION = "world"
WINDOW = 70  # matches summarize_top50_after_rerank's limit(50)+20 over-fetch


def _wordcount(text: str | None) -> int:
    return len((text or "").split())


def main() -> int:
    # ---- Step 1: force a cache miss on the top window -------------------------
    rows = (
        supabase.table("story_clusters")
        .select("id, summary")
        .contains("sections", [EDITION])
        .order(f"rank_{EDITION}", desc=True)
        .limit(WINDOW)
        .execute()
    ).data or []
    ids = [r["id"] for r in rows]
    before = {r["id"]: _wordcount(r.get("summary")) for r in rows}
    print(f"[revamp] top-{WINDOW} window: {len(ids)} clusters")
    print(f"[revamp] BEFORE word counts: min={min(before.values(), default=0)} "
          f"mean={round(sum(before.values())/max(1,len(before)))} "
          f"max={max(before.values(), default=0)}")

    nulled = 0
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        supabase.table("story_clusters").update(
            {"summary_article_hash": None}
        ).in_("id", batch).execute()
        nulled += len(batch)
    print(f"[revamp] nulled summary_article_hash on {nulled} clusters (force regen)")

    # ---- Step 2: run the production summarizer (merged fixes) -----------------
    print("[revamp] summarizing top 50 (this makes ~50 Gemini calls, a few minutes)...")
    metrics = summarize_top50_after_rerank(
        supabase, edition=EDITION, limit=50, flash_top_n=10
    )
    metrics_summary = {k: v for k, v in metrics.items()
                       if k not in ("updated_ids", "updated_summaries")}
    print(f"[revamp] summarize metrics: {metrics_summary}")

    # Reconcile the flash top-10 (premium tier) for the highest-impact stories.
    try:
        recon = reconcile_flash_top10(supabase, edition=EDITION, top_n=10)
        recon_summary = {k: v for k, v in recon.items()
                         if not isinstance(v, (list, dict))}
        print(f"[revamp] reconcile_flash_top10: {recon_summary}")
    except Exception as e:
        print(f"[revamp] reconcile_flash_top10 skipped: {e}")

    # ---- Step 3: word-count evidence -----------------------------------------
    after_rows = (
        supabase.table("story_clusters")
        .select("id, summary")
        .contains("sections", [EDITION])
        .order(f"rank_{EDITION}", desc=True)
        .limit(50)
        .execute()
    ).data or []
    counts = [_wordcount(r.get("summary")) for r in after_rows]
    short = sum(1 for c in counts if c < 40)
    over = sum(1 for c in counts if c > 90)
    print(f"[revamp] AFTER top-50 word counts: min={min(counts, default=0)} "
          f"mean={round(sum(counts)/max(1,len(counts)))} max={max(counts, default=0)} "
          f"| under-40={short} over-90={over}")
    print("[revamp] done. Redeploy the frontend to re-prerender the feed with these.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
