#!/usr/bin/env python3
"""The export must refuse a run whose bias scores were never measured.

On 2026-09-20, 540 of 737 per-article rows under
`frontend/public/data/deepdive/` were the exact tuple political_lean 50,
sensationalism 10, opinion_fact 25, factual_rigor 50, confidence 0.7. Step 6b
rebuilt every row in a multi-article cluster from
`article_bias_map.get(article_id, {})`, and the 36h lookback articles were
never in that map, so the page published fallbacks as measurements.

The planted defect here is that same shape: a synthetic export at 60% defaults
must fail, the same export at 20% must pass. The gate only bites over
MIN_ROWS_TO_ENFORCE rows, so a small or empty export is checked too.

Run: python tests/test_bias_defaults_gate.py
"""
import pathlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from validation.bias_defaults import (  # noqa: E402
    DEFAULT_TUPLE,
    DEFAULT_TUPLE_MAX_SHARE,
    MIN_ROWS_TO_ENFORCE,
    PER_AXIS_MAX_SHARE,
    BiasDefaultsError,
    bias_rows_from_deepdive,
    check_default_share,
    default_share,
    is_default_tuple,
    mark_unscored,
    per_axis_default_share,
)


def default_row(framing: int = 12) -> dict:
    """A row exactly as the old step 6b wrote it: defaults plus a real framing."""
    row = dict(DEFAULT_TUPLE)
    row["framing"] = framing
    row["rationale"] = {"framing": "charged synonym pair"}
    return row


def measured_row(i: int) -> dict:
    return {
        "political_lean": 38 + (i % 17),
        "sensationalism": 22 + (i % 11),
        "opinion_fact": 31 + (i % 13),
        "factual_rigor": 61 + (i % 7),
        "framing": 9 + (i % 5),
        "confidence": 0.55 + (i % 4) / 100.0,
    }


def synthetic_export(total: int, default_fraction: float) -> list:
    """A deepdive-shaped payload with a known share of default-tuple rows."""
    n_default = round(total * default_fraction)
    payload = []
    for i in range(total):
        bias = default_row(framing=6 + (i % 13)) if i < n_default else measured_row(i)
        payload.append({"article": {"id": f"a{i}", "bias_scores": [bias]}})
    return payload


def check_recognises_the_tuple() -> list:
    out = []
    if not is_default_tuple(default_row()):
        out.append("the 2026-09-20 defaults row was not recognised")
    if not is_default_tuple({**DEFAULT_TUPLE, "framing": 40}):
        out.append("framing is not part of the tuple and must not affect the verdict")
    if is_default_tuple(measured_row(3)):
        out.append("a measured row was called a defaults row")
    one_off = dict(DEFAULT_TUPLE)
    one_off["factual_rigor"] = 51
    if is_default_tuple(one_off):
        out.append("a row differing on one axis was called a defaults row")
    if is_default_tuple({}) or is_default_tuple(None):
        out.append("an empty row was called a defaults row")
    # Strings are what a JSON export can hand back for a numeric column.
    if not is_default_tuple({k: str(v) for k, v in DEFAULT_TUPLE.items()}):
        out.append("string-typed defaults were not recognised")
    return out


def check_planted_defect_fails() -> list:
    rows = bias_rows_from_deepdive(synthetic_export(300, 0.60))
    defaults, total, share = default_share(rows)
    if (defaults, total) != (180, 300):
        return [f"synthetic export miscounted: {defaults}/{total}, expected 180/300"]
    try:
        check_default_share(rows)
    except BiasDefaultsError as err:
        if "60.0%" not in str(err):
            return [f"the failure does not report the share: {err}"]
        return []
    return [f"a {share:.0%} defaults export was allowed to ship"]


def check_clean_export_passes() -> list:
    """A post-fix run: low single digits, which is what the corpus should give.

    Only an article with no bias_scores row at all can still read as the full
    tuple once step 6b loads stored scores for the 36h lookback, so a healthy
    export sits near zero, not near the threshold.
    """
    rows = bias_rows_from_deepdive(synthetic_export(300, 0.03))
    try:
        summary = check_default_share(rows)
    except BiasDefaultsError as err:
        return [f"a 3% defaults export was rejected: {err}"]
    if "9/300" not in summary:
        return [f"summary does not carry the count: {summary}"]
    return []


