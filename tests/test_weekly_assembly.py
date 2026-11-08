#!/usr/bin/env python3
"""Assembly gates for "The Argument" rev 2: the timeline, the silences, the
chapters, the casting, and the score against the standard.

The timeline half is pure: `build_timeline` measures audio only through a
lengths table, so a fake duration exercises every placement decision at a
millisecond's precision. The score half renders the weekly's cues at Issue
32's seed and measures them with `onair_score` exactly as the producer does,
then plants a defect for each rule that is the weekly's own.

What is checked is what an ear cannot check twice: that THE SPINE is exactly
the pause it is supposed to be, that the argument is DRY and the sting ends at
the floor before it, that the frame closes in the rest, that the bed before
Void Opinion stops and the silence is held, that the chapter offsets are exact
by construction, and that the score is calm, half-time, and resolves once.
"""

import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing import onair_score as S  # noqa: E402
from briefing import weekly_music as W  # noqa: E402
from briefing import onair_music as M  # noqa: E402
from briefing.weekly_producer import (  # noqa: E402
    GAPS, NOT_A_CHAPTER, PAN, SIZE_CAP_BYTES, bed_ending, build_cues, build_timeline, chapters,
    weekly_voicing,
)
from briefing.weekly_script import (  # noqa: E402
    CORRESPONDENT_VOICES, HOST_VOICE, SPEED, VOICE_WPM, cast_for_week, parse_script,
)

_failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


SCRIPT = """## COLD
H: the week's hardest image
## OPEN
H: From Void News, this is The Argument. The week of October twenty-sixth to November first.
H: the week in one image
## CONTENTS
H: Inside this week.
H: one
H: two
## COVER | The cover
A: the lead feature, first passage
A: second passage
B: third passage
## DATELINE
H: Tuesday. Twenty-four sources.
## COVER
A: fourth passage
B: the last passage
## TOPIC
H: they argue about the same outbreak
H: The left column first.
## LEFT
A: the left column
A: more of it
## RIGHT
B: the right column
B: more of it
## REST
## TURN
H: what each side leaves out
H: and more
## SECOND | Second feature
B: the second feature
A: its last passage
## WEEK
H: The week in brief.
A: item one
B: item two
A: item three
B: item four
A: item five
## EDITORIAL | The editorial
H: This is Void Opinion. The headline.
H: paragraph one
H: paragraph two
H: paragraph three
## CLOSE
H: the open question?
H: That's The Argument, from Void News. Every source, every story, scored for bias.
"""


def _timeline(line_s=4.0):
    script = parse_script(SCRIPT)
    cues = build_cues(script)
    tl = build_timeline(cues, {c.idx: line_s for c in cues})
    return script, cues, tl


def _at(tl, kind):
    return [c for c in tl.cues if c.kind == kind]


def _music(tl, name):
    return [m for m in tl.music if m.name == name]


def test_opening():
    print("\nWB-00  the cold open, the theme, the sign-on")
    _, _, tl = _timeline()
    cold = _at(tl, "COLD")[0]
    theme = _music(tl, "theme")[0]
    check("the cold open plays before any music", cold.end <= theme.start, f"cold ends {cold.end:.1f}, theme at {theme.start:.1f}")
    signon = _at(tl, "OPEN")[0]
    check("the sign-on lands on the theme's downbeat",
          abs(signon.start - (theme.start + W.THEME_DOWNBEAT_S + GAPS["theme_downbeat_offset"])) < 0.01)
    check("the theme's downbeat is where the hook's cadence lands", abs(W.THEME_DOWNBEAT_S - 5 * M.BAR) < 0.01)
    open_bed = _music(tl, "open")[0]
    check("the open bed enters under the theme's hold", theme.start < open_bed.start < theme.end)


def test_spine():
    """THE SPINE is the format's one irreducible silence."""
    print("\nWB-01  the spine")
    _, _, tl = _timeline()
    left, right = _at(tl, "LEFT")[-1], _at(tl, "RIGHT")[0]
    gap = right.start - left.end
    check("the pause between the columns is exactly the spine", abs(gap - GAPS["spine"]) < 1e-6, f"{gap:.2f} s")
    check("nothing is scheduled inside it",
          not any(left.end < m.start < right.start for m in tl.music), str([(m.name, m.start) for m in tl.music]))


