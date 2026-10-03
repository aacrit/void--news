#!/usr/bin/env python3
"""History owns its title and its share card.

WHY THIS WAS BROKEN FOR AS LONG AS IT WAS. `app/history/page.tsx` was a Client
Component, and a Client Component cannot export `metadata` or
`generateMetadata` at all. Next does not warn; the route just inherits the root
layout. So /history/ shared the title "Void News. See through the void." and
the site-wide card, and all 78 event pages shared that image too. The event
pages at least had titles, because `[slug]/page.tsx` is a server component,
which is exactly why nobody noticed the landing had none.

None of that is visible in the page. It is visible only when someone shares a
link, which is the moment it matters most and the moment nobody is watching.

These checks read the SOURCE rather than the build, so they run in seconds with
no Node, no network and no `next build`.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "app"
ok = True


def check(label, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"  [{'ok' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def read(rel):
    p = APP / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def test_landing_owns_metadata():
    """HM-01  the route is a server component and exports metadata."""
    print("\nHM-01  the landing owns its metadata")
    page = read("history/page.tsx")
    check("history/page.tsx exists", bool(page))
    # The whole defect in one assertion.
    check("the route is NOT a client component", '"use client"' not in page,
          "a client component cannot export metadata, which is how this broke")
    check("it exports generateMetadata", "generateMetadata" in page)
    check("the interactive tree still exists", bool(read("history/HistoryClient.tsx")))
    check("and is still a client component", '"use client"' in read("history/HistoryClient.tsx"))


def test_cards_exist():
    """HM-02  both card routes exist, are static, and mirror their pages."""
    print("\nHM-02  the share cards")
    landing = read("history/opengraph-image.tsx")
    event = read("history/[slug]/opengraph-image.tsx")
    check("the landing card route exists", bool(landing))
    check("the per-event card route exists", bool(event))
    # Without force-static, `next/og` is treated as a dynamic route handler and
    # `output: export` refuses to collect it.
    for name, src in (("landing", landing), ("event", event)):
        check(f"the {name} card is force-static", 'dynamic = "force-static"' in src)

    # A card route that prerenders a different slug set than its page emits an
    # image for a page that does not exist, or misses one that does, and
    # dynamicParams is false so nothing covers the gap at runtime.
    page = read("history/[slug]/page.tsx")
    for src, who in ((page, "page"), (event, "card")):
        check(f"the {who} builds its slugs from the catalog + mocks",
              "getHistorySlugs()" in src and "MOCK_EVENTS" in src)


def test_yields_to_the_file():
    """HM-03  metadata must not declare an image, or the card file is ignored."""
    print("\nHM-03  metadata yields to the card file")
    meta = read("history/historyMeta.ts")
    check("historyMeta exists", bool(meta))
    # Next uses opengraph-image.tsx ONLY when the route declares no
    # openGraph.images, and pageMetadata declares the site-wide card for every
    # route. Leaving it is precisely how a section ships a card saying nothing.
    check("it deletes the inherited openGraph image", "delete og.images" in meta)
    check("and the twitter one", "delete tw.images" in meta)
    check("the landing uses it", "landingMetadata" in read("history/page.tsx"))
    check("every event page uses it", "eventMetadata" in read("history/[slug]/page.tsx"))


def test_headers():
    """HM-04  Pages must be told these extensionless paths are PNGs."""
    print("\nHM-04  Content-Type for the card routes")
    h = (ROOT / "frontend" / "public" / "_headers").read_text(encoding="utf-8")
    # Next emits the card at an EXTENSIONLESS path. Cloudflare Pages infers
    # Content-Type from the extension, serves application/octet-stream, and the
    # global nosniff then forbids every scraper from treating it as an image.
    # The card renders nowhere and nothing in the build says so.
    for route in ("/history/opengraph-image", "/history/*/opengraph-image"):
        block = re.search(re.escape(route) + r"\n((?:  .+\n)+)", h)
        check(f"{route} is pinned", bool(block) and "image/png" in (block.group(1) if block else ""),
              "without this, nosniff makes the card unusable")


def test_shared_card():
    """HM-05  one card definition, not two that drift."""
    print("\nHM-05  the card is shared with Weekly")
    shared = read("lib/ogCard.tsx")
    check("the shared card module exists", bool(shared))
    check("Weekly uses it", 'from "../lib/ogCard"' in read("weekly/ogCard.tsx"))
    check("History uses it", 'from "../lib/ogCard"' in read("history/ogCard.tsx"))
    # satori silently mis-lays-out an element with children and no display.
    check("the shared card sets display on its wrappers",
          shared.count('display: "flex"') >= 5)
    # The taxonomy's punctuation is not for the most public surface we have.
    check("era and region are humanised on the card",
          "replace(/[-_]+/g" in read("history/ogCard.tsx"),
          "the card read 'SOUTH-ASIA' before this")


if __name__ == "__main__":
    test_landing_owns_metadata()
    test_cards_exist()
    test_yields_to_the_file()
    test_headers()
    test_shared_card()
    print("\n" + ("All History metadata gates passed." if ok else "FAILURES above."))
    sys.exit(0 if ok else 1)
