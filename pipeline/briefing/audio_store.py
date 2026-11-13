"""Daily and Weekly MP3s out of git: a release store plus a hashed manifest (P2-2, rev 85).

688 MB of the repository's 743 MB pack is MP3 (67 blobs), and every On Air
episode (6 to 11 MB) and Weekly episode (11 to 22 MB) adds to it forever: git
keeps every byte of every render. History audio already left git for a GitHub
Release that the deploy pulls into the publish directory
(`pipeline/history/release_store.py`, read its header for why a release is a
STORE and never a CDN: iOS Safari will not play a release asset in place).
This is the same pattern for `frontend/public/audio/world/` (On Air) and
`frontend/public/audio/weekly-*/` (The Argument).

    VOID_AUDIO_STORE=git       (default) MP3s are written into the tree and committed
                               exactly as before. This module does nothing.
    VOID_AUDIO_STORE=release   every MP3 `_write_audio_static` writes is ALSO uploaded
                               to the release `<edition>-audio` and recorded in
                               frontend/public/data/audio-store.json with its URL,
                               size and SHA-256. The tree copy is what the rest of
                               the run reads (podcast feed, sidecar checks); once
                               the switch-over in docs/proposals/AUDIO-OUT-OF-GIT.md
                               makes those paths untracked, git never sees it.

The deploy side is `python -m pipeline.briefing.audio_store fetch --out DIR`:
every file the manifest lists is downloaded, its SHA-256 checked against the
manifest, and the deploy FAILS on a miss or a mismatch, because a Listen button
that 404s, or plays yesterday, is worse than a deploy that does not happen.

The default is OFF because the switch needs a workflow change in the same
breath (the deploy must fetch before it uploads, the pipeline needs a token
that can write releases, and the committed MP3s must leave the index). Turning
it on alone would only add an upload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "frontend" / "public" / "data" / "audio-store.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "aacrit/void--news")
MODES = ("git", "release")


def mode() -> str:
    m = (os.environ.get("VOID_AUDIO_STORE") or "git").strip().lower()
    return m if m in MODES else "git"


def enabled() -> bool:
    return mode() == "release"


def tag_for(edition: str) -> str:
    """One release per programme: `world-audio`, `weekly-world-audio`."""
    return f"{edition}-audio"


def asset_for(edition: str, filename: str) -> str:
    return f"{edition}--{filename}"


def url_for(edition: str, filename: str) -> str:
    return (f"https://github.com/{REPO}/releases/download/"
            f"{tag_for(edition)}/{asset_for(edition, filename)}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

def load(path: Path | None = None) -> dict:
    path = path or MANIFEST
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("files"), dict):
            data.setdefault("aliases", {})
            return data
    except (OSError, ValueError):
        pass
    return {"version": 1, "files": {}, "aliases": {}}


def save(manifest: dict, path: Path | None = None) -> None:
    path = path or MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# The store (a GitHub Release). Injected in tests.
# ---------------------------------------------------------------------------

def _github_upload(edition: str, filename: str, data: bytes) -> None:
    """Upload one asset, replacing a same-named one. Needs GITHUB_TOKEN."""
    try:
        from history.release_store import _req, UPLOADS, API
    except ImportError:
        from pipeline.history.release_store import _req, UPLOADS, API  # type: ignore
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to store audio in a release")
    tag = tag_for(edition)
    try:
        rel = _req(f"{API}/releases/tags/{tag}", token=token)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        rel = _req(f"{API}/releases", method="POST", ctype="application/json", token=token,
                   data=json.dumps({
                       "tag_name": tag, "name": f"Void News audio: {edition}",
                       "body": ("Rendered episodes. A STORE, not a CDN: the deploy pulls these "
                                "into the published site; readers never fetch them from here."),
                       "draft": False, "prerelease": False}).encode())
    name = asset_for(edition, filename)
    for a in rel.get("assets", []):
        if a.get("name") == name:
            _req(f"{API}/releases/assets/{a['id']}", method="DELETE", token=token)
    _req(f"{UPLOADS}/releases/{rel['id']}/assets?name={name}", method="POST",
         data=data, ctype="audio/mpeg", token=token, raw=True)


def _github_delete(edition: str, filename: str) -> None:
    try:
        from history.release_store import _req, API
    except ImportError:
        from pipeline.history.release_store import _req, API  # type: ignore
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return
    rel = _req(f"{API}/releases/tags/{tag_for(edition)}", token=token)
    for a in rel.get("assets", []):
        if a.get("name") == asset_for(edition, filename):
            _req(f"{API}/releases/assets/{a['id']}", method="DELETE", token=token)


Uploader = Callable[[str, str, bytes], None]
Deleter = Callable[[str, str], None]


def record(edition: str, filename: str, data: bytes, *, alias: str | None = "latest.mp3",
           uploader: Optional[Uploader] = None, manifest_path: Path | None = None) -> dict:
    """Store one rendered MP3 and record it. Raises when the upload fails: an
    episode that is not in the store will not be deployed, so the caller must
    not publish a URL to it."""
    (uploader or _github_upload)(edition, filename, data)
    m = load(manifest_path)
    key = f"{edition}/{filename}"
    entry = {"edition": edition, "tag": tag_for(edition), "asset": asset_for(edition, filename),
             "url": url_for(edition, filename), "sha256": sha256(data), "bytes": len(data),
             "storedAt": datetime.now(timezone.utc).isoformat()}
    m["files"][key] = entry
    if alias:
        m["aliases"][f"{edition}/{alias}"] = key
    save(m, manifest_path)
    return entry


def prune(edition: str, keep: set[str], *, deleter: Optional[Deleter] = None,
          manifest_path: Path | None = None) -> list[str]:
    """Drop manifest entries (and release assets) for this edition's files that
    the tree's rotation removed. `keep` is the set of filenames still served."""
    m = load(manifest_path)
    gone = [k for k, e in m["files"].items()
            if e.get("edition") == edition and k.split("/", 1)[1] not in keep]
    for k in gone:
        try:
            (deleter or _github_delete)(edition, k.split("/", 1)[1])
        except Exception as e:  # pragma: no cover - best effort, the manifest is the truth
            print(f"  [audio-store] could not delete {k} from the release: {e}")
        m["files"].pop(k, None)
    m["aliases"] = {a: t for a, t in m["aliases"].items() if t in m["files"]}
    if gone:
        save(m, manifest_path)
    return gone