def test_argument_is_dry():
    """No bed under the columns or the spine; the sting ends at the floor
    before the first column; the tension bed ends at the sting."""
    print("\nWB-02  the argument is dry, and the frame around it is not")
    _, _, tl = _timeline()
    beds = tl.beds()
    for kind in ("LEFT", "RIGHT"):
        for c in _at(tl, kind):
            inside = [m.name for m in beds if m.start < c.end and m.end > c.start]
            check(f"no bed under {kind}", not inside, str(inside))
    left, right = _at(tl, "LEFT")[0], _at(tl, "RIGHT")[-1]
    check("no bed in the spine", not any(m.start < right.start and m.end > _at(tl, "LEFT")[-1].end for m in beds))
    sting = _music(tl, "sting")[0]
    check("the sting ends, then the floor is held, then the left column",
          abs(left.start - (sting.end + GAPS["sting_to_column"])) < 1e-6 and GAPS["sting_to_column"] >= 1.0)
    tension = _music(tl, "tension")[0]
    topic = _at(tl, "TOPIC")
    check("the tension bed enters under the host's framing (from the interlude's release) and ends at the sting",
          topic[0].start < tension.start < topic[0].end and abs(tension.end - sting.start) < 1e-6,
          f"topic {topic[0].start:.1f}-{topic[0].end:.1f}, bed {tension.start:.1f}-{tension.end:.1f}, sting {sting.start:.1f}")
    check("the tension bed rises into the sting", bed_ending(tl, tension)[0] == "rise"
          and bed_ending(tl, tension)[1].name == "sting")
    for kind in ("OPEN", "CONTENTS", "TURN", "WEEK", "EDITORIAL", "CLOSE"):
        # the sign-on and the Void Opinion introduction land on a featured cue's
        # hold; their bed enters under them, so the SECOND line is the one tested
        c = _at(tl, kind)[1 if kind in ("OPEN", "EDITORIAL") else 0]
        check(f"a bed under {kind}", any(m.start <= c.start <= m.end for m in beds),
              f"{kind} at {c.start:.1f}; beds {[(m.name, round(m.start, 1), round(m.end, 1)) for m in beds]}")


def test_rest_and_frame():
    print("\nWB-04  the held pause, and the frame closing in it")
    _, _, tl = _timeline()
    right, turn = _at(tl, "RIGHT")[-1], _at(tl, "TURN")[0]
    check("the rest sits between the argument and the reckoning",
          abs(turn.start - right.end - GAPS["rest"]) < 1e-6 and GAPS["rest"] >= 5.0, f"{turn.start - right.end:.1f} s")
    tb = _music(tl, "turn")[0]
    check("the turn's bed swells in during the rest, after the right column has ended",
          right.end < tb.start < turn.start - 2.0, f"right ends {right.end:.1f}, bed at {tb.start:.1f}, turn at {turn.start:.1f}")


def test_stop_and_entrance():
    print("\nWB-09  the stop, the held silence, Void Opinion")
    _, _, tl = _timeline()
    week = _at(tl, "WEEK")[-1]
    wb = _music(tl, "week")[0]
    en = _music(tl, "entrance")[0]
    ed = _at(tl, "EDITORIAL")[0]
    check("the week bed stops: its hit lands after the last word and rings out",
          abs(wb.end - (week.end + GAPS["week_to_stop"] + W.STOP_RING_S)) < 1e-6)
    check("the bed before the entrance is the one that stops", bed_ending(tl, wb)[0] == "stop")
    check("the silence between the stop and the entrance is held",
          abs(en.start - wb.end - GAPS["stop_to_entrance"]) < 1e-6 and GAPS["stop_to_entrance"] >= 1.0)
    check("nothing plays in it", not any(wb.end < m.start < en.start for m in tl.music))
    check("the host speaks once the entrance's last note has landed",
          abs(ed.start - (en.start + M.ENTRANCE_VOICE_S)) < 1e-6)
    check("Void Opinion's chapter starts at the entrance", tl.editorial_at == en.start)
    eb = _music(tl, "editorial")
    check("the editorial's bed enters under the introduction, after the entrance's held note",
          eb and ed.start < eb[0].start < ed.end and eb[0].start >= en.end - 1.0, f"intro {ed.start:.1f}-{ed.end:.1f}, bed at {eb[0].start:.1f}")
    # the week breathes after every second item: the gaps say so
    items = _at(tl, "WEEK")[1:]
    gaps = [b.start - a.end for a, b in zip(items, items[1:])]
    check("the week breathes after items two and four and not after the last",
          abs(gaps[1] - GAPS["week_breath"]) < 1e-6 and abs(gaps[0] - GAPS["week_items"]) < 1e-6 and len(wb.tags) == 2,
          f"{[round(g, 2) for g in gaps]} tags {wb.tags}")


