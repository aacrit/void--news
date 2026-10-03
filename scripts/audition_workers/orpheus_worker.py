"""Orpheus 3B worker for scripts/audition_tts.py. Runs inside .venv-audition-orpheus.

Plain transformers + the SNAC 24 kHz decoder, following the model card's
reference inference: prompt = SOH(128259) + "<voice>: <text>" + EOT(128009)
+ EOH(128260); generate until EOS 128258; the audio codes are the ids after
the last SOS 128257, offset 128266, seven per frame over three SNAC layers.
Built-in voices only.

jobs.json: [{"id", "text", "voice", "temperature", "top_p", "repetition_penalty", "seed"}]
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

MODEL = os.environ.get("VOID_ORPHEUS_MODEL", "canopylabs/orpheus-3b-0.1-ft")
SR = 24000


def seed_all(s: int) -> None:
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def codes_to_audio(snac, ids: list[int]):
    ids = [t - 128266 for t in ids]
    n = len(ids) // 7
    l1, l2, l3 = [], [], []
    for i in range(n):
        f = ids[7 * i: 7 * i + 7]
        l1.append(f[0])
        l2.append(f[1] - 4096)
        l3.append(f[2] - 2 * 4096)
        l3.append(f[3] - 3 * 4096)
        l2.append(f[4] - 4 * 4096)
        l3.append(f[5] - 5 * 4096)
        l3.append(f[6] - 6 * 4096)
    allc = l1 + l2 + l3
    if not n or min(allc) < 0 or max(allc) > 4095:
        raise ValueError(f"bad code stream ({n} frames)")
    dev = next(snac.parameters()).device
    codes = [torch.tensor(x, device=dev).unsqueeze(0) for x in (l1, l2, l3)]
    with torch.inference_mode():
        return snac.decode(codes).squeeze().float().cpu().numpy()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from snac import SNAC
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to("cuda").eval()
    snac = SNAC.from_pretrained("hubertsiuzdak/snac_24khz").to("cuda").eval()
    load_s = time.time() - t0
    versions = {"torch": torch.__version__, "cuda": torch.version.cuda,
                "transformers": transformers.__version__, "model": MODEL,
                "gpu": torch.cuda.get_device_name(0)}
    jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    ok, failed, synth_s, audio_s = [], {}, 0.0, 0.0
    torch.cuda.reset_peak_memory_stats()
    for j in jobs:
        try:
            seed_all(int(j["seed"]))
            ids = tok(f"{j['voice']}: {j['text']}", return_tensors="pt").input_ids
            ids = torch.cat([torch.tensor([[128259]]), ids, torch.tensor([[128009, 128260]])], dim=1).to("cuda")
            t = time.time()
            with torch.inference_mode():
                gen = model.generate(ids, attention_mask=torch.ones_like(ids),
                                     max_new_tokens=int(j.get("max_new_tokens", 2400)),
                                     do_sample=True, temperature=float(j["temperature"]),
                                     top_p=float(j["top_p"]),
                                     repetition_penalty=float(j["repetition_penalty"]),
                                     eos_token_id=128258, pad_token_id=128263)
            row = gen[0].tolist()
            sos = [i for i, t_ in enumerate(row) if t_ == 128257]
            row = row[sos[-1] + 1:] if sos else row[ids.shape[1]:]
            row = [t_ for t_ in row if t_ != 128258]
            row = row[: len(row) // 7 * 7]
            wav = codes_to_audio(snac, row)
            torch.cuda.synchronize()
            synth_s += time.time() - t
            audio_s += len(wav) / SR
            sf.write(str(out / f"{j['id']}.wav"), wav, SR)
            ok.append(j["id"])
            print(f"  {j['id']} {len(wav) / SR:5.1f}s", flush=True)
        except Exception as e:  # report, never hide
            failed[j["id"]] = repr(e)[:300]
    (out / "result.json").write_text(json.dumps({
        "ok": ok, "failed": failed, "versions": versions, "sample_rate": SR,
        "timing": {"load_s": round(load_s, 1), "synth_s": round(synth_s, 1), "audio_s": round(audio_s, 1),
                   "rtf": round(synth_s / audio_s, 3) if audio_s else None,
                   "vram_peak_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
