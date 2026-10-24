"""Local TTS audition: render one passage of a History script through a model,
mastered identically to every other model, and check it against the text.

    python scripts/audition_tts.py --model {chatterbox,orpheus,kokoro} --from OPEN --to "SCENE 2"
    python scripts/audition_tts.py --model orpheus --check          # render + transcript diff
    python scripts/audition_tts.py --model kokoro --check-only      # diff an existing render
    python scripts/audition_tts.py --docvoice                       # Chatterbox document-voice pre-audition

A listening test, never published: output goes to out/audition/ (gitignored).
See docs/handoffs/PARTITION-TTS-AUDITION.md. Hard rules: no word of the script
changes; built-in or synthetic voices only (never a real person's voice); the
signed archival clip plays as itself, dry; no music, no stings, no EQ chain.

Everything structural is the production producer's own code
(pipeline/history/history_producer.py): parse_script, the clip gates, the mood
speeds, build_turns, the silence grammar, build_timeline, load_clip, clip_bus,
loudnorm_two_pass, encode_mp3. Only synthesis differs between models.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT))

from history import history_producer as hp                         # noqa: E402
from history import mood as moodmod                                # noqa: E402
from history import clips as cliplib                               # noqa: E402
from history.casting import cast                                   # noqa: E402
from history.script_format import parse_script, validate_script    # noqa: E402
from briefing import radio_producer as rp                          # noqa: E402
from briefing.spoken_text import normalize_for_speech, spoken_numbers  # noqa: E402
from briefing.tts_engines import TurnSpec, KokoroEngine, _to_24k_mono  # noqa: E402
from pipeline.history.verify_clip import align, render_diff, words_of  # noqa: E402

OUT = ROOT / "out" / "audition"
WORKERS = ROOT / "scripts" / "audition_workers"
HOME = Path.home()

# Delivery. Reference style is a Ken Burns documentary: an unhurried,
# understated narrator and plain, sincere document reads. Chatterbox starts
# from the handoff's values (narrator 0.35 / 0.4, documents 0.25 / 0.5).
CB_NARRATOR = {"dread": (0.35, 0.40), "procedure": (0.30, 0.45), "rupture": (0.35, 0.40)}
CB_DOCUMENT = (0.25, 0.50)
CB_TEMPERATURE = 0.8
ORPHEUS = {"N": "leo", "M": "dan", "F": "tara"}
ORPHEUS_SAMPLING = {"temperature": 0.6, "top_p": 0.8, "repetition_penalty": 1.1}
SEEDS = {"N": 1947, "M": 1948, "F": 1949}
SENTENCE_GAP_MS = 160
EDGE_KEEP_MS = 120
MIN_UNIT_WORDS = 4      # a shorter sentence rides with its neighbour (text unchanged)
CB_NARRATOR_REF: str | None = None   # --cb-narrator-ref: a synthetic reference clip (never a real person)
UNIT = "sentence"                     # --unit line: one generation per script line (keeps the line's arc)
SEED_OFFSET = 0         # --seed-offset: a second take, to tell a one-off sampling error from a systematic one

# Only names an ASR model cannot be trusted to spell. A common word that is
# also a proper noun ("Commons", "Delhi") is judged as a word: Orpheus read
# "to the Commons" as "to the comments" and that is a misread, not a spelling.
NAMES = {"radcliffe", "attlee", "abell", "sutlej", "beas", "nehru", "prasad", "rajendra", "jawaharlal"}
NUMBER_WORDS = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
                "hundred", "thousand", "million", "first", "second", "third", "fourth", "fifth", "sixth",
                "twelfth", "fourteenth", "fifteenth", "fortieth"}

# Neutral text for document-voice references: not from any script, no names.
REF_TEXT = ("The committee met on a Tuesday morning. The minutes of the previous meeting "
            "were read aloud, approved without amendment, and filed with the clerk before noon.")


# --------------------------------------------------------------------------- script

def _matches(script, i: int, sel: str) -> bool:
    """history_producer.subset's selector rule: "SCENE n" is the n-th SCENE."""
    seg = script.segments[i]
    sel = sel.strip().upper()
    if seg.kind == "SCENE" and sel.startswith("SCENE "):
        n = sum(1 for s in script.segments[:i + 1] if s.kind == "SCENE")
        return sel == f"SCENE {n}"
    return sel == seg.kind or sel == f"{seg.kind} {seg.title or ''}".upper().strip()