def test_interludes_and_datelines():
    print("\nWB-10  the interludes and the dateline's toll")
    _, _, tl = _timeline()
    ils = _music(tl, "interlude")
    check("two interludes: into the argument and into the second feature", len(ils) == 2)
    topic, second = _at(tl, "TOPIC")[0], _at(tl, "SECOND")[0]
    check("the voice after an interlude speaks over its release bar",
          all(abs(c.start - (il.start + W.INTERLUDE_VOICE_S)) < 1e-6 for il, c in zip(ils, (topic, second))))
    cover_end = _at(tl, "COVER")[-1].end
    check("the first interlude follows the cover", abs(ils[0].start - cover_end - GAPS["story_to_interlude"]) < 1e-6)
    d = _at(tl, "DATELINE")[0]
    feature = [m for m in _music(tl, "feature") if m.start < d.start < m.end]
    check("a feature bed plays under the dateline", bool(feature))
    check("a toll is placed after the dateline's last word, inside the held beat",
          feature and any(abs(feature[0].start + a - (d.end + 0.35)) < 0.01 for a in feature[0].accents),
          str(feature[0].accents if feature else None))
    nxt = [c for c in tl.cues if c.start > d.end][0]
    check("the beat out of the dateline is held", abs(nxt.start - d.end - GAPS["from_dateline"]) < 1e-6)
    for il in ils:
        clash = [c for c in tl.cues if c.start < il.start + W.INTERLUDE_VOICE_S - 0.01 and c.end > il.start]
        check(f"the interlude at {il.start:.1f} is heard in the clear until its release", not clash)


def test_chapters():
    print("\nWB-05  chapters")
    _, _, tl = _timeline()
    chs = chapters(tl)
    check("starts at zero", chs and chs[0]["startTime"] == 0.0)
    check("strictly increasing", all(chs[i]["startTime"] < chs[i + 1]["startTime"] for i in range(len(chs) - 1)))
    check("every end meets the next start", all(chs[i]["endTime"] == chs[i + 1]["startTime"] for i in range(len(chs) - 1)))
    check("the last chapter ends with the programme", chs[-1]["endTime"] == round(tl.total, 3))
    kinds = [c["kind"] for c in chs]
    check("no beat is offered as a chapter", not any(k.upper() in NOT_A_CHAPTER for k in kinds), str(kinds))
    for want in ("open", "contents", "cover", "topic", "second", "week", "editorial", "close"):
        check(f"a listener can jump to {want}", want in kinds)
    check("the interrupted cover is one chapter", kinds.count("cover") == 1, str(kinds))
    topic = next(c for c in chs if c["kind"] == "topic")
    check("The Argument's chapter starts at the interlude before it", topic["startTime"] == round(_music(tl, "interlude")[0].start, 3))
    ed = next(c for c in chs if c["kind"] == "editorial")
    check("Void Opinion's chapter is titled so and starts at the entrance",
          ed["title"] == "Void Opinion" and ed["startTime"] == round(tl.editorial_at, 3) and ed.get("subtitle") == "The editorial")