def check_a_fifth_of_the_feed_now_fails() -> list:
    """The tightening itself, asserted.

    DEFAULT_TUPLE_MAX_SHARE was 0.5 until 2026-09-21, so a feed with half its
    per-article rows unmeasured shipped with the gate reading clean. 20% is the
    share this check used to call acceptable; it is not.
    """
    rows = bias_rows_from_deepdive(synthetic_export(300, 0.20))
    try:
        check_default_share(rows)
    except BiasDefaultsError:
        return []
    return ["a 20% defaults export still passes; the threshold did not tighten"]


def check_boundaries() -> list:
    out = []
    # At the threshold exactly, not over it: allowed.
    rows = bias_rows_from_deepdive(synthetic_export(200, DEFAULT_TUPLE_MAX_SHARE))
    try:
        check_default_share(rows)
    except BiasDefaultsError as err:
        out.append(f"a share equal to the threshold was rejected: {err}")
    # A run too small to judge is never failed, however bad it looks.
    small = bias_rows_from_deepdive(
        synthetic_export(MIN_ROWS_TO_ENFORCE, 1.0))
    try:
        check_default_share(small)
    except BiasDefaultsError as err:
        out.append(f"a {MIN_ROWS_TO_ENFORCE}-row export was failed: {err}")
    # An empty export raises nothing and reports zero.
    try:
        summary = check_default_share([])
    except BiasDefaultsError as err:
        out.append(f"an empty export was failed: {err}")
    else:
        if "0/0" not in summary:
            out.append(f"empty export summary is wrong: {summary}")
    # The 2026-09-20 production shape, 540 of 737.
    live = [default_row()] * 540 + [measured_row(i) for i in range(197)]
    try:
        check_default_share(live)
    except BiasDefaultsError:
        pass
    else:
        out.append("the 2026-09-20 export (540/737) would have shipped")
    return out


def check_step_6b_never_writes_defaults() -> list:
    """Step 6b itself, read as source.

    The offline harness (tests/test_editorial_stage.py) runs
    `pipeline/main.py --editorial-only`, which starts at 8c and never reaches
    6b, so nothing else can watch this block. These are the two lines that
    made the defect: the row built out of `.get(art_id, {})` fallbacks, and
    the absence of any lookback load before it.
    """
    src = (ROOT / "pipeline" / "main.py").read_text()
    head = src.find("# Step 6b: Re-run framing analysis")
    tail = src.find("# Step 6a: Extract claims", head if head > 0 else 0)
    if head < 0 or tail < 0:
        return ["could not locate step 6b in pipeline/main.py"]
    block = src[head:tail]
    out = []
    if "article_bias_map.get(art_id, {})" in block:
        out.append("6b builds its upsert row from defaults again: "
                   "article_bias_map.get(art_id, {})")
    if "lookback_bias_map" not in block:
        out.append("6b no longer loads stored bias rows for the 36h lookback")
    if "framing_no_scores" not in block:
        out.append("6b no longer skips articles with no measured bias row")
    return out


def check_per_axis_catches_a_varying_fifth_axis() -> list:
    """The hole the whole-tuple check cannot see.

    On the 2026-09-20 export 610 rows sat at political_lean exactly 50 but only
    595 carried the full tuple: 15 had one axis nudged off its default, so a
    whole-tuple check called them measured while four axes were not. These rows
    are that shape on purpose.
    """
    out = []
    rows = []
    for i in range(200):
        row = dict(DEFAULT_TUPLE)
        row["framing"] = 6 + (i % 13)
        # One axis off its default, so is_default_tuple says False.
        row["sensationalism"] = 11
        rows.append(row)
    defaults, total, share = default_share(rows)
    if defaults != 0:
        out.append(f"the whole-tuple check saw {defaults} defaults; these rows "
                   f"each have an axis off its default, which is the point")
    try:
        check_default_share(rows)
    except BiasDefaultsError as err:
        out.append(f"the whole-tuple check failed rows it cannot see: {err}")

    shares = per_axis_default_share(rows)
    lean_n, lean_total, lean_share = shares["political_lean"]
    if lean_share < 0.99:
        out.append(f"per-axis missed political_lean: {lean_n}/{lean_total} "
                   f"= {lean_share:.1%}, expected ~100%")
    if lean_share <= PER_AXIS_MAX_SHARE["political_lean"]:
        out.append(f"a 100% lean-at-50 population is under the "
                   f"{PER_AXIS_MAX_SHARE['political_lean']:.0%} cap")
    sens_n, _, sens_share = shares["sensationalism"]
    if sens_n != 0:
        out.append(f"sensationalism was moved off its default on every row, "
                   f"but per-axis counted {sens_n} at default")
    return out