def range_bounds(script, frm: str, to: str) -> tuple[int, int]:
    structural = ("OPEN", "TITLE", "SCENE", "TURN", "PERSPECTIVE", "CLOSE", "REST")
    segs = script.segments
    start = next(i for i in range(len(segs)) if _matches(script, i, frm))
    end = max(i for i in range(len(segs)) if _matches(script, i, to))
    while end + 1 < len(segs) and segs[end + 1].kind not in structural:
        end += 1
    while end + 1 < len(segs) and segs[end + 1].kind == "REST":
        end += 1
    if end < start:
        raise SystemExit(f"--to {to!r} comes before --from {frm!r}")
    return start, end


def rest_plan(script, moods) -> tuple[dict[int, int | str], int]:
    """The REST block of history_producer.produce(), verbatim in effect, plus
    the length of a trailing REST (no next segment to open it before)."""
    rests: dict[int, int | str] = {}
    tail = 0
    for i, seg in enumerate(script.segments):
        if seg.kind != "REST":
            continue
        short = (seg.title or "").strip().lower() == "short"
        prev_m = next((moods[j] for j in range(i - 1, -1, -1)
                       if script.segments[j].kind != "REST"), None) if moods else None
        nxt = next((j for j in range(i + 1, len(script.segments))
                    if script.segments[j].kind != "REST"), None)
        if prev_m:
            mo = moodmod.MOODS[prev_m]
            length = mo.rest_short_ms if short else mo.rest_ms
        else:
            length = hp.GAPS["rest_short" if short else "rest"]
        if nxt is not None:
            rests[nxt] = length
        else:
            tail = max(tail, int(length))
    return rests, tail


def original_lines(script, admitted) -> list[str | None]:
    """The script's own text for each turn build_turns makes (None = a clip),
    in the same order and with the same skips. The transcript is checked
    against THIS, not the respelled form the engine was given."""
    out: list[str | None] = []
    for si, seg in enumerate(script.segments):
        slot = admitted.get(si)
        if slot is not None and slot.replaces == "none":
            out.append(None)
        clip_done = False
        for line in seg.lines:
            if slot is not None and slot.replaces == "document" and line.speaker in ("M", "F"):
                if not clip_done:
                    out.append(None)
                    clip_done = True
                continue
            if not normalize_for_speech(line.text, script.say):
                continue
            out.append(line.text)
    return out


# --------------------------------------------------------------------------- sentences

_ABBR = {"mr", "mrs", "ms", "dr", "st", "sir", "gen", "lt", "col", "no", "vol", "mt", "jr", "sr"}
_BOUNDARY = re.compile(r"[.!?][\"')\]]?\s+(?=[\"'(]?[A-Z])")


def split_sentences(text: str, min_words: int = MIN_UNIT_WORDS) -> list[str]:
    """Split at sentence ends without touching a character. A sentence under
    `min_words` rides with the next one (or the previous, at the end): a very
    short generation is where autoregressive TTS hallucinates."""
    text = re.sub(r"\s+", " ", text).strip()
    pieces, start = [], 0
    for m in _BOUNDARY.finditer(text):
        tok = re.search(r"(\S+)$", text[start:m.start() + 1])
        word = (tok.group(1) if tok else "").rstrip(".!?\"')]").lower()
        if (len(word) == 1 and word.isalpha()) or word in _ABBR:
            continue
        pieces.append(text[start:m.end()].strip())
        start = m.end()
    pieces.append(text[start:].strip())
    pieces = [p for p in pieces if p]
    merged: list[str] = []
    carry = ""
    for p in pieces:
        p = f"{carry} {p}".strip() if carry else p
        if len(p.split()) < min_words:
            carry = p
            continue
        merged.append(p)
        carry = ""
    if carry:
        if merged:
            merged[-1] = f"{merged[-1]} {carry}"
        else:
            merged.append(carry)
    if " ".join(merged) != text:
        raise AssertionError(f"sentence split altered the text: {text!r}")
    return merged


# --------------------------------------------------------------------------- engines

def venv_python(name: str) -> str:
    env = os.environ.get(f"VOID_AUDITION_{name.upper()}_PYTHON", "").strip()
    for cand in (env, ROOT / f".venv-audition-{name}" / "bin" / "python",
                 HOME / f".venv-audition-{name}" / "bin" / "python"):
        if cand and Path(cand).exists():
            return str(cand)
    raise SystemExit(f"no interpreter for {name}: create ~/.venv-audition-{name} or set VOID_AUDITION_{name.upper()}_PYTHON")


def run_worker(name: str, args: list[str]) -> None:
    py = venv_python(name)
    cmd = [py, str(WORKERS / f"{name}_worker.py"), *args]
    print(f"  [audition] {name} worker: {' '.join(cmd[2:])[:160]}")
    p = subprocess.run(cmd)
    if p.returncode not in (0, 1):
        raise SystemExit(f"{name} worker exited {p.returncode}")


