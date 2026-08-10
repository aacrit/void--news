"""
Offline unit tests for the Phase-3 summary hygiene post-checks in
cluster_summarizer.py. Pure functions, no network, no DB. Run with:

    cd pipeline && python -m summarizer.test_summary_postchecks

Each test asserts (a) the target defect is repaired AND (b) a clean control
summary is left untouched (the "never corrupt a clean summary" invariant).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from summarizer import cluster_summarizer as c  # noqa: E402


def _wc(s):
    return len(s.split())


# ---------------------------------------------------------------------------
# 3a — hard 90-word trim to a sentence boundary
# ---------------------------------------------------------------------------
def test_trim_over_cap_to_sentence_boundary():
    # 5 sentences of 30 words each = 150 words; cap should keep whole sentences.
    sent = " ".join(["word"] * 29) + " end."
    long = " ".join([sent] * 5)
    assert _wc(long) == 150
    out = c._trim_summary_to_word_cap(long)
    assert _wc(out) <= 90, _wc(out)
    # Kept only complete sentences (each ends with "end.").
    assert out.strip().endswith("end.")
    # Trimmed to the last complete sentence at or under cap -> 3 sentences (90w).
    assert out.count("end.") == 3, out.count("end.")


def test_trim_noop_when_within_cap():
    clean = "The senate passed the bill Tuesday. 60 members voted yes."
    assert c._trim_summary_to_word_cap(clean) == clean


def test_trim_first_sentence_exceeds_cap():
    huge = " ".join(["token"] * 200) + "."
    out = c._trim_summary_to_word_cap(huge)
    assert _wc(out) <= 90
    assert out.rstrip().endswith(".")


# ---------------------------------------------------------------------------
# 3b — drop terminal restatement of the lead
# ---------------------------------------------------------------------------
def test_drop_terminal_restatement():
    # Final sentence's content words (firefighters, battled, 102, fires,
    # overnight) all appear earlier -> pure restatement, dropped.
    s = ("Firefighters battled 102 fires across the region overnight. "
         "Governor Lopez called in 400 troops to help. "
         "Firefighters battled the 102 fires overnight.")
    out = c._drop_terminal_restatement(s)
    assert out.count(".") == 2  # final restatement dropped
    assert "Governor Lopez" in out  # body preserved
    assert out.strip().endswith("to help.")


def test_terminal_restatement_keeps_new_fact():
    # Final sentence introduces a NEW content word ("Wednesday", "hearing").
    s = ("Firefighters battled 102 blazes Tuesday. "
         "Governor Lopez called in 400 troops. "
         "A federal hearing on the response opens Wednesday.")
    out = c._drop_terminal_restatement(s)
    assert "hearing" in out and "Wednesday" in out


def test_terminal_restatement_never_reduces_two_sentences():
    s = ("The strait remains closed to tankers. "
         "The strait remains closed to tankers today.")
    # Only 2 sentences -> guard refuses to drop to 1.
    assert c._drop_terminal_restatement(s) == s


# ---------------------------------------------------------------------------
# 3c — collapse consecutive "unknown / ongoing investigation" padding
# ---------------------------------------------------------------------------
def test_collapse_consecutive_unknown_padding():
    s = ("A fire tore through the Cape Town market before dawn. "
         "The cause is not yet known. "
         "Authorities are still looking into the blaze. "
         "The investigation remains ongoing.")
    out = c._collapse_unknown_padding(s)
    # Keeps the first unknown sentence, drops the two consecutive followers.
    assert "cause is not yet known" in out
    assert "still looking into" not in out
    assert "investigation remains ongoing" not in out
    assert "tore through" in out  # lead preserved


def test_unknown_padding_noop_when_single():
    s = ("A fire tore through the market. "
         "The cause is not yet known. "
         "Twelve shops were destroyed.")
    # Single unknown sentence, not consecutive with another -> untouched.
    assert c._collapse_unknown_padding(s) == s


# ---------------------------------------------------------------------------
# 3d — drop near-duplicate repeated claims
# ---------------------------------------------------------------------------
def test_drop_repeated_claim_near_duplicate():
    s = ("Iran said the Strait of Hormuz stays closed until sanctions are lifted. "
         "Oil prices rose four percent on the news. "
         "Tehran repeated that the Strait of Hormuz stays closed until sanctions "
         "are lifted.")
    out = c._drop_repeated_claim_sentences(s)
    assert out.lower().count("stays closed until sanctions") == 1
    assert "Oil prices rose" in out


def test_repeated_claim_keeps_distinct_sentences():
    s = ("Iran closed the Strait of Hormuz to tankers. "
         "Saudi Arabia opened a new pipeline to bypass the strait.")
    # Distinct facts, low Jaccard -> both kept.
    assert c._drop_repeated_claim_sentences(s) == s


# ---------------------------------------------------------------------------
# 3e — drop ungrounded ages
# ---------------------------------------------------------------------------
def test_drop_ungrounded_year_old():
    summary = ("An 80-year-old Marine veteran, David Warrington, was named to the "
               "post. He starts Monday.")
    src = "David Warrington, a Marine veteran, was named to the post. He starts Monday."
    out = c._drop_ungrounded_ages(summary, src)
    assert "80-year-old" not in out
    assert "David Warrington" in out
    assert "Marine veteran" in out


def test_keep_grounded_year_old():
    summary = "The 75-year-old canoeist finished the route in record time."
    src = "The canoeist, 75, described the route. She finished in record time."
    # "75" appears in source -> age is grounded, kept.
    assert c._drop_ungrounded_ages(summary, src) == summary


def test_drop_ungrounded_is_age_whole_sentence():
    summary = ("Trump signed the order Friday. Trump is 80 and served one prior term.")
    src = "Trump signed the order Friday. He served one prior term."
    out = c._drop_ungrounded_ages(summary, src)
    assert "is 80" not in out
    assert "Trump signed the order Friday" in out


def test_is_age_not_confused_with_percentage():
    summary = "Support is 80 percent according to the new poll of 1,000 voters."
    src = "A poll of voters put support near four in five."
    # "is 80 percent" must NOT be treated as an age -> sentence untouched.
    assert c._drop_ungrounded_ages(summary, src) == summary


def test_aged_form_excised():
    summary = "The suspect, aged 42, appeared in court and denied the charges."
    src = "The suspect appeared in court and denied the charges."
    out = c._drop_ungrounded_ages(summary, src)
    assert "aged 42" not in out
    assert "appeared in court" in out


# ---------------------------------------------------------------------------
# Full chain + clean-control invariant
# ---------------------------------------------------------------------------
def test_apply_chain_clean_summary_untouched():
    clean = ("The central bank cut rates half a point Tuesday. "
             "Three lenders had failed in the prior week. "
             "Markets closed up two percent.")
    assert c._apply_summary_postchecks(clean, "") == clean


def test_apply_chain_repairs_multiple_defects():
    summary = (
        "An 80-year-old official, Dana Reyes, announced the evacuation Tuesday. "
        "Reyes ordered 12,000 residents to leave by nightfall. "
        "The cause of the leak is not yet known. "
        "Authorities are still investigating the cause. "
        "Reyes announced the evacuation of residents on Tuesday.")
    src = ("Dana Reyes announced the evacuation Tuesday, ordering 12,000 "
           "residents to leave by nightfall. The cause of the leak is not known.")
    out = c._apply_summary_postchecks(summary, src)
    assert "80-year-old" not in out               # 3e
    assert out.lower().count("not yet known") + out.lower().count(
        "still investigating") <= 1               # 3c
    assert _wc(out) <= 90                          # 3a
    assert "Dana Reyes" in out                     # substance preserved


def test_apply_chain_empty_and_none_safe():
    assert c._apply_summary_postchecks("", "") == ""
    assert c._apply_summary_postchecks("   ", "") == "   "


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} post-check tests passed")


if __name__ == "__main__":
    _run()
