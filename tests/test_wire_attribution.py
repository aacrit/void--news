#!/usr/bin/env python3
"""A wire's own copy must be recognised as the wire's.

`deduplicator._pick_origin` chooses which article in a confirmed syndicate
group is the origin. Everything else in the group becomes `is_wire_copy`, which
is what stops the Bench counting one AP story under twenty mastheads as twenty
independent sources.

Two defects, both measured on 2026-09-22 rather than inferred:

  the hand-written slug set matched **5 of the 40** outlets the roster marks
  `"type": "wire"` (afp, ap-news, ians, reuters, upi), missing
  dpa-international, kyodo-news, pti-india, anadolu-agency, tass-english and
  30 others through near-miss slugs. So the origin was usually picked by
  publish time, and a wire that files after its subscribers was tagged the
  duplicate.

  a `tier == "wire"` branch sat ABOVE the slug test and matched ZERO rows,
  because `tier` only ever holds independent / international / us_major. Dead
  code at the top of a priority list is worse than dead code anywhere else: it
  reads as the rule, and the rule that decides is the one underneath it.

This file asserts the fix cannot silently regress: the derived set must cover
every wire in the roster, and a wire that files LATE must still win the origin,
which is the case the old publish-time fallback got wrong.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from clustering.deduplicator import (  # noqa: E402
    CANONICAL_WIRE_SLUGS, WIRE_SLUGS, _pick_origin)

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


rows = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
roster_wires = {str(r["id"]).lower() for r in rows
                if str(r.get("type") or "").lower() == "wire"}

check("the roster still marks some outlets as wires", bool(roster_wires),
      "no row carries type=wire, so this gate is asserting nothing")
uncovered = sorted(roster_wires - set(WIRE_SLUGS))
check("every wire in the roster is in WIRE_SLUGS", not uncovered,
      f"{len(uncovered)} of {len(roster_wires)} uncovered: {uncovered[:6]}")
check("the hand-written set is kept as a superset, not the source of truth",
      set(CANONICAL_WIRE_SLUGS) <= set(WIRE_SLUGS)
      and len(WIRE_SLUGS) > len(CANONICAL_WIRE_SLUGS),
      f"{len(CANONICAL_WIRE_SLUGS)} hand-written, {len(WIRE_SLUGS)} derived")

# The regression that mattered: a wire filing after its subscribers.
LATE_WIRE = [
    {"source_id": "the-punch", "published_at": "2026-09-22T01:00:00Z"},
    {"source_id": "vanguard", "published_at": "2026-09-22T02:00:00Z"},
    {"source_id": "kyodo-news", "published_at": "2026-09-22T09:00:00Z"},
]
check("a wire that files last is still the origin",
      _pick_origin(LATE_WIRE)["source_id"] == "kyodo-news",
      _pick_origin(LATE_WIRE)["source_id"])

# Every roster wire must win against a non-wire, one at a time, so a single
# near-miss slug cannot hide behind the others.
lost = []
for slug in sorted(roster_wires):
    group = [{"source_id": "the-punch", "published_at": "2026-09-22T01:00:00Z"},
             {"source_id": slug, "published_at": "2026-09-22T09:00:00Z"}]
    if _pick_origin(group)["source_id"] != slug:
        lost.append(slug)
check(f"each of the {len(roster_wires)} roster wires wins its own group",
      not lost, f"{len(lost)} lost: {lost[:6]}")

# With no wire present the order is publish time, then position. Asserted
# because removing the dead tier branch changed the key's arity.
NO_WIRE = [
    {"source_id": "the-punch", "published_at": "2026-09-22T09:00:00Z"},
    {"source_id": "vanguard", "published_at": "2026-09-22T01:00:00Z"},
]
check("with no wire in the group the earliest wins",
      _pick_origin(NO_WIRE)["source_id"] == "vanguard",
      _pick_origin(NO_WIRE)["source_id"])
UNDATED = [{"source_id": "a"}, {"source_id": "b"}]
check("a group with no timestamps still resolves deterministically",
      _pick_origin(UNDATED)["source_id"] == "a")

# `tier` must not come back: it decided nothing and read as though it did.
src = (ROOT / "pipeline" / "clustering" / "deduplicator.py").read_text(
    encoding="utf-8")
check("no wire-service value is matched against `tier` again",
      'tier in ("wire"' not in src and "tier in ('wire'" not in src)

if failures:
    print(f"\nFAIL  {len(failures)} wire-attribution check(s)")
    sys.exit(1)
print(f"\nPASS  all {len(roster_wires)} roster wires are recognised as wires")