def load_wav(path: Path):
    from pydub import AudioSegment
    return _to_24k_mono(AudioSegment.from_file(str(path), format="wav"))


def trim_edges(seg, keep_ms: int = EDGE_KEEP_MS, thresh: float = -45.0):
    from pydub.silence import detect_leading_silence
    lead = detect_leading_silence(seg, silence_threshold=thresh, chunk_size=10)
    trail = detect_leading_silence(seg.reverse(), silence_threshold=thresh, chunk_size=10)
    a = max(0, lead - keep_ms)
    b = len(seg) - max(0, trail - keep_ms)
    return seg[a:b] if b > a else seg


def synthesize(model: str, units: list[dict], work: Path, voices: dict, doc_ref: str | None) -> dict:
    """units: [{"id", "text", "speaker", "mood", "speed"}] -> {"audio": {id: seg}, "timing", "versions", "settings"}."""
    work.mkdir(parents=True, exist_ok=True)
    if model == "kokoro":
        vmap = {"A": voices["narrator"], "B": voices["document_m"], "C": voices["document_f"]}
        eng = KokoroEngine(voices=vmap)
        ok, why = eng.available()
        if not ok:
            raise SystemExit(f"kokoro unavailable: {why}")
        role = {"N": "A", "M": "B", "F": "C"}
        specs = [TurnSpec(idx=k, role=role[u["speaker"]], text=u["text"], speed=u["speed"])
                 for k, u in enumerate(units)]
        t0 = time.time()
        res = eng.synthesize_batch(specs, deadline_s=1800)
        if res.failed:
            raise SystemExit(f"kokoro failed on {len(res.failed)} unit(s): {list(res.failed.items())[:3]}")
        from importlib.metadata import version as _v
        try:
            kv = subprocess.run([eng.python, "-c", "import importlib.metadata as m;print(m.version('kokoro-onnx'),m.version('onnxruntime'))"],
                                capture_output=True, text=True).stdout.split()
        except Exception:
            kv = ["?", "?"]
        timing = dict(res.timing)
        timing["synth_s"] = round(time.time() - t0, 1)
        return {"audio": {u["id"]: res.audio[k] for k, u in enumerate(units)}, "timing": timing,
                "versions": {"kokoro-onnx": kv[0] if kv else "?", "onnxruntime": kv[1] if len(kv) > 1 else "?",
                             "pydub": _v("pydub")},
                "settings": {"voices": vmap, "speeds": "per mood (MOODS narrator/document speed)", "device": "CPU (onnxruntime)"}}

    jobs = []
    if model == "chatterbox":
        for u in units:
            if u["speaker"] == "N":
                ex, cfg = CB_NARRATOR.get(u["mood"] or "", (0.35, CB_NARRATOR["dread"][1]))
                voice = "narrator"
            else:
                ex, cfg = CB_DOCUMENT
                voice = "document"
            jobs.append({"id": u["id"], "text": u["text"], "voice": voice, "exaggeration": ex,
                         "cfg_weight": cfg, "temperature": CB_TEMPERATURE, "seed": SEEDS[u["speaker"]] + SEED_OFFSET})
        (work / "voices.json").write_text(json.dumps({"narrator": CB_NARRATOR_REF, "document": doc_ref}))
        (work / "jobs.json").write_text(json.dumps(jobs, indent=1), encoding="utf-8")
        run_worker("chatterbox", ["--jobs", str(work / "jobs.json"), "--voices", str(work / "voices.json"),
                                  "--out", str(work / "wav")])
        settings = {"narrator": CB_NARRATOR_REF or "built-in default voice", "document": doc_ref or "built-in default voice",
                    "unit": UNIT,
                    "narrator_exaggeration_cfg_by_mood": CB_NARRATOR, "document_exaggeration_cfg": CB_DOCUMENT,
                    "temperature": CB_TEMPERATURE, "seeds": SEEDS}
    elif model == "orpheus":
        for u in units:
            jobs.append({"id": u["id"], "text": u["text"], "voice": ORPHEUS[u["speaker"]],
                         "seed": SEEDS[u["speaker"]] + SEED_OFFSET, **ORPHEUS_SAMPLING})
        (work / "jobs.json").write_text(json.dumps(jobs, indent=1), encoding="utf-8")
        run_worker("orpheus", ["--jobs", str(work / "jobs.json"), "--out", str(work / "wav")])
        settings = {"voices": ORPHEUS, **ORPHEUS_SAMPLING, "seeds": SEEDS, "emotion_tags": "none (verbatim audition)",
                    "dtype": "bfloat16"}
    else:
        raise SystemExit(f"unknown model {model}")
    result = json.loads((work / "wav" / "result.json").read_text())
    if result["failed"]:
        raise SystemExit(f"{model} failed on {len(result['failed'])} unit(s): {list(result['failed'].items())[:3]}")
    audio = {u["id"]: load_wav(work / "wav" / f"{u['id']}.wav") for u in units}
    return {"audio": audio, "timing": result["timing"], "versions": result["versions"], "settings": settings}


