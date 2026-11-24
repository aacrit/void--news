#!/usr/bin/env python3
"""Every account in the data is argued by exactly one segment in the script.

The Hearing renders each account's case under that account's name. If the
resolver maps two segments to one account, or leaves one unmapped, the page
prints an argument under the wrong heading. That is worse than the current page
rather than better: attributing an argument to the side that did not make it is
precisely what the History section exists not to do.

So the assertion is not "most events resolve". It is that every event's
segments resolve to a PERMUTATION of its accounts: total, one to one, onto.

The first draft of the resolver failed two events, cuban-missile-crisis and
russian-revolution, by scoring six-character prefixes as equal-length sets:
"cuban" never equals "cubans", and "white" never equals "whites". H-09 asks
whether the stem occurs as a SUBSTRING, which is why it passed both scripts
while the resolver did not. They must not diverge again, so this checks the two
agree on all 78.
"""
import glob
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.history.export_scripts import resolve_accounts  # noqa: E402
from pipeline.history.script_format import parse_script  # noqa: E402

failures: list[str] = []
events = 0
segments_total = 0

for path in sorted(glob.glob(str(ROOT / "data/history/scripts/*.txt"))):
    slug = pathlib.Path(path).stem
    ev_path = ROOT / "data/history/events" / f"{slug}.yaml"
    if not ev_path.exists():
        failures.append(f"{slug}: script with no event record")
        continue
    event = yaml.safe_load(ev_path.read_text(encoding="utf-8"))
    script = parse_script(pathlib.Path(path).read_text(encoding="utf-8"), slug)

    accounts = event.get("perspectives") or []
    seg_titles = [s.title for s in script.segments if s.kind == "PERSPECTIVE"]
    mapped = resolve_accounts(script, event)
    events += 1
    segments_total += len(mapped)

    if len(mapped) != len(accounts):
        failures.append(
            f"{slug}: {len(mapped)} segment(s) for {len(accounts)} account(s)")
        continue

    unresolved = [seg_titles[i] for i, a in enumerate(mapped) if a is None]
    if unresolved:
        failures.append(f"{slug}: unresolved {unresolved}")
        continue

    if sorted(a for a in mapped if a is not None) != list(range(len(accounts))):
        named = [accounts[a].get("viewpoint") for a in mapped]
        failures.append(f"{slug}: not a permutation, got {named}")
        continue

    # Onto and one to one is not enough on its own: a mapping could be a valid
    # permutation and still be the WRONG permutation. Where a segment's title
    # names its account outright, that is the account it must get.
    from pipeline.history.script_format import _norm
    for i, title in enumerate(seg_titles):
        t = _norm(title or "")
        claims = [ai for ai, acc in enumerate(accounts)
                  if any(stem and stem in t for stem in
                         [w[:6] for w in _norm(acc.get("viewpoint") or "").split()
                          if len(w) > 3])]
        if len(claims) == 1 and mapped[i] != claims[0]:
            failures.append(
                f"{slug}: '{title}' names "
                f"'{accounts[claims[0]].get('viewpoint')}' but got "
                f"'{accounts[mapped[i]].get('viewpoint')}'")

if failures:
    print(f"FAIL  {len(failures)} account-resolution problem(s)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print(f"PASS  {events} events: {segments_total} segments resolve to a "
      f"permutation of their accounts, and a segment that names its account gets it")
