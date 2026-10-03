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

    # ── WG-07  The week is read from what Void printed ─────────────────────
    # The 2026-09-27 issue read story_clusters, which step 8c.1 prunes to two
    # days: its covers saw Friday and Saturday, its second cover was a Spanish
    # local crime cluster that never reached the front page, and the run died
    # on a summary decoded to a list. printed_stories keeps every day's top 20.
    print("\nWG-07  the week comes from the printed record, every day of it")
    from datetime import datetime, timezone
    conn = g.supabase._conn
    days = [f"2026-09-{d}" for d in range(21, 28)]
    for d in days:
        conn.execute("INSERT OR IGNORE INTO printed_days (printed_on) VALUES (?)", (d,))

    def put(pid, day, pos, title, summary, thread, src=20, rank=50.0):
        conn.execute(
            "INSERT INTO printed_stories (id, printed_on, edition_position, source_cluster_id,"
            " title, summary, rank_world, source_count, story_thread_id)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, day, pos, "c-" + pid, title, summary, rank, src, thread))

    hormuz = "Iran offers to reopen the Strait of Hormuz if the US lifts its naval blockade of Iranian ports."
    for i, d in enumerate(days[:5]):
        put(f"h{i}", d, 1, f"Iran Offers to Reopen Strait of Hormuz, Day {i}", hormuz, "t-hormuz", 40, 90.0)
    ban = "A federal judge ordered the White House to end its ban on network television reporters."
    for i, d in enumerate(days[1:4]):
        put(f"b{i}", d, 2, "White House Media Ban Ordered Lifted by Judge", ban, "t-ban", 30, 80.0)
    # Misfiled by the daily threader under the media-ban thread (as on 09-24).
    put("x0", days[3], 3, "Trump Hails Friendship With Xi Jinping During State Visit",
        "Chinese President Xi Jinping met President Trump in Washington on a state visit.",
        "t-ban", 20, 99.0)
    for i, d in enumerate(days):
        put(f"o{i}", d, 5, f"Flooding Displaces Families in Region {i}",
            f"Floods in region {i} displaced families and closed roads, officials said.", f"t-o{i}", 8, 30.0)
    put("e0", days[6], 6, "A Headline With No Summary", "", "t-empty", 50, 95.0)
    put("j0", days[6], 7, "{Unknown}", "[1, 2]", "t-json", 5, 10.0)  # prose shaped like JSON
    conn.commit()

    ws = datetime(2026, 9, 21, tzinfo=timezone.utc)
    we = datetime(2026, 9, 27, 23, 59, 59, tzinfo=timezone.utc)
    printed = g._fetch_week_printed(ws, we)
    check("the printed read spans the whole week",
          sorted({r["printed_on"] for r in printed}) == days)
    check("a printed row with no summary is not a story",
          not any(r["title"] == "A Headline With No Summary" for r in printed))
    check("prose shaped like JSON comes back as text",
          all(isinstance(r["title"], str) and isinstance(r["summary"], str) for r in printed))
    threads = g._link_story_threads(printed)
    hz = [t for t in threads if "Hormuz" in t["title"]]
    check("a story printed five days is one five-day thread",
          len(hz) == 1 and hz[0]["daily_appearances"] == 5,
          f"{[(t['title'], t['daily_appearances']) for t in hz]}")
    check("a row the daily threader misfiled is not joined to that thread",
          not any("Xi" in c["title"] and any("Media Ban" in o["title"] for o in t["clusters"])
                  for t in threads for c in t["clusters"]))
    top = g._score_weekly_threads(threads, [], "world")
    check("the lead cover is the story the week printed most",
          bool(top) and "Hormuz" in top[0]["title"], top[0]["title"] if top else "none")
    recap = g._spread_over_week(g._one_per_thread(printed), 10)
    check("the recap spans the week, not one day",
          len({r["printed_on"] for r in recap}) >= 5,
          f"{sorted({r['printed_on'] for r in recap})}")

    # ── WG-08  The writer is told the words that drop its piece ────────────
    print("\nWG-08  the drop list reaches the prompt, and agrees with the rule")
    from utils.prohibited_terms import SLOP_PROMPT_WORDS, find_slop
    unmatched = [w for w in SLOP_PROMPT_WORDS if not find_slop(f"They {w} here.")]
    check("every word the prompt bans is one the rule drops", not unmatched, f"{unmatched}")
    seen = []
    real = g._smart_generate_text
    g._smart_generate_text = lambda prompt, system_instruction=None, **kw: (
        seen.append(system_instruction) or "Headline\n\nBody text.")
    try:
        g._gen_essay("p", "SYSTEM", label="probe")
    finally:
        g._smart_generate_text = real
    check("an essay prompt carries the drop list",
          bool(seen) and all(w in seen[0] for w in ("robust", "underscore", "multifaceted")))

    # ── WG-12  A short sourced piece is not padded ─────────────────────────
    # Issue #26's Greenland cover was asked for 800-1200 words from ONE printed
    # story of about 450 words. The writer reached past the story to fill the
    # brief, and seventeen of its claims had to be cut. The brief is sized to
    # the printed rows now, and a piece inside that brief is not regenerated.
    print("\nWG-12  a short sourced piece is sized to its sources, and not padded")
    one_row = {
        "id": "c-gl", "printed_on": "2026-09-19", "title": "Denmark, Greenland Affirm Sovereignty",
        "summary": " ".join(["Denmark and Greenland said the agreement respects sovereignty."] * 20),
        "consensus_points": ["The agreement is expected to be signed next week."],
        "divergence_points": [], "source_count": 13, "first_published": "2026-09-19T08:00:00+00:00",
    }
    thread = {"lead_cluster": one_row, "clusters": [one_row], "title": one_row["title"],
              "cumulative_sources": 13, "daily_appearances": 1}
    words = g.source_words([one_row])
    prompts, replies = [], []

    def fake_text(prompt, system_instruction=None, **kw):
        prompts.append(prompt)
        return replies[min(len(prompts) - 1, len(replies) - 1)]

    short_essay = "Greenland Holds Its Line\n\n" + " ".join(
        ["Denmark and Greenland said the agreement respects sovereignty."] * 22)
    real_text, real_sleep = g._smart_generate_text, g.time.sleep
    g._smart_generate_text, g.time.sleep = fake_text, (lambda *_: None)
    try:
        replies[:] = [short_essay]
        covers, calls = g._generate_cover_stories([thread], "world")
    finally:
        g._smart_generate_text, g.time.sleep = real_text, real_sleep
    spec = covers[0].get("_spec") if covers else None
    check("the cover brief is sized to the printed words, not 800-1200",
          bool(spec) and spec["max_words"] <= words and "800-1200" not in prompts[0],
          f"{spec} from {words} source words")
    check("the writer is handed the consensus points, not just title and summary",
          "expected to be signed next week" in prompts[0])
    check("a piece inside its sized brief is not regenerated to add words", calls == 1, f"{calls}")
    check("a thread with almost nothing printed gets no cover and spends no call",
          g.sized_spec(g.ESSAY_SPECS["cover"], 40) is None)

    # ── WG-13  Length is checked AFTER the cut ─────────────────────────────
    print("\nWG-13  length is measured on what survived grounding and the source check")
    sized = {"min_words": 270, "max_words": 450}
    fragment = {"text": "One sentence survived the source check.", "_spec": sized}
    short_ok = {"text": " ".join(["A sourced sentence stands here."] * 30), "_spec": sized}
    kept = g._after_cut("cover", [fragment, short_ok])
    check("a piece cut to a fragment does not ship", fragment not in kept)
    check("a piece cut short, but past the fragment line, ships short", short_ok in kept)
    src = (ROOT / "pipeline" / "briefing" / "weekly_digest_generator.py").read_text()
    run = src[src.index("def generate_weekly_digest"):]
    check("the length check runs after the source check, in the run itself",
          run.index('_after_cut("cover", covers)') > run.index("check_piece(c.get(\"text\")")
          and run.index("check_piece(c.get(\"text\")") > run.index("ground_text(text, src)"))
    check("an unsourced quotation is cut at write time, before the source check",
          run.index("ground_quotes(kept, qsrc)") < run.index("check_piece(c.get(\"text\")"))
    # W-T21b: the 2026-10-03 run handed every check call the whole printed
    # week (407,306 chars) and the model marked 10 of 10 recap briefs wholly
    # unsupported. Each piece is read against its own rows now.
    sc = run[run.index("── SOURCE CHECK ──"):run.index("LENGTH, AGAIN")]
    check("the source check reads each piece against its own evidence, not the whole week",
          "select_evidence(" in sc and "source_text(story_pool)" not in sc
          and sc.count("missing=") >= 3 and "errors=check_errors" in sc)

    # ── WG-14  A kill-list sentence is cut, and the piece is kept ──────────
    print("\nWG-14  the kill list cuts the sentence, not the piece")
    body = " ".join(["The council met on Tuesday and voted."] * 12)
    slop_essay = ("A Vote in the Council\n\n" + body
                  + " This incident underscores the vulnerability of the council. " + body)
    real_text = g._smart_generate_text
    g._smart_generate_text = lambda prompt, system_instruction=None, **kw: slop_essay
    try:
        r, n = g._gen_essay("p", "SYSTEM", spec={"min_words": 50, "max_words": 200}, label="probe")
    finally:
        g._smart_generate_text = real_text
    check("the piece ships", r is not None)
    check("without the sentence that carried the term",
          r is not None and "underscores" not in r["text"] and r["text"].count("The council met") == 24)
    check("the department switch is OFF by default (decision 5)", g.WEEKLY_DEPARTMENTS is False)
    check("a lowercase taxonomy label nominates a tech cluster",
          g._category({"category": "science"}) in g.TECH_CATEGORIES
          and g._category({"category": "Culture"}) in g.SPORTS_CATEGORIES)

    # ── WG-15  The audio band floats with the sourced words ────────────────
    print("\nWG-15  The Argument's band floats with the issue's sourced words, floor 14")
    from briefing.weekly_script import target_minutes, FLOOR_MINUTES, TARGET_MINUTES
    from briefing import weekly_rundown
    thin = {"opinion_text": "word " * 1500, "edition": "world", "opinions": []}
    full = {"opinion_text": "word " * 6000, "edition": "world", "opinions": []}
    check("a full issue keeps 18-22", target_minutes(full) == TARGET_MINUTES, str(target_minutes(full)))
    lo, hi = target_minutes(thin)
    check("a thin issue floats down, and never under 14",
          lo == FLOOR_MINUTES and hi < TARGET_MINUTES[1], f"{(lo, hi)}")
    asked = []
    weekly_rundown.generate(thin, lambda p, system_instruction=None: asked.append(system_instruction) or None)
    check("the rundown prompt asks for the floated band, not 18-22",
          bool(asked) and f"{lo:.0f} to {hi:.0f} minutes" in asked[0], (asked[0] if asked else "")[:0])

    # ── WG-09  A week with nothing in it stores nothing, and says so ───────
    print("\nWG-09  an empty week reports zero issues stored")
    stored = g.generate_weekly_digest(editions=["world"], week_offset=60)
    check("an empty week stores no issue, so the CLI exits non-zero", stored == 0, f"{stored}")
    src = (ROOT / "pipeline" / "briefing" / "weekly_digest_generator.py").read_text()
    check("the CLI fails when no issue was stored",
          "if not generate_weekly_digest(" in src and "sys.exit(1)" in src)

    # ── WG-10  A failed render ships the issue without audio ───────────────
    print("\nWG-10  The Argument failing does not discard the issue")
    src = (ROOT / "pipeline" / "briefing" / "weekly_digest_generator.py").read_text()
    body = src[src.index("        if not argument:"):src.index("        # A floor under what gets published")]
    check("no exception is raised when The Argument does not render",
          "raise" not in body, body.strip()[:80])
    check("the failure is still an Actions error annotation", "::error" in body)

    # ── WG-11  With no model, nothing is published ─────────────────────────
    print("\nWG-11  a run with no model stores no issue")
    import os as _os
    _os.environ["DISABLE_GEMINI"] = "1"
    _os.environ["DISABLE_AUDIO"] = "1"
    g._produce_argument = lambda *a, **k: (None, 0)
    g.find_cover_image_for_cluster = lambda *a, **k: None
    g.time.sleep = lambda *_: None
    real_window = g.weekly_window
    g.weekly_window = lambda now, off: (datetime(2026, 9, 21, tzinfo=timezone.utc),
                                        datetime(2026, 9, 27, 23, 59, 59, tzinfo=timezone.utc), 27)
    try:
        stored = g.generate_weekly_digest(editions=["world"], week_offset=0)
    finally:
        g.weekly_window = real_window
    check("summaries re-printed under a Weekly masthead are not stored", stored == 0, f"{stored}")

    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly generator gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
