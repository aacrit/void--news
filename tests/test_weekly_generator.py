#!/usr/bin/env python3
"""Import the weekly generator and CALL it. No LLM key, no network, no cron.

WHY THIS FILE EXISTS. The first launch run of Vol. I, No. 1 wrote every
essay, spent every model call, passed every validator, and then died on the
last line before persistence:

    NameError: name '_cover_item' is not defined

`_issue_view` is a module-level function; `_cover_item` was nested inside
`generate_weekly_digest`, defined 960 lines below it and below the call site
too. `py_compile` cannot see that, and no existing gate could, because they
all reach the weekly through `weekly_parse` — the pure core — precisely to
avoid importing this module.

The reason given for that has been the import wall: `utils.supabase_client`
raises `EnvironmentError` without `VOID_SQLITE_PATH`. That is true, and it is
also a wall with a door in it. Point the variable at a throwaway file and the
module imports, applies its schema to an empty database, and every pure
function in it becomes reachable. Nobody had tried the door.

So: import the real module and exercise the functions a run actually calls,
with the committed fixture as input. A name that only resolves at runtime
fails here in under a second instead of after four minutes of paid
generation.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
_failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


def _import_generator():
    """Returns the module, or None with a reason when a DEPENDENCY is absent.

    A missing third-party package is an environment gap and skips. Anything
    else — a syntax error, a bad import inside our own code — is a real
    failure and is raised.
    """
    os.environ.setdefault("VOID_SQLITE_PATH",
                          str(Path(tempfile.mkdtemp(prefix="void-gen-")) / "probe.db"))
    sys.path.insert(0, str(ROOT / "pipeline"))
    try:
        from briefing import weekly_digest_generator as g
        return g, None
    except ModuleNotFoundError as e:
        # Only OUR modules failing to resolve is a defect; a missing wheel is not.
        if (e.name or "").split(".")[0] in ("briefing", "utils", "summarizer", "media"):
            raise
        return None, f"dependency not installed: {e.name}"


def main():
    print("void --weekly generator gates")
    g, skip = _import_generator()
    if skip:
        print(f"\n  SKIPPED: {skip}")
        print("  (run in a job that installs pipeline/requirements.txt)")
        return 0

    print("\nWG-01  the module imports against an empty state DB")
    check("weekly_digest_generator imported", g is not None)

    # ── WG-02  Every module-level name a run reaches actually resolves ──────
    print("\nWG-02  _issue_view builds the shape the audio rundown reads")
    fx = json.loads((FIXTURES / "weekly_inputs.json").read_text())
    covers = fx["cover_items"]

    view = g._issue_view(
        "world", "2026-09-14", "2026-09-20", 26,
        covers, fx["opinions"], fx["tech"], fx["sports"],
        {"stories": fx["recap_stories"]}, fx["bias_data"], fx["weekly_opinion"],
    )
    check("it returns a dict", isinstance(view, dict), type(view).__name__)
    for key in ("edition", "issue_number", "week_start", "week_end",
                "cover_headline", "cover_text", "opinions", "departments",
                "recap_stories", "bias_report_data", "opinion_text"):
        check(f"the view carries {key}", key in view)

    check("both cover features are present", len(view["cover_text"]) == len(covers),
          f"{len(view['cover_text'])} of {len(covers)}")
    check("every cover carries its text",
          all((c.get("text") or "").strip() for c in view["cover_text"]))
    check("departments were built from tech and sports",
          [d["slug"] for d in view["departments"]] == ["tech", "sports"],
          str([d.get("slug") for d in view["departments"]]))
    check("opinions carry a pair_id",
          any(o.get("pair_id") for o in view["opinions"]))

    # The image lookup must NOT happen here: it is a network call per feature
    # and the rundown never reads the result.
    check("the view does no image lookup",
          not any("image_url" in c for c in view["cover_text"]),
          "cover_text carries image keys, so _issue_view is fetching pictures")

    # ── WG-03  The rundown's own reader agrees with that shape ─────────────
    print("\nWG-03  the rundown can read the view")
    from briefing import weekly_rundown
    from briefing.weekly_script import _bench_columns

    cols = _bench_columns(view["opinions"])
    check("the bench finds its two columns", set(cols) == {"L", "R"}, str(sorted(cols)))
    prompt = weekly_rundown.build_prompt(view)
    check("the prompt is built", len(prompt) > 2000, f"{len(prompt)} chars")
    check("it puts the left column in verbatim", "THE LEFT COLUMN, verbatim" in prompt)
    check("it puts the right column in verbatim", "THE RIGHT COLUMN, verbatim" in prompt)
    check("it carries the numbers the NUMBERS segment may read",
          "THE NUMBERS" in prompt)

    # ── WG-04  _cover_core is shared, not duplicated ───────────────────────
    print("\nWG-04  the cover core is one definition")
    core = g._cover_core(covers[0])
    for key in ("headline", "text", "timeline", "numbers", "cluster_id",
                "days_active", "week_sources"):
        check(f"the core carries {key}", key in core)
    check("the core adds no picture", "image_url" not in core)

    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly generator gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
