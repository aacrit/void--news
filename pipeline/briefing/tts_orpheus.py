"""Orpheus 3B as a TtsEngine: local GPU only, every unit word-checked.

Orpheus (canopylabs/orpheus-3b-0.1-ft; Apache-2.0 as stated, built on Llama
3.2, so treated as Llama-licensed) is the most natural voice the 2026-10-03
History audition heard, and the only one that changed words: "to the Commons"
became "to the comments" on two seeds. So this engine never returns a line
the ASR gate has not heard back word for word (tts_orpheus_worker.py), and a
line that never passes is reported, not hidden.

It runs in its own venv with CUDA torch (VOID_ORPHEUS_PYTHON, default
~/.venv-orpheus then ~/.venv-audition-orpheus). A GitHub runner has no GPU,
so it is never in the default engine chain: a render opts in with
`history_producer.py --engine orpheus` on a machine that has one.

There is no speed control. A turn's mood speed (Kokoro's pace knob) maps to a
temperature instead: the slow moods sample cooler, which reads steadier.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from briefing.tts_engines import EngineResult, TurnSpec, _to_24k_mono, PYDUB_AVAILABLE

try:
    from pydub import AudioSegment
    from pydub.silence import detect_leading_silence
except ImportError:  # pragma: no cover
    AudioSegment = None

# Casting: the 2026-10-03 audition chose tara as the narrator; Orpheus has no
# male voice as natural, so the men's documents go to leo and the women's to
# zoe. A reader of record never changes per speaker.
ORPHEUS_VOICES = {"A": "tara", "B": "leo", "C": "zoe"}
SAMPLING = {"top_p": 0.8, "repetition_penalty": 1.1}
SEEDS = {"A": 1947, "B": 1948, "C": 1949}
SENTENCE_GAP_MS = 160
EDGE_KEEP_MS = 120
MIN_UNIT_WORDS = 4

_ABBR = {"mr", "mrs", "ms", "dr", "st", "sir", "gen", "lt", "col", "no", "vol", "mt", "jr", "sr"}
_BOUNDARY = re.compile(r"[.!?][\"')\]]?\s+(?=[\"'(]?[A-Z])")


def temperature_for(speed: float | None) -> float:
    """Kokoro's mood speed, read as delivery: slower moods sample cooler."""
    if speed is None:
        return 0.6
    return 0.5 if speed < 0.96 else 0.6


def split_sentences(text: str, min_words: int = MIN_UNIT_WORDS) -> list[str]:
    """Split at sentence ends without changing a character; a sentence under
    `min_words` rides with its neighbour (very short generations degrade)."""
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
    merged, carry = [], ""
    for p in (p for p in pieces if p):
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


def _trim(seg, keep_ms: int = EDGE_KEEP_MS, thresh: float = -45.0):
    lead = detect_leading_silence(seg, silence_threshold=thresh, chunk_size=10)
    trail = detect_leading_silence(seg.reverse(), silence_threshold=thresh, chunk_size=10)
    a, b = max(0, lead - keep_ms), len(seg) - max(0, trail - keep_ms)
    return seg[a:b] if b > a else seg