# --------------------------------------------------------------------------- render

def render(args) -> Path:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not on PATH: the mastering helpers would silently copy the unmastered mix")
    slug = args.slug
    event = yaml.safe_load((hp.EVENTS / f"{slug}.yaml").read_text(encoding="utf-8"))
    raw = (hp.SCRIPTS / f"{slug}.txt").read_bytes()
    import hashlib
    script_sha = hashlib.sha256(raw).hexdigest()
    script = parse_script(raw.decode("utf-8"), slug)
    fails = [f for f in validate_script(script, event) if f.level == "fail"]
    if fails:
        raise SystemExit(f"script fails its own gates: {[(f.id, f.detail[:80]) for f in fails]}")

    admitted: dict = {}
    if any(seg.directives_of("CLIP") for seg in script.segments):
        slots, cfind = cliplib.evaluate(script, hp._load_ledger(slug), slug)
        if any(f.level == "fail" for f in cfind):
            raise SystemExit(f"clip gate failed: {[(f.id, f.detail[:80]) for f in cfind if f.level == 'fail']}")
        admitted = {s.seg_idx: s for s in slots if s.admitted}

    a, b = range_bounds(script, args.frm, args.to)
    import copy as _copy
    full = script
    script = _copy.copy(full)
    script.segments = full.segments[a:b + 1]
    admitted = {k - a: v for k, v in admitted.items() if a <= k <= b}
    for k, v in admitted.items():
        v.seg_idx = k
    if args.clip == "real" and any(seg.directives_of("CLIP") for seg in script.segments) and not admitted:
        raise SystemExit("the passage has a CLIP slot but no clip was admitted")

    moods = moodmod.segment_moods(script) if moodmod.has_moods(script) else None
    rests, tail_ms = rest_plan(script, moods)
    voices = cast(event)
    say = script.say if args.say else {}
    if not args.say:
        script.say = {}
    turns = hp.build_turns(script, moods, admitted)
    originals = original_lines(script, admitted)
    if len(originals) != len(turns):
        raise SystemExit(f"turn/line mismatch {len(turns)} vs {len(originals)}")

    units: list[dict] = []
    for (spec, meta), orig in zip(turns, originals):
        meta["original"] = orig
        if meta.get("clip") is not None:
            continue
        meta["units"] = []
        for k, piece in enumerate(split_sentences(spec.text) if UNIT == "sentence" else [spec.text]):
            uid = f"{spec.idx:03d}_{k:02d}"
            units.append({"id": uid, "text": piece, "speaker": meta["speaker"], "mood": meta.get("mood"),
                          "speed": spec.speed})
            meta["units"].append(uid)

    tag = args.tag or args.model + (f"-seed{args.seed_offset}" if args.seed_offset else "")
    work = OUT / tag
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    print(f"  [audition] {slug} {args.frm}..{args.to}: {len(script.segments)} segments, "
          f"{len(turns)} turns ({sum(1 for _, m in turns if m.get('clip') is not None)} clip), {len(units)} units")
    t0 = time.time()
    syn = synthesize(args.model, units, work / "synth", voices, args.cb_doc_ref)
    synth_wall = time.time() - t0

    from pydub import AudioSegment
    audio: dict[int, AudioSegment] = {}
    clip_audio: dict[int, AudioSegment] = {}
    for spec, meta in turns:
        if meta.get("clip") is not None:
            if args.clip != "real":
                continue
            seg = hp.load_clip(slug, meta["clip"])
            if seg is None:
                raise SystemExit("the SIGNED clip could not be loaded as verified; stopping (ask the CEO)")
            clip_audio[spec.idx] = seg
            audio[spec.idx] = seg
            continue
        joined = AudioSegment.silent(duration=0, frame_rate=24000)
        for k, uid in enumerate(meta["units"]):
            piece = trim_edges(syn["audio"][uid])
            joined += (AudioSegment.silent(duration=SENTENCE_GAP_MS, frame_rate=24000) if k else
                       AudioSegment.silent(duration=0, frame_rate=24000)) + piece
        audio[spec.idx] = joined
    turns = [(s, m) for s, m in turns if s.idx in audio]

    tl = hp.build_timeline(turns, audio, opener_ms=0, transition_ms=0, outro_ms=0, rests=rests, break_ms=0)
    total = tl.total_ms + tail_ms
    voice_bus = rp._silent(total)
    for c in tl.cues:
        if c.clip_id is None:
            voice_bus = voice_bus.overlay(audio[c.idx], position=c.start_ms)
    clipbus, placed = hp.clip_bus(tl, clip_audio, voice_bus, work)
    mix = voice_bus.set_channels(2)
    if placed:
        mix = mix.overlay(clipbus[:total], position=0)
    mix_wav, master_wav = work / "mix.wav", work / "master.wav"
    mix.export(str(mix_wav), format="wav")
    stats = rp.loudnorm_two_pass(mix_wav, master_wav) or {}
    mp3 = OUT / f"partition-{tag}.mp3" if slug == "partition-of-india" else OUT / f"{slug}-{tag}.mp3"
    if not rp.encode_mp3(master_wav, mp3, "128k", 2):
        raise SystemExit("mp3 encode failed")
    final = rp.measure_loudness(master_wav) or {}

    cues = []
    for c in tl.cues:
        meta = next(m for s, m in turns if s.idx == c.idx)
        cues.append({"idx": c.idx, "speaker": "CLIP" if c.clip_id else meta["speaker"], "kind": c.kind,
                     "mood": c.mood, "start_ms": c.start_ms, "end_ms": c.end_ms,
                     "original": meta.get("original"), "clip_id": c.clip_id})
    (work / "timeline.json").write_text(json.dumps({"cues": cues, "total_ms": total}, indent=1), encoding="utf-8")
    audio_s = sum(len(syn["audio"][u["id"]]) for u in units) / 1000
    t = syn["timing"]
    synth_s = float(t.get("synth_s") or synth_wall)
    run = {
        "model": args.model, "slug": slug, "range": [args.frm, args.to], "script_sha256": script_sha,
        "commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                                 capture_output=True, text=True).stdout.strip(),
        "seed_offset": args.seed_offset, "tag": tag, "units": len(units), "turns": len(turns), "say": bool(args.say), "clip": args.clip,
        "clips_placed": placed, "settings": syn["settings"], "versions": syn["versions"],
        "timing": {"load_s": t.get("load_s"), "synth_s": round(synth_s, 1), "speech_audio_s": round(audio_s, 1),
                   "rtf": round(synth_s / audio_s, 3) if audio_s else None, "wall_s": round(synth_wall, 1),
                   "vram_peak_gb": t.get("vram_peak_gb")},
        "programme_s": round(total / 1000, 1),
        "master": {"I": final.get("input_i"), "TP": final.get("input_tp"), "LRA": final.get("input_lra"),
                   "normalization_type": stats.get("normalization_type")},
        "ffmpeg": subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0],
        "mp3": str(mp3.relative_to(ROOT)),
    }
    (work / "run.json").write_text(json.dumps(run, indent=1, default=str), encoding="utf-8")
    print(f"  [audition] {mp3.relative_to(ROOT)}: {run['programme_s']}s, RTF {run['timing']['rtf']}, "
          f"I {run['master']['I']} TP {run['master']['TP']} ({run['master']['normalization_type']})")
    write_readme()
    return mp3


