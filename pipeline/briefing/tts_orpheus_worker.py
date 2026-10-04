"""Orpheus 3B synthesis with a word-perfect gate, in one GPU process.

Runs inside the Orpheus venv (torch CUDA, transformers, snac, faster-whisper),
spawned by briefing/tts_orpheus.py. One process holds the TTS model, the SNAC
decoder and the ASR model, so a retry costs a generation, not a model load.

For every unit (one or two sentences of one script line):
  1. generate with the job's voice, seed and temperature (the model card's
     prompt: SOH + "<voice>: <text>" + EOT + EOH; codes after the last SOS,
     offset 128266, seven per SNAC frame over three layers);
  2. reject a take that hit its token cap or runs far past its expected
     length (Orpheus babbles to the cap when it misses EOS);
  3. transcribe the take twice (beam 5 and greedy) with faster-whisper
     large-v3, no prompt; a word counts as wrong only when BOTH decodes
     disagree with the script the same way (one decode alone mishears);
  4. accept the first take with no wrong word. Names an ASR model cannot
     spell (the job's name tokens) never fail a take; they are logged for
     the CEO's ear. Otherwise retry with the next seed, then at a lower
     temperature; if nothing passes, keep the take with the fewest wrong
     words and say so.

Rule 1 is enforced by the caller: a unit that never passed is reported, and
a strict render refuses to master it.

jobs.json: [{"id", "text", "ref_words": [...], "name_tokens": [...], "voice",
             "seed", "temperature", "top_p", "repetition_penalty"}]
Writes <out>/<id>.wav and <out>/result.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from briefing.asr_words import norm_words, align, same_when_joined  # noqa: E402  (pure python, shared with the host)

MODEL_ID = "canopylabs/orpheus-3b-0.1-ft"
_BF16 = Path.home() / "models" / "orpheus-3b-0.1-ft-bf16"
# The bfloat16 copy (briefing/orpheus_bf16.py) when it exists: the published
# float32 shards are 15 GB and their page cache is what exhausted the WSL host.
MODEL = os.environ.get("VOID_ORPHEUS_MODEL") or (str(_BF16) if (_BF16 / "config.json").exists()
                                                  else "canopylabs/orpheus-3b-0.1-ft")
SNAC_MODEL = "hubertsiuzdak/snac_24khz"
ASR_MODEL = os.environ.get("VOID_ORPHEUS_ASR", "large-v3")
SR = 24000
TOKENS_PER_SECOND = 82.0          # SNAC 24 kHz: 11.72 coarse frames/s x 7 codes
SEED_RETRIES = 3
LOW_TEMPERATURE = 0.4


def _drop_page_cache(model: str) -> None:
    roots = [Path(model)] if Path(model).exists() else list(
        (Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub").glob(
            "models--" + model.replace("/", "--") + "/snapshots/*"))
    for root in roots:
        for f in root.rglob("*.safetensors"):
            try:
                fd = os.open(str(f), os.O_RDONLY)
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                os.close(fd)
            except OSError:
                pass


def seed_all(s: int) -> None:
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def codes_to_audio(snac, ids: list[int]) -> np.ndarray:
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


class Synth:
    def __init__(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from snac import SNAC
        from faster_whisper import WhisperModel
        import transformers
        import faster_whisper
        self.tok = AutoTokenizer.from_pretrained(MODEL)
        # Straight onto the GPU, shard by shard, then drop the files from the
        # page cache: under WSL2 cached file pages are RAM the host never gets back.
        self.model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda",
                                                          low_cpu_mem_usage=True).eval()
        _drop_page_cache(MODEL)
        self.snac = SNAC.from_pretrained(SNAC_MODEL).to("cuda").eval()
        self.asr = WhisperModel(ASR_MODEL, device="cuda", compute_type="float16")
        self.versions = {"torch": torch.__version__, "cuda": torch.version.cuda,
                         "transformers": transformers.__version__, "faster-whisper": faster_whisper.__version__,
                         "model": MODEL, "asr": ASR_MODEL, "gpu": torch.cuda.get_device_name(0)}

    def generate(self, job: dict, seed: int, temperature: float) -> np.ndarray:
        seed_all(seed)
        words = max(1, len(job["text"].split()))
        expected_s = words / 2.4                       # ~145 wpm
        cap = 7 * math.ceil(11.72 * (1.6 * expected_s + 1.5))
        ids = self.tok(f"{job['voice']}: {job['text']}", return_tensors="pt").input_ids
        ids = torch.cat([torch.tensor([[128259]]), ids, torch.tensor([[128009, 128260]])], dim=1).to("cuda")
        with torch.inference_mode():
            gen = self.model.generate(ids, attention_mask=torch.ones_like(ids), max_new_tokens=cap,
                                      do_sample=True, temperature=temperature, top_p=float(job["top_p"]),
                                      repetition_penalty=float(job["repetition_penalty"]),
                                      eos_token_id=128258, pad_token_id=128263)
        row = gen[0].tolist()
        hit_cap = row[-1] != 128258 and len(row) - ids.shape[1] >= cap
        sos = [i for i, t in enumerate(row) if t == 128257]
        row = row[sos[-1] + 1:] if sos else row[ids.shape[1]:]
        row = [t for t in row if t != 128258]
        row = row[: len(row) // 7 * 7]
        wav = codes_to_audio(self.snac, row)
        if hit_cap or len(wav) / SR > 1.8 * expected_s + 2.0:
            raise ValueError(f"babble: {len(wav) / SR:.1f}s for ~{expected_s:.1f}s expected")
        return wav

    def hear(self, wav: np.ndarray) -> list[str]:
        import torchaudio.functional as AF
        x = AF.resample(torch.from_numpy(wav).float(), SR, 16000).numpy()
        texts = []
        for beam in (5, 1):
            segs, _ = self.asr.transcribe(x, language="en", beam_size=beam, temperature=0.0,
                                          condition_on_previous_text=False, vad_filter=False)
            texts.append(" ".join(s.text.strip() for s in segs))
        return texts

    def judge(self, job: dict, texts: list[str]) -> tuple[list[tuple], list[tuple]]:
        """(wrong words agreed by both decodes, name ops for the ear)."""
        names = set(job.get("name_tokens") or [])
        sets = []
        for t in texts:
            hyp = norm_words(t)
            if same_when_joined(job["ref_words"], hyp):
                sets.append(set())
                continue
            sets.append({o for o in align(job["ref_words"], hyp) if o[0] != "="})
        agreed = sets[0] & sets[1]
        wrong = [o for o in agreed if not ((o[1] in names) or (o[2] in names) or
                                           (o[0] == "S" and o[1] in names))]
        heard_names = [o for o in agreed if o not in wrong]
        return sorted(wrong, key=str), sorted(heard_names, key=str)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None,
                    help="unit cache: a unit already accepted with the same model, voice, text and settings is reused, "
                         "so a render that dies (the 2026-10-03 WSL hang) resumes instead of starting over")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(a.cache) if a.cache else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8"))
    import hashlib
    import shutil

    def key_of(j: dict) -> str:
        k = {f: j.get(f) for f in ("voice", "text", "seed", "temperature", "top_p", "repetition_penalty")}
        # The bfloat16 copy is the same weights the GPU always ran (they were
        # cast at load), so it shares the published model's cache identity.
        k.update(model=MODEL_ID, asr=ASR_MODEL, retries=SEED_RETRIES, low=LOW_TEMPERATURE)
        if "seed_retries" in j or "low_temp" in j:   # natural mode; absent keys keep old cache ids
            k.update(seed_retries=j.get("seed_retries"), low_temp=j.get("low_temp"))
        return hashlib.sha256(json.dumps(k, sort_keys=True).encode()).hexdigest()[:24]

    cached = {}
    if cache:
        for j in jobs:
            meta = cache / f"{key_of(j)}.json"
            if meta.exists() and (cache / f"{key_of(j)}.wav").exists():
                cached[j["id"]] = json.loads(meta.read_text(encoding="utf-8"))
    t0 = time.time()
    s = Synth() if len(cached) < len(jobs) else None
    load_s = time.time() - t0
    units, synth_s, audio_s, takes_total = {}, 0.0, 0.0, 0
    torch.cuda.reset_peak_memory_stats()
    for j in jobs:
        if j["id"] in cached:
            shutil.copy(cache / f"{key_of(j)}.wav", out / f"{j['id']}.wav")
            units[j["id"]] = dict(cached[j["id"]], cached=True)
            audio_s += float((cached[j["id"]].get("accepted") or {}).get("seconds") or 0)
            print(f"  {j['id']} cached ({'ok' if cached[j['id']].get('passed') else 'FAIL'})", flush=True)
            continue
        retries = int(j.get("seed_retries", SEED_RETRIES))
        plan = [(j["seed"] + k, float(j["temperature"])) for k in range(1 + retries)]
        if j.get("low_temp", True):
            plan.append((j["seed"] + 100, LOW_TEMPERATURE))
        best, takes = None, []
        for seed, temp in plan:
            takes_total += 1
            t = time.time()
            try:
                wav = s.generate(j, seed, temp)
            except Exception as e:
                synth_s += time.time() - t
                takes.append({"seed": seed, "temperature": temp, "error": repr(e)[:200]})
                continue
            synth_s += time.time() - t
            texts = s.hear(wav)
            wrong, names = s.judge(j, texts)
            take = {"seed": seed, "temperature": temp, "seconds": round(len(wav) / SR, 2),
                    "heard": texts[0], "wrong": wrong, "names": names}
            takes.append(take)
            if best is None or len(wrong) < len(best[1]["wrong"]):
                best = (wav, take)
            if not wrong:
                break
        if best is None:
            units[j["id"]] = {"passed": False, "takes": takes, "error": "no take decoded"}
            print(f"  {j['id']} FAILED: no take decoded", flush=True)
            continue
        wav, take = best
        sf.write(str(out / f"{j['id']}.wav"), wav, SR)
        audio_s += len(wav) / SR
        passed = not take["wrong"]
        units[j["id"]] = {"passed": passed, "accepted": {k: take[k] for k in ("seed", "temperature", "seconds")},
                          "names": take["names"], "wrong": take["wrong"], "takes": takes}
        if cache:
            shutil.copy(out / f"{j['id']}.wav", cache / f"{key_of(j)}.wav")
            (cache / f"{key_of(j)}.json").write_text(json.dumps(units[j["id"]]), encoding="utf-8")
        print(f"  {j['id']} {'ok  ' if passed else 'FAIL'} {take['seconds']:5.1f}s after {len(takes)} take(s)"
              + (f"  wrong={take['wrong']}" if not passed else ""), flush=True)
    (out / "result.json").write_text(json.dumps({
        "units": units, "versions": s.versions if s else {"model": MODEL, "asr": ASR_MODEL, "note": "all units cached"}, "sample_rate": SR,
        "timing": {"load_s": round(load_s, 1), "synth_s": round(synth_s, 1), "audio_s": round(audio_s, 1),
                   "rtf": round(synth_s / audio_s, 3) if audio_s else None, "takes": takes_total,
                   "wall_s": round(time.time() - t0, 1),
                   "vram_peak_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
