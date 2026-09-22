#!/usr/bin/env python3
"""Apply discovered RSS feeds to data/sources.json, with a confidence bar.

CEO decision 2026-09-22: auto-apply above a confidence bar, list the rest for
review.

THE BAR. A discovered feed is applied automatically when it returns at least
MIN_ITEMS items AND at least MIN_OWN_LINKS of those items link to the outlet's
own registered domain. Both halves matter. Item count alone would accept a feed
of Google News redirects, which is the thing we are migrating away from;
own-domain links alone would accept a two-item stub. Anything that finds a feed
but misses the bar is written to the review file and NOT applied.

WHY A FEED IS ENOUGH. The pipeline's scraper fetches the article, so the feed
only has to supply a resolvable publisher URL. See
scripts/roster/discover_feeds.py for the measurement behind that.

REVERSIBILITY. Every change records the previous rss_url in the changelog file,
so the patch can be undone without consulting git. Nothing else on the row is
touched: tier, lean baseline, country and credibility notes are left exactly as
they were, because a feed repair is not a re-rating.

    python3 scripts/roster/apply_feeds.py --dry-run discover-*.jsonl
    python3 scripts/roster/apply_feeds.py --apply   discover-*.jsonl
"""
from __future__ import annotations
import json, sys, os, datetime

MIN_ITEMS = 10
MIN_OWN_LINKS = 10
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCES = os.path.join(ROOT, "data", "sources.json")
OUTDIR = os.path.join(ROOT, "data", "roster")


def strong(found: dict) -> bool:
    return (found.get("items", 0) >= MIN_ITEMS
            and found.get("own_domain_links", 0) >= MIN_OWN_LINKS)


def load(paths):
    recs = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
    # last write wins per outlet, so a re-probe supersedes an earlier one
    return {r["name"]: r for r in recs}


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_ = "--apply" in sys.argv
    if not args:
        print(__doc__)
        return 2
    recs = load(args)
    with open(SOURCES, encoding="utf-8") as fh:
        srcs = json.load(fh)
    by_name = {s["name"]: s for s in srcs}

    applied, review, absent = [], [], []
    for name, r in sorted(recs.items()):
        found = r.get("found")
        if not found:
            continue
        s = by_name.get(name)
        if s is None:
            absent.append(name)
            continue
        row = {"name": name, "was": s.get("rss_url"), "now": found["feed"],
               "items": found["items"], "own_domain_links": found["own_domain_links"]}
        (applied if strong(found) else review).append(row)

    print(f"discovery records: {len(recs)}, with a feed: "
          f"{sum(1 for r in recs.values() if r.get('found'))}")
    print(f"clears the bar (>= {MIN_ITEMS} items and >= {MIN_OWN_LINKS} own-domain links): "
          f"{len(applied)}")
    print(f"found a feed but below the bar, for review: {len(review)}")
    if absent:
        print(f"discovery named {len(absent)} outlet(s) not in the roster: {absent[:5]}")

    stamp = datetime.date.today().isoformat()
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, f"feed-review-{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(review, fh, indent=1)
    with open(os.path.join(OUTDIR, f"feed-changes-{stamp}.json"), "w", encoding="utf-8") as fh:
        json.dump(applied, fh, indent=1)

    if not apply_:
        print("\n--dry-run: data/sources.json untouched. "
              f"Wrote data/roster/feed-changes-{stamp}.json and feed-review-{stamp}.json")
        return 0

    for row in applied:
        by_name[row["name"]]["rss_url"] = row["now"]
    with open(SOURCES, "w", encoding="utf-8") as fh:
        json.dump(srcs, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\napplied {len(applied)} feed change(s) to data/sources.json")
    print(f"previous URLs recorded in data/roster/feed-changes-{stamp}.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
