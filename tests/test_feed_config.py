#!/usr/bin/env python3
"""frontend/config/feed.json is the ONE source of truth for feed size.

Two assertions:

  1. Python and TypeScript read the same numbers. Before 2026-09-06 the
     displayed size was a literal in both languages, kept in sync by comment
     ("# HomeContent.EDITION_FEED_SIZE" in run_eval.py), and they drifted: the
     JSON-LD ItemList advertised 30 items, the build guard demanded 30
     displayable rows, the pipeline summarized 50 and the page rendered 50.
  2. No stray literal remains. A re-introduced `EDITION_FEED_SIZE = 20` or
     `limit=50` is exactly how the drift started.

Run: python tests/test_feed_config.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

CONFIG = ROOT / "frontend" / "config" / "feed.json"


def check_python_matches_json() -> list[str]:
    from utils import feed_config
    cfg = json.loads(CONFIG.read_text())
    pairs = [
        ("displayed", feed_config.DISPLAYED),
        ("candidates", feed_config.CANDIDATES),
        ("pool", feed_config.POOL),
        ("minDisplayable", feed_config.MIN_DISPLAYABLE),
        ("leadBand", feed_config.LEAD_BAND),
        ("archiveCap", feed_config.ARCHIVE_CAP),
    ]
    return [
        f"feed_config.{key} is {got} but feed.json says {cfg[key]}"
        for key, got in pairs if cfg[key] != got
    ]


def check_typescript_matches_json() -> list[str]:
    """Read the JSON through node, the way the frontend bundle does."""
    cfg = json.loads(CONFIG.read_text())
    try:
        out = subprocess.run(
            ["node", "-e",
             f"const c=require({json.dumps(str(CONFIG))});"
             "process.stdout.write(JSON.stringify(c));"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return [f"SKIP: node unavailable ({e})"]
    if out.returncode != 0:
        return [f"node could not read feed.json: {out.stderr.strip()[:200]}"]
    if json.loads(out.stdout) != cfg:
        return ["node and python read different values from feed.json"]
    return []


# (path, regex, why). Each pattern is a literal that used to live in the code.
_STRAY = [
    ("frontend/app/components/HomeContent.tsx",
     re.compile(r"EDITION_FEED_SIZE\s*=\s*\d"),
     "the displayed cap must come from feedConfig, not a literal"),
    ("frontend/app/lib/serverFeed.ts",
     re.compile(r"MIN_STORIES\s*=\s*\d"),
     "the build guard must come from feedConfig"),
    ("pipeline/ranker/feed_ranker.py",
     re.compile(r"^FEED_CAP_END\s*=\s*\d", re.M),
     "FEED_CAP_END must be the configured displayed size"),
    ("pipeline/main.py",
     re.compile(r'edition="world",\s*limit=\d'),
     "the summary window must come from feed_config.CANDIDATES"),
]


def check_no_stray_literals() -> list[str]:
    out = []
    for rel, rx, why in _STRAY:
        text = (ROOT / rel).read_text()
        for m in rx.finditer(text):
            line = text[:m.start()].count("\n") + 1
            out.append(f"{rel}:{line} {m.group(0)!r} - {why}")
    return out


def main() -> int:
    failures: list[str] = []
    for name, fn in [
        ("python matches feed.json", check_python_matches_json),
        ("typescript matches feed.json", check_typescript_matches_json),
        ("no stray feed-size literals", check_no_stray_literals),
    ]:
        problems = fn()
        skips = [p for p in problems if p.startswith("SKIP")]
        real = [p for p in problems if not p.startswith("SKIP")]
        if real:
            print(f"[FAIL] {name}")
            for p in real:
                print(f"    - {p}")
            failures.extend(real)
        elif skips:
            print(f"[skip] {name}: {skips[0]}")
        else:
            print(f"[ ok ] {name}")
    if failures:
        print(f"\nFAILED: {len(failures)} issue(s)")
        return 1
    cfg = json.loads(CONFIG.read_text())
    print(f"\nOK: displayed={cfg['displayed']} candidates={cfg['candidates']} "
          f"pool={cfg['pool']} archiveCap={cfg['archiveCap']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
