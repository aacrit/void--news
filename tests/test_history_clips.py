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


# ---------------------------------------------------------------------------
# Fixtures: a throwaway copy of the pilot's evidence, one thing changed
# ---------------------------------------------------------------------------

import shutil  # noqa: E402
import tempfile  # noqa: E402

from history import clips as cl  # noqa: E402
from history import mood as md  # noqa: E402
from pipeline.history.ledger import load_ledger  # noqa: E402

NEHRU = "clip-nehru-tryst-19470814"
CREDIT_OLD = "N: Then, in English. Nehru, to the assembly.\n"
CREDIT_NEW = "N: Then, in English. Nehru, to the assembly, in the All India Radio recording.\n"
# What faster-whisper base.en heard, recorded by verify_clip on 2026-09-25
# (tests hold TEXT only; no audio is committed and CI runs no ASR).
HEARD_WINDOW = ("Long years ago, we made a twist with destiny, and now the time comes when we shall "
                "redeem our pledge, not only or in full measure, but very substantially. At the stroke "
                "of the midnight hour, when the world sleeps, India will awake to life and freedom.")
# The same speaker, the same recording, a different passage (60-93 s).
HEARD_OTHER_PASSAGE = ("her people, and to the still larger cause of humanity. At the dawn of history, India "
                       "started on her unending quest, and trackless centuries are filled with her striving, "
                       "and the grandeur of her successors and her failures. Through good and unfortunate "
                       "life, she has never lost sight of that quest, or forgotten the ideals which bring "
                       "her strength. We'll be right back.")
# The right passage with the out point run on into the next sentence (0-41 s).
HEARD_OVERRUN = HEARD_WINDOW + (" A movement comes, which comes but rarely in history, when we step out "
                                "from the You")
# The out point cut short, inside the second sentence (0-20 s).
HEARD_SHORT = ("Long years ago, we made a twist with destiny, and now the time comes when we shall redeem "
               "our pledge, not only or in full measure, but very substantially. At the stroke of")

assert CREDIT_OLD in RAW, "the pilot's credit line moved; update the fixture"


def fixture(mutate_rec=None, mutate_ver=None, script_edit=None, signed: bool = True):
    tmp = Path(tempfile.mkdtemp(prefix="void-clipfx-"))
    shutil.copytree(ROOT / "data/history/evidence" / SLUG, tmp / SLUG)
    led = tmp / SLUG / "ledger.yaml"
    raw = yaml.safe_load(led.read_text(encoding="utf-8"))
    rec = next(r for r in raw["recordings"] if r["id"] == NEHRU)
    if signed:
        rec["signed_by"], rec["signed_at"] = "TEST FIXTURE", "2026-09-25"
    if mutate_rec:
        mutate_rec(rec)
    led.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8")
    vp = tmp / SLUG / "recordings" / f"{NEHRU}.verification.json"
    if mutate_ver and vp.exists():
        ver = json.loads(vp.read_text(encoding="utf-8"))
        mutate_ver(ver)
        vp.write_text(json.dumps(ver), encoding="utf-8")
    text = RAW.replace(CREDIT_OLD, CREDIT_NEW)
    if script_edit:
        text = script_edit(text)
    sc = parse_script(text, SLUG)
    ledger = load_ledger(SLUG, evidence_dir=tmp)
    slots, findings = cl.evaluate(sc, ledger, SLUG, evidence=tmp)
    nehru = next((s for s in slots if s.clip_id == NEHRU), None)
    shutil.rmtree(tmp, ignore_errors=True)
    return sc, slots, findings, nehru


def _ids(findings, clip=NEHRU):
    return {f.id for f in findings if clip in f.segment or f.segment in ("TOTAL", "OPEN")}


# ---------------------------------------------------------------------------
# 2. The committed pilot, and the clean fixture
# ---------------------------------------------------------------------------

