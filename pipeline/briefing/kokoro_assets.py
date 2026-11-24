"""Kokoro model files: pinned release, download on miss, sha256 verified.

The int8 ONNX model (~88 MB) and the voice bank (~27 MB) come from the
kokoro-onnx GitHub release named in kokoro.lock.json. They are cached under
VOID_KOKORO_MODEL_DIR (default ~/.cache/void-kokoro/<release>), which the
workflows cache between runs keyed on the release name.

    python -m briefing.kokoro_assets      # fetch + verify, print paths

Stdlib only (urllib, hashlib) so it runs in either interpreter.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

LOCK_PATH = Path(__file__).parent / "kokoro.lock.json"


def _lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def model_dir() -> Path:
    env = os.environ.get("VOID_KOKORO_MODEL_DIR", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "void-kokoro" / _lock()["release"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_model_files(quiet: bool = False) -> tuple[Path, Path]:
    """Return (model_path, voices_path); download + verify on a miss.

    Raises RuntimeError on a checksum mismatch: a corrupted or substituted
    model must never be loaded silently.
    """
    lock = _lock()
    d = model_dir()
    d.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for entry in lock["files"]:
        target = d / entry["name"]
        if not target.exists() or target.stat().st_size != int(entry.get("size") or target.stat().st_size):
            if not quiet:
                print(f"  [kokoro] downloading {entry['name']} ...")
            tmp = target.with_suffix(target.suffix + ".part")
            with urllib.request.urlopen(entry["url"], timeout=120) as r, tmp.open("wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.replace(target)
        digest = _sha256(target)
        if entry.get("sha256") and digest != entry["sha256"]:
            target.unlink(missing_ok=True)
            raise RuntimeError(
                f"kokoro asset {entry['name']} sha256 {digest[:12]} != pinned {entry['sha256'][:12]}")
        paths[entry["role"]] = target
    return paths["model"], paths["voices"]


if __name__ == "__main__":
    try:
        m, v = ensure_model_files()
        print(f"model:  {m}\nvoices: {v}")
    except Exception as e:
        print(f"[kokoro] {e}", file=sys.stderr)
        sys.exit(1)
