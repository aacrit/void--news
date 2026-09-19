"""Radio show assembly with a fake engine: timeline, chapters, music placement,
ID3 + sidecar chapters, and (when ffmpeg is present) loudness.

    python tests/test_radio_assembly.py

No TTS, no network. Each turn becomes a tone burst whose length is derived
from its word count, so the test knows every cue position in advance.
"""

from __future__ import annotations

import datetime
import re
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from pydub import AudioSegment  # noqa: E402
from pydub.generators import Sine  # noqa: E402

from briefing.radio_script_generator import parse_rundown  # noqa: E402
from briefing.tts_engines import TurnSpec, EngineResult  # noqa: E402
from briefing import radio_producer as rp  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "radio_rundown_2026-09-18.txt"
EDITORIAL = ("Now, void opinion.\nThrough a pragmatic lens today.\nA headline for the opinion.\n\n"
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
        return {"A": "fake_a", "B": "fake_b", "C": "fake_c"}[role]

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
    # Bind STORY/FINALLY ids from the feed the way the pipeline does (validator).
    from briefing.radio_script_generator import validate_rundown, RundownContext
    feed_path = ROOT / "frontend" / "build-data" / "feed.json"
    rows = json.loads(feed_path.read_text(encoding="utf-8"))["clusters"][:20]
    if rows[0]["id"] != "d3afa900-ea54-4eb8-b95e-f6ed157317a3":
        rows = [{"id": "d3afa900-ea54-4eb8-b95e-f6ed157317a3", "title": "Canada"}] + [
            {"id": f"00000000-0000-0000-0000-0000000000{n:02d}", "title": f"story {n}"} for n in range(2, 21)]
    validate_rundown(rundown, RundownContext(top20=rows, has_editorial=True, date_spoken="Friday, September eighteenth"))
    turns = rp.build_turns(rundown, EDITORIAL)
    kinds = [m["kind"] for _, m in turns]
    check(kinds[0] == "OPEN" and kinds[-1] == "CLOSE", "OPEN first, CLOSE last")
    check("THROW" not in kinds, "no spoken throw: the entrance music announces the opinion")
    check(kinds.index("OPINION") > kinds.index("FINALLY"), "opinion after the kicker")
    check(all(s.role == "C" for s, m in turns if m["kind"] == "OPINION"), "opinion is its own voice C")
    check(not any(s.role == "C" for s, m in turns if m["kind"] != "OPINION"), "voice C reads nothing but the opinion")
    verdicts = [m for _, m in turns if m["kind"] == "OPINION" and m.get("verdict")]
    check(len(verdicts) == 1, f"one one-sentence verdict paragraph detected ({len(verdicts)})")
    check(not any(ch.isdigit() for s, _ in turns for ch in s.text), "no digits reach the engine")
    check(any("ko-haht" in s.text for s, _ in turns), "SAY respelling applied before synthesis")
    check(not any(re.search(r"[A-Z]{2,}", s.text) for s, _ in turns if "U-" not in s.text and "E-" not in s.text and "C-" not in s.text and "J-" not in s.text),
          "no all-caps runs reach the engine except spelled initialisms")
    check(any("U-S President" in s.text for s, _ in turns), "initialisms hyphenated")

    # timeline against the gap table
    eng = FakeEngine()
    res = eng.synthesize_batch([s for s, _ in turns])
    L = rp.CueLengths(opener_ms=8000, opener_is_theme=True, transition_ms=2900,
                      break_ms=9000, opinion_theme_ms=6500, outro_ms=14000)
    tl = rp.build_timeline(turns, res.audio, L)
    G = rp.RADIO_GAPS
    c = tl.cues
    check(c[0].start_ms == 8000 - G["theme_overlap"], "sign-on starts inside the THEME's release")
    by_kind = {}
    for cue in c:
        by_kind.setdefault(cue.kind, []).append(cue)
    menu = by_kind["MENU"]
    check(menu[0].start_ms - by_kind["OPEN"][-1].end_ms == G["open_to_menu"], "OPEN -> MENU gap")
    check(menu[1].start_ms - menu[0].end_ms == G["menu_item"], "menu item gap")
    story = by_kind["STORY"]
    check(story[0].start_ms - menu[-1].end_ms == G["menu_to_story"], "MENU -> STORY gap")
    check(tl.news_start_ms == story[0].start_ms, "news_start = STORY 1 start")
    s1 = [x for x in story if x.segment_idx == story[0].segment_idx]
    check(s1[1].start_ms - s1[0].end_ms == G["same_speaker"], "same-speaker beat")
    check(s1[-1].start_ms - s1[-2].end_ms == G["speaker_change"], "speaker-change beat")

    # Seams: a transition (or, once, the break) plays IN THE CLEAR.
    segs = []
    for x in story:
        if x.segment_idx not in segs:
            segs.append(x.segment_idx)
    per_seg = {i: [x for x in story if x.segment_idx == i] for i in segs}
    s2 = per_seg[segs[1]]
    check(s2[0].start_ms - s1[-1].end_ms == G["transition_lead"] + 2900 + G["transition_settle"],
          "story -> story seam reserves the transition")
    s3 = per_seg[segs[2]]
    check(tl.break_at_ms == s2[-1].end_ms + G["break_lead"], "the break lands after deep story 2")
    check(s3[0].start_ms == tl.break_at_ms + 9000 + G["break_settle"], "story 3 waits for the break")
    check(len(tl.transition_at_ms) == 3, f"three transitions, the break takes the other seam ({len(tl.transition_at_ms)})")
    check(tl.break_at_ms not in tl.transition_at_ms, "the break replaces the transition, never both")
    turns_all = [x for x in c if x.kind in rp.SPOKEN_KINDS]
    for at in tl.transition_at_ms:
        check(not any(x.start_ms < at + 2900 and x.end_ms > at for x in turns_all),
              f"transition at {at}ms plays in the clear")
    check(not any(x.start_ms < tl.break_at_ms + 9000 and x.end_ms > tl.break_at_ms for x in turns_all),
          "the break plays in the clear")
    briefs = by_kind["BRIEFS"]
    check(briefs[1].start_ms - briefs[0].end_ms == G["briefs_item"], "briefs item gap")
    fin = by_kind["FINALLY"]
    check(fin[0].start_ms - briefs[-1].end_ms == G["briefs_to_finally"], "BRIEFS -> FINALLY gap")

    # The opinion entrance IS the throw.
    ed = by_kind["OPINION"]
    check(tl.opinion_theme_at_ms == fin[-1].end_ms + G["to_opinion"], "opinion entrance follows the kicker")
    check(ed[0].start_ms == tl.opinion_theme_at_ms + 6500 - G["opinion_overlap"],
          "first opinion sentence starts over the entrance's tail")
    check(tl.opinion_start_ms == tl.opinion_theme_at_ms, "the Opinion chapter begins at its music")
    vi = next(i for i, x in enumerate(ed) if x.verdict)
    check(ed[vi].start_ms - ed[vi - 1].end_ms == G["opinion_verdict"], "beat before the verdict")
    check(ed[vi + 1].start_ms - ed[vi].end_ms == G["opinion_verdict"], "beat after the verdict")
    check(ed[1].start_ms - ed[0].end_ms == G["opinion_paragraph"], "paragraph beat")
    close = by_kind["CLOSE"]
    check(close[0].start_ms - ed[-1].end_ms == G["opinion_to_close"], "OPINION -> CLOSE gap")
    check(tl.outro_at_ms == close[-1].end_ms - G["outro_overlap"], "outro under the sign-off")
    check(tl.total_ms == tl.outro_at_ms + 14000 + G["tail"], "the file ends after the outro's fall")

    # The legacy opener and the sparse style both still lay out.
    tl_id = rp.build_timeline(turns, res.audio, rp.CueLengths(opener_ms=2400, outro_ms=2000))
    check(tl_id.cues[0].start_ms == 2400 - G["ident_overlap"], "ident opener uses its own overlap")
    check(tl_id.transition_at_ms == [] and tl_id.break_at_ms is None, "no cues reserved when absent")
    st = [x for x in tl_id.cues if x.kind == "STORY"]
    s1b = [x for x in st if x.segment_idx == st[0].segment_idx]
    s2b = next(x for x in st if x.segment_idx != st[0].segment_idx)
    check(s2b.start_ms - s1b[-1].end_ms == G["story_to_story"], "bare seam falls back to story_to_story")

    # chapters derive from the cues
    chapters = rp.chapters_from_timeline(tl, "An editorial headline", {"d3afa900-ea54-4eb8-b95e-f6ed157317a3": "https://x/story/1/"})
    kinds_c = [ch["kind"] for ch in chapters]
    check(kinds_c == ["headlines", "story", "story", "story", "story", "briefs", "finally", "opinion"], f"chapter kinds {kinds_c}")
    check(chapters[0]["startTime"] == 0.0, "first chapter at 0")
    check(abs(chapters[1]["startTime"] - story[0].start_ms / 1000) < 0.001, "story 1 chapter == cue start")
    check(abs(chapters[-1]["startTime"] - tl.opinion_theme_at_ms / 1000) < 0.001,
          "the Opinion chapter starts at its entrance music")
    check(chapters[-1]["title"] == "Opinion", f"chapter title {chapters[-1]['title']!r}")
    check(chapters[1]["url"] == "https://x/story/1/" and chapters[1]["rank"] == 1, "permalink + rank on story chapters")
    check(chapters[-1]["subtitle"] == "An editorial headline", "editorial subtitle")
    check(all(chapters[i]["endTime"] == chapters[i + 1]["startTime"] for i in range(len(chapters) - 1)), "contiguous chapters")
    check(chapters[-1]["endTime"] == round(tl.total_ms / 1000, 3), "last chapter ends at the end")
    check(all(chapters[i]["startTime"] < chapters[i + 1]["startTime"] for i in range(len(chapters) - 1)), "monotonic")
    titles = [ch["title"] for ch in chapters]
    check(titles[1] == "Canada turns toward Europe" and titles[0] == "Headlines", f"titles {titles[:2]}")

    # ── music envelope, both styles ────────────────────────────────────────
    # The bookends are identical in either style; what changes is whether a
    # bed runs under the spoken body.
    prev_style = rp.MUSIC_STYLE
    try:
        rp.MUSIC_STYLE = "sparse"
        env = rp.bed_envelope(tl, 20000, 12000)
        assets = {e["asset"]: e for e in env}
        check(set(assets) == {"menu_bed", "close_bed"}, f"sparse beds {set(assets)}")
        mb = assets["menu_bed"]
        check(mb["start"] == max(0, by_kind["OPEN"][0].start_ms - rp.BED_MENU_PRE), "opening bed starts under the sign-on")
        check(mb["end"] == story[0].start_ms - rp.BED_MENU_STOP_BEFORE_STORY, "menu bed gone before story 1")
        cb = assets["close_bed"]
        check(cb["start"] == close[0].start_ms - rp.BED_CLOSE_PRE, "close bed starts under the sign-off")
        check(cb.get("loop") is False, "the close bed is a one-shot, never looped")
        check(cb["end"] - cb["start"] <= 24000, "close bed is clamped to its own length")
        check(cb["end"] <= tl.outro_at_ms + rp.BED_CLOSE_HANDOVER, "close bed hands over to the outro")
        for x in story[1:] + briefs + fin + ed:
            check(all(not (e["start"] < x.end_ms and e["end"] > x.start_ms) for e in env),
                  f"sparse: no bed under {x.kind} turn {x.idx}")

        rp.MUSIC_STYLE = "daily"
        env = rp.bed_envelope(tl, 20000, 12000)
        assets = {e["asset"]: e for e in env}
        check(set(assets) == {"menu_bed", "story_bed", "opinion_bed", "close_bed"}, f"daily beds {set(assets)}")
        story_cues = [e for e in env if e["asset"] == "story_bed"]
        ed_cues = [e for e in env if e["asset"] == "opinion_bed"]
        check(all(e.get("duck") for e in story_cues + ed_cues), "beds under speech are ducked")
        # ARCS, not one continuous bed: music enters per segment and leaves.
        check(len(story_cues) >= 2, f"one music arc per news segment, got {len(story_cues)}")
        news_end = (fin or briefs)[-1].end_ms
        covered = sum(min(e["end"], news_end) - max(e["start"], story[0].start_ms)
                      for e in story_cues if e["end"] > story[0].start_ms)
        span = news_end - story[0].start_ms
        check(0.15 < covered / span < 0.60,
              f"music covers {covered / span:.0%} of the news block: scored, not wallpaper")
        check(all(e["end"] < ed[0].start_ms for e in story_cues), "news music is gone before the opinion")
        check(ed_cues and ed_cues[0]["start"] <= ed[0].start_ms, "editorial music enters at the throw")

        # THE point of the design: every fade-out completes UNDER a sentence,
        # never in a gap, which is what makes music feel woven into the read.
        turns = [c for c in tl.cues if c.kind in rp.SPOKEN_KINDS]
        for e in story_cues + ed_cues:
            if e.get("handoff"):
                # Hands over to the close bed, so it must outlast the last word.
                check(e["end"] > ed[-1].end_ms, f"{e.get('tag')} carries past the opinion")
                continue
            inside = any(c.start_ms <= e["end"] < c.end_ms for c in turns)
            check(inside, f"{e.get('tag')} fade-out at {e['end']}ms lands under a sentence")
        # and weave_end is idempotent: snapping an already-woven point moves nothing
        for e in story_cues:
            check(rp.weave_end(tl, e["end"], rp.STORY_MUSIC_FADE_OUT) == e["end"],
                  f"{e.get('tag')} weave point is stable")
        # transitions land in gaps, never on top of a turn
        for at in rp.transition_points(tl):
            inside = [c for c in tl.cues if c.start_ms <= at < c.end_ms]
            check(not inside, f"transition at {at}ms lands in a gap, not over turn {inside}")

        # the duck curve: full level in a gap, DUCK_DB under a voice
        duck = rp.duck_envelope(tl)
        floor = 10 ** (rp.DUCK_DB / 20.0)
        mid = (story[0].start_ms + story[0].end_ms) // 2
        check(abs(duck[mid // rp.DUCK_STEP_MS] - floor) < 1e-6, "music is at the duck floor mid-sentence")
        gap = story[0].end_ms + rp.DUCK_RELEASE_MS + 50
        if gap < tl.total_ms and not any(c.start_ms <= gap < c.end_ms for c in tl.cues):
            check(duck[gap // rp.DUCK_STEP_MS] > floor, "music recovers in the gap after a turn")
        pre = max(0, story[0].start_ms - 20)
        check(duck[pre // rp.DUCK_STEP_MS] < 1.0, "duck is already falling before the voice arrives")
    finally:
        rp.MUSIC_STYLE = prev_style

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
            check(result.engine == "fake" and result.voices == "fake:fake_a+fake_b+fake_c", f"voices label {result.voices}")
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
