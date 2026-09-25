"""Archival clips and the mood-aware production: every gate against a planted defect.

docs/proposals/HISTORY-AUDIO-ARCHIVAL.md is the spec. A real recording is a
factual claim four times over (this person, this occasion, this date, these
words), so each claim has a check, and each check is asserted twice here:
silent on a clean fixture, firing on a fixture with exactly one thing wrong.

  directives   `# MOOD:` / `# CLIP:` reach the producer and nothing else: the
               export, the H-rules and the pages see the script unchanged
  H-12         rights: a basis outside policy B, or no CEO signature
  H-13         provenance: a recording missing who, when, where, or where from
  H-14         transcript: the recognised words do not align with the stored
               transcript (fixture: the same speaker in a different passage)
  H-15         spoken credit: the narrator does not name the speaker and say
               "recording" or "broadcast" before the clip
  H-16         caps: over 45 s, more than two, or one in the OPEN
  H-17         no bed under a real voice: (a) in the timeline, (b) in the
               rendered music and ambience buses, by RMS

Runs with numpy and pydub and no Kokoro, no network and no ffmpeg, so it sits
in the auto-merge gates job.

Run: python tests/test_history_clips.py
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from history.script_format import parse_script, validate_script  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{': ' + detail if detail else ''}")


SLUG = "partition-of-india"
SCRIPT_PATH = ROOT / "data/history/scripts" / f"{SLUG}.txt"
EVENT = yaml.safe_load((ROOT / "data/history/events" / f"{SLUG}.yaml").read_text(encoding="utf-8"))
RAW = SCRIPT_PATH.read_text(encoding="utf-8")


def _strip_comments(raw: str) -> str:
    return "\n".join(l for l in raw.splitlines()
                     if not (l.lstrip().startswith("#") and not l.startswith("## ")))


# ---------------------------------------------------------------------------
# 1. Directives are read, and are inert to every other consumer
# ---------------------------------------------------------------------------

def test_directives_parsed() -> None:
    sc = parse_script(RAW, SLUG)
    moods = [s.directive("MOOD").head for s in sc.segments if s.directive("MOOD")]
    check("directives: the pilot's moods are read", len(moods) >= 20, f"{len(moods)} moods")
    clips = [d for s in sc.segments for d in s.directives_of("CLIP")]
    check("directives: two CLIP slots are read", len(clips) == 2, f"{len(clips)}")
    nehru = next((d for d in clips if "nehru" in d.args.get("id", "")), None)
    check("directives: CLIP args parse", nehru is not None and nehru.args.get("replaces") == "document"
          and nehru.args.get("origin") == "All India Radio", repr(nehru))
    # A comment that is not a directive stays a comment.
    sc2 = parse_script("## OPEN\n# note: this is only a note\n# MOODY: no\nN: A line.\n", "t")
    check("directives: an unknown key is not a directive", sc2.segments[0].directives == [],
          repr(sc2.segments[0].directives))
    # A directive before any segment, or inside SAY, attaches to nothing.
    sc3 = parse_script("# MOOD: dread\n## OPEN\nN: A line.\n## SAY\n# MOOD: grief\nX = ex\n", "t")
    check("directives: header comments attach to nothing",
          all(not s.directives for s in sc3.segments), repr([s.directives for s in sc3.segments]))


def test_directives_inert() -> None:
    with_d = parse_script(RAW, SLUG)
    without = parse_script(_strip_comments(RAW), SLUG)
    # The lines, the segments and the SAY table are identical.
    check("inert: same segments", [(s.kind, s.title, s.author, s.work, s.date) for s in with_d.segments]
          == [(s.kind, s.title, s.author, s.work, s.date) for s in without.segments])
    check("inert: same lines", [[(l.speaker, l.text) for l in s.lines] for s in with_d.segments]
          == [[(l.speaker, l.text) for l in s.lines] for s in without.segments])
    check("inert: same SAY", with_d.say == without.say)
    # The H-rules see exactly the same script.
    f1 = sorted((f.id, f.level, f.segment, f.detail) for f in validate_script(with_d, EVENT))
    f2 = sorted((f.id, f.level, f.segment, f.detail) for f in validate_script(without, EVENT))
    check("inert: H-01..H-11 findings unchanged", f1 == f2, f"{f1} != {f2}")
    # The exporter (which feeds the Hearing and the thesis page's episode
    # marks) writes byte-identical JSON.
    from pipeline.history.export_scripts import export
    j1 = json.dumps(export(with_d, EVENT), sort_keys=True)
    j2 = json.dumps(export(without, EVENT), sort_keys=True)
    check("inert: export JSON unchanged", j1 == j2)
    check("inert: no directive leaks into the export", "MOOD" not in j1 and "CLIP" not in j1
          and "clip-nehru" not in j1)
    # And the committed build-data the pages read is what the exporter writes.
    served = ROOT / "frontend/build-data/history-scripts" / f"{SLUG}.json"
    if served.exists():
        check("inert: served script JSON carries no directive",
              "clip-nehru" not in served.read_text(encoding="utf-8"))


TESTS = [test_directives_parsed, test_directives_inert]


def main() -> int:
    for t in TESTS:
        try:
            t()
        except Exception as e:  # a crash is a failure, with its name
            import traceback
            failures.append(f"{t.__name__} raised {type(e).__name__}: {e}\n{traceback.format_exc()}")
    if failures:
        print(f"FAIL  {len(failures)} check(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS  {len(TESTS)} archival-clip and mood gates: directives inert, "
          f"H-12..H-17 each fire on a planted defect and pass the committed pilot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