# --------------------------------------------------------------------------- check

def _norm_words(text: str) -> list[str]:
    t = spoken_numbers(text or "")
    t = re.sub(r"[-‐-―]", " ", t)
    t = re.sub(r"\bper cent\b", "percent", t, flags=re.I)
    return words_of(t)


def check(model: str) -> dict:
    work = OUT / model
    run = json.loads((work / "run.json").read_text())
    tl = json.loads((work / "timeline.json").read_text())
    mp3 = ROOT / run["mp3"]
    tr_path = work / "transcript.json"
    # One window per spoken line, padded into the silence around it but never
    # into the neighbour; the archival clip is not the model's and is skipped.
    cues = [c for c in tl["cues"] if c["original"] and not c["clip_id"]]
    all_cues = sorted(tl["cues"], key=lambda c: c["start_ms"])
    # Two windows per line: tight (250 ms) and wide (half the gap to each
    # neighbour, up to 900 ms). A word is a defect only when BOTH decodes
    # disagree with the script in the same way; one decode alone missed the
    # first "The" of a line that a wider window heard clearly (2026-10-03).
    windows = []
    for c in cues:
        k = all_cues.index(c)
        prev_end = all_cues[k - 1]["end_ms"] if k else 0
        next_start = all_cues[k + 1]["start_ms"] if k + 1 < len(all_cues) else tl["total_ms"]
        for tag, pre, post in (("", 250, 250),
                               ("~wide", min(900, (c["start_ms"] - prev_end) // 2),
                                min(900, (next_start - c["end_ms"]) // 2))):
            windows.append({"id": f"{c['idx']}{tag}",
                            "start": max(prev_end, c["start_ms"] - max(pre, 0)) / 1000,
                            "end": min(next_start, c["end_ms"] + max(post, 0)) / 1000})
    (work / "windows.json").write_text(json.dumps(windows), encoding="utf-8")
    run_worker("asr", [str(mp3), "--windows", str(work / "windows.json"), "--out", str(tr_path)])
    tr = json.loads(tr_path.read_text(encoding="utf-8"))
    defects, listen, diffs = [], [], []
    ref_total, errs = 0, 0
    for c in cues:
        ref = " ".join(_norm_words(c["original"]))
        al = align(ref, " ".join(_norm_words(tr["windows"].get(str(c["idx"]), ""))))
        al_w = align(ref, " ".join(_norm_words(tr["windows"].get(f"{c['idx']}~wide", ""))))
        confirmed = {o for o in al_w["ops"] if o[0] != "="}
        ref_total += al["ref_words"]
        at = c["start_ms"] / 1000
        stamp = f"{int(at // 60)}:{at % 60:04.1f}"
        bad = [o for o in al["ops"] if o[0] != "=" and o in confirmed]
        errs += len(bad)
        if any(o[0] != "=" and o not in confirmed for o in al["ops"]):
            diffs.append(f"{stamp} (one decode only, not counted): " + " ".join(render_diff(al["ops"])))
        if bad:
            diffs.append(f"{stamp} {c['speaker']}: " + " ".join(render_diff([o if o in confirmed or o[0] == '=' else ('=', o[1], o[1]) for o in al["ops"] if o[1] is not None or o in confirmed])))
        for op, r, h in bad:
            tokens = {x for x in (r, h) if x}
            kind = "NAME" if (r in NAMES or h in NAMES) else "NUMBER" if tokens & NUMBER_WORDS else "WORD"
            item = {"op": op, "ref": r, "heard": h, "at": stamp, "kind": kind, "line": c["original"][:80]}
            (listen if kind == "NAME" else defects).append(item)
    wer = round(errs / ref_total, 4) if ref_total else None
    summary = {"model": model, "asr": f"faster-whisper {tr['version']} {tr['model']}, per line",
               "ref_words": ref_total, "wer": wer, "defects": defects, "names_to_listen": listen,
               "rule1": "PASS" if not defects else "FAIL", "diff": diffs}
    (work / "check.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"  [check] {model}: WER {wer}, {len(defects)} defect(s), {len(listen)} name(s) to listen -> {summary['rule1']}")
    for d in defects:
        print(f"    {d['at']} {d['kind']:6} {d['op']} ref={d['ref']} heard={d['heard']}")
    write_readme()
    return summary


# --------------------------------------------------------------------------- docvoice

def docvoice(args) -> None:
    """Chatterbox has one built-in voice. Candidate document readers: Orpheus
    built-in voices (synthetic, never a real person) speaking neutral text,
    used as Chatterbox reference clips, plus the bare default voice. Each
    reads the Attlee extract; distinctness from the narrator is measured with
    Chatterbox's own speaker encoder. The CEO decides by ear."""
    d = OUT / "docvoice"
    d.mkdir(parents=True, exist_ok=True)
    cands = args.doc_candidates.split(",")
    refs = d / "refs"
    jobs = [{"id": f"ref-{v}", "text": REF_TEXT, "voice": v, "seed": 7, **ORPHEUS_SAMPLING} for v in cands]
    (d / "ref_jobs.json").write_text(json.dumps(jobs))
    run_worker("orpheus", ["--jobs", str(d / "ref_jobs.json"), "--out", str(refs)])
    attlee = ("For the purpose of determining the population of districts, "
              "the nineteen forty-one census figures will be taken as authoritative.")
    narr = ("You would assume a line like that was drawn carefully. Over years. "
            "By people who knew the ground.")
    voices = {"narrator": None, "default": None}
    voices.update({f"orpheus-{v}": str(refs / f"ref-{v}.wav") for v in cands})
    cjobs = [{"id": "narrator", "text": narr, "voice": "narrator", "exaggeration": 0.35, "cfg_weight": 0.4,
              "temperature": CB_TEMPERATURE, "seed": SEEDS["N"]}]
    cjobs += [{"id": f"attlee-{v}", "text": attlee, "voice": v, "exaggeration": CB_DOCUMENT[0],
               "cfg_weight": CB_DOCUMENT[1], "temperature": CB_TEMPERATURE, "seed": SEEDS["M"]}
              for v in voices if v != "narrator"]
    (d / "voices.json").write_text(json.dumps(voices))
    (d / "jobs.json").write_text(json.dumps(cjobs))
    run_worker("chatterbox", ["--jobs", str(d / "jobs.json"), "--voices", str(d / "voices.json"), "--out", str(d / "wav")])
    wavs = [str(d / "wav" / f"{j['id']}.wav") for j in cjobs]
    run_worker("chatterbox", ["--out", str(d / "wav"), "--embed", *wavs])
    emb = json.loads((d / "wav" / "embed.json").read_text())
    n = emb[wavs[0]]

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))

    rows = [{"candidate": j["id"].replace("attlee-", ""), "wav": str(Path(w).relative_to(ROOT)),
             "similarity_to_narrator": round(cos(n, emb[w]), 3)} for j, w in zip(cjobs[1:], wavs[1:])]
    rows.sort(key=lambda r: r["similarity_to_narrator"])
    (d / "summary.json").write_text(json.dumps(rows, indent=1))
    print("  [docvoice] lower similarity = more distinct from the narrator")
    for r in rows:
        print(f"    {r['candidate']:16} {r['similarity_to_narrator']}  {r['wav']}")


# --------------------------------------------------------------------------- README

LISTEN = """\
1. Is the narrator one person from the OPEN to the Nehru credit (timbre, age, accent, energy)?
2. Does the document voice sound like a different reader of record, not an impersonation, on Attlee and Radcliffe?
3. Do the pauses breathe: the line gaps in the dread opening, the beat into Attlee's read, the short REST after "He had five weeks", the long REST after SCENE 2?
4. Does any line rush or run words together ("...from the figures of one census, six years old"; "the fifteenth of August, and four judges on each of two commissions")?
5. Are "nineteen forty seven", "fifteenth"/"fourteenth" and "Sutlej"/"Beas" clean?
6. Does the real Nehru recording sit naturally (nothing synthetic near it, level about 3 LU under the narrator)?
7. Any artefacts: metallic sibilants, warble, breath pops, truncated final words?
8. Ken Burns test: does it sound like a documentary narrator who trusts the material, or like an announcer selling it?
"""


def write_readme() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["# Partition TTS audition", "",
             "A listening test, never published (docs/handoffs/PARTITION-TTS-AUDITION.md). Passage: `## OPEN` "
             "through `## SCENE 2` of `data/history/scripts/partition-of-india.txt`, verbatim. Every file is mastered "
             "identically: dry voice only (no bed, no stings, no EQ chain), the production silence grammar and rests, "
             "the real signed Nehru recording at its slot, then two-pass loudnorm to -16 LUFS / -1 dBTP and MP3 128k.",
             "", "RTF = synthesis seconds / seconds of speech produced (below 1 is faster than real time).", "",
             "Environment (WSL2 Ubuntu, Python 3.12.3, RTX 4090 Laptop 16 GB, driver 576.02): torch 2.6.0+cu126 in each "
             "GPU venv; `setuptools<81` pinned in the Chatterbox venv (resemble-perth imports pkg_resources, removed in "
             "setuptools 81); `av<16` (15.1.0) pinned in the ASR venv (faster-whisper 1.2.1 passes an argument PyAV 19 "
             "dropped). Chatterbox embeds Resemble's imperceptible Perth watermark in every output.", ""]
    for rp_ in sorted(OUT.glob("*/run.json")):
        model = rp_.parent.name
        run = json.loads(rp_.read_text())
        lines += [f"## {model}" + (f" (take 2: seeds +{run['seed_offset']})" if run.get("seed_offset") else ""), "", f"- File: `{run['mp3']}` ({run['programme_s']} s)",
                  f"- Script sha256 `{run['script_sha256'][:16]}…` at commit `{run['commit']}`; {run['units']} sentence units, SAY respellings {'on' if run['say'] else 'off'}",
                  f"- Versions: `{json.dumps(run['versions'])}`",
                  f"- Settings: `{json.dumps(run['settings'], default=str)}`",
                  f"- Timing: load {run['timing']['load_s']} s, synth {run['timing']['synth_s']} s for "
                  f"{run['timing']['speech_audio_s']} s of speech, **RTF {run['timing']['rtf']}**, VRAM peak {run['timing']['vram_peak_gb']} GB",
                  f"- Master: I {run['master']['I']} LUFS, TP {run['master']['TP']} dBTP, LRA {run['master']['LRA']}, "
                  f"{run['master']['normalization_type']}; {run['ffmpeg']}",
                  f"- Clip: {json.dumps(run['clips_placed'])}"]
        ck = OUT / model / "check.json"
        if ck.exists():
            c = json.loads(ck.read_text())
            lines += [f"- Transcript check ({c['asr']}): WER {c['wer']} over {c['ref_words']} words, "
                      f"{len(c['defects'])} defect(s) -> **Rule 1 {c['rule1']}**"]
            for d in c["defects"]:
                lines.append(f"  - {d['at']} {d['kind']} `{d['op']}` script `{d['ref']}` heard `{d['heard']}`")
            if c["names_to_listen"]:
                lines.append("  - Names to confirm by ear: " + ", ".join(
                    f"{d['ref'] or d['heard']} at {d['at']} (ASR heard `{d['heard']}`)" for d in c["names_to_listen"]))
        lines.append("")
    dv = OUT / "docvoice" / "summary.json"
    if dv.exists():
        lines += ["## Chatterbox document-voice candidates", "",
                  "Synthetic references only (Orpheus built-in voices on neutral text, or the default voice). "
                  "Similarity to the narrator from Chatterbox's own speaker encoder; lower = more distinct.", ""]
        lines += [f"- {r['candidate']}: {r['similarity_to_narrator']} `{r['wav']}`" for r in json.loads(dv.read_text())]
        lines.append("")
    lines += ["## Listen-check for the CEO", "", LISTEN]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=["chatterbox", "orpheus", "kokoro"])
    ap.add_argument("--slug", default="partition-of-india")
    ap.add_argument("--from", dest="frm", default="OPEN")
    ap.add_argument("--to", default="SCENE 2")
    ap.add_argument("--clip", choices=["real"], default="real")
    ap.add_argument("--say", dest="say", action="store_true", default=True)
    ap.add_argument("--no-say", dest="say", action="store_false")
    ap.add_argument("--cb-doc-ref", default=None, help="synthetic reference wav for Chatterbox's document voice")
    ap.add_argument("--tag", default=None, help="output name (partition-<tag>.mp3), default the model")
    ap.add_argument("--cb-narrator-cfg", type=float, default=None,
                    help="Chatterbox narrator cfg_weight for every mood (lower = slower, more deliberate)")
    ap.add_argument("--cb-narrator-ref", default=None, help="synthetic reference wav for Chatterbox's narrator")
    ap.add_argument("--cb-narrator-exag", type=float, default=None, help="Chatterbox narrator exaggeration, every mood")
    ap.add_argument("--cb-temp", type=float, default=None, help="Chatterbox temperature")
    ap.add_argument("--orpheus-narrator", default=None, help="Orpheus built-in voice for N: lines")
    ap.add_argument("--orpheus-temp", type=float, default=None)
    ap.add_argument("--unit", choices=["sentence", "line"], default="sentence")
    ap.add_argument("--seed-offset", type=int, default=0, help="second take with every seed shifted")
    ap.add_argument("--check", action="store_true", help="transcribe and diff after rendering")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--docvoice", action="store_true", help="Chatterbox document-voice pre-audition")
    ap.add_argument("--doc-candidates", default="dan,zac,leah")
    a = ap.parse_args()
    if a.docvoice:
        docvoice(a)
        write_readme()
        return 0
    if not a.model:
        ap.error("--model is required")
    global SEED_OFFSET, CB_NARRATOR_REF, UNIT, CB_TEMPERATURE
    SEED_OFFSET = a.seed_offset
    CB_NARRATOR_REF = a.cb_narrator_ref
    UNIT = a.unit
    if a.orpheus_narrator:
        ORPHEUS["N"] = a.orpheus_narrator
    if a.orpheus_temp is not None:
        ORPHEUS_SAMPLING["temperature"] = a.orpheus_temp
    if a.cb_temp is not None:
        CB_TEMPERATURE = a.cb_temp
    if a.cb_narrator_exag is not None:
        for k in list(CB_NARRATOR):
            CB_NARRATOR[k] = (a.cb_narrator_exag, CB_NARRATOR[k][1])
    tag = a.tag or a.model + (f"-seed{a.seed_offset}" if a.seed_offset else "")
    if a.cb_narrator_cfg is not None:
        for k in list(CB_NARRATOR):
            CB_NARRATOR[k] = (CB_NARRATOR[k][0], a.cb_narrator_cfg)
    if not a.check_only:
        render(a)
    if a.check or a.check_only:
        s = check(tag)
        return 0 if s["rule1"] == "PASS" else 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
