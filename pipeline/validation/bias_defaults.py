"""The default-tuple gate: refuse to export a run whose bias scores were not measured.

Step 6b used to rebuild every per-article `bias_scores` row from
`article_bias_map.get(article_id, {})`. Articles that entered clustering from
the 36h lookback were never in that map, so their rows were written from the
fallbacks instead of their own measurement, and yesterday's numbers were
overwritten with

    political_lean 50, sensationalism 10, opinion_fact 25,
    factual_rigor 50, confidence 0.7

On the 2026-09-20 export, 540 of 737 rows under
`frontend/public/data/deepdive/` carried exactly that tuple: the page showed a
measurement it had not made. `framing` is deliberately NOT part of the tuple,
because the defaults rows carried a real, varying framing score (that was the
one axis 6b had just computed).

The bug is fixed in `pipeline/main.py`. This module is the control that keeps it
fixed, and after the 2026-09-21 audit it does two separate jobs.

**It degrades, it does not block (CEO, 2026-09-21).** A default-tuple row is
not a measurement, so `mark_unscored` stamps `lean_unscored` on it and the
export carries that flag through to the page: the article is left out of the
cluster lean aggregate, its dot is left off the Deep Dive spectrum, and its
label reads "Unscored" instead of drawing a measurement nobody made. That
happens per row, with no threshold to argue about, and the news still ships. A
failing gate that stopped the daily export would cost readers the newspaper to
protect one axis of one panel.

**The share is a regression alarm, not a kill switch.** `check_default_share`
still raises, but its caller is now `tests/test_bias_defaults_gate.py` over the
COMMITTED export, so a regression fails CI (visible, blocks a merge) instead of
failing the newspaper. `export_static.py` prints the share and the per-axis
breakdown every run and ships.

Why a per-axis share as well as the whole-tuple one. Three counts on the same
2026-09-20 export, and the gaps between them are the hole:

    540 of 737 (73.3%)  match all five keys of DEFAULT_TUPLE, confidence included
    595 of 737 (80.7%)  match the four SCORE axes, whatever the confidence
    610 of 737 (82.8%)  sit at political_lean exactly 50

So a whole-tuple check clears 70 rows whose lean was never measured, because
one other axis moved. `PER_AXIS_MAX_SHARE` closes that. The thresholds differ
by axis because a default is not equally suspicious on each: lean 50 is also
what a genuinely centrist wire item scores, while sensationalism exactly 10
almost never is.

What the same audit REFUTED, so nobody re-derives it: the hypothesis in
`docs/OPEN-ITEMS.md` that `source_map.get(slug, {"political_lean_baseline":
"center"})` at `pipeline/main.py` was silently anchoring articles to centre.
Every source name in the export matched the roster (0 misses in 737 rows), and
on the 142 rows that were genuinely measured the baseline ladder came through
monotonically (far-left 30, left 35, centre-left 46, centre 50, centre-right
52, right 58, far-right 61) with stdev 21.2 across the full 10..97 range. The
analyzer and the outlet baselines were doing their job; the rows that were
never scored were the whole of the "80% of sources read as centre" figure.

Stdlib only, no DB, no pipeline imports, so `tests/test_bias_defaults_gate.py`
runs it without `VOID_SQLITE_PATH` or spaCy.
"""

# The exact tuple step 6b used to write when it had nothing measured.
DEFAULT_TUPLE = {
    "political_lean": 50,
    "sensationalism": 10,
    "opinion_fact": 25,
    "factual_rigor": 50,
    "confidence": 0.7,
}

# Above this share of whole-tuple default rows, something is structurally
# wrong with the bias step. 0.5 until 2026-09-21, which would have let half a
# feed ship unmeasured; post-fix a real corpus should sit in the low single
# digits, because only an article with no bias_scores row at all can still
# read as the full tuple.
DEFAULT_TUPLE_MAX_SHARE = 0.10

# Per-axis default shares. Higher than the whole-tuple threshold because a
# single axis at its default is not by itself evidence of a miss: lean 50 is
# also what a genuinely centrist wire item scores, and a short item can
# honestly land on a round number. These are the points past which the
# population stops looking like a measurement. On the damaged 2026-09-20
# export political_lean was 82.8% at exactly 50 against the 40% below, and
# every one of the four axes was over its cap.
PER_AXIS_MAX_SHARE = {
    "political_lean": 0.40,
    "sensationalism": 0.60,
    "opinion_fact": 0.60,
    "factual_rigor": 0.60,
}

# Small runs (a test export, a single-cluster rebuild) can legitimately be all
# defaults by coincidence, so the gate only bites once there are real numbers.
MIN_ROWS_TO_ENFORCE = 100


