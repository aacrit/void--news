"""Mirror History's verified Wikimedia images into R2.

Hotlinking Wikimedia works and is legal, and it has one weakness that shows up
exactly when the site gets read: upload.wikimedia.org rate-limits per client IP
and answers HTTP 429. Four images on one event page is fine; a crawler, a burst
of readers behind one NAT, or a hot link from elsewhere is not. This copies each
image once into a bucket Void controls and rewrites the urls to point there.

Re-hosting these is legal precisely because of the work already done:
resolve_commons.py refuses anything Wikimedia does not report as public domain
or permissive Creative Commons, so every file here is one Void may redistribute.
What it may not do is drop the credit, and it does not: the author and licence
stay on the record and keep rendering under the picture. That is the licence
condition for CC BY and CC BY-SA, not a courtesy.

Keys are content-addressed (sha1 of the bytes), so re-running this uploads only
what actually changed and every url can be cached for a year with no purge.

    python -m pipeline.history.mirror_images              # upload what is missing
    python -m pipeline.history.mirror_images --dry-run    # list, touch nothing
    python -m pipeline.history.mirror_images --recheck    # re-verify stored keys

Writes the R2 url back into each record in data/history/commons_media.json as
`cdn`. export_history.py prefers `cdn` and falls back to the Wikimedia url, so
this is reversible by deleting the field and is a no-op until R2 is configured.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO / "pipeline"))

from utils import media  # noqa: E402

CACHE = REPO / "data" / "history" / "commons_media.json"
UA = "VoidNewsHistory/1.0 (https://news.voidvision.org; aacrit@gmail.com)"

EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/tiff": ".jpg",   # Commons renders a tiff thumbnail as jpeg
}


def download(url: str, tries: int = 4) -> tuple[bytes, str] | None:
    """Fetch an image, retrying through Wikimedia's throttle.

    A 429 here is the very problem this script exists to remove, so it must not
    be mistaken for a missing file: a throttled fetch that got recorded as a
    failure would drop a real picture off the site.
    """
    delay = 5.0
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read(), (resp.headers.get("Content-Type") or "").split(";")[0]
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or attempt == tries - 1:
                print(f"    HTTP {e.code}")
                return None
            print(f"    throttled ({e.code}); waiting {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
        except Exception as e:
            print(f"    {type(e).__name__}: {e}")
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be uploaded, change nothing")
    ap.add_argument("--recheck", action="store_true",
                    help="re-verify that each stored key is really in the bucket")
    ap.add_argument("--limit", type=int, default=0, help="stop after N uploads")
    args = ap.parse_args()

    if not CACHE.exists():
        print("no commons_media.json; run pipeline.history.resolve_commons first")
        return 1

    if not args.dry_run and not media.enabled():
        print(media.describe())
        print("Refusing to rewrite urls with no bucket to put the bytes in.")
        print("Set VOID_MEDIA_BASE and the R2_* variables, or pass --dry-run.")
        return 2

    print(media.describe())
    cache = json.loads(CACHE.read_text(encoding="utf-8"))
    files: dict = cache.get("files") or {}
    backfill: dict = cache.get("backfill") or {}

    # Every record carrying an image url, from both halves of the catalogue.
    records: list[tuple[str, dict]] = [(name, rec) for name, rec in files.items()]
    for slug, items in backfill.items():
        for rec in items:
            records.append((f"{slug}:{rec.get('name', '?')}", rec))

    uploaded = skipped = failed = 0
    for label, rec in records:
        src = rec.get("url")
        if not src:
            continue
        if rec.get("cdn") and not args.recheck:
            skipped += 1
            continue
        if args.recheck and rec.get("cdn") and rec.get("key") and media.exists(rec["key"]):
            skipped += 1
            continue
        if args.limit and uploaded >= args.limit:
            break

        if args.dry_run:
            print(f"  would mirror {label[:56]}")
            uploaded += 1
            continue

        print(f"  {label[:56]}")
        got = download(src)
        if not got:
            failed += 1
            continue
        data, mime = got
        if not mime.startswith("image/"):
            print(f"    not an image ({mime or 'no content-type'})")
            failed += 1
            continue

        key = media.image_key(data, EXT_BY_MIME.get(mime, ".jpg"))
        try:
            # skip_if_present is free correctness here: the key IS the bytes, so
            # an object already at that key is already this exact image.
            cdn = media.put(key, data, mime,
                            cache_control=media.IMMUTABLE, skip_if_present=True)
        except Exception as e:
            print(f"    upload failed: {type(e).__name__}: {e}")
            failed += 1
            continue

        rec["cdn"] = cdn
        rec["key"] = key
        rec["bytes"] = len(data)
        uploaded += 1
        print(f"    -> {key}  ({len(data) // 1024} KB)")

    if not args.dry_run:
        CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False),
                         encoding="utf-8")

    total_mb = sum(r.get("bytes", 0) for _, r in records) / (1024 * 1024)
    print(f"\nmirrored {uploaded}, already present {skipped}, failed {failed}"
          f"  ({total_mb:.0f} MB recorded)")
    if failed:
        print("A failure leaves that image on its Wikimedia url, which still works.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
