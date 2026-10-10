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
# 3a — hard runaway-cap trim to a sentence boundary (cap is a safety guard now,
# not an editorial target; house length policy is 200-300 words)
# ---------------------------------------------------------------------------
def test_trim_over_cap_to_sentence_boundary():
    # Sentences of 30 words each, total well over the runaway cap so the trim
    # fires and keeps only whole sentences at or under the cap.
    sent = " ".join(["word"] * 29) + " end."       # 30 words per sentence
    n = c._SUMMARY_WORD_CAP // 30 + 6
    long = " ".join([sent] * n)
    assert _wc(long) > c._SUMMARY_WORD_CAP
    out = c._trim_summary_to_word_cap(long)
    assert _wc(out) <= c._SUMMARY_WORD_CAP, _wc(out)
    # Kept only complete sentences (each ends with "end.").
    assert out.strip().endswith("end.")


def test_trim_noop_when_within_cap():
    # A normal full-length brief (well under the runaway cap) is untouched.
    clean = "The senate passed the bill Tuesday. 60 members voted yes."
    assert c._trim_summary_to_word_cap(clean) == clean


def test_trim_first_sentence_exceeds_cap():
    huge = " ".join(["token"] * (c._SUMMARY_WORD_CAP + 60)) + "."
    out = c._trim_summary_to_word_cap(huge)
    assert _wc(out) <= c._SUMMARY_WORD_CAP
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
    assert _wc(out) <= c._SUMMARY_WORD_CAP         # 3a runaway guard
    assert "Dana Reyes" in out                     # substance preserved


def test_apply_chain_empty_and_none_safe():
    assert c._apply_summary_postchecks("", "") == ""
    assert c._apply_summary_postchecks("   ", "") == "   "


# ---------------------------------------------------------------------------
# Runaway guard (length policy restored 2026-08-11 to 200-300 words): the cap is
# now only a safety ceiling. A normal 200-300 word brief must pass through
# untouched; only a runaway (> _SUMMARY_WORD_CAP) is trimmed at the storage
# boundary on both the flash and flash-lite write paths.
# ---------------------------------------------------------------------------
def test_full_brief_passes_through_uncapped():
    """A 200-300 word brief (the house target) is NOT trimmed."""
    sent = " ".join(["fact"] * 24) + " landed."   # 25 words each
    brief = " ".join([sent] * 10)                  # 250 words, well within cap
    assert _wc(brief) == 250
    stored = c._trim_summary_to_word_cap(brief)
    assert stored == brief                          # untouched, no cap applied


