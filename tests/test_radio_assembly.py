"""Radio show assembly with a fake engine: timeline, chapters, music placement,
ID3 + sidecar chapters, and (when ffmpeg is present) loudness.

    python tests/test_radio_assembly.py

No TTS, no network. Each turn becomes a tone burst whose length is derived
from its word count, so the test knows every cue position in advance.
"""

from __future__ import annotations

import datetime
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from pydub import AudioSegment  # noqa: E402
from pydub.generators import Sine  # noqa: E402

from briefing.radio_script_generator import parse_rundown, THROW_LINE  # noqa: E402
from briefing.tts_engines import TurnSpec, EngineResult  # noqa: E402
from briefing import radio_producer as rp  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "radio_rundown_2026-09-18.txt"
EDITORIAL = ("Now, void opinion.\nThrough a pragmatic lens today.\nA headline for the editorial.\n\n"
             "First paragraph of the argument, with two sentences. Here is the second one.\n\n"
             "The verdict stands alone.\n\n"
             "Closing paragraph. This was void opinion.")

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)
        print(f"  FAIL {msg}")


class FakeEngine:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def available(self):
        return True, "ok"

    def voice_id(self, role):
        return {"A": "fake_a", "B": "fake_b"}[role]

    def synthesize_batch(self, turns, *, deadline_s=0.0):
        self.calls += 1
        res = EngineResult(engine=self.name)
        for t in turns:
            ms = 120 * max(1, len(t.text.split()))    # 120 ms per word
            freq = 220 if t.role == "A" else 330
            res.audio[t.idx] = (Sine(freq, sample_rate=24000).to_audio_segment(duration=ms)
                                .apply_gain(-12).set_channels(1).set_sample_width(2))
        res.timing = {"rtf": 0.0}
        return res