def test_no_gap_is_silent_dead_air():
    print("\nWB-06  the silences are bounded")
    _, _, tl = _timeline()
    worst = max(b.start - a.end for a, b in zip(tl.cues, tl.cues[1:]))
    check("no gap longer than the entrance and its held silence", worst <= M.ENTRANCE_S + W.STOP_RING_S + 4.0, f"{worst:.1f} s")
    check("the outro starts before the last word ends", tl.outro_at < tl.cues[-1].end)
    check("the file is long enough to hold the outro", tl.total >= tl.outro_at + W.OUTRO_S)


def test_casting():
    print("\nWB-07  casting")
    cast = cast_for_week("2026-10-26")
    check("three distinct voices", len(set(cast.values())) == 3, str(cast))
    check("the host is On Air's anchor: one family, one voice for Void", cast["H"] == HOST_VOICE == "af_aoede")
    check("the correspondents are neither the host nor each other", set(CORRESPONDENT_VOICES) == {cast["A"], cast["B"]})
    check("one house pace for all three, On Air's", SPEED == 0.88)
    check("every voice in the cast has a measured rate", all(v in VOICE_WPM for v in cast.values()))
    check("three positions in the room: host centre, correspondents apart",
          PAN["H"] == 0.0 and PAN["A"] < 0 < PAN["B"] and PAN["A"] == -PAN["B"])


def test_size_cap():
    print("\nWB-08  the size cap")
    check("the cap clears twenty minutes at 128k stereo", SIZE_CAP_BYTES > 20 * 60 * 16000)
    check("and stays under the Pages per-file limit", SIZE_CAP_BYTES <= 25 * 1024 * 1024)
    src = (ROOT / "pipeline" / "briefing" / "weekly_producer.py").read_text()
    check("the ladder never drops a segment", "never dropped" in src)


# ---------------------------------------------------------------------------
# The score
# ---------------------------------------------------------------------------

def _shape(x, fi, fo):
    return S._normalise(S.fade(S.shape_bed(x), fi, fo))


def low_onsets(x: np.ndarray) -> float:
    """Kicks a second: onsets in 40-120 Hz on a 50 ms grid (the beat's band;
    `clock_density` is the same meter in the clock's band)."""
    from scipy import signal as sg
    m = S.mono(x)
    band = sg.sosfilt(sg.butter(4, [40.0, 120.0], btype="band", fs=S.SR, output="sos"), m)
    n = int(0.05 * S.SR)
    k = len(band) // n
    env = np.sqrt(np.mean(band[: k * n].reshape(k, n) ** 2, axis=1))
    flux = np.diff(env, prepend=env[:1])
    thr = float(np.median(flux) + 1.5 * np.std(flux))
    peaks = sum(1 for i in range(1, k - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]
                and env[i] >= 2.0 * float(np.mean(env[max(0, i - 4):i]) + 1e-9))
    return peaks / (k * 0.05)


