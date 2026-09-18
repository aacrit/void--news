"""TTS timing bench: measures the production engine on a fixed set of turns.

    python pipeline/briefing/tts_bench.py [--engine kokoro|edge] [--rtf-budget 2.0]

Prints model load time, real-time factor (synthesis seconds per audio second)
and measured words per minute per voice, and exits 1 when the engine is slower
than the budget or takes longer than 30 s to load. Runs in CI (radio-audio job)
so a Kokoro regression is caught before the 11:00 UTC show, not by it.

Measured 2026-09-18 on a 4-core sandbox: Kokoro int8 rtf 1.4 (slow CPU),
am_michael 163 wpm at speed 1.08, af_heart 168 wpm at 1.0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from briefing.tts_engines import TurnSpec, engine_chain  # noqa: E402

BENCH_FILE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "radio_bench_turns.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=os.environ.get("VOID_TTS_ENGINE", "kokoro"))
    ap.add_argument("--rtf-budget", type=float, default=float(os.environ.get("VOID_TTS_RTF_BUDGET", "2.0")))
    ap.add_argument("--load-budget", type=float, default=30.0)
    args = ap.parse_args()

    turns_raw = json.loads(BENCH_FILE.read_text(encoding="utf-8"))
    turns = [TurnSpec(idx=i, role=t["role"], text=t["text"]) for i, t in enumerate(turns_raw)]
    words = {"A": 0, "B": 0}
    for t in turns:
        words[t.role] += len(t.text.split())

    eng = next((e for e in engine_chain(args.engine) if e.name == args.engine.replace("-only", "")), None)
    if eng is None:
        print(f"[bench] no engine named {args.engine}")
        return 1
    ok, why = eng.available()
    print(f"[bench] {eng.name}: available={ok} ({why})")
    if not ok:
        return 1
    t0 = time.time()
    res = eng.synthesize_batch(turns, deadline_s=600)
    wall = time.time() - t0
    if len(res.audio) != len(turns):
        print(f"[bench] FAIL {len(res.failed)} of {len(turns)} turns failed: {list(res.failed.items())[:3]}")
        return 1
    audio_s = {"A": 0.0, "B": 0.0}
    for t in turns:
        audio_s[t.role] += len(res.audio[t.idx]) / 1000.0
    total_audio = audio_s["A"] + audio_s["B"]
    load_s = float(res.timing.get("load_s") or 0.0)
    synth_s = float(res.timing.get("synth_s") or wall)
    rtf = synth_s / total_audio if total_audio else float("inf")
    print(f"[bench] load {load_s:.1f}s, synth {synth_s:.1f}s for {total_audio:.1f}s audio, rtf {rtf:.2f}, wall {wall:.1f}s")
    for role in ("A", "B"):
        wpm = words[role] / audio_s[role] * 60 if audio_s[role] else 0
        print(f"[bench] voice {role} ({eng.voice_id(role)}): {words[role]} words in {audio_s[role]:.1f}s = {wpm:.0f} wpm")
    status = 0
    if rtf > args.rtf_budget:
        print(f"[bench] FAIL rtf {rtf:.2f} > budget {args.rtf_budget}")
        status = 1
    if load_s > args.load_budget:
        print(f"[bench] FAIL load {load_s:.1f}s > budget {args.load_budget}s")
        status = 1
    if status == 0:
        print("[bench] OK")
    return status


if __name__ == "__main__":
    sys.exit(main())
