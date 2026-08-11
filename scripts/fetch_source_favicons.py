#!/usr/bin/env python3
"""Fetch and self-host outlet favicons for the Deep Dive source portal.

Void News never hotlinks a third-party favicon service at READ time (that would
leak each reader's IP and which outlet they are viewing). Instead we fetch each
source's favicon ONCE here, at build time, on our own machine, and commit the
tiny icons as first-party static assets under frontend/public/logos/. The site
then serves them from its own origin. Showing an outlet's mark to identify that
outlet is nominative use (the same thing Ground News / Google News / Techmeme
do); these are small brand identifiers, attributed to the source they label.

Output:
  frontend/public/logos/<slug>.png         one 64px icon per source that resolved
  frontend/app/lib/sourceLogos.json        { normalized source name: "<slug>" }

Idempotent: existing icons are skipped, so re-runs only fill gaps. Misses simply
fall back to the lean-colored letter monogram in the UI, so a failed fetch is
never fatal.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "data", "sources.json")
LOGO_DIR = os.path.join(ROOT, "frontend", "public", "logos")
MANIFEST = os.path.join(ROOT, "frontend", "app", "lib", "sourceLogos.json")

UA = "Mozilla/5.0 (compatible; VoidNewsFaviconFetch/1.0; +https://news.voidvision.org)"


def normalize_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def domain_of(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def slug_of(domain: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", domain).strip("-")


def fetch_icon(domain: str, dest: str) -> bool:
    """Fetch a 64px favicon for `domain` to `dest`. Returns True on a real icon.

    Uses Google's favicon service at build time (server-side, not reader-side, so
    no reader privacy leak). Rejects the tiny default globe by size heuristic.
    """
    url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=12) as resp:
            data = resp.read()
    except Exception:
        return False
    # Google returns a ~16px default globe (a few hundred bytes) for unknown
    # domains; a real 64px icon is meaningfully larger. Drop the obvious defaults.
    if not data or len(data) < 500:
        return False
    try:
        with open(dest, "wb") as fh:
            fh.write(data)
    except Exception:
        return False
    return True


def main() -> int:
    os.makedirs(LOGO_DIR, exist_ok=True)
    with open(SOURCES, encoding="utf-8") as fh:
        sources = json.load(fh)

    # De-dupe by slug so shared domains fetch once; keep every name -> slug link.
    name_to_slug: dict[str, str] = {}
    slug_to_domain: dict[str, str] = {}
    for s in sources:
        name = s.get("name")
        dom = domain_of(s.get("url") or "")
        if not name or not dom:
            continue
        slug = slug_of(dom)
        if not slug:
            continue
        name_to_slug[normalize_name(name)] = slug
        slug_to_domain.setdefault(slug, dom)

    todo = [
        (slug, dom)
        for slug, dom in slug_to_domain.items()
        if not os.path.exists(os.path.join(LOGO_DIR, f"{slug}.png"))
    ]
    print(f"{len(slug_to_domain)} distinct domains, {len(todo)} to fetch")

    ok_slugs: set[str] = {
        slug for slug in slug_to_domain
        if os.path.exists(os.path.join(LOGO_DIR, f"{slug}.png"))
    }
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = {
            pool.submit(fetch_icon, dom, os.path.join(LOGO_DIR, f"{slug}.png")): slug
            for slug, dom in todo
        }
        done = 0
        for fut in as_completed(futs):
            slug = futs[fut]
            if fut.result():
                ok_slugs.add(slug)
            done += 1
            if done % 100 == 0:
                print(f"  fetched {done}/{len(todo)}")

    # Manifest: normalized name -> slug, but ONLY where the icon actually landed.
    manifest = {
        name: slug for name, slug in name_to_slug.items() if slug in ok_slugs
    }
    manifest = dict(sorted(manifest.items()))
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=0)
        fh.write("\n")

    print(f"resolved {len(ok_slugs)} icons; manifest has {len(manifest)} names -> {MANIFEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
