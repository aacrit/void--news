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
fixed: `pipeline/export_static.py` calls `check_default_share` over the rows it
has just written, prints the share in the run summary, and raises when a run of
any size worth judging is mostly defaults.

`VOID_BIAS_DEFAULTS_GATE=warn` downgrades the raise to a printed warning, for
the one caller that exports a snapshot written before the fix:
`tests/test_editorial_stage.py` builds its DB from the committed 2026-09-20
deepdive files. The daily pipeline never sets it, and the line can go once a
post-fix feed has been committed.

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

# Above this share of default rows the export fails rather than ships.
DEFAULT_TUPLE_MAX_SHARE = 0.5

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


def format_summary(defaults: int, total: int, share: float) -> str:
    """One line for the export's run summary."""
    return (f"bias defaults: {defaults}/{total} per-article rows are the "
            f"default tuple ({share:.1%}; gate fails above "
            f"{DEFAULT_TUPLE_MAX_SHARE:.0%} over {MIN_ROWS_TO_ENFORCE} rows)")


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
