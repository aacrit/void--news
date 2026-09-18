"""Text-to-speech engines behind one interface, for the On Air radio show.

    engine_chain()  ->  [KokoroEngine, EdgeTtsEngine]   (VOID_TTS_ENGINE=kokoro, default)
                        [EdgeTtsEngine]                 (VOID_TTS_ENGINE=edge)

Kokoro-82M is the production voice (CEO 2026-09-18): Apache-2.0, trained on
permissive audio, runs on the CI runner's CPU in a separate virtualenv (see
tts_kokoro_worker.py). edge-tts (Microsoft neural voices through an unofficial
endpoint) is only the automatic fallback: it carries a commercial terms-of-
service risk and has broken without notice before, so a show never DEPENDS
on it, but a show always ships.

Every engine synthesises a batch of turns (one per spoken line) and returns
24 kHz mono pydub AudioSegments keyed by turn index. Timing is built by the
assembler from the audio lengths, so no engine needs word-boundary metadata.
Engines are never mixed within one show.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:  # pragma: no cover
    AudioSegment = None  # type: ignore
    PYDUB_AVAILABLE = False

SAMPLE_RATE = 24000
Role = Literal["A", "B"]

# Kokoro v1.0 roster picks (hexgrad VOICES.md grades):
#   am_michael  C+  lowest and most even of the three best-trained American
#               male voices (am_michael / am_fenrir / am_puck) -> the anchor
#   af_heart    A   the only A-grade voice; warm, clear, a full register
#               contrast to Michael -> alternate stories + the editorial
# Ear-test alternates: am_fenrir (brighter), af_bella (A-), bf_emma (British).
KOKORO_VOICES: dict[str, str] = {
    "A": os.environ.get("VOID_KOKORO_VOICE_A", "am_michael"),
    "B": os.environ.get("VOID_KOKORO_VOICE_B", "af_heart"),
}
# Measured 2026-09-18 on a 78-word news paragraph: am_michael reads 155 wpm at
# speed 1.0 and 163 at 1.08; af_heart reads 168 at 1.0. Per-voice speeds put
# both in the 160-170 wpm news band (VOID_KOKORO_SPEED_A / _B override).
KOKORO_SPEED: dict[str, float] = {
    "A": float(os.environ.get("VOID_KOKORO_SPEED_A", "1.08") or 1.08),
    "B": float(os.environ.get("VOID_KOKORO_SPEED_B", "1.0") or 1.0),
}

EDGE_VOICES: dict[str, str] = {
    "A": "en-US-AndrewMultilingualNeural",
    "B": "en-US-AvaMultilingualNeural",
}
EDGE_RATE = os.environ.get("VOID_EDGE_RATE", "+8%")


@dataclass
class TurnSpec:
    idx: int
    role: Role
    text: str
    speed: float | None = None   # per-turn override, else engine default


@dataclass
class EngineResult:
    engine: str
    audio: dict[int, "AudioSegment"] = field(default_factory=dict)
    failed: dict[int, str] = field(default_factory=dict)
    timing: dict = field(default_factory=dict)

    def coverage(self, turns: list[TurnSpec]) -> float:
        return len(self.audio) / len(turns) if turns else 0.0


class TtsEngine(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...
    def voice_id(self, role: Role) -> str: ...
    def synthesize_batch(self, turns: list[TurnSpec], *, deadline_s: float) -> EngineResult: ...


def _to_24k_mono(seg: "AudioSegment") -> "AudioSegment":
    return seg.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)


# ---------------------------------------------------------------------------
# Kokoro (subprocess worker in .venv-tts)
# ---------------------------------------------------------------------------

class KokoroEngine:
    name = "kokoro"

    def __init__(self, python: str | None = None, voices: dict[str, str] | None = None,
                 speed: dict[str, float] | None = None, threads: int | None = None):
        self.python = python or os.environ.get("VOID_KOKORO_PYTHON", "").strip() or self._find_python()
        self.voices = dict(voices or KOKORO_VOICES)
        self.speed = dict(speed or KOKORO_SPEED)
        self.threads = threads if threads is not None else int(os.environ.get("VOID_KOKORO_THREADS", "0") or 0)
        self._worker = Path(__file__).parent / "tts_kokoro_worker.py"

    @staticmethod
    def _find_python() -> str:
        root = Path(__file__).resolve().parents[2]
        for cand in (root / ".venv-tts" / "bin" / "python", root / ".venv-tts" / "Scripts" / "python.exe"):
            if cand.exists():
                return str(cand)
        return ""

    def available(self) -> tuple[bool, str]:
        if not PYDUB_AVAILABLE:
            return False, "pydub not installed"
        if not self.python or not Path(self.python).exists():
            return False, "no .venv-tts interpreter (VOID_KOKORO_PYTHON)"
        try:
            from briefing.kokoro_assets import ensure_model_files
        except ImportError:
            from pipeline.briefing.kokoro_assets import ensure_model_files  # type: ignore
        try:
            self._model, self._voices_bin = ensure_model_files(quiet=True)
        except Exception as e:
            return False, f"model files unavailable: {e}"
        probe = subprocess.run([self.python, "-c", "import kokoro_onnx, onnxruntime"],
                               capture_output=True, text=True, timeout=120)
        if probe.returncode != 0:
            return False, f"kokoro-onnx import failed: {probe.stderr.strip()[-200:]}"
        return True, "ok"

    def voice_id(self, role: Role) -> str:
        return self.voices.get(role, KOKORO_VOICES[role])

    def synthesize_batch(self, turns: list[TurnSpec], *, deadline_s: float = 900.0) -> EngineResult:
        res = EngineResult(engine=self.name)
        if not turns:
            return res
        ok, why = self.available()
        if not ok:
            res.failed = {t.idx: why for t in turns}
            return res
        work = Path(tempfile.mkdtemp(prefix="void-kokoro-"))
        try:
            jobs = [{"id": f"{t.idx:04d}", "text": t.text, "voice": self.voice_id(t.role),
                     "speed": t.speed or self.speed.get(t.role, 1.0),
                     "lang": "en-gb" if self.voice_id(t.role)[0] == "b" else "en-us"}
                    for t in turns]
            (work / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
            cmd = [self.python, str(self._worker), "--jobs", str(work / "jobs.json"), "--out", str(work / "out"),
                   "--model", str(self._model), "--voices", str(self._voices_bin),
                   "--threads", str(self.threads), "--deadline-seconds", str(deadline_s),
                   "--speed", str(self.speed.get("A", 1.0))]
            t0 = time.time()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=deadline_s + 180)
            wall = time.time() - t0
            if proc.stdout.strip():
                print(f"  [tts] {proc.stdout.strip().splitlines()[-1]}")
            result_path = work / "out" / "result.json"
            if not result_path.exists():
                err = (proc.stderr or "").strip()[-300:]
                res.failed = {t.idx: f"worker produced no result ({err})" for t in turns}
                return res
            result = json.loads(result_path.read_text(encoding="utf-8"))
            res.timing = dict(result.get("timing") or {}, wall_s=round(wall, 1), status=result.get("status"))
            failed = result.get("failed") or {}
            for t in turns:
                jid = f"{t.idx:04d}"
                wav = work / "out" / f"{jid}.wav"
                if jid in result.get("ok", []) and wav.exists():
                    try:
                        res.audio[t.idx] = _to_24k_mono(AudioSegment.from_file(str(wav), format="wav"))
                    except Exception as e:  # pragma: no cover
                        res.failed[t.idx] = f"decode: {e}"
                else:
                    res.failed[t.idx] = failed.get(jid, result.get("status", "missing"))
            return res
        except subprocess.TimeoutExpired:
            res.failed = {t.idx: "worker timeout" for t in turns}
            return res
        finally:
            shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# edge-tts (fallback only)
# ---------------------------------------------------------------------------

class EdgeTtsEngine:
    name = "edge"

    def __init__(self, voices: dict[str, str] | None = None, rate: str | None = None):
        self.voices = dict(voices or EDGE_VOICES)
        self.rate = rate or EDGE_RATE
        try:
            import edge_tts  # noqa: F401
            self._module = edge_tts
        except ImportError:
            self._module = None

    def available(self) -> tuple[bool, str]:
        if not PYDUB_AVAILABLE:
            return False, "pydub not installed"
        if self._module is None:
            return False, "edge-tts not installed"
        return True, "ok (fallback engine; unofficial endpoint)"

    def voice_id(self, role: Role) -> str:
        return self.voices.get(role, EDGE_VOICES[role])

    def synthesize_batch(self, turns: list[TurnSpec], *, deadline_s: float = 600.0) -> EngineResult:
        import asyncio
        res = EngineResult(engine=self.name)
        if not turns:
            return res
        ok, why = self.available()
        if not ok:
            res.failed = {t.idx: why for t in turns}
            return res
        work = Path(tempfile.mkdtemp(prefix="void-edge-"))
        edge = self._module

        async def one(t: TurnSpec) -> None:
            comm = edge.Communicate(t.text, self.voice_id(t.role), rate=self.rate)
            await comm.save(str(work / f"{t.idx:04d}.mp3"))

        async def all_() -> list:
            sem = asyncio.Semaphore(8)

            async def guarded(t: TurnSpec):
                async with sem:
                    return await one(t)
            return await asyncio.gather(*(guarded(t) for t in turns), return_exceptions=True)

        t0 = time.time()
        loop = asyncio.new_event_loop()
        try:
            outcomes = loop.run_until_complete(asyncio.wait_for(all_(), timeout=deadline_s))
        except Exception as e:
            res.failed = {t.idx: f"{type(e).__name__}: {e}" for t in turns}
            shutil.rmtree(work, ignore_errors=True)
            loop.close()
            return res
        finally:
            if not loop.is_closed():
                loop.close()
        for t, outcome in zip(turns, outcomes):
            path = work / f"{t.idx:04d}.mp3"
            if isinstance(outcome, BaseException) or not path.exists():
                res.failed[t.idx] = str(outcome) if isinstance(outcome, BaseException) else "no file"
                continue
            try:
                res.audio[t.idx] = _to_24k_mono(AudioSegment.from_file(str(path), format="mp3"))
            except Exception as e:
                res.failed[t.idx] = f"decode: {e}"
        shutil.rmtree(work, ignore_errors=True)
        audio_s = sum(len(a) for a in res.audio.values()) / 1000.0
        wall = time.time() - t0
        res.timing = {"wall_s": round(wall, 1), "audio_s": round(audio_s, 1),
                      "rtf": round(wall / audio_s, 3) if audio_s else None}
        return res


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def engine_chain(preferred: str | None = None) -> list:
    """Ordered engines to try. Default: Kokoro, then edge-tts as fallback."""
    pref = (preferred or os.environ.get("VOID_TTS_ENGINE", "kokoro") or "kokoro").strip().lower()
    if pref == "edge":
        return [EdgeTtsEngine()]
    if pref == "kokoro-only":
        return [KokoroEngine()]
    return [KokoroEngine(), EdgeTtsEngine()]


def synthesize_with_fallback(turns: list[TurnSpec], *, engines: list | None = None,
                             deadline_s: float | None = None, required: set[int] | None = None,
                             min_coverage: float = 0.98) -> EngineResult | None:
    """Try each engine in turn; accept the first whose result covers the show.

    ``required`` are turn indices that must be present (sign-on, sign-off);
    ``min_coverage`` is the fraction of turns that must synthesise.
    """
    # Kokoro int8 measured at real-time factor ~1.4 on a 4-core sandbox CPU
    # (2026-09-18); a 9-minute show is ~13 minutes of synthesis there, so the
    # default deadline leaves headroom for a slow runner.
    deadline_s = deadline_s or float(os.environ.get("VOID_TTS_DEADLINE_SECONDS", "1500") or 1500)
    for eng in engines or engine_chain():
        ok, why = eng.available()
        if not ok:
            print(f"  [tts] {eng.name}: unavailable ({why})")
            continue
        print(f"  [tts] {eng.name}: synthesising {len(turns)} turns "
              f"(A={eng.voice_id('A')}, B={eng.voice_id('B')})")
        res = eng.synthesize_batch(turns, deadline_s=deadline_s)
        cov = res.coverage(turns)
        missing_required = [i for i in (required or set()) if i not in res.audio]
        print(f"  [tts] {eng.name}: {len(res.audio)}/{len(turns)} turns, coverage {cov:.0%}, "
              f"timing {res.timing}")
        if res.failed:
            sample = list(res.failed.items())[:3]
            print(f"  [tts] {eng.name}: failures e.g. {sample}")
        if cov >= min_coverage and not missing_required:
            return res
        print(f"  [tts] {eng.name}: rejected (coverage {cov:.0%}, missing required {missing_required})")
    return None


if __name__ == "__main__":  # quick manual probe
    for eng in engine_chain(sys.argv[1] if len(sys.argv) > 1 else None):
        print(eng.name, eng.available())
