#!/usr/bin/env python3
"""A correction to the YAML must actually reach the page.

The History section serves committed static JSON. `data/history/events/*.yaml`
is the record; `frontend/public/data/history.json` is what a reader gets. They
are two files, and nothing kept them in step.

This was not hypothetical. Ten fabricated quotations were deleted from the YAML
on 2026-09-20, and all ten were still in the served JSON afterwards, including
a line attributed to a sultan that no chronicle carries and one its own record
called apocryphal. The deletion was real and the reader would still have read
them. The same gap applies to `frontend/build-data/history-scripts/`, which the
event page reads at build time.

A fix that does not ship is not a fix, so this re-exports both to a scratch
directory and compares. It never writes to the tree it is checking.

Run: python3 tests/test_history_export_parity.py
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVED = ROOT / "frontend/public/data/history.json"
SCRIPTS_DIR = ROOT / "frontend/build-data/history-scripts"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


def canon(obj):
    """Order-insensitive only where the exporter is; otherwise exact."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = pathlib.Path(tmp)
    env = dict(os.environ)
    env["VOID_EXPORT_PUBLIC_DIR"] = str(tmpdir / "public")
    env["VOID_EXPORT_BUILD_DIR"] = str(tmpdir / "build")

    # ---------------------------------------------------- history.json
    run = subprocess.run(
        [sys.executable, "-m", "pipeline.history.export_history"],
        cwd=ROOT, env=env, capture_output=True, text=True)
    if run.returncode != 0:
        check("export_history runs", False, run.stderr.strip()[-400:])
    else:
        fresh_path = tmpdir / "public" / "history.json"
        check("export_history writes history.json", fresh_path.exists())
        if fresh_path.exists() and SERVED.exists():
            fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
            served = json.loads(SERVED.read_text(encoding="utf-8"))

            f_events = fresh.get("events", fresh) if isinstance(fresh, dict) else fresh
            s_events = served.get("events", served) if isinstance(served, dict) else served

            check("the served file has every event the record has",
                  len(f_events) == len(s_events),
                  f"record {len(f_events)}, served {len(s_events)}")

            f_by = {e.get("slug"): e for e in f_events}
            s_by = {e.get("slug"): e for e in s_events}
            drifted = sorted(
                slug for slug in f_by.keys() & s_by.keys()
                if canon(f_by[slug]) != canon(s_by[slug])
            )
            check("no event has drifted from its record",
                  not drifted,
                  f"stale in history.json: {', '.join(drifted[:8])}"
                  + (f" (+{len(drifted) - 8} more)" if len(drifted) > 8 else ""))

            missing = sorted(f_by.keys() - s_by.keys())
            extra = sorted(s_by.keys() - f_by.keys())
            check("no event is missing from the served file", not missing, str(missing[:6]))
            check("the served file invents no event", not extra, str(extra[:6]))

    # -------------------------------------------- build-data/history-scripts
    run = subprocess.run(
        [sys.executable, "-m", "pipeline.history.export_scripts"],
        cwd=ROOT, env=env, capture_output=True, text=True)
    fresh_scripts = tmpdir / "build" / "history-scripts"
    if not fresh_scripts.exists():
        # The exporter writes to a fixed path; only compare when it honoured
        # the override, rather than silently passing on nothing.
        print("note: export_scripts did not honour VOID_EXPORT_BUILD_DIR, "
              "comparing against a re-parse instead")
        sys.path.insert(0, str(ROOT))
        import yaml
        from pipeline.history.export_scripts import export  # noqa: E402
        from pipeline.history.script_format import parse_script  # noqa: E402
        stale = []
        for path in sorted((ROOT / "data/history/scripts").glob("*.txt")):
            slug = path.stem
            ev_path = ROOT / "data/history/events" / f"{slug}.yaml"
            out = SCRIPTS_DIR / f"{slug}.json"
            if not ev_path.exists() or not out.exists():
                stale.append(slug)
                continue
            event = yaml.safe_load(ev_path.read_text(encoding="utf-8"))
            blob = export(parse_script(path.read_text(encoding="utf-8"), slug), event)
            if canon(blob) != canon(json.loads(out.read_text(encoding="utf-8"))):
                stale.append(slug)
        check("no exported script has drifted from its source",
              not stale,
              f"stale: {', '.join(stale[:8])}"
              + (f" (+{len(stale) - 8} more)" if len(stale) > 8 else ""))
    else:
        stale = []
        for fp in sorted(fresh_scripts.glob("*.json")):
            committed = SCRIPTS_DIR / fp.name
            if not committed.exists():
                stale.append(fp.stem)
            elif canon(json.loads(fp.read_text(encoding="utf-8"))) != \
                    canon(json.loads(committed.read_text(encoding="utf-8"))):
                stale.append(fp.stem)
        check("no exported script has drifted from its source",
              not stale,
              f"stale: {', '.join(stale[:8])}"
              + (f" (+{len(stale) - 8} more)" if len(stale) > 8 else ""))

if failures:
    print(f"\nFAIL  {len(failures)} export-parity check(s)")
    print("  Regenerate with:")
    print("    python3 -m pipeline.history.export_history")
    print("    python3 -m pipeline.history.export_scripts")
    print("  and commit the result. A correction that does not ship is not a correction.")
    sys.exit(1)

print("\nPASS  the served History JSON matches the record it was exported from")
