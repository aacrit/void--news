#!/usr/bin/env python3
"""Apply VERIFIED RSS feeds to data/sources.json, with a confidence bar.

CEO decision 2026-09-22: auto-apply above a confidence bar, list the rest for
review.

INPUT IS `verify_feeds.py` OUTPUT, not `discover_feeds.py` output. That changed
on 2026-09-22 and it is the whole point of this file. The original bar was
"10+ items AND 10+ links on the FEED's own registered domain", and every word
of it turned out to be too weak:

  the feed's own domain   Botswana Guardian's discovered feed resolves to
                          bettingbotswana.com. Every item links to
                          bettingbotswana.com, so own_domain_links was 10 of 10
                          and the HIJACKED FEED CLEARED THE BAR. The comparison
                          has to be against the roster's expected domain.
  channel vs item links   discover_feeds reads <link> anywhere in the XML,
                          which in RSS 2.0 includes the CHANNEL's link (the
                          site homepage). verify_feeds reads inside <item> only.
  no article-shape test   A feed of section fronts passed.
  no title test           A guessed-but-live domain passes a domain test by
                          construction.

THE BAR NOW. Applied automatically when the feed returns 200 AND has at least
MIN_ITEMS items AND at least MIN_ON_EXPECTED of them link to the ROSTER's
expected domain AND at least MIN_ARTICLES of those look like articles rather
than section fronts AND the feed's own channel title names the outlet. Anything
that misses any part goes to the review file and is NOT applied.

WHY A FEED IS ENOUGH. The pipeline's scraper fetches the article, so the feed
only has to supply a resolvable publisher URL. See
scripts/roster/discover_feeds.py for the measurement behind that.

REVERSIBILITY. Every change records the previous rss_url and the evidence
behind the decision, so the patch can be undone without consulting git and a
wrong call can be argued with. Nothing else on the row is touched: tier, lean
baseline, country and credibility notes are left exactly as they were, because
a feed repair is not a re-rating.

    python3 scripts/roster/discover_feeds.py cands.json  > discovered.jsonl
    python3 scripts/roster/verify_feeds.py   verify.json > verified.jsonl
    python3 scripts/roster/apply_feeds.py --dry-run verified.jsonl
    python3 scripts/roster/apply_feeds.py --apply   verified.jsonl
    python3 scripts/roster/apply_feeds.py --apply --label=gfed verified.jsonl

A dry run writes NOTHING, including no record files. A real run refuses to
overwrite an existing record for the same date and label; `--label=<name>`
writes beside it and `--force` replaces it.
"""
from __future__ import annotations
import json, re, sys, os, datetime

MIN_ITEMS = 10          # a feed of three stories is not a daily feed
MIN_ON_EXPECTED = 10    # links must be on the outlet's OWN registered domain
MIN_ARTICLES = 10       # and must look like articles, not section fronts
# 2026-09-26: 24.kg English cleared every test above with its Russian elections
# section, last updated in 2021. So the newest item must be recent, and an outlet
# listed by an edition's path (https://24.kg/english/) must get that edition.
MAX_NEWEST_AGE_DAYS = 14
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Overridable so this script can be exercised against a throwaway tree.
# It was not testable before, which is why a dry run that wrote two files went
# unnoticed until it overwrote a committed record:
# tests/test_apply_feeds.py now runs it against a temp copy.
DATA = os.environ.get("VOID_ROSTER_DATA") or os.path.join(ROOT, "data")
SOURCES = os.path.join(DATA, "sources.json")
OUTDIR = os.path.join(DATA, "roster")