def test_pilot_as_committed() -> None:
    sc = parse_script(RAW, SLUG)
    ledger = load_ledger(SLUG)
    slots, findings = cl.evaluate(sc, ledger, SLUG)
    check("pilot: no clip gate FAILS on the committed script", not [f for f in findings if f.level == "fail"],
          str([(f.id, f.detail) for f in findings if f.level == "fail"]))
    check("pilot: nothing is admitted while unsigned", not any(s.admitted for s in slots))
    nehru = next(s for s in slots if s.clip_id == NEHRU)
    got = {f.id for f in nehru.findings}
    # Unsigned, and the script says "to the assembly" until it is signed
    # (§4b): those two, and nothing about provenance or the words.
    check("pilot: Nehru is blocked only by the signature and the credit", got == {"H-12", "H-15"}, str(got))
    check("pilot: Nehru is not signed in the committed ledger",
          not cl.is_signed(ledger.recordings[NEHRU]))
    ver = cl.load_verification(SLUG, ledger.recordings[NEHRU])
    check("pilot: the Nehru verification record passed", bool(ver and ver.get("pass")))
    check("pilot: the Nehru window is 45 s or less", ver and ver["window"]["seconds"] <= 45.0)
    mb = next(s for s in slots if "mountbatten" in s.clip_id)
    check("pilot: Mountbatten is blocked on rights and provenance",
          {"H-12", "H-13"} <= {f.id for f in mb.findings} and not mb.admitted)


def test_clean_fixture_admits() -> None:
    sc, slots, findings, nehru = fixture()
    check("clean: the signed, verified, credited Nehru clip is admitted", nehru.admitted,
          str([(f.id, f.detail) for f in nehru.findings]))
    check("clean: no finding on it", not nehru.findings, str([(f.id, f.detail) for f in nehru.findings]))


# ---------------------------------------------------------------------------
# 3. H-12 .. H-16, each against one planted defect
# ---------------------------------------------------------------------------

def test_h12_rights() -> None:
    _, _, f, n = fixture(signed=False)
    check("H-12 fires on an unsigned row", "H-12" in {x.id for x in n.findings} and not n.admitted)
    check("H-12 warns, not fails, while unsigned", all(x.level == "warn" for x in n.findings))
    _, _, f, n = fixture(mutate_rec=lambda r: r.update(rights_basis="fair-use-excerpt"))
    check("H-12 fires on a basis outside policy B", "H-12" in {x.id for x in n.findings} and not n.admitted)
    check("H-12 FAILS once the row is signed", any(x.id == "H-12" and x.level == "fail" for x in n.findings))
    _, _, f, n = fixture(mutate_rec=lambda r: r.update(licence_as_stated=None))
    check("H-12 fires when the licence is not recorded as stated", "H-12" in {x.id for x in n.findings})
    _, _, f, n = fixture(mutate_rec=lambda r: r.update(signed_at=None))
    check("H-12 fires on a signature with no date", "H-12" in {x.id for x in n.findings} and not n.admitted)


def test_h13_provenance() -> None:
    for k in ("occasion", "date", "speaker", "repository", "accession", "origin_as_stated", "file_md5"):
        _, _, f, n = fixture(mutate_rec=lambda r, k=k: r.update({k: None}))
        check(f"H-13 fires without {k}", "H-13" in {x.id for x in n.findings} and not n.admitted,
              str([x.id for x in n.findings]))


