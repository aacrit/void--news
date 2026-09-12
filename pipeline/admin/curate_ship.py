"""
One-off ship board curation (2026-08-05).

Cleans the void --ship / Ship board for launch: removes an internal test card
and rewrites stale, jargon-y shipped items into plain reader English. Matches
rows by their current title, so it is idempotent: once a title has been renamed
the operation no longer matches and re-running is a no-op.

Runs in CI (service-role key) because the anon key cannot write ship_requests
(migration 068 constrains anon INSERT to default-shaped rows and blocks UPDATE/
DELETE). Dispatched via .github/workflows/curate-ship.yml.

Usage:
    python -m pipeline.admin.curate_ship
"""

from pipeline.utils.supabase_client import supabase


# Each op matches a ship_requests row by its CURRENT title.
# - delete: remove the row entirely (the internal test card).
# - update: overwrite the given fields (reader-facing rewrites / typo fix).
CURATION = [
    {
        "op": "delete",
        "match_title": "launch verification (ignore)",
        "why": "internal post-migration test card, not a real request",
    },
    {
        "op": "update",
        "match_title": "Lean Tilt Bell Curve instead of spectrum",
        "fields": {
            "title": "Show bias as a curve, not just a bar",
            "description": (
                "The Deep Dive plots each story's coverage as a bell curve across "
                "the political spectrum, sources sitting along the curve, so you see "
                "the full spread at a glance instead of one score."
            ),
        },
        "why": "shipped feature, rewritten from internal jargon into reader English",
    },
    {
        "op": "update",
        "match_title": "Top Stories",
        "fields": {
            "title": "A ranked front page, not an endless feed",
            "description": (
                "Cap the homepage at the 50 most consequential stories of the day, "
                "clustered and ranked once, the same for everyone, instead of an "
                "infinite scroll."
            ),
        },
        "why": "shipped feature, rewritten (old description described the retired multi-edition spec)",
    },
    {
        "op": "update",
        "match_title": "Hostory Books",
        "fields": {"title": "History Books"},
        "why": "typo fix on the won't-ship card",
    },
]


def run() -> int:
    applied = 0
    for step in CURATION:
        title = step["match_title"]
        # Look the row up first so we can report precisely (and stay idempotent).
        found = (
            supabase.table("ship_requests")
            .select("id, title, status")
            .eq("title", title)
            .execute()
        )
        rows = found.data or []
        if not rows:
            print(f"[skip] no row titled {title!r} (already curated or absent)")
            continue

        if step["op"] == "delete":
            supabase.table("ship_requests").delete().eq("title", title).execute()
            print(f"[delete] removed {len(rows)} row(s) titled {title!r} ({step['why']})")
            applied += len(rows)
        elif step["op"] == "update":
            supabase.table("ship_requests").update(step["fields"]).eq("title", title).execute()
            new_title = step["fields"].get("title", title)
            print(f"[update] {title!r} -> {new_title!r} ({step['why']})")
            applied += len(rows)

    print(f"\nCuration complete. {applied} row(s) affected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
