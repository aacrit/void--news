#!/usr/bin/env python3
"""Paper's source-level and local-build gates.

    python3 tests/test_paper.py

scripts/verify_sections.py P-01..P-04 run against the LIVE host. These run
against the repo, and against frontend/out/ when a static export is present, so
a Paper regression is caught before it is deployed rather than after.

Stdlib only, no test runner, exit 1 on any failure.
"""

from __future__ import annotations

import json
import re
import sys
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "frontend" / "app" / "paper"
OUT = ROOT / "frontend" / "out"

# Same two extractions verify_sections.py uses, duplicated deliberately: this
# file is the check that they still find anything.
HOME_HEADLINE_RE = (
    r'class="(?:lead-headline__text|lead-story__headline-text'
    r'|story-card__headline-text)"[^>]*>([^<]*)<'
)
PAPER_HEADLINE_RE = r'class="np-article__headline-text"[^>]*>([^<]*)<'

# Dead edition machinery. Every one of these fabricated something Paper could
# not support: a city for a category, a section name for an edition that does
# not exist, a subhead made of a category in capitals.
RETIRED = (
    "US_DATELINES", "INDIA_DATELINES", "WORLD_DATELINES", "getDateline",
    "getSectionConfig", "editionSubtitle", "editionDisplayName",
    "generateSubheads", "generateFillers",
)

failures: list[str] = []


def check(code: str, passed: bool, detail: str) -> None:
    if not passed:
        failures.append(code)
    print(f"[{'ok  ' if passed else 'FAIL'}] {code}: {detail}")


def paper_sources() -> list[Path]:
    return sorted(p for p in PAPER_DIR.rglob("*")
                  if p.is_file() and p.suffix in (".ts", ".tsx", ".css"))


def main() -> int:
    # T-01 — the feed-size constant verify_sections.py hard-codes still agrees
    # with the one source of truth. Every other consumer reads feed.json; the
    # gate cannot, because it runs with no repo on the path.
    cfg = json.loads((ROOT / "frontend" / "config" / "feed.json").read_text())
    gate = (ROOT / "scripts" / "verify_sections.py").read_text()
    m = re.search(r"^FEED_DISPLAYED = (\d+)$", gate, flags=re.M)
    check("T-01", bool(m) and int(m.group(1)) == cfg["displayed"],
          f"verify_sections FEED_DISPLAYED={m.group(1) if m else '(missing)'}, "
          f"feed.json displayed={cfg['displayed']}")

    # T-02 — no em or en dash anywhere in Paper's source. Six of them shipped.
    dashed = []
    for path in paper_sources():
        text = path.read_text()
        for n, line in enumerate(text.splitlines(), 1):
            if "—" in line or "–" in line:
                dashed.append(f"{path.relative_to(ROOT)}:{n}")
    check("T-02", not dashed,
          "no dash in Paper's source" if not dashed
          else f"{len(dashed)} dash(es): {dashed[:5]}")

    # T-03 — the dead edition machinery is gone, and so is the route it served.
    joined = "\n".join(p.read_text() for p in paper_sources())
    left = [name for name in RETIRED if name in joined]
    edition_route = (PAPER_DIR / "[edition]").exists()
    check("T-03", not left and not edition_route,
          "edition machinery and the [edition] route are gone"
          if not left and not edition_route
          else f"still present: {left}"
               + ("; [edition]/ still exists" if edition_route else ""))

    # T-04 — Paper reads the deploy tree, not the decommissioned database.
    check("T-04", "lib/supabase" not in joined,
          "no Supabase import" if "lib/supabase" not in joined
          else "Paper still imports lib/supabase")

    # T-05 — every headline is a link into the archive, and the canonical lean
    # ladder is the only one on the page.
    content = (PAPER_DIR / "PaperContent.tsx").read_text()
    check("T-05",
          "np-article__headline-link" in content
          and "storyShapeLabel" in content
          and "permalink" in content,
          "headlines link to their Deep Dive and the lean caption is the card's storyShapeLabel"
          if "np-article__headline-link" in content and "storyShapeLabel" in content
          else "PaperContent is missing the headline link or the canonical lean label")

    # T-06 — the local export, when there is one: the same headlines in the
    # same order as the front page. This is P-02 against out/ instead of a host.
    home_file = OUT / "index.html"
    paper_file = OUT / "paper" / "index.html"
    if not home_file.exists() or not paper_file.exists():
        print("[skip] T-06: no frontend/out/ export (run `npm run build` first)")
    else:
        home = [unescape(h).strip()
                for h in re.findall(HOME_HEADLINE_RE, home_file.read_text())]
        paper = [unescape(h).strip()
                 for h in re.findall(PAPER_HEADLINE_RE, paper_file.read_text())]
        n = cfg["displayed"]
        same = len(paper) == n and paper == home[:n]
        first = next((i for i, (p, h) in enumerate(zip(paper, home)) if p != h), None)
        check("T-06", same,
              f"{n} articles, headlines match the front page in order" if same
              else f"paper has {len(paper)}, home has {len(home)}"
                   + (f"; first divergence at {first + 1}: "
                      f'"{paper[first][:50]}" vs "{home[first][:50]}"'
                      if first is not None else ""))

        # T-07 — no dash, and the links are real /story/ permalinks.
        body = re.sub(r"<head\b.*?</head>", "", paper_file.read_text(), flags=re.S)
        body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
        dashes = body.count("—") + body.count("–")
        story_links = len(re.findall(r'href="[^"]*/story/[^"]+/"', paper_file.read_text()))
        check("T-07", dashes == 0 and story_links >= n,
              f"no dash in the exported prose, {story_links} /story/ link(s)"
              if dashes == 0 and story_links >= n
              else f"{dashes} dash(es); {story_links} /story/ link(s), expected at least {n}")

    if failures:
        print(f"\n{len(failures)} check(s) failed: {failures}")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