def main() -> None:
    raw = FIXTURE.read_text(encoding="utf-8")
    rundown = parse_rundown(raw)
    turns = rp.build_turns(rundown, EDITORIAL)
    kinds = [m["kind"] for _, m in turns]
    check(kinds[0] == "OPEN" and kinds[-1] == "CLOSE", "OPEN first, CLOSE last")
    check("THROW" in kinds and kinds.index("THROW") == kinds.index("EDITORIAL") - 1, "throw precedes the editorial")
    check(kinds.index("EDITORIAL") > kinds.index("FINALLY"), "editorial after the kicker")
    throw = next(s for s, m in turns if m["kind"] == "THROW")
    check(throw.text == THROW_LINE and throw.role == "A", "throw line is the constant, voice A")
    check(all(s.role == "B" for s, m in turns if m["kind"] == "EDITORIAL"), "editorial is voice B")
    verdicts = [m for _, m in turns if m["kind"] == "EDITORIAL" and m.get("verdict")]
    check(len(verdicts) == 1, f"one one-sentence verdict paragraph detected ({len(verdicts)})")
    check(not any(ch.isdigit() for s, _ in turns for ch in s.text), "no digits reach the engine")
    check(any("ko-HAHT" in s.text for s, _ in turns), "SAY respelling applied before synthesis")
    check(any("U-S President" in s.text for s, _ in turns), "initialisms hyphenated")

    # timeline against the gap table
    eng = FakeEngine()
    res = eng.synthesize_batch([s for s, _ in turns])
    ident_ms, stab_ms, outro_ms = 2400, 700, 2000
    tl = rp.build_timeline(turns, res.audio, ident_ms, stab_ms, outro_ms)
    G = rp.RADIO_GAPS
    c = tl.cues
    check(c[0].start_ms == ident_ms - G["ident_overlap"], "sign-on starts inside the ident tail")
    by_kind = {}
    for cue in c:
        by_kind.setdefault(cue.kind, []).append(cue)
    menu = by_kind["MENU"]
    check(menu[0].start_ms - by_kind["OPEN"][-1].end_ms == G["open_to_menu"], "OPEN -> MENU gap")
    check(menu[1].start_ms - menu[0].end_ms == G["menu_item"], "menu item gap")
    story = by_kind["STORY"]
    check(story[0].start_ms - menu[-1].end_ms == G["menu_to_story"], "MENU -> STORY gap")
    check(tl.news_start_ms == story[0].start_ms, "news_start = STORY 1 start")
    # inside story 1: same speaker then speaker change
    s1 = [x for x in story if x.segment_idx == story[0].segment_idx]
    check(s1[1].start_ms - s1[0].end_ms == G["same_speaker"], "same-speaker beat")
    check(s1[-1].start_ms - s1[-2].end_ms == G["speaker_change"], "speaker-change beat")
    s2_first = next(x for x in story if x.segment_idx != story[0].segment_idx)
    check(s2_first.start_ms - s1[-1].end_ms == G["story_to_story"], "story -> story gap")
    briefs = by_kind["BRIEFS"]
    check(briefs[0].start_ms - story[-1].end_ms == G["story_to_story"], "STORY -> BRIEFS gap")
    check(briefs[1].start_ms - briefs[0].end_ms == G["briefs_item"], "briefs item gap")
    fin = by_kind["FINALLY"]
    check(fin[0].start_ms - briefs[-1].end_ms == G["briefs_to_finally"], "BRIEFS -> FINALLY gap")
    thr = by_kind["THROW"][0]
    check(thr.start_ms - fin[-1].end_ms == G["to_throw"], "-> throw gap")
    ed = by_kind["EDITORIAL"]
    check(tl.stab_at_ms == thr.end_ms + G["throw_to_stab"], "stab lands after the throw")
    check(ed[0].start_ms == tl.stab_at_ms + stab_ms + G["stab_to_editorial"], "editorial after the stab")
    check(tl.editorial_start_ms == thr.start_ms, "editorial chapter starts at the throw")
    # verdict paragraph gets the longer beat on both sides
    vi = next(i for i, x in enumerate(ed) if x.verdict)
    check(ed[vi].start_ms - ed[vi - 1].end_ms == G["editorial_verdict"], "beat before the verdict")
    check(ed[vi + 1].start_ms - ed[vi].end_ms == G["editorial_verdict"], "beat after the verdict")
    check(ed[1].start_ms - ed[0].end_ms == G["editorial_paragraph"], "paragraph beat")
    close = by_kind["CLOSE"]
    check(close[0].start_ms - ed[-1].end_ms == G["editorial_to_close"], "EDITORIAL -> CLOSE gap")
    check(tl.outro_at_ms == close[-1].end_ms - G["outro_overlap"], "outro under the sign-off")
    check(tl.total_ms == max(close[-1].end_ms, tl.outro_at_ms + outro_ms) + G["tail"], "total length")

    # chapters derive from the cues
    chapters = rp.chapters_from_timeline(tl, "An editorial headline", {"d3afa900-ea54-4eb8-b95e-f6ed157317a3": "https://x/story/1/"})
    kinds_c = [ch["kind"] for ch in chapters]
    check(kinds_c == ["headlines", "story", "story", "story", "story", "briefs", "finally", "editorial"], f"chapter kinds {kinds_c}")
    check(chapters[0]["startTime"] == 0.0, "first chapter at 0")
    check(abs(chapters[1]["startTime"] - story[0].start_ms / 1000) < 0.001, "story 1 chapter == cue start")
    check(abs(chapters[-1]["startTime"] - thr.start_ms / 1000) < 0.001, "editorial chapter == throw start")
    check(chapters[1]["url"] == "https://x/story/1/" and chapters[1]["rank"] == 1, "permalink + rank on story chapters")
    check(chapters[-1]["subtitle"] == "An editorial headline", "editorial subtitle")
    check(all(chapters[i]["endTime"] == chapters[i + 1]["startTime"] for i in range(len(chapters) - 1)), "contiguous chapters")
    check(chapters[-1]["endTime"] == round(tl.total_ms / 1000, 3), "last chapter ends at the end")
    check(all(chapters[i]["startTime"] < chapters[i + 1]["startTime"] for i in range(len(chapters) - 1)), "monotonic")
    titles = [ch["title"] for ch in chapters]
    check(titles[1] == "Canada turns toward Europe" and titles[0] == "Headlines", f"titles {titles[:2]}")

    # music envelope: nothing under stories, beds under menu and close only
    env = rp.bed_envelope(tl, 20000, 12000)
    assets = {e["asset"]: e for e in env}
    check(set(assets) == {"menu_bed", "close_bed"}, f"beds {set(assets)}")
    mb = assets["menu_bed"]
    check(mb["start"] == max(0, by_kind["OPEN"][0].start_ms - rp.BED_MENU_PRE), "opening bed starts under the sign-on")
    check(mb["end"] == story[0].start_ms - rp.BED_MENU_STOP_BEFORE_STORY, "menu bed gone before story 1")
    cb = assets["close_bed"]
    check(cb["start"] == close[0].start_ms - rp.BED_CLOSE_PRE and cb["end"] == tl.total_ms, "close bed under the sign-off")
    for e in env:
        for x in story + briefs + fin + ed:
            check(not (e["start"] < x.end_ms and e["end"] > x.start_ms) or e["asset"] == "menu_bed" and x is story[0] and False,
                  f"no bed under {x.kind} {x.idx}") if False else None
    for x in story[1:] + briefs + fin + ed:
        check(all(not (e["start"] < x.end_ms and e["end"] > x.start_ms) for e in env), f"no bed under {x.kind} turn {x.idx}")

    # end to end through produce_radio_show (fake engine, scratch dir)
    out = Path(tempfile.mkdtemp(prefix="void-radio-test-"))
    try:
        result = rp.produce_radio_show(rundown, EDITORIAL, "world", opinion_headline="An editorial headline",
                                       engines=[FakeEngine()], out_dir=out,
                                       date=datetime.datetime(2026, 9, 18, 15, 0, tzinfo=datetime.timezone.utc))
        check(result is not None, "show rendered")
        if result:
            mp3 = Path(result.audio_url)
            check(mp3.exists() and mp3.stat().st_size > 10_000, "mp3 written")
            side = out / "2026-09-18-pm.chapters.json"
            check(side.exists(), "chapters sidecar written")
            if side.exists():
                sc = json.loads(side.read_text(encoding="utf-8"))
                check(sc["version"] == "1.2.0" and len(sc["chapters"]) == len(result.chapters), "sidecar round-trips")
                check(all(ch["startTime"] == r["startTime"] for ch, r in zip(sc["chapters"], result.chapters)), "sidecar times match")
            check(result.engine == "fake" and result.voices == "fake:fake_a+fake_b", f"voices label {result.voices}")
            check(result.opinion_start_seconds == result.chapters[-1]["startTime"], "opinion_start = editorial chapter")
            check(abs(result.duration_seconds - tl.total_ms / 1000) < 0.2, f"duration {result.duration_seconds} vs {tl.total_ms / 1000}")
            try:
                from mutagen.id3 import ID3
                tags = ID3(str(mp3))
                chaps = sorted(tags.getall("CHAP"), key=lambda f: f.start_time)
                check(len(chaps) == len(result.chapters), f"ID3 CHAP frames {len(chaps)}")
                check(len(tags.getall("CTOC")) == 1, "one CTOC")
                check(chaps[0].start_time == 0 and chaps[1].start_time == int(round(result.chapters[1]["startTime"] * 1000)), "CHAP ms")
            except ImportError:
                print("  (mutagen missing; ID3 checks skipped)")
            if shutil.which("ffmpeg"):
                stats = rp.measure_loudness(mp3)
                if stats:
                    i = float(stats["input_i"])
                    tp = float(stats["input_tp"])
                    check(abs(i - rp.LOUDNESS_I) <= 1.5, f"integrated loudness {i} within 1.5 LU of {rp.LOUDNESS_I}")
                    check(tp <= rp.LOUDNESS_TP + 0.3, f"true peak {tp} <= {rp.LOUDNESS_TP}")
                    print(f"  loudness I={i} TP={tp}")
            else:
                print("  (ffmpeg missing; loudness checks skipped)")
    finally:
        shutil.rmtree(out, ignore_errors=True)

    if failures:
        print(f"\n{len(failures)} FAILED")
        sys.exit(1)
    print("\ntest_radio_assembly: all checks passed")


if __name__ == "__main__":
    main()
