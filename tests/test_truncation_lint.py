#!/usr/bin/env python3
"""A capped query must not have its length published as an exact count.

`_fetch_week_clusters` ended in a bare `.limit(500)`. Both archived Weekly
issues reported `total_clusters: 500`, hitting the cap exactly, two for two,
and the Colophon printed "Assembled from 2,355 articles in 500 story clusters"
as a fact. The real number was unknown and larger. Its sibling
`_fetch_bias_stats` had been given a `truncated` flag in rev 71; this one was
missed, and nothing noticed for two issues.

There are 75 `.limit(` calls in this pipeline and almost all of them are fine:
a cap on work is not a lie, a cap reported as a total is. So this does not
police caps. It policies the one shape that produced the error: a function that
caps a query AND publishes a length as a count AND has no way to say the number
is a floor.

A function trips this if all three hold:
  1. it contains a `.limit(...)` call with a cap that is not literally 1;
  2. it stores a `len(...)` under a key or name that reads as a total;
  3. it never mentions `truncated`, `capped`, `at_least` or `is_floor`.

The fix is never to delete the count. It is to page the query, or to carry a
flag so the page can say "more than", which `Colophon.tsx` already renders.
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOTS = [ROOT / "pipeline", ROOT / "scripts"]

# "total" or "count" as a whole word. Deliberately not a bare "n": `n_single`
# in source_track_record is a matrix split index, not a published number, and a
# lint that cries wolf gets an allowlist entry instead of a fix.
COUNT_NAME = re.compile(r"(^|_)(total|totals|count|counts)($|_)", re.IGNORECASE)
HONEST = ("truncated", "capped", "at_least", "is_floor", "more_than")

# Sites reviewed and judged not to publish a count. Each needs a reason, so
# that adding one is a decision somebody made rather than a line somebody
# pasted. A file only silences the sites named here, never the whole file.
REVIEWED: dict[str, str] = {
    # module::function -> why its cap cannot reach a published count
    "scripts/snapshot_feed.py::main":
        "`count` is the length of the snapshot this file writes, not the size "
        "of the population it was drawn from. It is exact and stays exact.",
}

failures: list[str] = []


def caps(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "limit" and n.args):
            a = n.args[0]
            if isinstance(a, ast.Constant) and a.value == 1:
                continue
            return True
    return False


def published_counts(node: ast.AST) -> list[str]:
    """Names and dict keys that receive a len() inside this function."""
    out = []
    for n in ast.walk(node):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "len"):
            continue
        for parent in ast.walk(node):
            # len() as a dict value: {"total_clusters": len(rows)}
            if isinstance(parent, ast.Dict):
                for k, v in zip(parent.keys, parent.values):
                    if v is n and isinstance(k, ast.Constant) and \
                            isinstance(k.value, str) and COUNT_NAME.search(k.value):
                        out.append(k.value)
            # len() assigned to a name: total_clusters = len(rows)
            if isinstance(parent, ast.Assign) and parent.value is n:
                for t in parent.targets:
                    if isinstance(t, ast.Name) and COUNT_NAME.search(t.id):
                        out.append(t.id)
                    if isinstance(t, ast.Subscript) and \
                            isinstance(t.slice, ast.Constant) and \
                            isinstance(t.slice.value, str) and \
                            COUNT_NAME.search(t.slice.value):
                        out.append(t.slice.value)
    return sorted(set(out))


checked = 0
for root in ROOTS:
    for path in sorted(root.rglob("*.py")):
        if "test_" in path.name:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            failures.append(f"{path.relative_to(ROOT)}: does not parse: {exc}")
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not caps(fn):
                continue
            checked += 1
            names = published_counts(fn)
            if not names:
                continue
            body = ast.get_source_segment(path.read_text(encoding="utf-8"), fn) or ""
            if any(h in body for h in HONEST):
                continue
            key = f"{path.relative_to(ROOT)}::{fn.name}"
            if key in REVIEWED:
                continue
            failures.append(
                f"{key} caps a query and publishes {', '.join(names)} "
                f"as an exact count, with no truncation flag"
            )

if failures:
    print(f"FAIL  {len(failures)} capped-count site(s)")
    for f in failures:
        print(f"  - {f}")
    print("\n  Fix: page the query, or carry a `truncated` flag through to the "
          "page so it can say 'more than'. Do not delete the count.")
    print("  If the cap genuinely cannot reach a published number, add the site "
          "to REVIEWED with a reason.")
    sys.exit(1)

# A lint nobody has watched fail is not a lint. Plant the exact shape the
# Weekly shipped and assert this file would have rejected it.
PLANTED = '''
def _fetch_week_clusters(sb, start, end):
    rows = (sb.table("story_clusters").select("*")
            .gte("first_seen", start).lte("first_seen", end)
            .order("headline_rank", desc=True).limit(500).execute()).data or []
    return {"clusters": rows, "total_clusters": len(rows)}
'''
planted = ast.parse(PLANTED)
fn = next(n for n in ast.walk(planted) if isinstance(n, ast.FunctionDef))
if not (caps(fn) and published_counts(fn) == ["total_clusters"]):
    print("FAIL  the lint no longer catches the defect it was written for")
    sys.exit(1)

# And the fixed shape must pass, or the lint would just ban counting.
FIXED = PLANTED.replace(
    'return {"clusters": rows, "total_clusters": len(rows)}',
    'return {"clusters": rows, "total_clusters": len(rows), "truncated": len(rows) >= 500}')
fixed_fn = next(n for n in ast.walk(ast.parse(FIXED)) if isinstance(n, ast.FunctionDef))
if "truncated" not in (ast.get_source_segment(FIXED, fixed_fn) or ""):
    print("FAIL  the lint does not recognise the fix")
    sys.exit(1)

print("PASS  the lint still catches the Weekly's capped-count shape")
print(f"PASS  {checked} capped quer(ies): none publishes its cap as a count")