def test_score():
    print("\nWB-11  the score against the standard, at Issue 32's seed")
    t0 = time.time()
    v = weekly_voicing({"edition": "world", "week_start": "2026-10-26"})
    v2 = weekly_voicing({"edition": "world", "week_start": "2026-11-02"})
    check("two weeks get two voicings", v.seed != v2.seed)
    theme, _ = S.level_featured(_shape(W.render_theme(v), 0.01, 1.0))
    check("the theme meets the featured standard", not S.check_cue(theme, "featured"), str([f.id for f in S.check_cue(theme, "featured")]))
    mom = S.lufs_momentary(theme)
    hit = int(W.THEME_DOWNBEAT_S / 0.1)
    check("the theme's downbeat is a hit within 3 dB of its loudest moment",
          float(np.max(mom[hit - 2:hit + 4])) >= float(np.max(mom)) - 3.0, f"{float(np.max(mom[hit - 2:hit + 4])):.1f} vs {float(np.max(mom)):.1f}")
    beds = {}
    for seg, dur in (("open", 30.0), ("feature", 36.0), ("tension", 20.0), ("turn", 30.0), ("week", 36.0),
                     ("editorial", 30.0), ("close", 18.0)):
        bed, _ = S.level_bed(_shape(W.render_bed(v, seg, dur), 2.0, 2.5))
        beds[seg] = bed
        f = S.check_cue(bed, "bed")
        check(f"the {seg} bed meets the bed standard", not f, str([x.id for x in f]))
        check(f"the {seg} bed sits at {S.BED_LUFS} LUFS", abs(S.lufs_integrated(bed) - S.BED_LUFS) < 0.6, f"{S.lufs_integrated(bed):.1f}")
    # half-time: the weekly's beat lands half as often as On Air's, on the same grid
    onair = S.voicing_for("onair:world:2026-11-08")
    lead, _ = S.level_bed(S.render_bed(onair, "lead", 30.0))
    k_w, k_o = low_onsets(beds["open"]), low_onsets(lead)
    check("half-time: the open bed's kicks a second are at most 0.7 of On Air's lead bed's",
          k_o > 0 and k_w <= 0.7 * k_o, f"{k_w:.2f}/s against {k_o:.2f}/s")
    check("the tension bed carries no clock and no kick", S.clock_density(beds["tension"]) <= 0.15 and low_onsets(beds["tension"]) <= 0.2 * max(k_o, 1e-9),
          f"clock {S.clock_density(beds['tension']):.2f}/s, kicks {low_onsets(beds['tension']):.2f}/s")
    check("the slow rooms carry under half the open bed's clock",
          all(S.clock_density(beds[s]) <= 0.5 * S.clock_density(beds["open"]) for s in ("turn", "editorial")) and S.clock_density(beds["open"]) >= 0.3,
          f"{S.clock_density(beds['open']):.2f} vs turn {S.clock_density(beds['turn']):.2f}, editorial {S.clock_density(beds['editorial']):.2f}")
    # the stop
    stop, _ = S.level_bed(_shape(W.render_bed(v, "week", 25.0, ending="stop", tags=(8.0, 14.0)), 2.0, 1.0))
    check("a stopped week bed still meets the bed standard", not S.check_cue(stop, "bed"), str([f.id for f in S.check_cue(stop, "bed")]))
    smom = S.lufs_momentary(stop)
    h = int((len(stop) / S.SR - W.STOP_RING_S - 0.1) / 0.1)
    check("the stop is a hit within 3 dB of the bed's loudest moment", float(smom[h]) >= float(np.max(smom)) - 3.0, f"{smom[h]:.1f} vs {np.max(smom):.1f}")
    check("the stopped bed ends at the floor", float(smom[-1]) <= float(np.max(smom)) - 30.0, f"{smom[-1]:.1f}")
    # the interludes
    ils = []
    for i in range(2):
        il, _ = S.level_interlude(_shape(W.render_interlude(v, i), 0.01, 1.2))
        ils.append(il)
        check(f"interlude {i} meets the interlude standard", not S.check_cue(il, "interlude"), str([f.id for f in S.check_cue(il, "interlude")]))
    plans = [W.interlude_plan(v, i) for i in range(2)]
    check("two interludes in one episode share no tune, chord triple or voice",
          plans[0][0] is not plans[1][0] and plans[0][1] != plans[1][1] and plans[0][2] != plans[1][2], str([p[1:] for p in plans]))
    cos = float(S.chroma_profile(ils[0]) @ S.chroma_profile(ils[1]))
    check("the two interludes differ in what they play", cos < 0.9, f"chroma cosine {cos:.2f}")
    check("the interlude is four bars after its riser, the voice over the release bar",
          abs(W.INTERLUDE_S - (W.INTERLUDE_RISER_S + 4 * M.BAR)) < 0.06 and W.INTERLUDE_RISER_S + 3 * M.BAR <= W.INTERLUDE_VOICE_S < W.INTERLUDE_S)
    # the sting
    st, _ = S.level_sting(_shape(W.render_sting(v), 0.01, 0.2))
    check("the sting meets its standard", not S.check_cue(st, "sting"), str([f.id for f in S.check_cue(st, "sting")]))
    check("the sting is short", W.STING_S <= 6.0)
    tail = S.mono(st)[-int(0.3 * S.SR):]
    check("the sting ends at the floor", 20 * np.log10(float(np.sqrt(np.mean(tail ** 2))) + 1e-12) < S.STING_TAIL_DBFS)
    swell = np.concatenate([st[: int(1.2 * S.SR)] * 0.0, st[: len(st) - int(1.2 * S.SR)]])  # the hit moved 1.2 s later: still inside
    padded = st.copy()
    padded[-int(1.0 * S.SR):] = 0.02 * np.sin(2 * np.pi * 110.0 * np.arange(int(1.0 * S.SR)) / S.SR)[:, None]
    check("a sting that does not end at the floor is caught", any(f.id == "sting-tail" for f in S.check_cue(padded, "sting")))
    late = np.concatenate([np.zeros((int(3.0 * S.SR), 2)), st[: len(st) - int(3.0 * S.SR)]])
    check("a sting that swells instead of hitting is caught", any(f.id == "sting-hit" for f in S.check_cue(late, "sting")))
    check("a sting with its hit inside the window passes that rule", not any(f.id == "sting-hit" for f in S.check_cue(swell, "sting")))
    # the entrance and the outro
    en, _ = S.level_featured(_shape(W.render_entrance(v), 0.02, 1.4))
    check("the entrance (On Air's) meets the featured standard", not S.check_cue(en, "featured"))
    outro, _ = S.level_featured(_shape(W.render_outro(v), 0.02, 3.0))
    check("the outro meets the featured standard", not S.check_cue(outro, "featured"), str([f.id for f in S.check_cue(outro, "featured")]))
    check("the outro falls to silence", float(np.max(np.abs(outro[-S.SR // 2:]))) < 1e-3)
    land = S.chroma_profile(outro[int(W.OUTRO_LAND_S * S.SR): int((W.OUTRO_LAND_S + 3.0) * S.SR)])
    before = S.chroma_profile(outro[: int(W.OUTRO_LAND_S * S.SR)])
    check("the outro lands on D major: the major third rings where the minor did",
          land[6] > land[5] + 0.1 and before[5] > before[6], f"landing F# {land[6]:.2f} F {land[5]:.2f}; before F {before[5]:.2f} F# {before[6]:.2f}")
    check("every bed's weight is in the bass, the low-mids left for the voice",
          all(S.band_share(x, 40.0, 120.0) >= 0.75 and S.band_share(x, 150.0, 400.0, 100.0) <= S.BED_LOWMID_MAX_SHARE for x in beds.values()))
    # the toll: the same bed with and without the dateline's toll differs only there
    va, vb = weekly_voicing({"week_start": "2026-10-26"}), weekly_voicing({"week_start": "2026-10-26"})
    acc = (9.0, 17.0)
    with_, without = W.render_bed(va, "feature", 26.0, accents=acc), W.render_bed(vb, "feature", 26.0)
    diff = S.mono(with_ - without)
    n = int(1.5 * S.SR)
    k = len(diff) // n
    med = float(np.median(np.mean(diff[: k * n].reshape(k, n) ** 2, axis=1)))
    at_acc = [float(np.mean(diff[int(t * S.SR): int(t * S.SR) + n] ** 2)) for t in acc]
    check("the tolls are where the bed with them differs from the bed without",
          all(e >= 8.0 * (med + 1e-18) for e in at_acc) and float(np.max(np.abs(diff))) > 0.02, f"{[round(e / (med + 1e-18)) for e in at_acc]}x")
    quiet = [float(np.mean(diff[int(t * S.SR): int(t * S.SR) + n] ** 2)) for t in (2.0, 13.0, 22.0)]
    check("away from the tolls the two renders agree", all(q <= 0.15 * min(at_acc) for q in quiet))
    print(f"  (score measured in {time.time() - t0:.0f}s)")


def main():
    print("void --weekly audio assembly gates")
    test_opening()
    test_spine()
    test_argument_is_dry()
    test_rest_and_frame()
    test_stop_and_entrance()
    test_interludes_and_datelines()
    test_chapters()
    test_no_gap_is_silent_dead_air()
    test_casting()
    test_size_cap()
    test_score()
    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly-audio assembly gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