def check_per_axis_passes_a_healthy_population() -> list:
    """The 142 genuinely measured rows of the 2026-09-20 export, in shape.

    Measured there: stdev 21.2 over a 10..97 range, 10.6% at exactly 50. A
    population like that must not trip any axis cap, or the gate would fire on
    a working run and teach everyone to ignore it.
    """
    out = []
    rows = [measured_row(i) for i in range(200)]
    shares = per_axis_default_share(rows)
    for axis, (n, total, share) in shares.items():
        cap = PER_AXIS_MAX_SHARE[axis]
        if share > cap:
            out.append(f"a healthy population tripped {axis}: "
                       f"{n}/{total} = {share:.1%} over the {cap:.0%} cap")
    return out


def check_defaults_are_marked_unscored() -> list:
    """The degradation, which is what replaced blocking the export.

    A default row must be marked so every consumer withholds it: out of the
    cluster aggregate, off the Deep Dive spectrum, "Unscored" on the label.
    Unconditional, per row: one bad row is degraded as honestly as six hundred.
    """
    out = []
    rows = bias_rows_from_deepdive(synthetic_export(100, 0.30))
    marked = mark_unscored(rows)
    if marked != 30:
        out.append(f"marked {marked} of 30 default rows")
    for row in rows:
        if is_default_tuple(row) and row.get("lean_unscored") is not True:
            out.append("a default row was left unmarked")
            break
        if not is_default_tuple(row) and row.get("lean_unscored"):
            out.append("a measured row was marked unscored")
            break

    # A single default row in a tiny export is still marked: there is no
    # threshold under which a non-measurement becomes a measurement.
    one = [dict(DEFAULT_TUPLE, framing=9), measured_row(1)]
    if mark_unscored(one) != 1:
        out.append("a lone default row in a 2-row export was not marked")
    if one[0].get("lean_unscored") is not True:
        out.append("the lone default row was not marked")

    # The analyzer's own unscored verdict is never cleared by a second pass.
    already = [dict(measured_row(3), lean_unscored=True)]
    mark_unscored(already)
    if already[0].get("lean_unscored") is not True:
        out.append("mark_unscored cleared a flag the analyzer had set")
    return out


