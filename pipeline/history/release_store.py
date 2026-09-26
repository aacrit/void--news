"""Keep the History audio out of git, without moving it off our own domain.

The catalogue is 78 finished documentaries, about 900 MB of MP3. Committing
that is a one-way door: git keeps every byte of every re-render forever, and
the repository's entire history before this project was 167 MB.

The obvious fix is to serve the audio from somewhere else. The obvious
somewhere else is a GitHub Release, which is free, durable and unlimited
enough on a public repo. But pointing a browser at a release asset is a trap,
and the probe is worth recording so nobody re-tries it: GitHub serves those
assets as `application/octet-stream`, behind a signed redirect that expires
in an hour, with `Content-Disposition: attachment`. Range requests do work
(HTTP 206), so seeking would be fine, but an <audio> element fed
octet-stream over a redirect chain is exactly the combination that plays in
Chrome and fails in iOS Safari. The iPhone is a primary surface here.

So the release is a STORE, not a CDN. The bytes live there between render and
deploy, and the deploy pulls them into the directory Cloudflare publishes.
The reader still fetches /audio/history/<slug>.mp3 from news.voidvision.org:
same origin, correct MIME from Pages, no redirect, no CORS. The manifest does
not change, the frontend does not change, and git never sees an MP3 again.

    python pipeline/history/release_store.py upload <file> [<file> ...]
    python pipeline/history/release_store.py fetch --out DIR

Needs GITHUB_TOKEN for upload. Fetch is public and needs nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = os.environ.get("GITHUB_REPOSITORY", "aacrit/void--news")
TAG = "history-audio"
API = f"https://api.github.com/repos/{REPO}"
UPLOADS = f"https://uploads.github.com/repos/{REPO}"


def _req(url: str, *, method="GET", data=None, ctype=None, token=None, raw=False):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if ctype:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return body if raw else json.loads(body or b"{}")


def _release(token: str | None, tag: str = TAG) -> dict:
    """The release that holds the catalogue (or, under another tag, the
    un-stitched masters), created on first use when a token is given."""
    try:
        return _req(f"{API}/releases/tags/{tag}", token=token)
    except urllib.error.HTTPError as e:
        if e.code != 404 or not token:
            raise
    body = json.dumps({
        "tag_name": tag,
        "name": "History audio editions" if tag == TAG else f"History audio ({tag})",
        "body": ("Rendered episodes of the Void News History audio edition.\n\n"
                 "This release is a STORE, not a CDN. The deploy workflow pulls "
                 "these files into the published directory; readers fetch them "
                 "from news.voidvision.org, same origin, never from here."),
        "draft": False, "prerelease": False,
    }).encode()
    return _req(f"{API}/releases", method="POST", data=body,
                ctype="application/json", token=token)


def has_asset(name: str, tag: str = TAG) -> bool:
    """Whether the release under `tag` carries an asset of that name. Public
    on a public repo, so no token is needed to ask."""
    try:
        rel = _release(os.environ.get("GITHUB_TOKEN"), tag)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
    return any(a.get("name") == name for a in rel.get("assets", []))


def upload(paths: list[Path], tag: str = TAG, replace: bool = True) -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN is required to upload", file=sys.stderr)
        return 1
    rel = _release(token, tag)
    existing = {a["name"]: a["id"] for a in rel.get("assets", [])}
    for p in paths:
        if not p.exists():
            print(f"  [skip] {p.name} does not exist")
            continue
        if p.name in existing and not replace:
            # The clean-master tag keeps its first copy forever.
            print(f"  [keep] {p.name} already under {tag}")
            continue
        data = p.read_bytes()
        if p.name in existing:
            # A re-render replaces the asset: same name, new bytes. Upload
            # under a temporary name first, then delete the old one and
            # rename, so a deploy fetching mid-replacement sees the name
            # missing for well under a second rather than for the whole
            # upload of a 14 MB file.
            tmp = f"{p.name}.incoming"
            for a in rel.get("assets", []):
                if a.get("name") == tmp:
                    _req(f"{API}/releases/assets/{a['id']}", method="DELETE", token=token)
            new = _req(f"{UPLOADS}/releases/{rel['id']}/assets?name={tmp}",
                       method="POST", data=data, ctype="audio/mpeg", token=token)
            _req(f"{API}/releases/assets/{existing[p.name]}", method="DELETE", token=token)
            _req(f"{API}/releases/assets/{new['id']}", method="PATCH",
                 data=json.dumps({"name": p.name}).encode(), ctype="application/json", token=token)
        else:
            _req(f"{UPLOADS}/releases/{rel['id']}/assets?name={p.name}",
                 method="POST", data=data, ctype="audio/mpeg", token=token, raw=True)
        print(f"  [store] {p.name} ({len(data)//1024} KB){'' if tag == TAG else f' under {tag}'}")
    return 0


def fetch(out_dir: Path, tag: str = TAG, slugs: list[str] | None = None) -> int:
    """Pull every episode the manifest claims (or just `slugs`) into the
    publish directory.

    Fails loudly on a miss. A deploy that quietly ships a site whose every
    Listen button 404s is worse than a deploy that does not happen.
    """
    manifest = json.loads((ROOT / "frontend" / "public" / "data"
                           / "history-audio.json").read_text())
    want = sorted(slugs) if slugs else sorted(manifest.get("episodes", {}))
    if not want:
        print("  [store] manifest lists no episodes, nothing to fetch")
        return 0
    out_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for slug in want:
        dest = out_dir / f"{slug}.mp3"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        url = f"https://github.com/{REPO}/releases/download/{tag}/{slug}.mp3"
        try:
            # curl follows the signed redirect and is already present on the
            # runner; urllib would need redirect handling for the same result.
            #
            # RETRIES, because one reset connection failed a whole deploy.
            # 45 of 49 episodes fetched and four came back with curl exit 35,
            # "Recv failure: Connection reset by peer", against a CDN serving
            # ~13 MB per file. There was no retry, so a single transient reset
            # took the site's deploy down with it and the three runs behind it
            # were skipped by concurrency, leaving production on a stale build
            # with nothing saying why.
            #
            # `--retry-all-errors` is the part that matters: plain `--retry`
            # does not cover a mid-transfer reset, which is exactly the error
            # seen here.
            subprocess.run(
                ["curl", "-sSfL", "--retry", "4", "--retry-delay", "2",
                 "--retry-all-errors", url, "-o", str(dest)],
                check=True,
            )
            size = dest.stat().st_size
            if size < 100_000:
                raise ValueError(f"{size} bytes is too small to be an episode")
            print(f"  [store] fetched {slug}.mp3 ({size//1024} KB)")
        except (subprocess.CalledProcessError, ValueError, OSError) as e:
            dest.unlink(missing_ok=True)
            missing.append(f"{slug} ({e})")
    if missing:
        print("error: episodes in the manifest are not in the store:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        if slugs:
            raise FileNotFoundError("; ".join(missing))
        return 1
    print(f"  [store] {len(want)} episode(s) ready in {out_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    up = sub.add_parser("upload"); up.add_argument("files", nargs="+")
    up.add_argument("--tag", default=TAG)
    fe = sub.add_parser("fetch"); fe.add_argument("--out", required=True)
    fe.add_argument("--tag", default=TAG)
    a = ap.parse_args()
    if a.cmd == "upload":
        return upload([Path(f) for f in a.files], tag=a.tag)
    return fetch(Path(a.out), tag=a.tag)


if __name__ == "__main__":
    raise SystemExit(main())
