#!/usr/bin/env python3
"""Add verified major outlets to data/sources.json.

Inputs, all three required so that nothing is invented here:

  metadata    data/roster/majors-metadata-<date>.json, the facts about each
              outlet (roster name, country, type, notes) plus the L/C/R to
              baseline map.
  target      scripts/roster/majors_target.py, which supplies the intended
              side. It is editorial judgement and says so in its own header.
  verified    the output of scripts/roster/verify_feeds.py, filtered to the
              rows that passed. An outlet with no verified direct feed is NOT
              added: the whole reason this work exists is that 540 sources fed
              by Google News queries carry a median of 11 words and cannot be
              scored on their text, so adding an outlet we could only feed
              through Google would add a row to the roster and nothing to the
              measurement.

WHAT IS AND IS NOT MEASURED, restated here because it is the one thing a
reader of the roster could be misled by: name, url, country, tier and type are
facts. `political_lean_baseline` is NOT. It is the intended side mapped
conservatively inward (L to center-left, C to center, R to center-right), so a
new row is never claimed to be extreme on evidence nobody has, and every row's
notes carry the sentence saying so. Leaving them `unrated` was the other
option and is worse: `political_lean.py` drops every article from an unrated
outlet out of the lean aggregate and off the Deep Dive spectrum, so an unrated
major would be invisible exactly where it is most needed.

    python3 scripts/roster/add_sources.py <metadata.json> <verified.jsonl>
    python3 scripts/roster/add_sources.py <metadata.json> <verified.jsonl> --apply
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from majors_target import MAJORS  # noqa: E402

ROSTER = ROOT / "data" / "sources.json"

# The bar for auto-applying, and every part of it was earned by a measured
# failure on 2026-09-22. See scripts/roster/verify_feeds.py for the two the
# first version of this pass got wrong.
MIN_ITEMS = 10          # a feed of three stories is not a daily feed
MIN_ON_EXPECTED = 10    # links must be on the outlet's OWN registered domain
MIN_ARTICLES = 10       # and must look like articles, not section fronts

PROVISIONAL = ("Baseline is a provisional inward placement from the "
               "majors-target side, not a measurement; pending the "
               "outlet-baseline programme.")


def slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s


def side_of(target: str) -> str | None:
    for entries in MAJORS.values():
        for name, side in entries:
            if name == target:
                return side
    return None


def _title_uses_own_brand(meta_row: dict, verified: dict) -> bool:
    """Does the feed title carry a brand this outlet has declared as its own?

    `verify_feeds.named` asks whether the title carries a word of the outlet's
    name, which is the right default and rejects two correct feeds: Frankfurter
    Allgemeine titles its feed "Aktuell - FAZ.NET" and Elsevier Weekblad,
    renamed EW Magazine in 2018, titles its "EWmagazine.nl". Loosening the
    check would have accepted those and everything else; a token declared per
    outlet in the metadata keeps the equivalence reviewable.
    """
    tokens = meta_row.get("feed_tokens") or []
    if not tokens:
        return False
    # Title AND the expected domain, which is exactly the haystack
    # `verify_feeds.named` uses. Hankyoreh's feed titles itself only in Korean
    # ("\uc804\uc7b4\uae30\uc0ac : \ub274\uc2a4 : \ud55c\uac78\ub808"), so its declared brand `hani` appears in
    # hani.co.kr and nowhere a title check can see. The domain is not a free
    # pass: it is the same value every item link in this feed was just
    # required to sit on.
    hay = re.sub(r"[^a-z0-9]", "",
                 f"{verified.get('title') or ''} "
                 f"{verified.get('expected_domain') or ''}".lower())
    return any(re.sub(r"[^a-z0-9]", "", t.lower()) in hay for t in tokens)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    meta_doc = json.loads(pathlib.Path(args[0]).read_text(encoding="utf-8"))
    lean_map = meta_doc["_lean_map"]
    meta = meta_doc["outlets"]
    verified = [json.loads(l) for l in
                pathlib.Path(args[1]).read_text(encoding="utf-8").splitlines() if l.strip()]

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    taken_ids = {str(s.get("id")) for s in roster}
    taken_names = {str(s.get("name")) for s in roster}

    added, rejected = [], []
    for v in verified:
        target = v["name"]
        m = meta.get(target)
        if not m:
            rejected.append((target, "no metadata row"))
            continue
        side = side_of(target)
        if side is None:
            rejected.append((target, "not in majors_target"))
            continue
        if v.get("status") != 200:
            rejected.append((target, f"feed status {v.get('status')}"))
            continue
        if (v.get("items", 0) < MIN_ITEMS
                or v.get("on_expected", 0) < MIN_ON_EXPECTED
                or v.get("articles", 0) < MIN_ARTICLES):
            rejected.append((target, f"items={v.get('items')} "
                                     f"on_expected={v.get('on_expected')} "
                                     f"articles={v.get('articles')}"))
            continue
        if not v.get("named") and not _title_uses_own_brand(m, v):
            rejected.append((target, f"feed title does not name the outlet: "
                                     f"{v.get('title','')!r}"))
            continue
        name = m["roster_name"]
        sid = m.get("id") or slug(name)
        if name in taken_names or sid in taken_ids:
            rejected.append((target, f"already on the roster as {name!r}/{sid!r}"))
            continue
        row = {
            "id": sid,
            "name": name,
            # The homepage verify_feeds checked the item links against. Taking
            # it from the verified record rather than re-deriving it is what
            # stops the roster's `url` and the domain we validated against
            # drifting apart.
            "url": m.get("url") or v["url"],
            "rss_url": v["feed"],
            "country": m["country"],
            "tier": m.get("tier", "international"),
            "type": m["type"],
            "political_lean_baseline": lean_map[side],
            "credibility_notes": f"{m['notes']} {PROVISIONAL}",
        }
        added.append(row)
        taken_names.add(name)
        taken_ids.add(sid)

    print(f"verified rows in: {len(verified)}")
    print(f"would add: {len(added)}")
    for r in added:
        print(f"  + {r['name']:34s} {r['country']}  {r['political_lean_baseline']:13s} {r['rss_url'][:64]}")
    print(f"held for review: {len(rejected)}")
    for name, why in rejected:
        print(f"  - {name:34s} {why}")

    if apply:
        roster.extend(added)
        ROSTER.write_text(json.dumps(roster, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        stamp = os.environ.get("VOID_ROSTER_DATE", "2026-09-22")
        log = ROOT / "data" / "roster" / f"majors-added-{stamp}.json"
        log.write_text(json.dumps(
            {"added": added, "held": [{"name": n, "why": w} for n, w in rejected]},
            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote {len(added)} rows to {ROSTER.relative_to(ROOT)} "
              f"(roster now {len(roster)}) and the record to "
              f"{log.relative_to(ROOT)}")
        # The frontend's copy reads the roster's size from a generated config.
        # Regenerated here, in the same call, so the two cannot be updated
        # separately: the site said "50 stories" for two weeks after the feed
        # became 20 because the number lived in two places.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "emit_roster_config", HERE / "emit_roster_config.py")
        emit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(emit)
        emit.main()
    else:
        print("\ndry run. pass --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