# ---------------------------------------------------------------------------
# Materialize: the deploy's half, and the run's own back-catalogue
# ---------------------------------------------------------------------------

def _download(url: str) -> bytes:
    last: Exception | None = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:   # follows the signed redirect
                return r.read()
        except (urllib.error.URLError, OSError) as e:
            last = e
    raise RuntimeError(f"download failed: {url}: {last}")


def materialize(out_root: Path, edition: str | None = None, *,
                fetcher: Callable[[str], bytes] = _download,
                manifest_path: Path | None = None) -> list[str]:
    """Write every manifest file (and alias) under out_root/<edition>/<name>,
    each checked against its SHA-256. A file already present with the right
    hash is left alone. Returns the problems; empty means complete."""
    m = load(manifest_path)
    problems: list[str] = []
    cache: dict[str, bytes] = {}
    targets = [(k, k) for k in m["files"]] + list(m["aliases"].items())
    for path, key in targets:
        e = m["files"].get(key)
        if not e or (edition and e.get("edition") != edition):
            continue
        dest = Path(out_root) / path
        if dest.exists() and sha256(dest.read_bytes()) == e["sha256"]:
            continue
        try:
            data = cache.get(key) or fetcher(e["url"])
        except Exception as ex:
            problems.append(f"{path}: {ex}")
            continue
        if sha256(data) != e["sha256"]:
            problems.append(f"{path}: SHA-256 mismatch (store has {sha256(data)[:12]}, "
                            f"manifest says {e['sha256'][:12]})")
            continue
        cache[key] = data
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as fh:
            fh.write(data)
        Path(fh.name).replace(dest)
    return problems


def verify(root: Path, manifest_path: Path | None = None) -> list[str]:
    """Every manifest file present under root with its recorded hash."""
    m = load(manifest_path)
    out = []
    for path, key in [(k, k) for k in m["files"]] + list(m["aliases"].items()):
        e = m["files"].get(key)
        if not e:
            out.append(f"{path}: alias to a file the manifest does not hold")
            continue
        f = Path(root) / path
        if not f.exists():
            out.append(f"{path}: missing")
        elif sha256(f.read_bytes()) != e["sha256"]:
            out.append(f"{path}: SHA-256 differs from the manifest")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Daily and Weekly audio release store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    fe = sub.add_parser("fetch", help="pull every manifest file into DIR, hash-checked")
    fe.add_argument("--out", required=True)
    fe.add_argument("--edition")
    ve = sub.add_parser("verify", help="check DIR against the manifest")
    ve.add_argument("--root", required=True)
    a = ap.parse_args()
    if a.cmd == "fetch":
        probs = materialize(Path(a.out), a.edition)
        n = len(load()["files"])
        if probs:
            print("error: audio in the manifest is not in the store:", file=sys.stderr)
            for p in probs:
                print(f"  - {p}", file=sys.stderr)
            return 1
        print(f"  [audio-store] {n} file(s) ready under {a.out}")
        return 0
    probs = verify(Path(a.root))
    for p in probs:
        print(f"  - {p}", file=sys.stderr)
    return 1 if probs else 0


if __name__ == "__main__":
    raise SystemExit(main())
