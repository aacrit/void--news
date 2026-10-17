"""One-time: write a bfloat16 copy of Orpheus 3B beside the HF cache.

The published weights are float32 (15.1 GB in four shards) while the model
runs in bfloat16 on the GPU (about 7.5 GB). Loading the float32 shards read
all 15 GB through the page cache, and under WSL2 that cache is RAM the VM
keeps from Windows: the 2026-10-03 Partition renders pushed the WSL VM to
22 GB and the host to under 2 GB free, which hung the machine once and had
the render reaped three times. This converts shard by shard, one tensor at a
time, and tells the kernel to drop each file from the cache as it goes
(posix_fadvise DONTNEED, no root needed), so peak memory stays at about one
output shard. Weights are cast, not changed: the GPU path already cast them
to bfloat16 at load.

    python pipeline/briefing/orpheus_bf16.py [--out ~/models/orpheus-3b-0.1-ft-bf16]

Then VOID_ORPHEUS_MODEL=<out> (tts_orpheus_worker.py prefers it when present).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO = "canopylabs/orpheus-3b-0.1-ft"
DEFAULT_OUT = Path.home() / "models" / "orpheus-3b-0.1-ft-bf16"


def drop_cache(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
        try:
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)
    except (OSError, AttributeError):
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    import torch
    from huggingface_hub import snapshot_download
    from safetensors import safe_open
    from safetensors.torch import save_file

    # The weights already downloaded for the audition: never fetch the rest
    # of the repo (it holds other large artefacts).
    src = Path(snapshot_download(REPO, local_files_only=True,
                                 allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model"]))
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    shards = sorted(src.glob("model-*.safetensors"))
    if not shards:
        print(f"no shards in {src}")
        return 1
    weight_map = {}
    for shard in shards:
        dst = out / shard.name
        tensors = {}
        with safe_open(str(shard), framework="pt") as f:
            for k in f.keys():
                t = f.get_tensor(k)
                tensors[k] = t.to(torch.bfloat16) if t.is_floating_point() else t
                weight_map[k] = shard.name
        save_file(tensors, str(dst), metadata={"format": "pt"})
        del tensors
        drop_cache(shard)
        drop_cache(dst)
        print(f"  {shard.name}: {shard.stat().st_size / 1e9:.2f} GB -> {dst.stat().st_size / 1e9:.2f} GB", flush=True)
    total = sum((out / s.name).stat().st_size for s in shards)
    (out / "model.safetensors.index.json").write_text(json.dumps(
        {"metadata": {"total_size": total}, "weight_map": weight_map}, indent=1))
    for f in src.iterdir():
        if f.suffix in (".json", ".txt", ".model") and f.name != "model.safetensors.index.json":
            shutil.copy(f, out / f.name)
    cfg = json.loads((out / "config.json").read_text())
    cfg["torch_dtype"] = "bfloat16"
    (out / "config.json").write_text(json.dumps(cfg, indent=1))
    print(f"wrote {out} ({total / 1e9:.2f} GB, bfloat16) from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
