"""faster-whisper on the GPU for scripts/audition_tts.py --check. Runs inside .venv-audition-asr.

Each line is transcribed on its own, cut at its exact timeline position: a
whole-file pass stitches 30 s windows and duplicates or drops words at the
seams, which reads as a misread that never happened (measured 2026-10-03 on
the Kokoro audition: "1947" doubled at a seam, "as authoritative" lost at
another, both clean when the line was transcribed alone).

No initial prompt: a spelling hint would hide a mispronounced name.
--windows: JSON [{"id", "start", "end"}] in seconds. Writes
{"windows": {id: text}, "model", "version"} to --out.
"""
import argparse
import json
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--windows", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="large-v3")
    a = ap.parse_args()
    import faster_whisper
    from faster_whisper import WhisperModel, decode_audio
    sr = 16000
    audio = decode_audio(a.audio, sampling_rate=sr)
    m = WhisperModel(a.model, device="cuda", compute_type="float16")
    out = {}
    for w in json.loads(open(a.windows, encoding="utf-8").read()):
        clip = audio[int(max(0.0, w["start"]) * sr): int(w["end"] * sr)]
        segs, _ = m.transcribe(clip, language="en", beam_size=5, temperature=0.0,
                               condition_on_previous_text=False, vad_filter=False)
        out[w["id"]] = " ".join(s.text.strip() for s in segs)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump({"windows": out, "model": a.model, "version": faster_whisper.__version__}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
