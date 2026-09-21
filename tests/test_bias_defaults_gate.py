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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

from validation.bias_defaults import (  # noqa: E402
    DEFAULT_TUPLE,
    DEFAULT_TUPLE_MAX_SHARE,
    MIN_ROWS_TO_ENFORCE,
    BiasDefaultsError,
    bias_rows_from_deepdive,
    check_default_share,
    default_share,
    is_default_tuple,
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
    rows = bias_rows_from_deepdive(synthetic_export(300, 0.20))
    try:
        summary = check_default_share(rows)
    except BiasDefaultsError as err:
        return [f"a 20% defaults export was rejected: {err}"]
    if "60/300" not in summary:
        return [f"summary does not carry the count: {summary}"]
    return []


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


CHECKS = (
    ("step 6b never writes a defaults row", check_step_6b_never_writes_defaults),
    ("recognises the default tuple", check_recognises_the_tuple),
    ("planted defect: 60% defaults fails", check_planted_defect_fails),
    ("clean run: 20% defaults passes", check_clean_export_passes),
    ("thresholds and edge cases", check_boundaries),
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
