"""Re-pick the published weekly's cover image from a freely licensed source.

Issue #26 shipped with an AFP TOPSHOT photograph hotlinked off a Nigerian
newspaper's CDN, credited only "Image via Punch Nigeria". `find_cover_image_for_
cluster` used to try the publisher's og:image first and reach Wikimedia only if
that failed; that order is fixed now, but the fix only takes effect on the next
weekly run, and a wire photograph should not sit on the live site until Monday.

This re-picks the cover for the ALREADY PUBLISHED snapshot, in place: no LLM
call, no database, no regeneration of a single word of the issue. It searches
Wikimedia Commons for the cover headline and its topic words, and writes the
result into frontend/public/data/weekly.json.

When nothing licensed fits, the image is CLEARED rather than left. A weekly with
no cover photograph is a design compromise; a weekly with someone else's wire
photograph is a legal one.

    python -m pipeline.briefing.refresh_weekly_cover            # apply
    python -m pipeline.briefing.refresh_weekly_cover --dry-run  # show only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO / "pipeline"))

from media.image_search import search_wikimedia, verify_image  # noqa: E402

WEEKLY = REPO / "frontend" / "public" / "data" / "weekly.json"

# Words that make a headline a headline rather than a search term.
STOP = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "from", "by", "as", "is", "are", "was", "were", "be", "been",
    "its", "his", "her", "their", "this", "that", "these", "those", "new",
    "amid", "after", "before", "over", "under", "into", "contested", "control",
}


def search_terms(headline: str, cover_text) -> list[str]:
    """Queries to try, most specific first.

    The headline entire is the best query when it names something Commons has a
    picture of. Failing that, its proper nouns are what a photograph could
    plausibly depict: a place, a person, an institution.
    """
    terms: list[str] = []
    head = (headline or "").strip()
    if head:
        terms.append(head)

    proper = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", head)
    proper = [w for w in proper if w.lower() not in STOP]
    if len(proper) >= 2:
        terms.append(" ".join(proper[:3]))
    if proper:
        terms.append(proper[0])

    # The lead essay's own headline, when the cover carries one.
    if isinstance(cover_text, list) and cover_text:
        lead = (cover_text[0] or {}).get("headline") if isinstance(cover_text[0], dict) else None
        if lead and lead != head:
            terms.append(str(lead))

    seen, out = set(), []
    for t in terms:
        k = t.lower()
        if t and k not in seen:
            seen.add(k)
            out.append(t)
    return out


def pick(headline: str, cover_text) -> dict | None:
    for term in search_terms(headline, cover_text):
        try:
            results = search_wikimedia(term, max_results=4)
        except Exception as e:
            print(f"  [warn] search failed for {term!r}: {e}")
            continue
        for r in results:
            low = r.url.lower()
            if any(w in low for w in ("logo", "icon", "flag_of", "coat_of_arms", "symbol")):
                continue
            if verify_image(r.url):
                print(f"  matched on {term!r}")
                return {"url": r.url, "attribution": r.attribution, "source": "wikimedia"}
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not WEEKLY.exists():
        print(f"no weekly snapshot at {WEEKLY}")
        return 1

    data = json.loads(WEEKLY.read_text(encoding="utf-8"))
    current = data.get("cover_image_url")
    print(f"issue #{data.get('issue_number')} ({data.get('week_start')})")
    print(f"  current: {str(current)[:96]}")
    print(f"  credit : {data.get('cover_image_attribution')!r} "
          f"(source {data.get('cover_image_source')!r})")

    chosen = pick(data.get("cover_headline", ""), data.get("cover_text"))
    if chosen:
        print(f"  new    : {chosen['url'][:96]}")
        print(f"  credit : {chosen['attribution']}")
    else:
        print("  nothing freely licensed matched; clearing the cover image")

    if args.dry_run:
        return 0

    data["cover_image_url"] = chosen["url"] if chosen else None
    data["cover_image_attribution"] = chosen["attribution"] if chosen else None
    data["cover_image_source"] = chosen["source"] if chosen else None
    WEEKLY.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")
    print("  written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