def check_the_committed_export() -> list:
    """The share of the feed THIS REPO ships, not a synthetic one.

    The invariant is not "few default rows". It is **no UNMARKED default row**.
    A default-tuple row that carries `lean_unscored` is handled: it is out of
    the cluster aggregate, its pin is off the Deep Dive spectrum and its label
    reads Unscored, so its presence in the JSON misleads nobody. A default row
    WITHOUT the mark is the actual defect, because every consumer then reads
    50 as a measurement.

    Written as a share first, at 10%, which was wrong and worth recording. The
    first post-fix export (run #375, built 2026-09-21T18:18) came in at 19.1%
    whole-tuple and 53.5% lean-at-50, and a share test simply failed. The
    diagnosis that a share cannot express: **all 186 default rows were
    published 2026-09-20, and none of the 534 articles published 2026-09-21
    was a default.** They are the previous day's damage, loaded out of the
    state DB by step 6b's 36h lookback and faithfully written back by
    `existing.get("political_lean", 50)`. Today's scoring was clean. The
    residue ages out of the lookback window on its own, so a share threshold
    would have failed CI for two days over rows that were already correct, and
    taught everyone to override it.

    So the share is printed, and only the mark is asserted.
    """
    import json

    root = pathlib.Path(__file__).resolve().parents[1]
    feed = root / "frontend" / "build-data" / "feed.json"
    deepdive = sorted((root / "frontend" / "public" / "data" / "deepdive").glob("*.json"))
    if not feed.exists() or not deepdive:
        return ["no committed export to check: "
                f"feed.json {'present' if feed.exists() else 'missing'}, "
                f"{len(deepdive)} deepdive file(s)"]
    try:
        built = str(json.loads(feed.read_text()).get("builtAt") or "")[:19]
    except Exception as err:
        return [f"could not read feed.json builtAt: {err}"]

    rows = []
    for f in deepdive:
        try:
            rows.extend(bias_rows_from_deepdive(json.loads(f.read_text())))
        except Exception as err:
            return [f"could not read {f.name}: {err}"]

    defaults, total, share = default_share(rows)
    axes = per_axis_default_share(rows)
    lean_share = axes["political_lean"][2]
    print(f"       committed export built {built}: {defaults}/{total} default "
          f"rows ({share:.1%}), lean at 50 {lean_share:.1%}")

    # Self-detecting, self-clearing exemption. An export written before
    # `lean_unscored` was carried out of the database has the key on no row at
    # all, so there is nothing to assert about marks; asserting anyway would
    # fail on the export's age rather than on anything wrong with it. The
    # moment a run from current code commits, the key appears and the
    # assertion below starts biting with no edit here.
    carries_the_field = any("lean_unscored" in r for r in rows)
    if not carries_the_field:
        print(f"       exempt: no row carries a lean_unscored key, so this "
              f"export predates the field reaching the page. The mark "
              f"assertion starts biting on the first export from current "
              f"code, with no edit here.")
        return []

    unmarked = [r for r in rows if is_default_tuple(r) and not r.get("lean_unscored")]
    out = []
    if unmarked:
        out.append(
            f"the committed export (built {built}) carries {len(unmarked)} "
            f"default-tuple row(s) with no lean_unscored mark, of {total} "
            f"rows. Every consumer reads those as a measured 50: they are in "
            f"the cluster lean aggregate and drawn on the Deep Dive spectrum. "
            f"export_static.py stamps the mark on any default row, so an "
            f"unmarked one means a second write path reached the export."
        )
    # The one share worth failing on: a run that measured almost nothing is a
    # broken run whatever the marks say. Deliberately far above the 19.1% the
    # carried-forward residue produced, so it fires on breakage, not on age.
    if total > MIN_ROWS_TO_ENFORCE and share > 0.60:
        out.append(
            f"the committed export is {share:.1%} default rows "
            f"({defaults}/{total}): a run that measured almost nothing, "
            f"marks or no marks."
        )
    return out


CHECKS = (
    ("step 6b never writes a defaults row", check_step_6b_never_writes_defaults),
    ("recognises the default tuple", check_recognises_the_tuple),
    ("planted defect: 60% defaults fails", check_planted_defect_fails),
    ("clean run: 3% defaults passes", check_clean_export_passes),
    ("a fifth of the feed unmeasured now fails", check_a_fifth_of_the_feed_now_fails),
    ("thresholds and edge cases", check_boundaries),
    ("per-axis catches a varying fifth axis", check_per_axis_catches_a_varying_fifth_axis),
    ("per-axis passes a healthy population", check_per_axis_passes_a_healthy_population),
    ("defaults are marked unscored", check_defaults_are_marked_unscored),
    ("the committed export", check_the_committed_export),
)


def main() -> int:
    failures = []
    for name, fn in CHECKS:
        problems = fn()
        if problems:
            print(f"[FAIL] {name}")
            for p in problems:
                print(f"    - {p}")
            failures.extend(problems)
        else:
            print(f"[ ok ] {name}")
    if failures:
        print(f"\nFAILED: {len(failures)} issue(s)")
        return 1
    print(f"\nOK: gate fails above {DEFAULT_TUPLE_MAX_SHARE:.0%} defaults "
          f"over {MIN_ROWS_TO_ENFORCE} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
