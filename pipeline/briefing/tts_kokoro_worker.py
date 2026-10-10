"""Kokoro-82M synthesis worker. Runs in its OWN interpreter (.venv-tts).

kokoro-onnx needs numpy 2 and the pipeline pins numpy 1.26 for spaCy and
scikit-learn, so the model lives in a separate virtualenv and this script is
the only thing that imports it. The pipeline talks to it through files:

    python tts_kokoro_worker.py --jobs jobs.json --out DIR --model M --voices V \
        [--threads N] [--deadline-seconds S] [--speed 1.08]

jobs.json: [{"id": "000", "text": "...", "voice": "am_michael" |
             {"blend": [["am_michael", 0.7], ["am_fenrir", 0.3]]},
             "speed": 1.08, "lang": "en-us"}, ...]

Writes DIR/<id>.wav (24 kHz mono int16) per job and DIR/result.json:
    {"ok": [ids], "failed": {id: message}, "status": "ok" | "deadline",
     "timing": {"load_s", "synth_s", "audio_s", "rtf"}, "sample_rate": 24000}

A deadline exits 0 with partial results and status "deadline"; the engine
treats that as a failure of the missing turns. Nothing here imports from the
pipeline package: this file must stay importable with only numpy + kokoro-onnx.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import wave
from pathlib import Path


def _write_wav(path: Path, samples, sample_rate: int) -> float:
    import numpy as np
    x = np.asarray(samples, dtype=np.float32)
    peak = float(np.abs(x).max()) if x.size else 0.0
    if peak > 0.891:  # keep -1 dBFS headroom; Kokoro occasionally clips
        x = x * (0.891 / peak)
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return len(pcm) / float(sample_rate)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--voices", required=True)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--deadline-seconds", type=float, default=0.0)
    ap.add_argument("--speed", type=float, default=1.0)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    result = {"ok": [], "failed": {}, "status": "ok", "timing": {}, "sample_rate": 24000}
    t0 = time.time()

    try:
        import numpy as np  # noqa: F401
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        opts = ort.SessionOptions()
        if args.threads > 0:
            opts.intra_op_num_threads = args.threads
        session = ort.InferenceSession(args.model, sess_options=opts,
                                       providers=["CPUExecutionProvider"])
        kokoro = Kokoro.from_session(session, args.voices)
    except Exception as e:  # pragma: no cover - environment failure
        result["status"] = "load-failed"
        result["failed"]["__load__"] = f"{type(e).__name__}: {e}"
        (out / "result.json").write_text(json.dumps(result), encoding="utf-8")
        print(f"[kokoro-worker] load failed: {e}", file=sys.stderr)
        return 0

    load_s = time.time() - t0
    result["timing"]["load_s"] = round(load_s, 2)
    voice_cache: dict[str, object] = {}

    def resolve_voice(spec):
        if isinstance(spec, str):
            return spec
        blend = spec.get("blend") or []
        key = json.dumps(blend)
        if key not in voice_cache:
            import numpy as np
            acc = None
            for name, weight in blend:
                style = kokoro.get_voice_style(name)
                acc = style * float(weight) if acc is None else acc + style * float(weight)
            voice_cache[key] = acc.astype(np.float32)
        return voice_cache[key]

    audio_s = 0.0
    synth_t0 = time.time()
    for job in jobs:
        if args.deadline_seconds and (time.time() - t0) > args.deadline_seconds:
            result["status"] = "deadline"
            break
        jid = str(job["id"])
        text = (job.get("text") or "").strip()
        if not text:
            result["failed"][jid] = "empty text"
            continue
        try:
            voice = resolve_voice(job.get("voice") or "am_michael")
            samples, sr = kokoro.create(
                text, voice=voice, speed=float(job.get("speed") or args.speed),
                lang=job.get("lang") or "en-us", trim=True,
            )
            result["sample_rate"] = int(sr)
            audio_s += _write_wav(out / f"{jid}.wav", samples, int(sr))
            result["ok"].append(jid)
        except Exception as e:
            result["failed"][jid] = f"{type(e).__name__}: {e}"

    synth_s = time.time() - synth_t0
    result["timing"].update({
        "synth_s": round(synth_s, 2),
        "audio_s": round(audio_s, 2),
        "rtf": round(synth_s / audio_s, 3) if audio_s else None,
    })
    (out / "result.json").write_text(json.dumps(result), encoding="utf-8")
    print(f"[kokoro-worker] {len(result['ok'])} ok, {len(result['failed'])} failed, "
          f"load {load_s:.1f}s, synth {synth_s:.1f}s for {audio_s:.1f}s audio "
          f"(rtf {result['timing']['rtf']}), status={result['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
