#!/usr/bin/env python3
"""Games' source-level gates: the banks it serves, and what they may say.

    python3 tests/test_games_content.py

scripts/verify_sections.py G-01..G-03 read the LIVE pages, and a static page
only carries the one puzzle it was rendered with. These read every string in
every bank, so a dash or a kill-list word in puzzle 17's reveal is caught
before deploy rather than on the day puzzle 17 comes round.

  1. No em or en dash, and no kill-list term (pipeline/utils/prohibited_terms),
     in any string literal under frontend/app/games/.
  2. THE FRAME stays withdrawn: its route is gone and its two paths redirect.
     Its one puzzle printed four headlines no outlet wrote under four real
     mastheads, with lean scores on a scale the engine does not use.
  3. The daily banks are rotations, not calendars: no puzzle carries a date,
     and every bank is non-empty, so no day can come up blank.
  4. The challenge built on an altered, unattributed quotation of a real
     document is not back.

Stdlib plus the repo's own prohibited_terms. Exit 1 on any failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "frontend" / "app" / "games"
sys.path.insert(0, str(ROOT))

from pipeline.utils.prohibited_terms import find_prohibited  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def string_literals(src: str) -> list[tuple[int, str]]:
    """(line, text) for every string literal and JSX text run, comments removed.

    Not a parser. Comments are blanked first (keeping newlines), then double,
    single and template literals are read with their escapes. JSX text between
    tags is taken as a literal too, since it reaches the reader the same way.
    """
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), src, flags=re.S)
    src = re.sub(r"(?<![:\"'`\\])//[^\n]*", "", src)
    out: list[tuple[int, str]] = []
    for m in re.finditer(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`', src):
        text = next(g for g in m.groups() if g is not None)
        out.append((src.count("\n", 0, m.start()) + 1, text.encode().decode("unicode_escape", "ignore")
                     if "\\u" in text else text))
    for m in re.finditer(r">([^<>{}\n]*[A-Za-z][^<>{}\n]*)<", src):
        out.append((src.count("\n", 0, m.start()) + 1, m.group(1)))
    return out


# ------------------------------------------------ 1. dashes and the kill list
files = sorted(p for p in GAMES.rglob("*") if p.suffix in (".ts", ".tsx"))
check("games source exists", bool(files), str(GAMES))
dash_hits: list[str] = []
kill_hits: list[str] = []
# UNDERTOW's artifacts are SPECIMENS: invented ad copy, LinkedIn posts and
# corporate statements that the reader is asked to dissect, so slop is their
# subject ("Here's what my worst quarter taught me"). An artifact's `text:` and
# a span a reveal puts in quotation marks are somebody else's words, the same
# exemption W-10 gives <blockquote> and <q>. The dash ban has no exemption.
SPECIMEN_LINE = re.compile(r"^\s*(text|highlighted_words):")
for path in files:
    rel = path.relative_to(ROOT)
    src_lines = path.read_text(encoding="utf-8").split("\n")
    for line, text in string_literals("\n".join(src_lines)):
        if re.search(r"[—–]|&mdash;|&ndash;|&#821[12];", text):
            dash_hits.append(f"{rel}:{line} {text[:70]!r}")
        if SPECIMEN_LINE.match(src_lines[line - 1]):
            continue
        prose = re.sub(r'\\"[^"\\]*(?:\\.[^"\\]*)*?\\"|"[^"]*"', " ", text)
        for term in find_prohibited(prose):
            kill_hits.append(f"{rel}:{line} {term!r} in {text[:70]!r}")
check("no em or en dash in Games copy", not dash_hits, "; ".join(dash_hits[:5]))
check("no kill-list term in Games copy", not kill_hits, "; ".join(kill_hits[:5]))

# --------------------------------------------------- 2. THE FRAME stays out
check("THE FRAME's route is not in the build", not (GAMES / "frame").exists(),
      "frontend/app/games/frame/ is back")
redirects = (ROOT / "frontend/public/_redirects").read_text()
for path in ("/games/frame", "/games/wire"):
    check(f"{path} redirects to the Games landing",
          re.search(rf"^{re.escape(path)}\s+/games/\s+30[12]\b", redirects, re.M) is not None)
check("Games itself is not redirected away",
      re.search(r"^/games/?\*?\s+/\s+30[12]\b", redirects, re.M) is None,
      "the 2026-08-03 301 to home is back")
hub = (GAMES / "GamesHub.tsx").read_text(encoding="utf-8")
check("the hub does not link THE FRAME", 'href: "/games/frame"' not in hub)

# ------------------------------------------- 3. rotations, not calendars
for rel, marker in (("undertow/data.ts", r"^    id: \d+,$"), ("wire/data.ts", r"^    id: \d+,$")):
    src = (GAMES / rel).read_text(encoding="utf-8")
    n = len(re.findall(marker, src, re.M))
    check(f"{rel} bank is non-empty", n > 0, f"{n} puzzles")
    check(f"{rel} carries no per-puzzle date", re.search(r"\bdate:\s*\"\d{4}-", src) is None,
          "a dated puzzle reads as a calendar that can run out")
    check(f"{rel} rotates through app/games/daily.ts", "rotationIndex(" in src)
    ids = [int(x) for x in re.findall(r"^    id: (\d+),$", src, re.M)]
    check(f"{rel} puzzle numbers run 1..{len(ids)}", ids == list(range(1, len(ids) + 1)),
          f"ids {ids[:8]}...")

# ------------------------------------------- 4. the altered quotation
undertow = (GAMES / "undertow/data.ts").read_text(encoding="utf-8")
check("no unattributed, altered quotation of the Declaration of Independence",
      "We hold these truths" not in undertow)

if failures:
    print(f"\nFAIL  {len(failures)} games check(s)")
    sys.exit(1)
print("\nPASS  games content")
