"""Tiny offline smoke test for the eval checks.

Runs entirely on mock clusters — NO Supabase, NO LLM, NO network. Asserts that
the deterministic checks flag the seeded defects. Run directly:

    python pipeline/evals/smoke_test.py

Exits non-zero on any assertion failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow both `python pipeline/evals/smoke_test.py` and `-m` invocation.
_PIPELINE_DIR = Path(__file__).resolve().parent.parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from evals import checks  # noqa: E402


def _mk(cluster_id, position, title, summary, member_titles,
        summary_tier="flash-lite", source_count=10, content_type="reporting"):
    members = [{"title": t, "source_id": f"src{i}"}
               for i, t in enumerate(member_titles)]
    return {
        "id": cluster_id, "position": position, "title": title,
        "summary": summary, "summary_tier": summary_tier,
        "content_type": content_type, "source_count": source_count,
        "category": "politics", "consensus_points": [], "divergence_points": [],
        "member_titles": member_titles, "member_articles": members,
    }


def main() -> int:
    # 1) CLEAN: summary matches the headline + members, has a tier, no dashes.
    clean = _mk(
        "c-clean", 1,
        "Senate Passes Infrastructure Bill After Late-Night Vote",
        "The Senate passed a major infrastructure bill after a late-night vote, "
        "sending the measure to the House.",
        ["Senate Passes Infrastructure Bill in Late-Night Vote",
         "Infrastructure Bill Clears Senate After Late Vote",
         "Senators Approve Infrastructure Package Overnight"],
    )

    # 2) BLANK SUMMARY: null summary + null tier => RF-4 CATASTROPHIC.
    blank = _mk(
        "c-blank", 2,
        "Central Bank Raises Interest Rates to Curb Inflation",
        "", ["Central Bank Raises Rates", "Bank Hikes Interest Rates on Inflation"],
        summary_tier="",
    )

    # 3) OFF-TOPIC SUMMARY: summary describes a totally different event than the
    #    cluster's member headlines => RF-1 cross-contamination candidate.
    offtopic = _mk(
        "c-offtopic", 3,
        "Wildfire Forces Evacuations Across Northern California",
        "A shipping company reported record quarterly earnings driven by higher "
        "freight volumes and container demand at Asian ports.",
        ["Wildfire Forces Thousands to Evacuate in Northern California",
         "California Wildfire Spreads as Firefighters Battle Flames",
         "Evacuation Orders Expand as Wildfire Grows"],
    )

    clusters = [clean, blank, offtopic]
    findings = checks.run_all_checks(clusters)

    by_cluster: dict[str, set[str]] = {}
    for f in findings:
        by_cluster.setdefault(f.cluster_id, set()).add(f.code)

    # --- assertions ---------------------------------------------------------
    # Clean cluster: no coverage/contamination/agreement red flags.
    clean_codes = by_cluster.get("c-clean", set())
    assert "RF-4" not in clean_codes, f"clean flagged RF-4: {clean_codes}"
    assert "RF-1" not in clean_codes, f"clean flagged RF-1: {clean_codes}"
    assert "RF-3" not in clean_codes, f"clean flagged RF-3: {clean_codes}"

    # Blank cluster: RF-4 CATASTROPHIC.
    blank_findings = [f for f in findings if f.cluster_id == "c-blank"]
    rf4 = [f for f in blank_findings if f.code == "RF-4"]
    assert rf4, "blank summary did not raise RF-4"
    assert rf4[0].grade == "CATASTROPHIC", f"RF-4 grade was {rf4[0].grade}"
    assert rf4[0].priority == "P0", f"RF-4 priority was {rf4[0].priority}"

    # Off-topic cluster: RF-1 contamination candidate with a judge payload.
    off_findings = [f for f in findings if f.cluster_id == "c-offtopic"]
    rf1 = [f for f in off_findings if f.code == "RF-1"]
    assert rf1, "off-topic summary did not raise RF-1"
    assert rf1[0].is_candidate, "RF-1 should be a judge candidate"
    assert rf1[0].judge_payload and rf1[0].judge_payload.get("member_titles"), \
        "RF-1 judge payload missing member_titles"

    # is_raw_excerpt port sanity.
    assert checks.is_raw_excerpt("Photo: A man walks past a building")
    assert checks.is_raw_excerpt("Reporting continuesThe ministerSaid moreHere")
    assert not checks.is_raw_excerpt(
        "The Senate passed a bill after a late-night vote.")

    # Scoring: a CATASTROPHIC caps the feed score at 40.
    score = checks.score_findings(findings)
    assert score.feed_score <= 40, f"feed_score not capped: {score.feed_score}"
    assert score.counts_by_grade["CATASTROPHIC"] >= 1
    assert score.n_candidates >= 1

    # Hygiene: an em dash in a summary raises RF-11.
    dashy = _mk("c-dash", 4, "Rates Rise Again",
                "The bank cut rates Tuesday — the third move this quarter.",
                ["Bank Cuts Rates Again", "Third Rate Cut This Quarter"])
    dash_findings = checks.check_hygiene([dashy])
    assert any(f.code == "RF-11" for f in dash_findings), \
        "em dash in summary did not raise RF-11"

    print(f"SMOKE OK: {len(findings)} findings across {len(clusters)} clusters; "
          f"feed_score={score.feed_score}; candidates={score.n_candidates}")
    for f in findings:
        print(f"  [{f.priority}] {f.code} {f.grade} #{f.position} "
              f"{f.cluster_id}: {f.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
