#!/usr/bin/env python3
"""A feed the front page cannot render must not reach main.

WHAT HAPPENED. `pipeline.yml` commits `frontend/build-data` and
`frontend/public/data` STRAIGHT TO MAIN, with no build behind it. On
2026-09-22 a run emitted a feed carrying 14 clusters with a real summary where
the previous day's had 35, almost certainly the Gemini 20-requests-per-day cap
biting mid-run. `serverFeed.ts` refuses to render a front page under
`FEED_MIN_DISPLAYABLE` and throws, by design (P0, 2026-08-11), so:

  - the Cloudflare build failed and the site froze on the previous day's data;
  - `auto-merge-claude.yml`'s build-check failed on every branch, because every
    branch inherits main's data, so THIRTY unrelated commits were blocked
    behind a pipeline run;
  - and nothing said so. The pipeline reported success.

The guard that would have caught it already existed. It just ran on the deploy
and on the branches, which is everywhere except the job that writes the file.

WHAT THIS ASSERTS: the same predicate `serverFeed.ts` applies, against the
emitted feed, before `git add`. A run that cannot fill the front page fails
loudly and leaves the last good data in place, which is a bad day rather than a
frozen site.

Deliberately NOT a summary-quality check. It asks only the question the front
page asks, from the one source of truth (`frontend/config/feed.json`), so the
two can never drift into disagreeing about what "displayable" means.

    python3 tests/test_feed_buildable.py [path/to/feed.json]
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FEED = ROOT / "frontend" / "build-data" / "feed.json"
CONFIG = ROOT / "frontend" / "config" / "feed.json"

#: `mapClustersToStories` drops a cluster under this many sources before the
#: count is taken, so the predicate here has to match.
MIN_SOURCES = 3


def displayable(cluster: dict) -> bool:
    """The predicate `clusterHasRealSummary` + the source floor apply.

    A cluster with no `summary_tier` carries raw lead text rather than a written
    summary. Those are what the 2026-09-22 feed was full of: 21 of its 35 had a
    summary field of 130 to 420 characters against a real summary's ~2,000.
    """
    if (cluster.get("source_count") or 0) < MIN_SOURCES:
        return False
    return bool((cluster.get("summary_tier") or "").strip())


def main(path: str | None = None) -> int:
    feed_path = pathlib.Path(path) if path else FEED
    if not feed_path.exists():
        print(f"FAIL  no feed at {feed_path}")
        return 1
    try:
        minimum = json.loads(CONFIG.read_text(encoding="utf-8"))["minDisplayable"]
    except Exception as exc:
        print(f"FAIL  could not read minDisplayable from {CONFIG}: {exc}")
        return 1

    data = json.loads(feed_path.read_text(encoding="utf-8"))
    clusters = data.get("clusters") or []
    ok = [c for c in clusters if displayable(c)]

    print(f"feed {feed_path.name}: builtAt {data.get('builtAt')}")
    print(f"  clusters emitted: {len(clusters)}")
    print(f"  displayable ({MIN_SOURCES}+ sources, real summary): {len(ok)}")
    print(f"  required by frontend/config/feed.json: {minimum}")

    if len(ok) < minimum:
        untiered = sum(1 for c in clusters
                       if (c.get("source_count") or 0) >= MIN_SOURCES
                       and not (c.get("summary_tier") or "").strip())
        print(
            f"\nFAIL  only {len(ok)} displayable stories against {minimum} required.\n"
            f"      {untiered} cluster(s) have the sources but no summary_tier, which\n"
            f"      means the summariser did not reach them. The usual cause is the\n"
            f"      gemini-2.5-flash 20-per-day cap.\n"
            f"      COMMITTING THIS WOULD FREEZE THE SITE: serverFeed.ts throws below\n"
            f"      the threshold, so the Cloudflare build and every branch's\n"
            f"      build-check fail until the data is replaced. Leaving the previous\n"
            f"      day's data in place is the better failure."
        )
        return 1

    print("\nPASS  the emitted feed can fill the front page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