def test_runaway_summary_trimmed_to_cap():
    """A runaway (> cap) summary is trimmed at the storage boundary."""
    sent = " ".join(["fact"] * 24) + " landed."   # 25 words each
    long_summary = " ".join([sent] * (c._SUMMARY_WORD_CAP // 25 + 4))  # over cap
    assert _wc(long_summary) > c._SUMMARY_WORD_CAP
    stored = c._trim_summary_to_word_cap(long_summary)
    assert _wc(stored) <= c._SUMMARY_WORD_CAP, _wc(stored)
    assert stored.strip().endswith("landed.")            # whole-sentence boundary


def test_cached_over_cap_runaway_would_be_trimmed():
    """A runaway summary over the safety cap is caught by the same deterministic
    trim the 8d cache-hit branch applies in place."""
    cached = " ".join(["word"] * (c._SUMMARY_WORD_CAP + 19)) + " end."
    assert _wc(cached) > c._SUMMARY_WORD_CAP
    assert _wc(c._trim_summary_to_word_cap(cached)) <= c._SUMMARY_WORD_CAP


def test_prompt_targets_full_brief_length():
    """TASK 2 asks for a 200-to-300-word full brief (restored 2026-08-11) and no
    longer caps output at the short 55-90 band."""
    tmpl = c._USER_PROMPT_TEMPLATE
    assert "200 to 300 words" in tmpl
    # The old short-band + brevity-maximizing instructions are gone.
    assert "55 to 90 words" not in tmpl
    assert "shorter, denser summary always beats" not in tmpl
    assert "AT MOST 90 words" not in tmpl
    # Soft floor sits below the runaway cap and above zero.
    assert 0 < c._SUMMARY_WORD_FLOOR < c._SUMMARY_WORD_CAP


# ---------------------------------------------------------------------------
# Grounding hardening (2026-08-10): (3f) warn-only grounding audit flags figures
# and proper nouns absent from the source text; the prompt block now feeds the
# real full_text body, sentence-bounded (no mid-sentence "..." severing a fact).
# ---------------------------------------------------------------------------
def test_grounding_flags_absent_number():
    """(i) A number in the summary that is NOT in the source text is flagged."""
    summary = "The council approved the plan by a vote of 55 to 12 on Tuesday."
    src = "The council approved the plan on Tuesday after a lengthy debate."
    flagged = c._flag_ungrounded_tokens(summary, src)
    assert "55" in flagged, flagged
    assert "12" in flagged, flagged


def test_grounding_does_not_flag_grounded_number():
    """(ii) A number present in the source text is NOT flagged."""
    summary = "The council approved the plan 55 to 12 on Tuesday."
    src = "Officials confirmed the 55 to 12 vote taken on Tuesday afternoon."
    flagged = c._flag_ungrounded_tokens(summary, src)
    assert "55" not in flagged, flagged
    assert "12" not in flagged, flagged


def test_grounding_flags_absent_proper_noun_not_grounded_one():
    # An invented multi-word entity is flagged; a grounded one is not.
    summary = "Dana Reyes met Victor Almeida in Geneva to sign the accord."
    src = "Dana Reyes traveled to Geneva to sign the accord."
    flagged = c._flag_ungrounded_tokens(summary, src)
    assert "Victor Almeida" in flagged, flagged
    assert "Dana Reyes" not in flagged, flagged


def test_grounding_thousands_separator_grounds():
    # "12,000" in source grounds "12000" digits in the summary token.
    summary = "Officials ordered 12,000 residents to evacuate."
    src = "The order covered 12,000 residents in the valley."
    assert c._flag_ungrounded_tokens(summary, src) == []


def test_grounding_empty_source_is_noop():
    assert c._flag_ungrounded_tokens("55 people, Jane Doe.", "") == []
    assert c._flag_ungrounded_tokens("", "some source text") == []


def test_articles_block_uses_full_text_sentence_bounded():
    """(iii) The prompt block feeds full_text (not the 400-char summary excerpt)
    and cuts on a sentence boundary with no trailing mid-sentence ellipsis."""
    # Body > _ARTICLE_BODY_MAX_CHARS so it must be sliced. Compose whole
    # sentences; the slice must end on one of them, not mid-word/mid-fact.
    sentence = ("Investigators traced the outage to a single failed relay near "
                "the north substation and confirmed no foul play was involved. ")
    body = sentence * 40  # well over 1800 chars
    marker = "UNIQUEBODYMARKER the relay was replaced within the hour."
    art = {
        "title": "Grid outage explained",
        "full_text": marker + " " + body,
        "summary": "SHORTRSSEXCERPT that must not be used when full_text exists.",
        "tier": "us_major",
        "published_at": "2026-08-10T09:00",
        "id": "a1",
    }
    block = c._build_articles_block([art])
    # full_text body is used, RSS summary is not.
    assert "UNIQUEBODYMARKER" in block
    assert "SHORTRSSEXCERPT" not in block
    # Sentence-bounded: the emitted body ends each sentence with a period and
    # never appends a mid-sentence "..." (the old summary[:397] + "..." path).
    assert "..." not in block
    # The excerpt helper itself is sentence-bounded and within budget.
    excerpt = c._sentence_bounded_excerpt(marker + " " + body)
    assert len(excerpt) <= c._ARTICLE_BODY_MAX_CHARS
    assert excerpt.rstrip().endswith((".", "!", "?"))


def test_sentence_bounded_excerpt_returns_short_text_whole():
    short = "One short sentence that fits. And a second one."
    assert c._sentence_bounded_excerpt(short) == short


def test_articles_block_falls_back_to_summary_without_full_text():
    art = {
        "title": "No body here",
        "full_text": "",
        "summary": "RSSFALLBACK excerpt stands in for a missing body.",
        "tier": "international",
        "published_at": "2026-08-10T08:00",
        "id": "b1",
    }
    block = c._build_articles_block([art])
    assert "RSSFALLBACK" in block


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