def test_h14_transcript() -> None:
    from pipeline.history import verify_clip as vc
    _, _, f, n = fixture(mutate_ver=lambda v: v.update(**{"pass": False, "coverage": 0.085}))
    check("H-14 fires on a failed verification (the other passage)", "H-14" in {x.id for x in n.findings}
          and not n.admitted)
    _, _, f, n = fixture(mutate_rec=lambda r: r.update(
        transcript=r["transcript"].replace("Long years ago", "Many years ago")))
    check("H-14 fires on a transcript that is not verbatim from its extract",
          any(x.id == "H-14" and "verbatim" in x.detail for x in n.findings))
    _, _, f, n = fixture(mutate_rec=lambda r: r.update(excerpt={"in": "00:00:00.000", "out": "00:00:30.000"}))
    check("H-14 fires when the record checked a different window",
          any(x.id == "H-14" and "window" in x.detail for x in n.findings))
    _, _, f, n = fixture(mutate_ver=lambda v: v["source"].update(md5="0" * 32))
    check("H-14 fires when the record checked a different file",
          any(x.id == "H-14" and "file" in x.detail for x in n.findings))
    _, _, f, n = fixture(mutate_rec=lambda r: r.update(verification="recordings/none.json"))
    check("H-14 fires with no verification record", any(x.id == "H-14" for x in n.findings) and not n.admitted)
    # The alignment itself, on what the ASR actually heard.
    ref = load_ledger(SLUG).recordings[NEHRU]["transcript"]
    ok, why = vc.verdict(vc.align(ref, HEARD_WINDOW))
    check("align: the verified window passes", ok, str(why))
    al = vc.align(ref, HEARD_OTHER_PASSAGE)
    ok, why = vc.verdict(al)
    check("align: the same speaker in a different passage FAILS", not ok and al["coverage"] < cl.COVERAGE_MIN,
          f"coverage {al['coverage']}")
    ok, why = vc.verdict(vc.align(ref, HEARD_OVERRUN))
    check("align: an out point that runs into the next sentence FAILS", not ok and any("after" in w for w in why),
          str(why))
    ok, why = vc.verdict(vc.align(ref, HEARD_SHORT))
    check("align: an out point cut short FAILS", not ok, str(why))
    al = vc.align("a b c d", "a x c d e")
    check("align: WER counts S, D and I", (al["substitutions"], al["deletions"], al["insertions"]) == (1, 0, 1)
          and abs(al["wer"] - 0.5) < 1e-9, str(al))


def test_h15_credit() -> None:
    _, _, f, n = fixture(script_edit=lambda t: t.replace(CREDIT_NEW, CREDIT_OLD))
    check("H-15 fires when the credit does not say recording", "H-15" in {x.id for x in n.findings}
          and not n.admitted)
    check("H-15 FAILS once the row is signed", any(x.id == "H-15" and x.level == "fail" for x in n.findings))
    _, _, f, n = fixture(script_edit=lambda t: t.replace(
        CREDIT_NEW, "N: Then, in English. Prasad, in the All India Radio recording.\n"))
    check("H-15 fires when the credit names someone else", "H-15" in {x.id for x in n.findings})
    ok_line = "N: Then, in English. Nehru, to the assembly, in the All India Radio broadcast.\n"
    _, _, f, n = fixture(script_edit=lambda t: t.replace(CREDIT_NEW, ok_line))
    check("H-15 accepts broadcast", "H-15" not in {x.id for x in n.findings})


def test_h16_caps() -> None:
    clip_line = f"# CLIP: id={NEHRU} replaces=none status=verified max=45s\n"
    _, slots, f, n = fixture(script_edit=lambda t: t.replace("## OPEN\n# MOOD: dread\n",
                                                             "## OPEN\n# MOOD: dread\n" + clip_line, 1))
    check("H-16 fires on a clip in the OPEN", any(x.id == "H-16" and "OPEN" in x.detail for x in f))
    check("H-16 stops every clip", not any(s.admitted for s in slots))
    third = "# CLIP: id=clip-extra replaces=none status=candidate max=30s\n"
    _, slots, f, n = fixture(script_edit=lambda t: t.replace("## SCENE 4 | How many\n",
                                                             "## SCENE 4 | How many\n" + third, 1))
    check("H-16 fires on a third clip", any(x.id == "H-16" and "at most" in x.detail for x in f))
    _, slots, f, n = fixture(script_edit=lambda t: t.replace(
        f"id={NEHRU} replaces=document status=candidate", f"id={NEHRU} replaces=document status=candidate").replace(
        "max=45s", "max=60s", 1))
    check("H-16 fires on a declared max over 45 s", any(x.id == "H-16" and "max=60s" in x.detail for x in f))

    def long_window(r):
        r["excerpt"] = {"in": "00:00:00.000", "out": "00:00:50.000"}
    _, slots, f, n = fixture(mutate_rec=long_window,
                             mutate_ver=lambda v: v["window"].update({"in": 0.0, "out": 50.0}))
    check("H-16 fires on an excerpt over 45 s", any(x.id == "H-16" and "50.0s" in x.detail for x in f))
    check("H-16 is structural: it fails", all(x.level == "fail" for x in f if x.id == "H-16"))


