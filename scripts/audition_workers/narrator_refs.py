"""Synthetic narrator reference clips for Chatterbox (run in the host venv).

Chatterbox copies timbre AND delivery from its reference clip, so the clip is
the real prompt. Every candidate here is a synthetic voice (Kokoro, Apache-2.0;
Orpheus built-ins via orpheus_worker.py), never a recording of a person, reading
a grave passage that is not from any script and names no one.

    python scripts/audition_workers/narrator_refs.py --out out/audition/narrator/refs
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.tts_engines import KokoroEngine, TurnSpec  # noqa: E402

TEXT = ("The river rose slowly through the night. By morning the bridge was gone, "
        "and the town on the far bank could only be reached by boat. "
        "No one had expected it. The water had never come this high before.")
KOKORO = ["bm_lewis", "bm_george", "bm_daniel", "bm_fable", "am_michael", "am_onyx"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=0.88)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for v in KOKORO:
        eng = KokoroEngine(voices={"A": v, "B": v, "C": v}, workers=1)
        res = eng.synthesize_batch([TurnSpec(idx=0, role="A", text=TEXT, speed=a.speed)], deadline_s=300)
        if 0 in res.audio:
            res.audio[0].export(str(out / f"kokoro-{v}.wav"), format="wav")
            print(f"  kokoro-{v}: {len(res.audio[0]) / 1000:.1f}s")
        else:
            print(f"  kokoro-{v}: FAILED {res.failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
