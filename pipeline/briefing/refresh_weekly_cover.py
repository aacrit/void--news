"""Re-pick the published weekly's cover image from a freely licensed source.

Issue #26 shipped with an AFP TOPSHOT photograph hotlinked off a Nigerian
newspaper's CDN, credited only "Image via Punch Nigeria". `find_cover_image_for_
cluster` used to try the publisher's og:image first and reach Wikimedia only if
that failed; that order is fixed now, but the fix only takes effect on the next
weekly run, and a wire photograph should not sit on the live site until Monday.

This re-picks the cover for ALREADY PUBLISHED issues, in place: no LLM call, no
database, no regeneration of a single word of any issue. It searches Wikimedia
Commons for the cover headline and its topic words.

It writes to BOTH places an issue lives, because they are not the same file and
only one of them is served. `frontend/public/data/weekly.json` is the latest
issue's snapshot; `frontend/build-data/weekly-issues.json` is the ARCHIVE OF
RECORD that /weekly and /weekly/<week> actually render from. Fixing only the
snapshot leaves the live page showing the picture you thought you had replaced,
and leaves every BACK issue untouched for good: issue #23 sat in that archive
hotlinking a photograph off theatlantic.com, on a page nothing was checking,
because the gate read the snapshot alone.

When a search runs and nothing licensed fits, the image is CLEARED rather than
left: a weekly with no cover photograph is a design compromise, a weekly with
someone else's wire photograph is a legal one. When Commons cannot be REACHED at
all, the cover is left exactly as it is and the exit code is 2. Those two look
identical from the outside and mean opposite things, and conflating them is how
this tool twice deleted its own good result the moment Wikimedia throttled it.

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
from history.resolve_commons import anchors, is_relevant  # noqa: E402
from briefing.weekly_parse import index_rows  # noqa: E402

WEEKLY = REPO / "frontend" / "public" / "data" / "weekly.json"
ARCHIVE = REPO / "frontend" / "build-data" / "weekly-issues.json"
# The slim index the BROWSER fetches, derived from the archive of record. It is
# the third copy of a cover url and the one the served-output gate reads, so a
# repair that skips it fixes the pages and leaves the evidence wrong.
INDEX = REPO / "frontend" / "public" / "data" / "weekly-archive.json"

# A cover url on one of these hosts is one Void may publish. Everything else is
# somebody's CDN, which is how a wire photograph gets in.
FREE_HOSTS = ("upload.wikimedia.org", "thumb.wikimedia.org",
              "images.unsplash.com", "images.pexels.com")

# A diagram is not a magazine cover, whatever its licence. These pass the
# relevance filter honestly (a locator map of France and Saudi Arabia really is
# about France and Saudi Arabia) and still must not run on a cover.
_NOT_A_COVER = ("locator", "_map", "map_", "relief_location", "cgi_", "flag",
                "blank_", "_svg", ".svg", "diagram", "chart")

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


def pick(headline: str, cover_text) -> tuple[dict | None, bool]:
    """(chosen image or None, whether any search actually completed).

    The second value matters: "searched and found nothing licensed" and "could
    not reach Commons" look identical from the outside and mean opposite things.
    Treating a throttled request as the former wipes a perfectly good cover, as
    this tool did to its own result twice before the distinction existed.
    """
    reached = False
    anchor_set = anchors("", headline)
    if not anchor_set:
        print("  headline carries no distinctive word to anchor a picture on")
        return None, False
    for term in search_terms(headline, cover_text):
        try:
            results = search_wikimedia(term, max_results=4)
        except Exception as e:
            print(f"  [warn] search failed for {term!r}: {e}")
            continue
        # search_wikimedia swallows its own failures and returns [], so an empty
        # list is only evidence of "reached" when something else came back.
        if results:
            reached = True
        for r in results:
            # The rendered thumbnail, not the multi-megabyte original.
            url = r.thumbnail_url or r.url
            # Commons search is keyword matching over file DESCRIPTIONS, so a
            # hit can be free, real and about something else entirely: this
            # search returned a photograph of a shepherd leading his camel for
            # an issue about sanctions, because the file's metadata mentions
            # Saudi Arabia. The same filter History uses applies here — the
            # file's own NAME must carry a distinctive prefix from the headline,
            # and maps, flags and locator diagrams are not covers. Better no
            # cover than the wrong one. (Filter shared with resolve_commons so
            # the two cannot drift.)
            if not is_relevant(url, "image/", anchor_set):
                continue
            if any(w in url.lower() for w in _NOT_A_COVER):
                continue
            if verify_image(url):
                print(f"  matched on {term!r}")
                return {"url": url, "attribution": r.attribution, "source": "wikimedia"}, True
    return None, reached


def is_free(url) -> bool:
    return any(h in str(url or "") for h in FREE_HOSTS)


def apply(row: dict, chosen: dict | None) -> None:
    row["cover_image_url"] = chosen["url"] if chosen else None
    row["cover_image_attribution"] = chosen["attribution"] if chosen else None
    row["cover_image_source"] = chosen["source"] if chosen else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="every issue in the archive, not only ones whose cover "
                         "is already on a non-free host")
    args = ap.parse_args()

    if not WEEKLY.exists():
        print(f"no weekly snapshot at {WEEKLY}")
        return 1

    snapshot = json.loads(WEEKLY.read_text(encoding="utf-8"))
    archive: list = []
    if ARCHIVE.exists():
        loaded = json.loads(ARCHIVE.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            archive = loaded
        else:
            print(f"  [warn] {ARCHIVE.name} is not a list; skipping the archive")
    else:
        print(f"  [warn] no {ARCHIVE.name}; only the latest snapshot will be updated")

    # One entry per issue number, carrying every row that holds that issue so a
    # single search result lands in both files at once.
    issues: dict = {}
    for row in [snapshot, *archive]:
        no = row.get("issue_number")
        issues.setdefault(no, []).append(row)

    unreachable = False
    changed = 0
    for no, rows in sorted(issues.items(), key=lambda kv: kv[0] or 0, reverse=True):
        head = rows[0]
        current = head.get("cover_image_url")
        print(f"issue #{no} ({head.get('week_start')})")
        print(f"  current: {str(current)[:96]}")
        print(f"  credit : {head.get('cover_image_attribution')!r} "
              f"(source {head.get('cover_image_source')!r})")

        # An issue already on a free host with a credit is left alone unless
        # --all: re-rolling a good cover churns the archive for nothing. The
        # check has to cover EVERY row that holds the issue, not just the first.
        # The snapshot and the archive are separate files and can disagree about
        # the same issue, and reading only the head is how a fixed snapshot hid
        # an unfixed archive row — the row that is actually served.
        settled = all(is_free(r.get("cover_image_url")) and r.get("cover_image_attribution")
                      for r in rows)
        agreed = len({r.get("cover_image_url") for r in rows}) == 1
        if not args.all and settled and agreed:
            print("  already on a freely licensed host; left as is")
            continue
        if settled and not agreed:
            # Both free, so there is nothing to search for: copy the snapshot's
            # (the freshest) across and move on.
            print("  rows disagree; reconciling the archive to the snapshot")
            if not args.dry_run:
                for row in rows[1:]:
                    apply(row, {"url": head["cover_image_url"],
                                "attribution": head.get("cover_image_attribution"),
                                "source": head.get("cover_image_source") or "wikimedia"})
                changed += 1
            continue

        chosen, reached = pick(head.get("cover_headline", ""), head.get("cover_text"))
        if chosen:
            print(f"  new    : {chosen['url'][:96]}")
            print(f"  credit : {chosen['attribution']}")
        elif not reached:
            # Leave THIS issue exactly as it is and keep going; an issue that
            # could not be searched must never be mistaken for one with nothing
            # to find, which is how this tool twice deleted its own good result.
            print("  could NOT reach Commons; leaving this cover exactly as it is")
            unreachable = True
            continue
        else:
            print("  nothing freely licensed matched; clearing the cover image")

        if args.dry_run:
            continue
        for row in rows:
            apply(row, chosen)
        changed += 1

    if args.dry_run:
        return 2 if unreachable and not changed else 0

    if changed:
        # Match export_static.wj() exactly (json.dump defaults, ensure_ascii=
        # False), so re-picking a cover is a three-key diff per issue and not a
        # whole-file reformat.
        WEEKLY.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        if archive:
            ARCHIVE.write_text(json.dumps(archive, ensure_ascii=False), encoding="utf-8")
            # Re-derive the served index rather than editing it: one definition
            # of what an index row is (weekly_parse.index_rows), shared with the
            # exporter that normally writes it.
            INDEX.write_text(json.dumps(index_rows(archive), ensure_ascii=False),
                             encoding="utf-8")
        print(f"  written ({changed} issue(s))")
    else:
        print("  nothing to change")
    return 2 if unreachable and not changed else 0


if __name__ == "__main__":
    sys.exit(main())
