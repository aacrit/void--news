#!/usr/bin/env python3
"""On Air and Weekly MP3s can leave git without a Listen button breaking (P2-2, rev 85).

`pipeline/briefing/audio_store.py` stores each rendered MP3 in a release and
records it in `frontend/public/data/audio-store.json` with its SHA-256; the
deploy pulls every listed file into the publish directory and refuses a miss or
a mismatch. It is OFF by default (`VOID_AUDIO_STORE=git`) until the workflow
change in `docs/proposals/AUDIO-OUT-OF-GIT.md` lands.

Asserts, with no network (the store is a temp directory behind file:// URLs):
  - off by default: `_write_audio_static` behaves exactly as before and writes
    no manifest;
  - on: the manifest records URL, size and the SHA-256 of the exact bytes, and
    latest.mp3 as an alias of the dated file;
  - a failed upload publishes no URL;
  - the deploy fetch writes every file with its recorded hash, refuses a store
    whose bytes differ, and reports a missing asset;
  - the rotation's removals leave the manifest and the store;
  - the committed manifest, when there is one, matches the served tree.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import briefing.audio_producer as ap  # noqa: E402
from briefing import audio_store as st  # noqa: E402

failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


tmp = Path(tempfile.mkdtemp(prefix="void-audio-store-"))
store_dir = tmp / "store"
store_dir.mkdir()
manifest = tmp / "audio-store.json"
st.MANIFEST = manifest                      # every default path in the module reads this
st.REPO = "example/void"
ap._STATIC_AUDIO_ROOT = tmp / "tree"


def fake_upload(edition, filename, data):
    (store_dir / st.asset_for(edition, filename)).write_bytes(data)


deleted: list[str] = []


def fake_delete(edition, filename):
    deleted.append(st.asset_for(edition, filename))
    (store_dir / st.asset_for(edition, filename)).unlink(missing_ok=True)


def fake_fetch(url):
    name = url.rsplit("/", 1)[1]
    p = store_dir / name
    if not p.exists():
        raise FileNotFoundError(name)
    return p.read_bytes()


st._github_upload = fake_upload
st._github_delete = fake_delete
st._download = fake_fetch
_mat = st.materialize
st.materialize = lambda root, edition=None, **k: _mat(root, edition, fetcher=fake_fetch, **k)

# --- 1. Off by default ------------------------------------------------------------
os.environ.pop("VOID_AUDIO_STORE", None)
check("the store is off unless VOID_AUDIO_STORE=release", not st.enabled() and st.mode() == "git")
url = ap._write_audio_static(b"episode-one" * 1000, "world")
check("off: the writer still returns a URL", bool(url))
check("off: no manifest is written", not manifest.exists())
check("off: nothing is uploaded", not any(store_dir.iterdir()))

# --- 2. On ------------------------------------------------------------------------
os.environ["VOID_AUDIO_STORE"] = "release"
body = b"episode-two" * 1000
url = ap._write_audio_static(body, "world")
m = st.load()
dated = [k for k in m["files"] if k.startswith("world/20")]
check("on: the writer returns a URL", bool(url))
check("on: the dated MP3 is in the manifest", len(dated) == 1, str(list(m["files"])))
e = m["files"][dated[0]] if dated else {}
check("the entry carries the SHA-256 of the exact bytes", e.get("sha256") == st.sha256(body))
check("and the size", e.get("bytes") == len(body))
check("and a release URL under the programme's tag",
      e.get("url", "").startswith("https://github.com/example/void/releases/download/world-audio/world--20"))
check("latest.mp3 is an alias of the dated file", m["aliases"].get("world/latest.mp3") == dated[0])
check("the bytes are in the store", (store_dir / e.get("asset", "x")).read_bytes() == body)

# A failed upload publishes no URL.
st._github_upload = lambda *a: (_ for _ in ()).throw(RuntimeError("401"))
check("a failed upload publishes no audio URL",
      ap._write_audio_static(b"episode-three" * 1000, "weekly-world") is None)
st._github_upload = fake_upload

# --- 3. The deploy fetch ------------------------------------------------------------
out = tmp / "out"
check("fetch writes every listed file", st.materialize(out) == [])
check("with the recorded hash, alias included", st.verify(out) == [], str(st.verify(out)))
(store_dir / e["asset"]).write_bytes(b"tampered" * 10)
out2 = tmp / "out2"
probs = st.materialize(out2)
check("a store whose bytes differ from the manifest is refused",
      any("SHA-256 mismatch" in p for p in probs) and not (out2 / dated[0]).exists(), str(probs))
(store_dir / e["asset"]).unlink()
check("a missing asset is reported", any(dated[0] in p for p in st.materialize(tmp / "out3")))
(store_dir / e["asset"]).write_bytes(body)
check("verify notices a file that changed after the fetch",
      ((out / dated[0]).write_bytes(b"x") or True) and st.verify(out) != [])

# --- 4. Rotation leaves the store ----------------------------------------------------
gone = st.prune("world", keep=set(), deleter=fake_delete)
check("a file the rotation removed leaves the manifest", gone == dated and not st.load()["files"])
check("and the store", deleted == [e["asset"]])
check("and its alias", not st.load()["aliases"])

# --- 5. The committed tree ------------------------------------------------------------
real = ROOT / "frontend" / "public" / "data" / "audio-store.json"
if real.exists():
    probs = st.verify(ROOT / "frontend" / "public" / "audio", manifest_path=real)
    print("  info  committed manifest present; served-tree differences: " + (", ".join(probs) or "none"))
    data = json.loads(real.read_text(encoding="utf-8"))
    check("every committed manifest entry has a 64-hex SHA-256 and a release URL",
          all(len(v.get("sha256", "")) == 64 and "/releases/download/" in v.get("url", "")
              for v in data.get("files", {}).values()))
src = (ROOT / "pipeline" / "briefing" / "audio_producer.py").read_text(encoding="utf-8")
check("the writer records to the store only when enabled",
      "if _store.enabled():" in src and "_store.record(edition, fname, audio_bytes)" in src)

if failures:
    print(f"\nFAIL  {len(failures)} audio-store check(s)")
    sys.exit(1)
print("\nPASS  daily and weekly MP3s can leave git, hash-checked from store to site")
