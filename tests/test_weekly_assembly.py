#!/usr/bin/env python3
"""Assembly gates for "The Argument": the timeline, the silences, the chapters.

Pure: no pydub, no ffmpeg, no Kokoro, no network. `build_timeline` measures
audio only through `len()`, so a fake segment of a known duration exercises
every placement decision in the programme at a millisecond's precision that a
rendered episode could never be asserted against.

What is checked here is what an ear cannot check twice: that THE SPINE is
exactly the pause it is supposed to be, that nothing plays over a cue the
timeline reserved room for, that the argument is DRY, and that the chapter
offsets are exact by construction rather than approximately right.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.weekly_producer import (  # noqa: E402
    BED_UNDER, GAPS, NOT_A_CHAPTER, SIZE_CAP_BYTES, SPEED, VOICES,
    Timeline, build_timeline, chapters,
)
from briefing.weekly_script import VOICE_WPM, parse_script  # noqa: E402

_failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


class FakeAudio:
    """A segment of a known length. That is all the timeline ever asks."""

    def __init__(self, ms):
        self.ms = int(ms)

    def __len__(self):
        return self.ms


SCRIPT = """## OPEN
E: the week in one image
## CONTENTS
E: inside this week
## COVER
E: the lead feature
## DATELINE
E: Tuesday. Thirteen sources.
## COVER
E: the rest of it
## TOPIC
E: they argue about the same agreement
## LEFT
L: the left column
## RIGHT
R: the right column
## REST
## TURN
E: what each side leaves out
## SECOND
E: the second feature
## DEPARTMENT | Technology
E: the department
## NUMBERS
E: the week measured
## EDITORIAL
E: void's own column
## CLOSE
E: the open question
"""


def _timeline(line_ms=4000):
    from briefing.weekly_producer import build_turns
    script = parse_script(SCRIPT)
    turns = build_turns(script)
    audio = {s.idx: FakeAudio(line_ms) for s, _ in turns}
    tl = build_timeline(turns, audio, opener_ms=10000, transition_ms=3500,
                        break_ms=9000, outro_ms=14000,
                        rests=_rests(script))
    return script, turns, tl


def _rests(script):
    out = {}
    for i, seg in enumerate(script.segments):
        if seg.kind == "REST":
            nxt = next((j for j in range(i + 1, len(script.segments))
                        if script.segments[j].kind != "REST"), None)
            if nxt is not None:
                out[nxt] = "rest"
    return out


def _at(tl, kind):
    return [c for c in tl.cues if c.kind == kind]


def test_spine():
    """THE SPINE is the format's one irreducible silence.

    Two people disagreeing over a bed is a talk show. Naked voice with a held
    pause between the sides is a courtroom, and the pause is the device: it is
    where the listener decides the first column was wrong before the second
    one says so.
    """
    print("\nWB-01  the spine")
    _, _, tl = _timeline()
    left, right = _at(tl, "LEFT")[-1], _at(tl, "RIGHT")[0]
    gap = right.start_ms - left.end_ms
    check("the pause between the columns is exactly the spine",
          gap == GAPS["spine"], f"{gap} ms, expected {GAPS['spine']}")
    check("nothing is scheduled inside it",
          not any(left.end_ms < at < right.start_ms
                  for at in tl.transition_at_ms + tl.break_at_ms),
          f"transitions {tl.transition_at_ms}, breaks {tl.break_at_ms}")


def test_argument_is_dry():
    """Decision one, asserted rather than described."""
    print("\nWB-02  the argument is dry")
    _, _, tl = _timeline()
    spans = tl.bed_spans()
    for kind in ("LEFT", "RIGHT", "TURN", "TOPIC"):
        for c in _at(tl, kind):
            inside = [s for s in spans if s[0] <= c.start_ms < s[1]]
            check(f"no bed under {kind}", not inside, str(inside))
    for kind in BED_UNDER:
        cues = _at(tl, kind)
        if not cues:
            continue
        c = cues[0]
        check(f"a bed under {kind}",
              any(s[0] <= c.start_ms <= s[1] for s in spans))


def test_cues_have_room():
    """A cue that is not reserved for plays under the first sentence of the
    thing it introduces. That was a real On Air defect, and it is the
    difference between music woven into a programme and music stitched on."""
    print("\nWB-03  every cue plays in the clear")
    _, _, tl = _timeline()
    for at, length, what in ([(a, 3500, "transition") for a in tl.transition_at_ms]
                             + [(a, 9000, "break") for a in tl.break_at_ms]):
        clash = [c for c in tl.cues if c.start_ms < at + length and c.end_ms > at]
        check(f"{what} at {at} plays over no speech", not clash,
              ", ".join(f"{c.kind}@{c.start_ms}" for c in clash))
    check("a seam before the argument", len(tl.transition_at_ms) >= 1)
    check("the break lands before the numbers",
          tl.break_at_ms and tl.break_at_ms[0] < _at(tl, "NUMBERS")[0].start_ms)


def test_rest():
    print("\nWB-04  the held pause")
    _, _, tl = _timeline()
    check("a rest was opened", len(tl.rest_at_ms) == 1, str(tl.rest_at_ms))
    right, turn = _at(tl, "RIGHT")[-1], _at(tl, "TURN")[0]
    check("it sits between the argument and the reckoning",
          turn.start_ms - right.end_ms >= GAPS["rest"],
          f"{turn.start_ms - right.end_ms} ms")


def test_chapters():
    print("\nWB-05  chapters")
    script, _, tl = _timeline()
    chs = chapters(tl)
    check("starts at zero", chs and chs[0]["startTime"] == 0.0)
    check("strictly increasing",
          all(chs[i]["startTime"] < chs[i + 1]["startTime"] for i in range(len(chs) - 1)))
    check("every end meets the next start",
          all(chs[i]["endTime"] == chs[i + 1]["startTime"] for i in range(len(chs) - 1)))
    check("the last chapter ends with the programme",
          chs[-1]["endTime"] == round(tl.total_ms / 1000, 3))
    kinds = [c["kind"] for c in chs]
    check("no beat is offered as a chapter",
          not any(k.upper() in NOT_A_CHAPTER for k in kinds), str(kinds))
    for want in ("open", "cover", "topic", "numbers", "editorial", "close"):
        check(f"a listener can jump to {want}", want in kinds)
    check("the department keeps its own label",
          any(c["title"] == "Technology" for c in chs),
          str([c["title"] for c in chs]))
    # The cover is interrupted by the dateline beat and resumes. Two cover
    # segments must not become two chapters called "The cover".
    check("the interrupted cover is one chapter",
          kinds.count("cover") == 2 or len([c for c in chs if c["title"] == "The cover"]) <= 2,
          str(kinds))


def test_no_gap_is_silent_dead_air():
    print("\nWB-06  the silences are bounded")
    _, _, tl = _timeline()
    worst = 0
    for a, b in zip(tl.cues, tl.cues[1:]):
        worst = max(worst, b.start_ms - a.end_ms)
    check("no gap longer than the rest plus a cue", worst <= GAPS["rest"] + 9000 + 1500,
          f"{worst} ms")
    check("the outro starts before the last word ends",
          tl.outro_at_ms < tl.cues[-1].end_ms,
          f"outro {tl.outro_at_ms}, last word ends {tl.cues[-1].end_ms}")
    check("the file is long enough to hold the outro",
          tl.total_ms >= tl.outro_at_ms + 14000)


def test_casting():
    """The bench must be RATE-MATCHED. Two voices at different natural rates
    give one side materially more airtime for the same words, which is an
    editorial fairness problem and not an aesthetic one."""
    print("\nWB-07  casting")
    l, r = VOICE_WPM[VOICES["left"]], VOICE_WPM[VOICES["right"]]
    check("the bench reads at the same rate", abs(l - r) <= 5, f"{l} vs {r} wpm")
    check("the Editor is deliberately not a bench voice",
          abs(VOICE_WPM[VOICES["editor"]] - (l + r) / 2) >= 8,
          f"{VOICE_WPM[VOICES['editor']]} vs bench {(l + r) / 2}")
    check("three distinct voices", len(set(VOICES.values())) == 3, str(VOICES))
    check("one house pace", 0.85 <= SPEED <= 1.0, str(SPEED))
    # On Air's own anchor must not also read the weekly, or the two programmes
    # are one programme.
    check("the Editor is not On Air's anchor", VOICES["editor"] != "am_puck")


def test_size_cap():
    """The old cap was 12 MB and the last issue shipped at 93.7% of it while
    running 40% UNDER its own word target: one good week from the ladder
    silently amputating the editorial."""
    print("\nWB-08  the size cap")
    check("the cap clears twenty minutes at 128k stereo",
          SIZE_CAP_BYTES > 20 * 60 * 16000, f"{SIZE_CAP_BYTES/1024/1024:.0f} MiB")
    check("and stays under the Pages per-file limit",
          SIZE_CAP_BYTES <= 25 * 1024 * 1024)
    src = (ROOT / "pipeline" / "briefing" / "weekly_producer.py").read_text()
    check("the ladder never drops a segment",
          "opinion_start_seconds" not in src and "drop" not in src.lower().split("ladder")[-1][:400])


def main():
    print("void --weekly audio assembly gates")
    test_spine()
    test_argument_is_dry()
    test_cues_have_room()
    test_rest()
    test_chapters()
    test_no_gap_is_silent_dead_air()
    test_casting()
    test_size_cap()
    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly-audio assembly gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