# ---------------------------------------------------------------------------
# 4. H-17, both halves, on a synthetic timeline (no Kokoro, no ffmpeg)
# ---------------------------------------------------------------------------

_SCORE: dict = {}


def _score():
    from history import history_producer as hp
    if not _SCORE:
        _SCORE.update(hp.history_score("contemporary"))
    return _SCORE


def synth_timeline(with_clip: bool = True):
    from pydub import AudioSegment
    from history import history_producer as hp
    sc = parse_script(RAW.replace(CREDIT_OLD, CREDIT_NEW), SLUG)
    sub = hp.subset(sc, ["OPEN", "SCENE 2", "SCENE 3"])
    moods, dry = md.segment_moods(sub), md.dry_segments(sub)
    admitted = {}
    if with_clip:
        si = next(i for i, s in enumerate(sub.segments) if s.directive("CLIP")
                  and NEHRU in s.directive("CLIP").value)
        admitted[si] = cl.ClipSlot(seg_idx=si, clip_id=NEHRU, replaces="document", rec={"title": "clip"})
    turns = hp.build_turns(sub, moods, admitted)
    audio = {s.idx: AudioSegment.silent(duration=28050 if m.get("clip") else 3000 + 200 * (s.idx % 7),
                                        frame_rate=24000) for s, m in turns}
    score = _score()

    def tr(meta):
        seg = score.get(f"transition:{meta.get('mood')}")
        return (0, "") if seg is None or dry[meta["seg_idx"]] else (len(seg), f"transition:{meta.get('mood')}")
    tl = hp.build_timeline(turns, audio, opener_ms=len(score["theme"]), transition_ms=tr,
                           outro_ms=len(score["outro"]), rests={}, break_ms=0)
    return sub, tl, dry, turns


def test_h17_timeline() -> None:
    from history import history_producer as hp
    sub, tl, dry, _ = synth_timeline()
    clips_ = [cl.Span("clip", c.start_ms, c.end_ms, c.clip_id) for c in tl.cues if c.clip_id]
    check("H-17 fixture: one clip on the timeline", len(clips_) == 1)
    plan = hp.mood_plan(tl, dry)
    check("H-17 timeline: the producer's own plan is clean", not cl.timeline_findings(clips_, plan),
          str([f.detail for f in cl.timeline_findings(clips_, plan)]))
    c = clips_[0]
    planted = [cl.Span("ambience", c.end_ms + 2000, c.end_ms + 9000, "wind")]
    check("H-17 timeline: ambience 2 s after a clip FAILS", bool(cl.timeline_findings(clips_, planted)))
    planted = [cl.Span("ambience", c.end_ms + 3100, c.end_ms + 9000, "wind")]
    check("H-17 timeline: ambience 3.1 s after a clip passes", not cl.timeline_findings(clips_, planted))
    planted = [cl.Span("bed", c.start_ms - 5000, c.start_ms + 1000, "dread")]
    check("H-17 timeline: a bed into a clip FAILS", bool(cl.timeline_findings(clips_, planted)))
    planted = [cl.Span("room", 0, tl.total_ms, "room")]
    check("H-17 timeline: room tone across a clip FAILS", bool(cl.timeline_findings(clips_, planted)))
    planted = [cl.Span("sting", c.end_ms + 100, c.end_ms + 600, "sting:from_clip")]
    check("H-17 timeline: a sting inside the trailing silence FAILS", bool(cl.timeline_findings(clips_, planted)))


