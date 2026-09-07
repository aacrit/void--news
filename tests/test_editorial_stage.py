#!/usr/bin/env python3
"""End-to-end regression test for the editorial half of the pipeline.

Runs 8c through 8f plus the static export against a synthetic state DB built
from committed snapshots (tests/build_test_db.py), with no LLM key so nothing
is generated and nothing is spent. It exists because three defects shipped that
only an end-to-end run would have caught:

  * the holistic re-rank wrote ZERO rows for weeks (partial-row upsert failed
    the title NOT NULL check) while the run summary said "Errors: 0";
  * the printed edition and the displayed feed were selected by different
    predicates and drifted, so the last cards of six consecutive editions
    shipped "/?story=" homepage links;
  * nothing asserted the printed edition size at all.

Each assertion below is one of those. Needs the pipeline requirements
(spaCy, numpy, scikit-learn) but no network and no secrets.

Run: python tests/test_editorial_stage.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from utils.display_window import filter_displayable  # noqa: E402
from utils.feed_config import ARCHIVE_CAP, DISPLAYED  # noqa: E402

sys.path.insert(0, str(ROOT / "tests"))
from build_test_db import build  # noqa: E402


def run(cmd: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, env={**os.environ, **env},
                          capture_output=True, text=True, timeout=1800)


def main() -> int:
    ok = True
    tmp = Path(tempfile.mkdtemp(prefix="void-editorial-"))
    try:
        db = tmp / "state.db"
        stats = build(db)
        print(f"built harness DB: {stats['clusters']} clusters, "
              f"{stats['articles']} articles, {stats['printed']} printed rows")

        env = {
            "VOID_SQLITE_PATH": str(db),
            "DISABLE_ANTHROPIC": "1",
            "VOID_EXPORT_BUILD_DIR": str(tmp / "build-data"),
            "VOID_EXPORT_PUBLIC_DIR": str(tmp / "public-data"),
        }
        env.pop("GEMINI_API_KEY", None)

        stage = run([sys.executable, "pipeline/main.py", "--editorial-only"], env)
        if stage.returncode != 0:
            print("FAIL: editorial stage exited non-zero")
            print(stage.stdout[-3000:])
            return 1
        out = stage.stdout

        # 1. The holistic re-rank actually writes. "0/N clusters re-ranked" is
        #    the exact string production printed every day for weeks.
        import re
        m = re.search(r"Done\. (\d+)/(\d+) clusters re-ranked", out)
        if not m:
            print("FAIL: no re-rank summary line in the run output")
            ok = False
        elif m.group(1) != m.group(2) or m.group(1) == "0":
            print(f"FAIL: re-rank wrote {m.group(1)} of {m.group(2)} rows")
            ok = False
        else:
            print(f"PASS: re-rank wrote all {m.group(1)} rows")
        if "NOT confirmed written" in out:
            print("FAIL: run reported unconfirmed re-rank writes")
            ok = False

        # 2. The printed edition is the configured size.
        m = re.search(r"Printed (\d+) stories", out)
        if not m:
            print("FAIL: no print-archive line in the run output")
            ok = False
        elif int(m.group(1)) != ARCHIVE_CAP:
            print(f"FAIL: printed {m.group(1)} stories, configured cap is {ARCHIVE_CAP}")
            ok = False
        else:
            print(f"PASS: printed exactly {ARCHIVE_CAP} stories")

        # 3. Phase 7 is off, so no cluster ships a source_count its links
        #    cannot support.
        if "[same-event-merge]" in out:
            print("FAIL: Phase 7 same-event merge ran")
            ok = False

        export = run([sys.executable, "pipeline/export_static.py"], env)
        if export.returncode != 0:
            print("FAIL: static export exited non-zero")
            print(export.stdout[-2000:])
            return 1

        feed = json.loads((tmp / "build-data" / "feed.json").read_text())["clusters"]
        amap = json.loads((tmp / "build-data" / "archiveMap.json").read_text())
        displayed = filter_displayable(feed, DISPLAYED)

        # 4. Enough stories to fill the page.
        if len(displayed) < DISPLAYED:
            print(f"FAIL: only {len(displayed)} displayable stories for {DISPLAYED} slots")
            ok = False
        else:
            print(f"PASS: {len(displayed)} displayable stories fill {DISPLAYED} slots")

        # 5. THE tail-URL regression: every displayed card resolves to a
        #    /story/<uuid>/ permalink, so serverFeed never falls back.
        missing = [c["title"][:50] for c in displayed if c["id"] not in amap]
        if missing:
            print(f"FAIL: {len(missing)} displayed cards have no permalink: {missing[:3]}")
            ok = False
        else:
            print(f"PASS: all {len(displayed)} displayed cards have a /story/ permalink")

        # 6. Every emitted permalink is the canonical shape.
        bad = [v for v in amap.values() if not re.match(r"^/story/[0-9a-f-]{36}/$", v)]
        if bad:
            print(f"FAIL: malformed permalinks: {bad[:3]}")
            ok = False
        else:
            print("PASS: every permalink is /story/<uuid>/")

        # 7. The export carries the fields the offline replay harness needs.
        for field in ("content_type", "disaster_severity"):
            if field not in feed[0]:
                print(f"FAIL: feed.json is missing {field}, the replay harness needs it")
                ok = False
        else:
            print("PASS: feed.json carries content_type and disaster_severity")

        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
