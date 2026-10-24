"""Chatterbox worker for scripts/audition_tts.py. Runs inside .venv-audition-chatterbox.

jobs.json: [{"id", "text", "voice", "exaggeration", "cfg_weight", "temperature", "seed"}]
voices.json: {"<voice>": null | "<reference wav>"}  (null = the model's built-in voice)
Writes <out>/<id>.wav and <out>/result.json (ok, failed, timing, versions).
--embed mode returns speaker embeddings (the model's own voice encoder) for
wavs, used to measure how distinct a document voice is from the narrator.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torchaudio


def seed_all(s: int) -> None:
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs")
    ap.add_argument("--voices")
    ap.add_argument("--out", required=True)
    ap.add_argument("--embed", nargs="*", help="wav paths to embed instead of synthesising")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    from chatterbox.tts import ChatterboxTTS
    from importlib.metadata import version as _v
    model = ChatterboxTTS.from_pretrained(device="cuda")
    load_s = time.time() - t0
    versions = {"torch": torch.__version__, "cuda": torch.version.cuda,
                "chatterbox-tts": _v("chatterbox-tts"), "gpu": torch.cuda.get_device_name(0)}
    if a.embed is not None:
        import librosa
        embs = {}
        for p in a.embed:
            wav, _ = librosa.load(p, sr=16000)
            e = model.ve.embeds_from_wavs([wav], sample_rate=16000)
            embs[p] = np.asarray(e).reshape(-1).tolist()
        (out / "embed.json").write_text(json.dumps(embs))
        return 0
    jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    voices = json.loads(Path(a.voices).read_text(encoding="utf-8"))
    # One conditionals object per voice, never copied: a reference-clip
    # conditional holds non-leaf tensors that deepcopy refuses, and nothing
    # needs a copy, because generate() re-applies the job's exaggeration to
    # whichever object is current.
    default_conds = model.conds
    conds = {}
    for v, ref in voices.items():
        if ref:
            with torch.inference_mode():
                model.prepare_conditionals(ref)
            conds[v] = model.conds
        else:
            conds[v] = default_conds
    ok, failed, synth_s, audio_s = [], {}, 0.0, 0.0
    torch.cuda.reset_peak_memory_stats()
    for j in jobs:
        try:
            model.conds = conds[j["voice"]]
            seed_all(int(j["seed"]))
            t = time.time()
            with torch.inference_mode():
                wav = model.generate(j["text"], exaggeration=float(j["exaggeration"]),
                                     cfg_weight=float(j["cfg_weight"]),
                                     temperature=float(j.get("temperature", 0.8)))
            torch.cuda.synchronize()
            synth_s += time.time() - t
            wav = wav.detach().cpu().float()
            audio_s += wav.shape[-1] / model.sr
            torchaudio.save(str(out / f"{j['id']}.wav"), wav, model.sr)
            ok.append(j["id"])
            print(f"  {j['id']} {wav.shape[-1] / model.sr:5.1f}s", flush=True)
        except Exception as e:  # report, never hide
            failed[j["id"]] = repr(e)[:300]
    (out / "result.json").write_text(json.dumps({
        "ok": ok, "failed": failed, "versions": versions, "sample_rate": model.sr,
        "timing": {"load_s": round(load_s, 1), "synth_s": round(synth_s, 1), "audio_s": round(audio_s, 1),
                   "rtf": round(synth_s / audio_s, 3) if audio_s else None,
                   "vram_peak_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