def title_tokens() -> dict:
    """roster id -> brands its own feed title may use in place of its masthead.

    Some feeds title themselves with the outlet's domain rather than its
    masthead: stltoday.com for the St. Louis Post-Dispatch, "SI Feed" for
    Sports Illustrated, "Alaska Dispatch News" for the Anchorage Daily News
    (its former name). The title check would reject all of those, and it must
    not be loosened to let them through, because a guessed-but-live domain
    passes a domain test by construction and the one feed this whole pass
    exists to catch (a hijacked bettingbotswana.com) cleared a bar with no
    title test at all.

    So the equivalence is declared per outlet in
    data/roster/feed-title-tokens.json, which also records the ones NOT
    declared and why: a platform feed carrying several papers, a feed that is
    a different outlet, a section feed.
    """
    path = os.path.join(OUTDIR, "feed-title-tokens.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("tokens") or {}
    except Exception:
        return {}


_TOKENS = None


def named_ok(v: dict) -> bool:
    global _TOKENS
    if v.get("named"):
        return True
    if _TOKENS is None:
        _TOKENS = title_tokens()
    toks = _TOKENS.get(v.get("id") or "") or []
    if not toks:
        return False
    hay = re.sub(r"[^a-z0-9]", "",
                 f"{v.get('title') or ''} {v.get('expected_domain') or ''}".lower())
    return any(re.sub(r"[^a-z0-9]", "", t.lower()) in hay for t in toks)


def why_not(v: dict) -> str | None:
    """Why this verified record may NOT be applied, or None if it may.

    Returns a reason rather than a boolean so the review file says what was
    wrong with each held row. A review list of names teaches nobody anything.
    """
    if v.get("status") != 200:
        return f"feed status {v.get('status')}" + (
            f" ({v['error']})" if v.get("error") else "")
    if v.get("items", 0) < MIN_ITEMS:
        return f"only {v.get('items', 0)} items"
    if v.get("on_expected", 0) < MIN_ON_EXPECTED:
        return (f"{v.get('on_expected', 0)} of {v.get('items', 0)} links on "
                f"{v.get('expected_domain')}: a feed whose items point "
                f"elsewhere is what we are migrating away from")
    if v.get("articles", 0) < MIN_ARTICLES:
        return (f"{v.get('articles', 0)} of {v.get('on_expected', 0)} "
                f"on-domain links look like articles")
    if not named_ok(v):
        return f"channel title does not name the outlet: {v.get('title', '')!r}"
    age = v.get("newest_age_days")
    if age is None:
        return "no dated item: cannot tell whether the feed is still published"
    if age > MAX_NEWEST_AGE_DAYS:
        return f"newest item is {age:g} days old: a feed that stopped is not a daily feed"
    if v.get("expected_path") and v.get("on_path", 0) < MIN_ON_EXPECTED:
        return (f"only {v.get('on_path', 0)} items under {v['expected_path']}/: the roster "
                f"lists this edition, and the feed is another section of the domain")
    return None


def load(paths):
    recs = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
    # Keyed on the roster id where the record carries one, falling back to the
    # name. An id survives a rename and cannot be shared; a name can be both.
    # Last write wins per outlet, so a re-probe supersedes an earlier one.
    return {(r.get("id") or r["name"]): r for r in recs}


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
    by_id = {s["id"]: s for s in srcs}

    applied, review, absent = [], [], []
    # feed url -> the id that holds it, seeded with every row we are NOT
    # changing so a migration cannot collide with an existing assignment.
    feed_owner = {row["rss_url"]: row["id"] for row in srcs
                  if row.get("rss_url") and "news.google.com" not in row["rss_url"]}
    for name, v in sorted(recs.items()):
        if "found" in v and "status" not in v:
            print(f"    [stop] {name}: this looks like discover_feeds output. "
                  f"Run it through scripts/roster/verify_feeds.py first; see "
                  f"this file's header for why.")
            return 2
        row0 = by_id.get(v.get("id")) or by_name.get(v.get("name") or name)
        if row0 is None:
            absent.append(name)
            continue
        if not v.get("feed"):
            continue
        row = {"name": row0["name"], "id": row0["id"],
               "was": row0.get("rss_url"), "now": v["feed"],
               "evidence": {"items": v.get("items"),
                            "on_expected": v.get("on_expected"),
                            "articles": v.get("articles"),
                            "expected_domain": v.get("expected_domain"),
                            "title": (v.get("title") or "")[:80],
                            "sample": v.get("sample")}}
        reason = why_not(v)
        # A feed may not be assigned to two rows. Caught by
        # tests/test_roster_config.py on this pass's own output: The American
        # Spectator and The American Spectator Blog both discovered
        # spectator.org/feed/, so the migration would have drawn every article
        # the magazine published twice on the Bench as two independent
        # sources. That is the double-count this whole roster effort exists to
        # remove, and the tool was able to create it. Checked against rows we
        # are not changing AND against earlier decisions in this same run.
        if not reason:
            owner = feed_owner.get(v["feed"])
            if owner and owner != row0["id"]:
                reason = (f"feed already belongs to {owner!r}: assigning it "
                          f"here would draw the same article twice on the "
                          f"Bench as two independent sources")
        if reason:
            row["why_held"] = reason
            review.append(row)
        else:
            feed_owner[v["feed"]] = row0["id"]
            applied.append(row)

    print(f"verified records: {len(recs)}")
    print(f"clears the bar ({MIN_ITEMS}+ items, {MIN_ON_EXPECTED}+ on the "
          f"roster's own domain, {MIN_ARTICLES}+ article-shaped, title names "
          f"the outlet): {len(applied)}")
    print(f"held for review, each with its reason: {len(review)}")
    if absent:
        print(f"discovery named {len(absent)} outlet(s) not in the roster: {absent[:5]}")

    # The run label keeps a second run on the same day beside the first rather
    # than on top of it. Two runs in a day is the normal case.
    stamp = datetime.date.today().isoformat()
    label = ""
    for a in sys.argv[1:]:
        if a.startswith("--label="):
            label = "-" + a.split("=", 1)[1].strip().strip("-")
    changes_path = os.path.join(OUTDIR, f"feed-changes-{stamp}{label}.json")
    review_path = os.path.join(OUTDIR, f"feed-review-{stamp}{label}.json")

    # A DRY RUN WRITES NOTHING. It used to write both record files before
    # reading this flag, and on 2026-09-22 two guard tests against an unrelated
    # input overwrote the committed record in place: 129 applied changes became
    # 35, and the review file's two named groups became a flat list. The flag
    # was being checked at the point of the dangerous action rather than at
    # every side effect, and a dry run is a promise about all of them.
    if not apply_:
        print(f"\n--dry-run: nothing written. A real run would write "
              f"{os.path.relpath(changes_path, ROOT)} "
              f"({len(applied)} change(s)) and "
              f"{os.path.relpath(review_path, ROOT)} ({len(review)} held).")
        return 0

    # A real run will not clobber an existing record for the same date and
    # label. Losing the record of what a previous run decided is worse than
    # failing here, because the record is the only thing that makes a change
    # reversible without reading git.
    existing = [q for q in (changes_path, review_path) if os.path.exists(q)]
    if existing and "--force" not in sys.argv:
        for q in existing:
            try:
                with open(q, encoding="utf-8") as fh:
                    held = json.load(fh)
                n = len(held) if isinstance(held, list) else len(held.keys())
            except Exception:
                n = "?"
            print(f"    [stop] {os.path.relpath(q, ROOT)} already exists and "
                  f"holds {n} row(s). Pass --label=<name> to write beside it, "
                  f"or --force to replace it.")
        return 2

    os.makedirs(OUTDIR, exist_ok=True)
    with open(review_path, "w", encoding="utf-8") as fh:
        json.dump(review, fh, indent=1, ensure_ascii=False)
    with open(changes_path, "w", encoding="utf-8") as fh:
        json.dump(applied, fh, indent=1, ensure_ascii=False)

    noop = [r for r in applied if r["was"] == r["now"]]
    for row in applied:
        target = by_id.get(row.get("id")) or by_name[row["name"]]
        target["rss_url"] = row["now"]
    with open(SOURCES, "w", encoding="utf-8") as fh:
        json.dump(srcs, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"\napplied {len(applied)} feed change(s) to data/sources.json")
    if noop:
        # Reported because it was NOT reported on 2026-09-22: 24 of 129 applied
        # changes were no-ops on outlets whose feeds already worked, which
        # inflated "370 broken feeds" into an upper bound nobody had labelled.
        print(f"    of which {len(noop)} were no-ops (the row already carried "
              f"that feed), so the repaired count is {len(applied) - len(noop)}")
    google = sum(1 for s in srcs if "news.google.com" in s.get("rss_url", ""))
    print(f"    Google-fed rows remaining: {google} of {len(srcs)} "
          f"({google / len(srcs) * 100:.1f}%)")
    print(f"previous URLs recorded in {os.path.relpath(changes_path, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
