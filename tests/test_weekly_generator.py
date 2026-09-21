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

    # ── WG-05  The cluster read is a count, not a ceiling ──────────────────
    # Issues #23 and #26 BOTH published exactly "500 story clusters", because
    # `_fetch_week_clusters` was a bare .limit(500). Two for two on a round
    # number is a cap, not a measurement, and the colophon printed it as an
    # exact claim along with `total_articles`, which sums the same capped rows.
    print("\nWG-05  the week's clusters are paged, and the ceiling is flagged")

    class _FakeQuery:
        """Only what the query chain actually calls, plus honest ranging."""

        def __init__(self, rows):
            self._rows = rows
            self._start, self._end = 0, len(rows) - 1

        def select(self, *a, **k): return self
        def contains(self, *a, **k): return self
        def gte(self, *a, **k): return self
        def lte(self, *a, **k): return self
        def order(self, *a, **k): return self

        def range(self, start, end):
            self._start, self._end = start, end
            return self

        def execute(self):
            return type("R", (), {"data": self._rows[self._start:self._end + 1]})()

    class _FakeDB:
        def __init__(self, n):
            self._rows = [{"id": f"c{i}", "title": f"t{i}", "source_count": 1}
                          for i in range(n)]
            self.pages = 0

        def table(self, name):
            self.pages += 1
            return _FakeQuery(self._rows)

    from datetime import date
    real_db, real_max = g.supabase, g._CLUSTER_MAX
    try:
        # 1,200 clusters in the week. The old query returned 500 of them.
        g.supabase = _FakeDB(1200)
        rows, trunc = g._fetch_week_clusters("world", date(2026, 9, 14), date(2026, 9, 20))
        check("a week larger than one page is read whole", len(rows) == 1200, f"{len(rows)}")
        check("a complete read is NOT flagged truncated", trunc is False, str(trunc))
        check("it took more than one query", g.supabase.pages > 1, f"{g.supabase.pages} page(s)")

        # Exactly one page. A real 500 must not be slandered as a cap.
        g.supabase = _FakeDB(g._CLUSTER_PAGE)
        rows, trunc = g._fetch_week_clusters("world", date(2026, 9, 14), date(2026, 9, 20))
        check("a week that really is one page long reads whole",
              len(rows) == g._CLUSTER_PAGE, f"{len(rows)}")
        check("and is not flagged", trunc is False, str(trunc))

        # The hard ceiling. When it IS hit, the row must say so.
        g._CLUSTER_MAX = g._CLUSTER_PAGE * 2
        g.supabase = _FakeDB(g._CLUSTER_PAGE * 5)
        rows, trunc = g._fetch_week_clusters("world", date(2026, 9, 14), date(2026, 9, 20))
        check("the hard ceiling stops the read", len(rows) == g._CLUSTER_MAX, f"{len(rows)}")
        check("and the ceiling is flagged", trunc is True, str(trunc))
    finally:
        g.supabase, g._CLUSTER_MAX = real_db, real_max

    # The flag has to survive the whole way to the row the page reads.
    rep_text, rep_data = g._generate_bias_report(
        [{"title": "x", "divergence_score": 1}],
        {"total_scored": 10, "avg_lean": 50.0, "avg_sensationalism": 20.0,
         "avg_rigor": 70.0, "lean_std": 10.0, "truncated": False},
        "world", clusters_truncated=True)
    check("the bias payload carries clusters_truncated",
          rep_data.get("clusters_truncated") is True, str(rep_data.get("clusters_truncated")))
    check("the report text hedges the cluster count",
          "across more than 1 story clusters" in rep_text, rep_text.splitlines()[0])
    check("stats is left whole, so the page cannot render NaN",
          set(rep_data["stats"]) >= {"avg_lean", "lean_std", "total_scored"})

    # No bias stats at all still has to carry the flag: the colophon prints the
    # cluster count whether or not The Week in Bias renders.
    _, no_stats = g._generate_bias_report([{"title": "x"}], None, "world",
                                          clusters_truncated=True)
    check("the flag survives a week with no bias stats",
          no_stats.get("clusters_truncated") is True, str(no_stats))
    check("and no half-built stats object is emitted", "stats" not in no_stats)

    # ── WG-06  Sports & Culture must contain sport or culture ──────────────
    # Issue #26 filed a German federal election under Sports & Culture. The
    # cluster carried the category label and nothing checked its words.
    print("\nWG-06  the Sports & Culture gate reads the cluster, not the label")

    german_election = {
        "id": "de-1",
        "category": "Culture",
        "title": "German election: far-right AfD surges to strongest result since the war",
        "summary": ("Germany's federal election returned the far-right AfD to its "
                    "strongest position since the Second World War, reshaping the "
                    "coalition arithmetic in the Bundestag and unsettling the "
                    "cultural discourse around accusation and blame."),
    }
    real_sport = {
        "id": "sp-1",
        "category": "Sports",
        "title": "Premier League clubs vote to scrap the January transfer window",
        "summary": "Twenty clubs met at Wembley; the vote was 14 to 6.",
    }
    real_culture = {
        "id": "cu-1",
        "category": "Culture",
        "title": "Cannes jury gives the Palme d'Or to a first-time director",
        "summary": "The film was shot in eleven days on a single roll of stock.",
    }
    unlabelled_sport = {
        "id": "sp-2",
        "category": "World",
        "title": "Olympic host city loses its main stadium contractor",
        "summary": "The tournament opens in nine months.",
    }

    check("a German election is NOT sport or culture",
          g._is_sport_or_culture(german_election) is False)
    check("a Premier League vote is", g._is_sport_or_culture(real_sport) is True)
    check("a Palme d'Or is", g._is_sport_or_culture(real_culture) is True)
    check("the word 'war' inside a political summary does not qualify it",
          g._is_sport_or_culture(
              {"title": "Chancellor names new cabinet",
               "summary": "The war cabinet met for ninety minutes."}) is False)

    sports, calls = g._generate_sports([german_election], "world")
    check("a week whose only labelled cluster is an election runs WITHOUT the department",
          sports is None, str(sports))
    check("and spends no model call on it", calls == 0, str(calls))

    # The gate must not silence a real one, and must still reach past the label.
    check("a labelled sports cluster is still selected",
          [c["id"] for c in [german_election, real_sport] if g._is_sport_or_culture(c)]
          == ["sp-1"])
    check("an unlabelled sports cluster is still reachable",
          g._is_sport_or_culture(unlabelled_sport) is True)

    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly generator gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
