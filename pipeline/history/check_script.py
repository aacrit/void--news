#!/usr/bin/env python3
"""Validate one History script against its event, and say whether it will render.

    python3 pipeline/history/check_script.py <slug> [...]

Exits non-zero if any script carries a `fail` finding. This exists so a drafter
never has to rediscover the validator's API, and so the length is judged at the
cast narrator's own speech rate rather than one average (H-07).
"""
import sys, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from history.script_format import (  # noqa: E402
    parse_script, validate_script, estimated_minutes, NARRATOR_WPM, WPM, MUSIC_MINUTES,
)
from history.casting import cast  # noqa: E402


def check(slug: str) -> bool:
    ev = yaml.safe_load((ROOT / f"data/history/events/{slug}.yaml").read_text())
    path = ROOT / f"data/history/scripts/{slug}.txt"
    if not path.exists():
        print(f"{slug}: NOT WRITTEN")
        return False
    sc = parse_script(path.read_text(), slug)
    findings = validate_script(sc, ev)
    mins, wpm, who = estimated_minutes(sc, ev)
    ceiling = int((15.0 - MUSIC_MINUTES) * NARRATOR_WPM.get(who, WPM))

    fails = [f for f in findings if f.level == "fail"]
    warns = [f for f in findings if f.level != "fail"]
    c = cast(ev)
    print(f"{slug}")
    print(f"  cast     {who} at {wpm:.0f} wpm  (M={c.get('document_m')} F={c.get('document_f')})")
    print(f"  length   {sc.words} words -> {mins:.2f} min   ceiling {ceiling} words / 15.00 min")
    print(f"  shape    {sum(1 for s in sc.segments if s.kind=='SCENE')} scenes, "
          f"{sum(1 for s in sc.segments if s.kind=='REST')} rests, "
          f"{sum(1 for s in sc.segments if s.kind=='DOCUMENT')} documents, "
          f"{sum(1 for s in sc.segments if s.kind=='PERSPECTIVE')} accounts")
    for f in fails:
        print(f"  FAIL {f.id}: {f.detail}")
    for f in warns:
        print(f"  warn {f.id}: {f.detail}")
    if not findings:
        print("  clean")
    return not fails


if __name__ == "__main__":
    slugs = sys.argv[1:]
    if not slugs:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(0 if all([check(s) for s in slugs]) else 1)
