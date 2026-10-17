"""Report how much of the PUBLISHED weekly issue can be illustrated.

Vol. I, No. 1 shipped with no photographs, and the fix (subject resolution
guarded by word overlap) cannot be honestly verified from a developer sandbox:
Wikimedia rate-limits shared egress IPs hard enough that a local run measures
the proxy, not the code. This runs the real lookup from CI, over the headlines
actually on the page, and prints what each one resolved to.

No Gemini call, no database, no writes. It reads the deploy tree and reports.

    python -m pipeline.media.probe_issue_images
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from media.image_search import find_cover_image_for_cluster  # noqa: E402

ISSUE = Path(__file__).resolve().parents[2] / "frontend/public/data/weekly.json"


def _listify(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return []
    return v or []


def main() -> int:
    if not ISSUE.exists():
        print(f"no published issue at {ISSUE}")
        return 1
    d = json.loads(ISSUE.read_text())

    targets = []
    for c in _listify(d.get("cover_text")):
        targets.append(("cover", c.get("headline"), c.get("cluster_title", "")))
    for e in _listify(d.get("departments")):
        targets.append(("department", e.get("headline") or e.get("label"), ""))
    for r in _listify(d.get("recap_stories")):
        targets.append(("brief", r.get("headline"), ""))

    hits = 0
    for kind, head, alt in targets:
        if not head:
            continue
        try:
            r = find_cover_image_for_cluster("probe", head, alt_title=alt or "")
        except Exception as e:
            r = None
            print(f"  [probe] {head[:40]!r} raised {e}")
        hits += bool(r)
        print(f"{'HIT ' if r else 'miss'} {kind:11} {(head or '')[:52]}")
        if r:
            print(f"        subject : {r.get('caption')}")
            print(f"        licence : {r['attribution'][:74]}")

    total = len([t for t in targets if t[1]])
    print(f"\n{hits}/{total} illustrated  (issue #{d.get('issue_number')}, "
          f"week of {d.get('week_start')})")
    # Reporting only. A low hit rate is a finding to read, not a build to fail:
    # the honest outcome for a headline naming no indexable subject is no
    # photograph, and failing here would pressure the next change to loosen
    # the guard that exists to prevent a wrong one.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