class OrpheusEngine:
    name = "orpheus"

    def __init__(self, voices: dict[str, str] | None = None, python: str | None = None,
                 name_tokens: set[str] | None = None, ledger_path: Path | None = None,
                 seed_offset: int = 0):
        self.voices = dict(voices or ORPHEUS_VOICES)
        self.python = python or os.environ.get("VOID_ORPHEUS_PYTHON", "").strip() or self._find_python()
        self.name_tokens = sorted(name_tokens or set())
        self.ledger_path = ledger_path
        self.seed_offset = seed_offset
        self._worker = Path(__file__).parent / "tts_orpheus_worker.py"
        self.ledger: dict = {}

    @staticmethod
    def _find_python() -> str:
        home = Path.home()
        for cand in (home / ".venv-orpheus" / "bin" / "python",
                     home / ".venv-audition-orpheus" / "bin" / "python"):
            if cand.exists():
                return str(cand)
        return ""

    def available(self) -> tuple[bool, str]:
        if not PYDUB_AVAILABLE:
            return False, "pydub not installed"
        if not self.python or not Path(self.python).exists():
            return False, "no Orpheus venv (VOID_ORPHEUS_PYTHON)"
        probe = subprocess.run([self.python, "-c", "import torch,snac,faster_whisper;"
                                "assert torch.cuda.is_available()"], capture_output=True, text=True, timeout=180)
        if probe.returncode != 0:
            return False, f"Orpheus venv not usable (needs CUDA, snac, faster-whisper): {probe.stderr.strip()[-200:]}"
        return True, "ok"

    def voice_id(self, role) -> str:
        return self.voices[role]

    def synthesize_batch(self, turns: list[TurnSpec], *, deadline_s: float = 0) -> EngineResult:
        from briefing.asr_words import norm_words
        res = EngineResult(engine=self.name)
        if not turns:
            return res
        work = Path(tempfile.mkdtemp(prefix="void-orpheus-"))
        try:
            jobs, by_turn = [], {}
            for t in turns:
                by_turn[t.idx] = []
                for k, piece in enumerate(split_sentences(t.text)):
                    uid = f"{t.idx:04d}_{k:02d}"
                    by_turn[t.idx].append(uid)
                    jobs.append({"id": uid, "text": piece, "ref_words": norm_words(piece),
                                 "name_tokens": self.name_tokens, "voice": self.voices[t.role],
                                 "seed": SEEDS[t.role] + self.seed_offset,
                                 "temperature": temperature_for(t.speed), **SAMPLING})
            (work / "jobs.json").write_text(json.dumps(jobs, indent=1), encoding="utf-8")
            t0 = time.time()
            cache = os.environ.get("VOID_ORPHEUS_CACHE", "").strip() or str(Path.home() / ".cache" / "void-orpheus-units")
            p = subprocess.run([self.python, str(self._worker), "--jobs", str(work / "jobs.json"),
                                "--out", str(work / "out"), "--cache", cache])
            result_path = work / "out" / "result.json"
            if p.returncode != 0 or not result_path.exists():
                res.failed = {t.idx: f"orpheus worker exited {p.returncode}" for t in turns}
                return res
            result = json.loads(result_path.read_text(encoding="utf-8"))
            units = result["units"]
            for t in turns:
                pieces = []
                for uid in by_turn[t.idx]:
                    wav = work / "out" / f"{uid}.wav"
                    if not wav.exists():
                        break
                    pieces.append(_trim(_to_24k_mono(AudioSegment.from_file(str(wav), format="wav"))))
                if len(pieces) != len(by_turn[t.idx]):
                    res.failed[t.idx] = "a unit produced no audio"
                    continue
                seg = AudioSegment.silent(duration=0, frame_rate=24000)
                for k, piece in enumerate(pieces):
                    if k:
                        seg += AudioSegment.silent(duration=SENTENCE_GAP_MS, frame_rate=24000)
                    seg += piece
                res.audio[t.idx] = seg
            failed_units = {u: v for u, v in units.items() if not v.get("passed")}
            res.timing = dict(result["timing"], wall_s=round(time.time() - t0, 1),
                              units=len(jobs), units_failed=len(failed_units))
            self.ledger = {"engine": "orpheus", "voices": self.voices, "sampling": SAMPLING,
                           "versions": result["versions"], "timing": res.timing,
                           "units": {j["id"]: dict(units.get(j["id"], {}), text=j["text"]) for j in jobs}}
            if self.ledger_path:
                self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
                self.ledger_path.write_text(json.dumps(self.ledger, indent=1), encoding="utf-8")
            return res
        finally:
            shutil.rmtree(work, ignore_errors=True)