class BiasDefaultsError(RuntimeError):
    """Raised when an export carries more default-tuple rows than the gate allows."""


def _num(value):
    """Return value as a float, or None when it is missing or not a number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_default_tuple(bias) -> bool:
    """True when every axis in DEFAULT_TUPLE equals its default in this row."""
    if not isinstance(bias, dict):
        return False
    for key, expected in DEFAULT_TUPLE.items():
        got = _num(bias.get(key))
        if got is None or abs(got - expected) > 1e-9:
            return False
    return True


def default_share(rows) -> tuple:
    """Count default-tuple rows in an iterable of bias dicts.

    Returns (defaults, total, share). An empty input gives (0, 0, 0.0).
    """
    total = 0
    defaults = 0
    for bias in rows:
        if not isinstance(bias, dict):
            continue
        total += 1
        if is_default_tuple(bias):
            defaults += 1
    share = (defaults / total) if total else 0.0
    return defaults, total, share


def per_axis_default_share(rows) -> dict:
    """Share of rows sitting exactly on each axis's default, per axis.

    Returns {axis: (at_default, total, share)}. Catches the case a whole-tuple
    check cannot: four axes unmeasured while a fifth varies, which is what 15
    rows on the 2026-09-20 export looked like.
    """
    counts = {k: 0 for k in PER_AXIS_MAX_SHARE}
    total = 0
    for bias in rows:
        if not isinstance(bias, dict):
            continue
        total += 1
        for axis in counts:
            got = _num(bias.get(axis))
            if got is not None and abs(got - DEFAULT_TUPLE[axis]) <= 1e-9:
                counts[axis] += 1
    return {
        axis: (n, total, (n / total) if total else 0.0)
        for axis, n in counts.items()
    }


def mark_unscored(rows) -> int:
    """Stamp `lean_unscored` on every default-tuple row. Returns how many.

    THE degradation, and the reason this module no longer blocks an export. A
    row carrying the whole default tuple is not a measurement of anything, so
    it is marked at the source and every consumer already knows what to do with
    the flag: the cluster aggregate excludes it (`pipeline/main.py`), the Deep
    Dive spectrum leaves its dot off, and the label reads "Unscored".

    Unconditional and per row: there is no share to argue about, and one bad
    row is degraded exactly as honestly as six hundred. It only ever sets the
    flag, never clears it, so a row the analyzer already marked unscored (an
    unrated outlet whose article showed no textual signal) keeps its mark.
    """
    marked = 0
    for bias in rows:
        if isinstance(bias, dict) and is_default_tuple(bias):
            bias["lean_unscored"] = True
            marked += 1
    return marked


def format_summary(defaults: int, total: int, share: float) -> str:
    """One line for the export's run summary."""
    return (f"bias defaults: {defaults}/{total} per-article rows are the "
            f"default tuple ({share:.1%}; CI fails above "
            f"{DEFAULT_TUPLE_MAX_SHARE:.0%} over {MIN_ROWS_TO_ENFORCE} rows). "
            f"All of them are marked unscored and kept out of the aggregate.")


def format_per_axis(shares: dict) -> str:
    """One line per axis for the run summary, worst first."""
    out = []
    for axis, (n, total, share) in sorted(
        shares.items(), key=lambda kv: -kv[1][2]
    ):
        cap = PER_AXIS_MAX_SHARE[axis]
        flag = "  OVER" if (total > MIN_ROWS_TO_ENFORCE and share > cap) else ""
        out.append(f"    {axis:16s} {n:5d}/{total:<5d} {share:6.1%}  "
                   f"(cap {cap:.0%}){flag}")
    return "bias per-axis defaults:\n" + "\n".join(out)


def check_default_share(
    rows,
    max_share: float = DEFAULT_TUPLE_MAX_SHARE,
    min_rows: int = MIN_ROWS_TO_ENFORCE,
) -> str:
    """Raise BiasDefaultsError when too many exported rows are unmeasured.

    Returns the summary line so the caller can print it either way.
    """
    defaults, total, share = default_share(rows)
    summary = format_summary(defaults, total, share)
    if total > min_rows and share > max_share:
        raise BiasDefaultsError(
            f"{summary}. Scores this close to the defaults were not measured: "
            f"check that step 6b is loading stored bias rows for the 36h "
            f"lookback instead of upserting fallbacks over them "
            f"(pipeline/main.py, step 6b)."
        )
    return summary


def bias_rows_from_deepdive(payload):
    """Pull the bias dicts out of one deepdive/<cluster>.json payload."""
    out = []
    for row in payload or []:
        if not isinstance(row, dict):
            continue
        article = row.get("article") or {}
        for bias in article.get("bias_scores") or []:
            if isinstance(bias, dict):
                out.append(bias)
    return out
