"""Resolve every History image to a canonical Wikimedia CDN url and a verified licence.

The event YAML records where an image CAME FROM, which is a Commons `File:` page
or an `upload.wikimedia.org` path. Neither is what a browser should be pointed
at:

  * `commons.wikimedia.org/wiki/Special:Redirect/file/<name>` (what the frontend
    built from a File: page) is a MediaWiki special page, not a CDN path.
    Wikimedia answers it with HTTP 429 under any real traffic, which is why the
    History pages rendered with no pictures at all.
  * The bare `upload.wikimedia.org/.../<name>` path serves the ORIGINAL, which
    for this catalogue runs to several megabytes an image.
  * Arbitrary thumbnail widths are refused ("Use thumbnail sizes listed on
    https://w.wiki/GHai"), so a width cannot simply be invented either.

So the width and the url are asked for, not guessed. This queries the Commons
API in batches and records, per file, the thumbnail url it hands back plus the
licence and author it reports. The licence is the POINT: the YAML's own
`license` field is a curator's note, while this is Commons' answer, and anything
that is not public domain or a permissive Creative Commons licence is refused
here rather than trusted downstream. Six YAML entries are marked `fair-use`
(Napalm Girl, Tank Man, Hector Pieterson among them) and one of those is not
hosted on Commons at all; both facts show up as a refusal.

Output: data/history/commons_media.json, committed. `export_history.py` reads it
and drops any image it cannot find there, so a resolution failure removes a
picture rather than shipping a broken one. Run it when the event YAML changes:

    python -m pipeline.history.resolve_commons            # only unresolved files
    python -m pipeline.history.resolve_commons --refresh  # re-query everything
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
EVENTS = REPO / "data" / "history" / "events"
CACHE = REPO / "data" / "history" / "commons_media.json"

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks for a descriptive agent that identifies the client and a way to
# reach its operator; an anonymous or generic one gets throttled fastest.
UA = "VoidNewsHistory/1.0 (https://news.voidvision.org; aacrit@gmail.com)"

# Commons serves a fixed set of thumbnail widths. 1280 covers the hero at
# retina width on a laptop; anything already narrower comes back as the
# original, which is correct rather than upscaled.
THUMB_WIDTH = 1280

BATCH = 40          # API allows 50 titles per query; 40 leaves headroom
PAUSE_SECONDS = 1.0  # deliberate: this is a build step, not a hot path

# Only these reach the site. Everything else, including `fair-use`, is refused.
FREE_LICENCES = (
    "public domain", "publicdomain", "pd-", "cc0", "cc-zero",
    "cc by", "cc-by", "attribution",
)
# Matched BEFORE the permissive list: "CC BY-NC" contains "cc by".
NONFREE_MARKERS = ("-nc", " nc-", "noncommercial", "non-commercial", "-nd", " nd-",
                   "noderiv", "fair use", "fair-use", "nonfree", "non-free")


def commons_filename(url: str) -> str | None:
    """The Commons file name behind a source url, or None if it is not Commons.

    Handles both shapes the YAML carries: a File: page and a direct upload path
    (including a /thumb/ path, whose last segment is a rendered size rather than
    the file).
    """
    u = str(url or "")
    if u.startswith("https://commons.wikimedia.org/wiki/File:"):
        return urllib.parse.unquote(u.split("/wiki/File:", 1)[1]).replace(" ", "_")
    if u.startswith("https://upload.wikimedia.org/"):
        parts = [p for p in urllib.parse.urlparse(u).path.split("/") if p]
        if "thumb" in parts:
            # .../thumb/a/ab/Name.jpg/800px-Name.jpg -> Name.jpg
            i = parts.index("thumb")
            if len(parts) > i + 3:
                return urllib.parse.unquote(parts[i + 3]).replace(" ", "_")
            return None
        return urllib.parse.unquote(parts[-1]).replace(" ", "_") if parts else None
    return None


def is_free(licence: str) -> bool:
    lic = (licence or "").strip().lower()
    if not lic:
        return False
    if any(m in lic for m in NONFREE_MARKERS):
        return False
    return any(m in lic for m in FREE_LICENCES)


def collect_filenames() -> dict[str, set[str]]:
    """Every Commons file the catalogue references, mapped to the slugs using it."""
    used: dict[str, set[str]] = {}
    for path in sorted(EVENTS.glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        slug = doc.get("slug") or path.stem
        urls = [m.get("source_url") for m in (doc.get("media") or [])]
        urls.append(doc.get("hero_image_url"))
        for url in urls:
            name = commons_filename(url)
            if name:
                used.setdefault(name, set()).add(slug)
    return used


def _get(params: dict) -> dict:
    """One API call, retrying through the throttle.

    A 429 must never be mistaken for an answer: the whole point of this file is
    that a refusal deletes a picture, so a throttled request that got recorded
    as "not hosted on Commons" would quietly strip real images off the site.
    """
    url = API + "?" + urllib.parse.urlencode(params)
    delay = 5.0
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
            if attempt == 5:
                raise
            print(f"    throttled ({e.code}); waiting {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def query(names: list[str]) -> dict:
    return _get({
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": str(THUMB_WIDTH),
        "titles": "|".join(f"File:{n}" for n in names),
    })


def search(term: str, limit: int = 8) -> list[str]:
    """Commons file names matching a search term, best first."""
    data = _get({
        "action": "query", "format": "json", "formatversion": "2",
        "list": "search", "srsearch": term, "srnamespace": "6", "srlimit": str(limit),
    })
    out = []
    for hit in data.get("query", {}).get("search", []) or []:
        title = str(hit.get("title", ""))
        if title.startswith("File:"):
            out.append(title.split("File:", 1)[1].replace(" ", "_"))
    return out


def resolve(names: list[str]) -> tuple[dict, list[tuple[str, str]]]:
    resolved: dict[str, dict] = {}
    refused: list[tuple[str, str]] = []

    for i in range(0, len(names), BATCH):
        chunk = names[i:i + BATCH]
        try:
            data = query(chunk)
        except Exception as e:  # a failed batch refuses its files, never invents one
            for n in chunk:
                refused.append((n, f"api error: {type(e).__name__}"))
            print(f"  [warn] batch {i // BATCH + 1} failed: {e}")
            time.sleep(PAUSE_SECONDS * 3)
            continue

        for page in data.get("query", {}).get("pages", []) or []:
            title = str(page.get("title", ""))
            name = title.split("File:", 1)[-1].replace(" ", "_")
            if page.get("missing") is not None or not page.get("imageinfo"):
                refused.append((name, "not hosted on Wikimedia Commons"))
                continue
            info = page["imageinfo"][0]
            ext = info.get("extmetadata") or {}
            licence = (ext.get("LicenseShortName") or {}).get("value", "")
            if not is_free(licence):
                refused.append((name, f"licence not free: {licence or 'unknown'}"))
                continue
            url = info.get("thumburl") or info.get("url")
            if not url:
                refused.append((name, "no url returned"))
                continue
            artist = (ext.get("Artist") or {}).get("value", "")
            # Artist arrives as HTML (it is a wiki field); keep the text only.
            artist = _strip_html(artist)
            resolved[name] = {
                "url": url,
                "width": info.get("thumbwidth") or info.get("width"),
                "height": info.get("thumbheight") or info.get("height"),
                "mime": info.get("mime"),
                "licence": licence,
                "artist": artist,
                "descriptionurl": info.get("descriptionurl"),
            }

        got = sum(1 for n in chunk if n in resolved)
        print(f"  batch {i // BATCH + 1}: {got}/{len(chunk)} resolved")
        time.sleep(PAUSE_SECONDS)

    # A title the API never mentioned (normalised away, or dropped) is refused.
    for n in names:
        if n not in resolved and not any(r[0] == n for r in refused):
            refused.append((n, "no response for this title"))
    return resolved, refused


def _strip_html(value: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", "", value or "")
    return " ".join(text.split()).strip()


def event_search_terms(doc: dict, commons: dict) -> list[str]:
    """What to search Commons for, when an event is short of pictures.

    The unresolved media entries are the best terms available: a curator wrote
    "Sikhs migrating to India, September 1947" describing the picture they
    wanted, and that is a far better query than the event title. The title is
    the fallback, and the subject line is dropped because it is written to be
    evocative rather than descriptive.
    """
    # The event title goes FIRST. It is the one term guaranteed to name the
    # subject, and putting it last meant it was cut off by the term limit on
    # events with several unresolved pictures: searching Tiananmen by its
    # curated captions ("Tank Man, Chang'an Avenue, June 5, 1989") returned a
    # California ghost town, while searching "Tiananmen Square" returns the
    # square.
    terms = [(doc.get("title") or "").strip()]
    for m in doc.get("media") or []:
        name = commons_filename(m.get("source_url"))
        if name and name in commons:
            continue  # this one already resolved
        title = (m.get("title") or "").strip()
        if title and len(title) > 6:
            terms.append(title)
    seen, out = set(), []
    for t in terms:
        k = t.lower()
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out


def verify_names(names: list[str]) -> dict:
    """imageinfo for candidate file names, keeping only free-licensed ones."""
    resolved, _ = resolve(names)
    return resolved


# Words that make a title a title rather than a subject a photograph can show.
_ANCHOR_STOP = {
    "the", "of", "and", "a", "an", "in", "on", "at", "to", "for",
    "war", "era", "age", "empire", "great", "first", "second", "new",
    "world", "history", "conference", "movement", "revolution", "crisis",
    "massacre", "genocide", "rise", "fall",
}
# What a naive Commons search returns most readily, and what none of it is: a
# photograph of the event. The Internet Archive book scans are the worst of it,
# because they are real, free, and completely unillustrative.
_JUNK_MARKERS = (
    "logo", "icon", "flag of", "coat of arms", "emblem", "seal of", "crest",
    "(ia ", "(ia_", ".djvu", ".pdf", " vol ", "microform", "barnstar", "userbox",
)


def anchors(slug: str, title: str) -> set[str]:
    """Distinctive word-prefixes an image of this event should mention.

    Prefixes rather than whole words, because Commons names the picture in
    whatever language and inflection its uploader used: the anchor `crusad`
    finds "Taking_of_Jerusalem_by_the_Crusaders" where `crusades` would not.
    """
    out = set()
    for word in re.split(r"[^a-z0-9]+", f"{slug} {title}".lower()):
        if len(word) >= 5 and word not in _ANCHOR_STOP:
            out.add(word[:6])
    return out


def is_relevant(name: str, mime: str, anchor_set: set[str]) -> bool:
    """Whether a search hit is plausibly a picture OF this event.

    Commons search is keyword matching over file descriptions, and left
    unchecked it is confidently wrong: searching the Tiananmen entries returned
    a photograph of a California ghost town, and the Bandung Conference returned
    four scanned reports on Chinese soft power. An event that comes up with
    nothing gets nothing; a page with fewer pictures is recoverable, a page
    illustrated with the wrong ones is not.
    """
    low = name.lower()
    spaced = low.replace("_", " ")
    if any(j in spaced or j in low for j in _JUNK_MARKERS):
        return False
    if not str(mime or "").startswith("image/"):
        return False
    return any(a in spaced for a in anchor_set)


def backfill(docs: list[dict], commons: dict, target: int,
             only: set[str] | None = None) -> dict:
    """Find real Commons files for events that came up short.

    Roughly a third of the catalogue's image references name files that are not
    on Commons at all, so verifying the existing list is not enough to put
    pictures on the page. This searches for each missing picture by the
    description the curator wrote for it and keeps the first free-licensed hit
    that is not already in use.
    """
    found: dict[str, list[dict]] = {}
    already = set(commons)

    for doc in docs:
        slug = doc["slug"]
        have = sum(
            1 for m in (doc.get("media") or [])
            if (n := commons_filename(m.get("source_url"))) and n in commons
        )
        if only and slug not in only:
            continue
        if have >= target:
            continue

        need = target - have
        candidates: list[str] = []
        for term in event_search_terms(doc, commons)[:4]:
            if len(candidates) >= need * 4:
                break
            try:
                hits = search(f"{term}", limit=6)
            except Exception as e:
                print(f"  [warn] search failed for {slug!r}: {e}")
                continue
            candidates.extend(h for h in hits if h not in already and h not in candidates)
            time.sleep(PAUSE_SECONDS)

        if not candidates:
            print(f"  {slug}: no candidates")
            continue

        verified = verify_names(candidates[:need * 4])
        anchor_set = anchors(slug, doc.get("title", ""))
        picked = []
        for name, rec in verified.items():
            if name in already:
                continue
            if not is_relevant(name, rec.get("mime", ""), anchor_set):
                continue
            picked.append({"name": name, **rec})
            already.add(name)
            if len(picked) >= need:
                break

        if picked:
            found[slug] = picked
            print(f"  {slug}: +{len(picked)} (had {have})")
        else:
            print(f"  {slug}: nothing usable (had {have})")

    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true",
                    help="re-query every file instead of only the unresolved ones")
    ap.add_argument("--backfill", type=int, metavar="N", default=0,
                    help="search Commons so every event reaches N verified images")
    ap.add_argument("--only", type=str, default="",
                    help="comma-separated slugs to backfill (default: every short event)")
    ap.add_argument("--prune", action="store_true",
                    help="re-apply the relevance rule to the stored backfill, no queries")
    args = ap.parse_args()

    used = collect_filenames()
    print(f"{len(used)} distinct Commons file(s) referenced by the catalogue")

    cache = {"files": {}, "refused": {}}
    if CACHE.exists() and not args.refresh:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
        cache.setdefault("files", {})
        cache.setdefault("refused", {})

    # Already-refused names are not retried: the refusal is a fact about the
    # file (not on Commons, or not freely licensed), re-asking only spends the
    # rate limit, and a throttled retry is exactly how a real image would get
    # mislabelled as missing. --refresh re-asks everything.
    pending = [n for n in sorted(used)
               if n not in cache["files"] and n not in cache["refused"]]
    if args.refresh:
        pending = sorted(used)
        cache = {"files": {}, "refused": {}}
    print(f"{len(pending)} to query ({len(used) - len(pending)} already cached)")

    if pending:
        resolved, refused = resolve(pending)
        cache["files"].update(resolved)
        for name, why in refused:
            cache["refused"][name] = why

    if args.prune:
        docs = {}
        for path in sorted(EVENTS.glob("*.yaml")):
            d = yaml.safe_load(path.read_text(encoding="utf-8"))
            if d and d.get("slug"):
                docs[d["slug"]] = d
        before = sum(len(v) for v in (cache.get("backfill") or {}).values())
        pruned = {}
        for slug, items in (cache.get("backfill") or {}).items():
            a = anchors(slug, (docs.get(slug) or {}).get("title", ""))
            keep = [r for r in items if is_relevant(r.get("name", ""), r.get("mime", ""), a)]
            if keep:
                pruned[slug] = keep
        cache["backfill"] = pruned
        after = sum(len(v) for v in pruned.values())
        print(f"pruned backfill: {before} -> {after} across {len(pruned)} event(s)")

    if args.backfill:
        docs = [yaml.safe_load(p.read_text(encoding="utf-8"))
                for p in sorted(EVENTS.glob("*.yaml"))]
        docs = [d for d in docs if d and d.get("slug")]
        only = {x.strip() for x in args.only.split(",") if x.strip()} or None
        print(f"\nbackfilling to {args.backfill} image(s) per event"
              + (f" (only {len(only)} slug(s))" if only else ""))
        found = backfill(docs, cache["files"], args.backfill, only=only)
        # A targeted run adds to what is stored; a full run replaces it.
        if only:
            cache.setdefault("backfill", {}).update(found)
        else:
            cache["backfill"] = found

    # Drop cache entries the catalogue no longer references.
    cache["files"] = {k: v for k, v in cache["files"].items() if k in used}
    cache["refused"] = {k: v for k, v in cache["refused"].items() if k in used}
    cache.setdefault("backfill", {})
    cache["thumbWidth"] = THUMB_WIDTH

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True, ensure_ascii=False),
                     encoding="utf-8")

    ok, no = len(cache["files"]), len(cache["refused"])
    print(f"\nresolved {ok} / {len(used)}  ({no} refused)")
    if cache["refused"]:
        print("refused:")
        for name, why in sorted(cache["refused"].items()):
            print(f"  {name[:58]:<58} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
