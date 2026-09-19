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
Role = Literal["A", "B", "C"]

# Kokoro v1.0 roster picks (hexgrad VOICES.md grades), cast by the CEO from a
# 12-voice sampler on 2026-09-19:
#   am_puck     C+  light American, 112 Hz median pitch, 2594 Hz centroid ->
#               the anchor. Reads 164 wpm at speed 1.0 on real rundown copy,
#               so it needs no slowdown, but it is the one voice that arrives
#               at the worker's -1 dBFS clamp (raw peak > 1.0): the clamp in
#               tts_kokoro_worker is what keeps A from reaching the bus hot.
#   af_nova     C   low female (159 Hz) -> alternate stories. A register
#               contrast to A without the brightness of af_heart.
#   af_heart    A   the only A-grade voice; warm and clear -> the editorial,
#               and nothing else.
# Ear-test alternates: am_michael (darker, the previous anchor), am_fenrir
# (brighter), af_sky (147 Hz, the darkest well-behaved female), bf_emma.
# Three roles since 2026-09-19 (CEO): A anchors the news, B takes alternate
# stories, C reads ONLY the editorial, so the opinion firewall is audible the
# moment the voice changes.
KOKORO_VOICES: dict[str, str] = {
    "A": os.environ.get("VOID_KOKORO_VOICE_A", "am_puck"),
    "B": os.environ.get("VOID_KOKORO_VOICE_B", "af_nova"),
    "C": os.environ.get("VOID_KOKORO_VOICE_C", "af_heart"),
}
# Speed is calibrated per voice against the 160-170 wpm news band, measured on
# the four long turns of tests/fixtures/radio_bench_turns.json (real rundown
# copy: short lines over-count, because the leading silence does not scale).
# 2026-09-19: am_puck 164 wpm at 1.0, am_michael 157 at 1.08, af_heart 168 at
# 1.0. VOID_KOKORO_SPEED_A / _B / _C override.
KOKORO_SPEED: dict[str, float] = {
    "A": float(os.environ.get("VOID_KOKORO_SPEED_A", "1.0") or 1.0),     # am_puck already reads 164 wpm
    "B": float(os.environ.get("VOID_KOKORO_SPEED_B", "0.98") or 0.98),   # af_nova reads 172 wpm at 1.0
    "C": float(os.environ.get("VOID_KOKORO_SPEED_C", "0.97") or 0.97),   # the editorial sits a touch under the news pace
}

EDGE_VOICES: dict[str, str] = {
    "A": "en-US-AndrewMultilingualNeural",
    "B": "en-US-AvaMultilingualNeural",
    "C": "en-US-EmmaMultilingualNeural",
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
                 speed: dict[str, float] | None = None, threads: int | None = None,
                 workers: int | None = None):
        self.python = python or os.environ.get("VOID_KOKORO_PYTHON", "").strip() or self._find_python()
        self.voices = dict(voices or KOKORO_VOICES)
        self.speed = dict(speed or KOKORO_SPEED)
        # ONNX intra-op threading scales poorly for this model: two worker
        # processes with half the threads each finish a show sooner than one
        # process with all of them (measured 2026-09-18, see tts_bench.py).
        self.workers = max(1, workers if workers is not None else int(os.environ.get("VOID_KOKORO_WORKERS", "2") or 2))
        cpu = os.cpu_count() or 4
        self.threads = threads if threads is not None else int(os.environ.get("VOID_KOKORO_THREADS", "0") or 0)
        if self.threads <= 0:
            self.threads = max(1, cpu // self.workers)
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
            # Round-robin the jobs over N workers so every process gets a
            # similar amount of audio; each writes its own out dir + result.
            n = min(self.workers, len(jobs))
            procs = []
            t0 = time.time()
            for w in range(n):
                share = jobs[w::n]
                (work / f"jobs{w}.json").write_text(json.dumps(share), encoding="utf-8")
                cmd = [self.python, str(self._worker), "--jobs", str(work / f"jobs{w}.json"),
                       "--out", str(work / f"out{w}"), "--model", str(self._model),
                       "--voices", str(self._voices_bin), "--threads", str(self.threads),
                       "--deadline-seconds", str(deadline_s), "--speed", str(self.speed.get("A", 1.0))]
                procs.append(subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            outs = []
            for proc in procs:
                try:
                    out, err = proc.communicate(timeout=deadline_s + 180)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    out, err = "", "worker timeout"
                outs.append((out, err))
            wall = time.time() - t0
            merged_ok: set[str] = set()
            merged_failed: dict[str, str] = {}
            timing = {"load_s": 0.0, "synth_s": 0.0, "audio_s": 0.0}
            statuses = []
            for w, (out, err) in enumerate(outs):
                if out.strip():
                    print(f"  [tts] worker {w}: {out.strip().splitlines()[-1]}")
                result_path = work / f"out{w}" / "result.json"
                if not result_path.exists():
                    for job in jobs[w::n]:
                        merged_failed[job["id"]] = f"worker {w} produced no result ({(err or '').strip()[-200:]})"
                    statuses.append("no-result")
                    continue
                result = json.loads(result_path.read_text(encoding="utf-8"))
                merged_ok.update(result.get("ok", []))
                merged_failed.update(result.get("failed") or {})
                statuses.append(result.get("status"))
                for k in ("load_s", "synth_s", "audio_s"):
                    timing[k] = max(timing[k], float((result.get("timing") or {}).get(k) or 0.0)) if k != "audio_s" \
                        else timing[k] + float((result.get("timing") or {}).get(k) or 0.0)
            timing["rtf"] = round(wall / timing["audio_s"], 3) if timing["audio_s"] else None
            res.timing = dict(timing, wall_s=round(wall, 1), workers=n, threads=self.threads,
                              status=",".join(str(s) for s in statuses))
            for t in turns:
                jid = f"{t.idx:04d}"
                w = jobs.index(next(j for j in jobs if j["id"] == jid)) % n
                wav = work / f"out{w}" / f"{jid}.wav"
                if jid in merged_ok and wav.exists():
                    try:
                        res.audio[t.idx] = _to_24k_mono(AudioSegment.from_file(str(wav), format="wav"))
                    except Exception as e:  # pragma: no cover
                        res.failed[t.idx] = f"decode: {e}"
                else:
                    res.failed[t.idx] = merged_failed.get(jid, "missing")
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
              f"(A={eng.voice_id('A')}, B={eng.voice_id('B')}, C={eng.voice_id('C')})")
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