def test_h17_bus() -> None:
    import numpy as np
    from pydub import AudioSegment
    from briefing import radio_producer as rp
    from history import history_producer as hp
    sub, tl, dry, _ = synth_timeline()
    clips_ = [cl.Span("clip", c.start_ms, c.end_ms, c.clip_id) for c in tl.cues if c.clip_id]
    plan = hp.mood_plan(tl, dry)
    bus, used = hp.mood_music_bus(tl, _score(), plan, room=rp._asset("room"))
    check("H-17 bus: the rendered music bus is silent under the clip", not cl.bus_findings(clips_, {"music": bus}),
          str([f.detail for f in cl.bus_findings(clips_, {"music": bus})]))
    c = clips_[0]
    r = cl.rms_dbfs(bus, c.start_ms - 400, c.end_ms + 400)
    check("H-17 bus: RMS under the clip is under -60 dBFS", r < -60.0, f"{r:.1f}")
    check("H-17 bus: the music bus is NOT silent elsewhere (the check can see sound)",
          cl.rms_dbfs(bus, 0, 8000) > -45.0, f"{cl.rms_dbfs(bus, 0, 8000):.1f}")
    # Planted: one second of pink noise on the ambience bus under the clip.
    n = 24000
    rng = np.random.default_rng(7)
    spec = np.fft.rfft(rng.standard_normal(n))
    f = np.maximum(np.fft.rfftfreq(n, 1 / 24000), 1.0)
    pink = np.fft.irfft(spec / np.sqrt(f), n)
    pink = (pink / np.max(np.abs(pink)) * 0.05 * 32767).astype(np.int16)
    noise = AudioSegment(pink.tobytes(), frame_rate=24000, sample_width=2, channels=1).set_channels(2)
    amb = rp._silent(tl.total_ms, channels=2).overlay(noise, position=c.start_ms + 5000)
    check("H-17 bus: 1 s of pink noise under a clip FAILS", bool(cl.bus_findings(clips_, {"ambience": amb})))
    # Planted: a bed laid across the clip after the mask (a regression in the mute).
    bed = rp._loop_to(_score()["bed:dread"].apply_gain(rp.BED_STORY_GAIN_DB), c.end_ms - c.start_ms)
    leaked = bus.overlay(bed.set_channels(2), position=c.start_ms)
    check("H-17 bus: a bed under a clip FAILS", bool(cl.bus_findings(clips_, {"music": leaked})))
    # The legacy (no-mood) bus mutes a clip too, so a clip is dry in both modes.
    assets = {k: rp._asset(k) for k in ("theme", "transition", "break", "story_bed", "outro", "room")}
    lbus, _ = hp.music_bus(tl, assets)
    check("H-17 bus: the legacy bus is silent under a clip too", not cl.bus_findings(clips_, {"music": lbus}))


# ---------------------------------------------------------------------------
# 5. Moods, the score, and the legacy path
# ---------------------------------------------------------------------------

def test_moods() -> None:
    from history import history_producer as hp
    check("moods: six, as specified", set(md.MOODS) == {"dread", "procedure", "rupture", "grief",
                                                        "testimony", "reckoning"})
    check("moods: no speed under 0.88", all(m.narrator_speed >= 0.88 and m.document_speed >= 0.88
                                              for m in md.MOODS.values()))
    check("moods: testimony and rupture are dry", md.MOODS["testimony"].dry and md.MOODS["rupture"].dry)
    check("moods: duck depths as specified", (md.MOODS["reckoning"].duck_db, md.MOODS["procedure"].duck_db,
                                              md.MOODS["dread"].duck_db, md.MOODS["grief"].duck_db)
          == (-18.0, -14.0, -10.0, -10.0))
    check("moods: REST in grief 4.5 s, in reckoning 2.0 s",
          (md.MOODS["grief"].rest_ms, md.MOODS["reckoning"].rest_ms) == (4500, 2000))
    check("moods: testimony's gap before a document read is 1.4 s", md.MOODS["testimony"].to_document_ms == 1400)
    sc = parse_script(RAW, SLUG)
    moods = md.segment_moods(sc)
    title_i = next(i for i, s in enumerate(sc.segments) if s.kind == "TITLE")
    check("moods: a segment with no mood inherits the previous one", moods[title_i] == "dread")
    turns = hp.build_turns(sc, moods)
    speeds = {(m["mood"], s.role): s.speed for s, m in turns}
    check("moods: dread narrator at 0.92", speeds.get(("dread", "A")) == 0.92)
    check("moods: testimony document voice at 0.93", speeds.get(("testimony", "C")) == 0.93)
    sub, tl, dry, _ = synth_timeline(with_clip=False)
    plan = hp.mood_plan(tl, dry)
    rupture_cues = [c for c in tl.cues if c.mood == "rupture"]
    beds = [p for p in plan if p.kind == "bed"]
    check("moods: no bed under a rupture word", not any(
        b.start_ms < c.end_ms and b.end_ms > c.start_ms for b in beds for c in rupture_cues),
        str([(b.start_ms, b.end_ms, b.label) for b in beds]))
    entry = [p for p in plan if p.label == "rupture_entry"]
    read = [c for c in rupture_cues if c.speaker in ("B", "C")]
    check("moods: the rupture entry lands on the last word of the read",
          len(entry) == 1 and read and abs(entry[0].start_ms - (read[-1].end_ms - 600)) < 2,
          f"{[e.start_ms for e in entry]} vs {[r.end_ms for r in read]}")
    # Unknown moods are ignored, not guessed.
    sc2 = parse_script("## OPEN\n# MOOD: melancholy\nN: A line.\n", "t")
    check("moods: an unknown name is reported and ignored", md.unknown_moods(sc2) == ["melancholy"]
          and md.segment_moods(sc2) == [None])


