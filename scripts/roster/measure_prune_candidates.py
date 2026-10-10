#!/usr/bin/env python3
"""Which of the 1,061 roster outlets are actually earning their place?

    python3 scripts/roster/measure_prune_candidates.py <pipeline_state.db>

THE QUESTION THIS SETTLES. "Do we need all 1,061 sources? We agreed to trim
duplicate wire prints and low-quality data." Three different things get collapsed
into one there, and they have three different answers, so each is measured
separately and reported separately.

THE TRAP, and the reason this file exists rather than a one-off query. The obvious
prune metric is "outlets we store no article body for", and it is catastrophically
wrong: that bucket is AP, Reuters, the New York Times, the Washington Post, the Wall
Street Journal, CNN and Bloomberg. They block non-browser clients, so we hold their
headlines and nothing else. Pruning on text availability deletes the front page.

An earlier pass of mine reported "never reached the front page: 750" from a join on
`printed_stories.article_id`. That column does not exist; the join threw and the
Counter stayed empty, so the number was an artifact of a failed query rather than a
measurement. Front-page presence lives in `printed_stories.members`, a JSON array
carrying `source_id` per member. That is what is read here.
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sqlite3
import sys
import unicodedata

USABLE_WORDS = 150      # the scorer's own full-confidence threshold
VOLUME_FLOOR = 20       # below this "zero bodies" is not evidence of a wall
JACCARD = 0.6           # near-identical titles, mastheads stripped
STOP = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "is", "are",
        "as", "at", "by", "with", "from", "after", "over", "says", "said"}


def load(db: str):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    src = {r["id"]: dict(r) for r in conn.execute("select * from sources")}
    fetched, with_text = collections.Counter(), collections.Counter()
    for r in conn.execute("select source_id, word_count from articles"):
        fetched[r["source_id"]] += 1
        if (r["word_count"] or 0) >= USABLE_WORDS:
            with_text[r["source_id"]] += 1
    printed = collections.Counter()
    for r in conn.execute("select members from printed_stories where members is not null"):
        for m in json.loads(r["members"]):
            if m.get("source_id"):
                printed[m["source_id"]] += 1
    return conn, src, fetched, with_text, printed


def contribution(src, fetched, with_text, printed) -> None:
    dead = [s for s in src if fetched[s] == 0]
    silent = [s for s in src if fetched[s] > 0 and printed[s] == 0]
    walled = [s for s in src if fetched[s] >= VOLUME_FLOOR and with_text[s] == 0]

    print(f"roster: {len(src):,}")
    print(f"  never fetched one article:        {len(dead):>5}  "
          f"({collections.Counter(src[s]['tier'] for s in dead)})")
    print(f"  fetches, never reaches the page:  {len(silent):>5}")
    print(f"  {VOLUME_FLOOR}+ articles, zero usable body:  {len(walled):>5}  "
          f"of which {sum(1 for s in walled if printed[s] > 0)} DO reach the page")

    majors = [src[s]["name"] for s in walled if src[s]["tier"] == "us_major"]
    print(f"\n  us_major outlets in the no-body bucket ({len(majors)}): "
          f"{', '.join(sorted(majors))}")
    print("  ^ THIS is why text availability is not a prune metric.")

    total = sum(printed.values())
    run = 0
    print(f"\nfront-page appearances: {total:,} across "
          f"{sum(1 for s in src if printed[s]):,} outlets")
    for i, (sid, n) in enumerate(printed.most_common(), 1):
        run += n
        if i in (50, 100, 200, 300, 400, 500):
            print(f"  top {i:>3} outlets carry {run / total:>5.1%}")


def syndication(conn, src) -> None:
    """How much of what the Bench prints as separate coverage is the same copy."""
    mastheads = set()
    for r in src.values():
        for w in re.sub(r"[^a-z ]", " ", (r["name"] or "").lower()).split():
            if len(w) > 3:
                mastheads.add(w)

    def toks(t: str) -> set:
        t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
        t = re.sub(r"[^a-z0-9 ]", " ", t.lower())
        return {w for w in t.split()
                if w not in STOP and w not in mastheads and len(w) > 2}

    titles = {r["url"]: r["title"]
              for r in conn.execute("select url, title from articles where url is not null")}

    rows = redundant = stories = 0
    widest: list[list[str]] = []
    for r in conn.execute("select members from printed_stories where members is not null"):
        items = []
        for m in json.loads(r["members"]):
            t = titles.get(m.get("url"))
            if t:
                s = toks(t)
                if len(s) >= 3:
                    items.append((m.get("source_name"), s))
        if len(items) < 2:
            continue
        stories += 1
        rows += len(items)
        parent = list(range(len(items)))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i][1], items[j][1]
                if a | b and len(a & b) / len(a | b) >= JACCARD:
                    parent[find(i)] = find(j)
        grp = collections.defaultdict(list)
        for i in range(len(items)):
            grp[find(i)].append(items[i][0])
        for g in grp.values():
            if len(g) > 1:
                redundant += len(g) - 1
                if len(g) >= 5:
                    widest.append(g)

    print(f"\nsyndication inside printed stories ({stories:,} stories, "
          f"{rows:,} members whose title is still stored)")
    if not rows:
        print("  no resolvable members; the article window has rolled past them")
        return
    print(f"  redundant rows at Jaccard >= {JACCARD}: {redundant:,} ({redundant / rows:.1%})")
    print(f"  groups of 5+ outlets on one copy: {len(widest)}")
    for g in sorted(widest, key=len, reverse=True)[:3]:
        print(f"    {len(g)}x  {', '.join(sorted(set(g))[:8])}")
    print("  ^ a dedup defect, not a roster-size defect: dropping outlets does not "
          "stop the survivors reprinting one wire.")


def main(db: str) -> int:
    if not pathlib.Path(db).exists():
        print(f"no such db: {db}")
        return 2
    conn, src, fetched, with_text, printed = load(db)
    contribution(src, fetched, with_text, printed)
    syndication(conn, src)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