def test_legacy_path() -> None:
    from history import history_producer as hp
    for p in sorted((ROOT / "data/history/scripts").glob("*.txt")):
        sc = parse_script(p.read_text(encoding="utf-8"), p.stem)
        if md.has_moods(sc):
            continue
        turns = hp.build_turns(sc)
        check(f"legacy: {p.stem} keeps the house speed", all(s.speed is None for s, _ in turns))
        check(f"legacy: {p.stem} has no clip turn", not any(m.get("clip") for _, m in turns))
    # A timeline with no clip has no blocks, so the old bus is untouched.
    sub, tl, dry, _ = synth_timeline(with_clip=False)
    check("legacy: no clip, no mute blocks", hp.clip_blocks(tl) == [])


def test_score() -> None:
    import numpy as np
    from briefing import generate_assets as ga
    cues = ga.history_cues("contemporary")
    for k in ("theme", "outro", "rupture_entry", "sting:to_document", "sting:from_clip",
              "bed:dread", "bed:procedure", "bed:grief", "bed:reckoning"):
        check(f"score: {k} rendered", k in cues and len(cues[k]) > 0)
    check("score: no bed and no transition for testimony or rupture",
          not any(k in cues for k in ("bed:testimony", "bed:rupture", "transition:testimony",
                                      "transition:rupture")))
    for k, x in cues.items():
        check(f"score: {k} does not clip", float(np.max(np.abs(x))) < 1.0)
        if k.startswith("bed:"):
            check(f"score: {k} loops without a seam", ga._seam_ratio(x) < 3.0, f"{ga._seam_ratio(x):.2f}")
    check("score: the outro ends in true silence", ga._rms_dbfs(cues["outro"][-4800:]) < -80.0)
    # The new parameters default to the old motif: On Air's theme renders
    # exactly as the committed file does.
    import wave as _w
    with _w.open(str(ga.ASSETS_DIR / "radio_theme.wav")) as fh:
        committed = np.frombuffer(fh.readframes(fh.getnframes()), dtype=np.int16)
    t = ga._time(8.0)
    sig = ga._theme_figure(t)
    sig *= ga._swell(t, 0.0, 0.25, 8.0 - 2.4, 2.1)
    sig = sig / (np.abs(sig).max() or 1.0) * 10 ** (-13 / 20)
    now = np.round(np.clip(sig, -1, 1) * 32767.0).astype(np.int16)
    check("score: On Air's theme is bit-identical under the new defaults", np.array_equal(committed, now))


TESTS = [test_directives_parsed, test_directives_inert, test_pilot_as_committed, test_clean_fixture_admits,
         test_h12_rights, test_h13_provenance, test_h14_transcript, test_h15_credit, test_h16_caps,
         test_h17_timeline, test_h17_bus, test_moods, test_legacy_path, test_score]


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
