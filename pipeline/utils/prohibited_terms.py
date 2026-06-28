"""
Shared prohibited terms for all Gemini-generated content.

Single canonical source for anti-slop, anti-sensationalism, and anti-AI-crutch
terms. Used by cluster_summarizer, daily_brief_generator, and any future
content generation modules.

$0 cost — pure rule-based string matching.
"""

# ---------------------------------------------------------------------------
# Canonical prohibited terms (~90 terms).
#
# Categories:
#   1. Sensationalist language (from cluster_summarizer)
#   2. Value-laden adjectives (from cluster_summarizer)
#   3. Unattributed speculation (from cluster_summarizer)
#   4. Meta-coverage framing (from cluster_summarizer)
#   5. Brief-specific anti-slop (from daily_brief_generator)
#   6. AI slop / LLM crutch phrases (new)
# ---------------------------------------------------------------------------
PROHIBITED_TERMS = frozenset({
    # --- 1. Sensationalist language ---
    "shocking", "stunned", "stunning", "explosive", "bombshell", "devastating",
    "chaos", "chaotic", "firestorm", "crackdown", "slams", "blasts",
    "doubles down", "war of words", "sparking outrage",

    # --- 2. Value-laden adjectives ---
    "controversial", "divisive", "landmark", "historic",
    "radical", "extreme", "common-sense",

    # --- 3. Unattributed speculation / vague framing ---
    "raising questions", "raises concerns", "casts doubt",
    "throws into question", "in an unprecedented", "unprecedented",
    "in a stunning", "the world watched",
    "experts say", "analysts believe", "experts believe", "analysts say",
    "it was widely reported", "it is widely understood",
    "could signal", "may mark", "might reshape",
    "most significant", "most important development", "key moment",

    # --- 4. Meta-coverage / generic source labels ---
    "downplayed", "failed to mention", "chose not to report",
    "a us major source", "an international outlet", "a major source",

    # --- 5. Brief-specific anti-slop ---
    "comprehensive", "amid", "amidst", "landscape", "breaking",

    # --- 6. AI slop / LLM crutch phrases ---
    "delve", "delves into",
    "navigate", "navigating",
    "underscores",
    "multifaceted",
    "robust",
    "pivotal",
    "realm",
    "tapestry",
    "spearheaded",
    "in terms of",
    "it's important to note", "it's crucial to",
    "serves as a reminder",
    "shed light on", "sheds light on",
    "a testament to",
    "paves the way",
    "sends a clear message",
    "nuanced",
    "game changer", "game-changing",
    "in summary", "to sum up",
    "at the end of the day",
    "sends shockwaves",
    "raises the stakes",
    "in the wake of",
    "double down", "doubled down",
    "sparked debate",
    "drew criticism", "drew praise",
    "gaining traction", "gaining momentum",

    # --- Show Don't Tell crutch words ---
    "significant", "notable", "importantly",
    "interestingly", "it should be noted", "it is worth mentioning",
    "crucially",

    # --- 7. Templatic transitions / filler scaffolding ---
    # These are structuring phrases that add zero information and sound
    # AI-generated. The sentence works better without them every time.
    "this isn't just", "this is not just",
    "it's not just", "it is not just",
    "what makes this", "what's interesting is",
    "here's the thing", "here is the thing",
    "here's why", "here is why",
    "the bigger picture",
    "the bottom line",
    "the takeaway",
    "let's be clear", "let us be clear",
    "to be sure",
    "to put it simply", "simply put",
    "make no mistake",
    "the reality is", "the truth is",
    "it's worth noting", "it is worth noting",
    "it bears mentioning",
    "what we're seeing", "what we are seeing",
    "broadly speaking",
    "the implications are",
    "the stakes are high", "the stakes are clear",
    "in other words",
    "needless to say",
    "this is a story about",
    "this is about more than",
    "the question now is",
    "this matters because",

    # --- 8. Vox/explainer scaffolding (synonym variants) ---
    # These slip through when the model paraphrases banned phrases.
    "this goes beyond", "it goes beyond",
    "what's really happening", "what is really happening",
    "here's what's happening", "here is what is happening",
    "here's what you need to know", "here is what you need to know",
    "think of it this way",
    "zoom out", "if you zoom out",
    "the short version",
    "let me explain",
    "so here's", "so here is",
    "the key thing", "the key here",
    "the point is",
    "what this means is",
    "the upshot",

    # --- 9. Commonly-slipping scaffolding ---
    "the question remains",
    "what remains to be seen",

    # --- 10. Claude-specific scaffolding ---
    "let's start with", "let us start with",
    "let's unpack", "let us unpack",
    "let's break this down", "let us break this down",
    "let's look at", "let us look at",
    "let's talk about", "let us talk about",

    # --- 11. Meta-narrative verbs (Category D) ---
    # Host steps outside the story to label what it means.
    # These are tells — the reader/listener should infer significance
    # from juxtaposed facts, not from the host naming it.
    "underlines", "highlights the",
    "illustrates the", "demonstrates the",
    "signals a", "signals that",
    "reflects a", "reflects the",
    "marks a shift", "marks a turning point",
    "in a sign of", "in a sign that",
    "in a rebuke to", "in a blow to", "in a boost for",
    "in a move that",
    "reveals the pattern", "the pattern connecting",
    "the structural consequence",

    # --- 12. Evaluative adverbs (Category B) ---
    # Substitute for a number. Every one of these should be
    # replaceable by a specific figure. If not, it's a tell.
    "sharply", "dramatically", "markedly",
    "overwhelmingly", "deeply divided",

    # --- 13. Temporal vagueness (Category C) ---
    # Create a feeling of accumulation without naming what accumulated.
    "growing concerns", "mounting pressure",
    "in recent weeks", "in recent months",
})


def check_prohibited_terms(text: str, context: str = "") -> list[str]:
    """
    Scan text for prohibited terms. Returns list of found terms.

    Args:
        text: The text to scan (will be lowercased internally).
        context: Optional label for logging (e.g., "cluster 42", "brief:world").

    Returns:
        List of prohibited terms found in the text (may be empty).
    """
    if not text:
        return []
    lower = text.lower()
    found = [term for term in PROHIBITED_TERMS if term in lower]
    return sorted(found)


# ---------------------------------------------------------------------------
# Deterministic editorial sanitizer (2026-06-28, Wave 1 / O5)
#
# The show-don't-tell + no-em-dash Cardinal Rules (CLAUDE.md) were only
# DETECTED (warning logs), never enforced, so "significant"/em-dashes leaked
# into displayed summaries on both the LLM and the rule-based fallback paths.
# This is the single mutating pass shared by both. $0, no LLM call.
#
# Scope is deliberately narrow to avoid distorting facts:
#   * em/en dashes  -> comma  (the most common AI tell; always safe)
#   * significance ADVERBS (significantly, notably, crucially, ...) -> removed
#     (parenthetical; removal leaves a grammatical sentence)
#   * significance ADJECTIVES (significant, notable, crucial) -> removed UNLESS
#     immediately negated/minimized ("no significant damage" stays, because
#     dropping the adjective there would invert the factual claim).
#
# IMPORTANT: do NOT run this on audio_script / opinion_audio_script — em dashes
# are intentional TTS prosody there (CLAUDE.md No-Em-Dash exception).
# ---------------------------------------------------------------------------
import re as _re

# Spaced or unspaced em/en dash -> ", ". Regular hyphens ("fact-check") are
# untouched (only the em "—" and en "–" code points are matched).
_EM_EN_DASH_RE = _re.compile(r"\s*[—–]\s*")

# Significance assertions. An optional leading intensifier (most/very/...) is
# swallowed with the word. A leading negation/minimizer is CAPTURED so the
# replacement can keep load-bearing phrases ("no significant damage") intact.
_SIGNIFICANCE_RE = _re.compile(
    r"\b(?P<neg>no|not|without|little|any|minimal|hardly|barely)?\s*"
    r"(?:(?:most|more|very|highly|particularly|quite|so|the\s+most)\s+)?"
    r"(?P<word>significantly|significant|notably|notable|crucially|crucial|"
    r"remarkably|strikingly|importantly|interestingly|markedly)\b",
    _re.IGNORECASE,
)


def _significance_sub(m: "_re.Match") -> str:
    # Keep the phrase when the significance word is negated/minimized — removing
    # it would change the meaning ("no significant damage" != "no damage").
    if m.group("neg"):
        return m.group(0)
    return ""


def sanitize_editorial_text(text: str) -> str:
    """Enforce the no-em-dash + show-don't-tell Cardinal Rules deterministically.

    Returns a cleaned copy of ``text``. Safe on None/empty. Do NOT apply to
    audio script fields (em dashes are intentional prosody there).
    """
    if not text or not isinstance(text, str):
        return text
    out = _EM_EN_DASH_RE.sub(", ", text)
    out = _SIGNIFICANCE_RE.sub(_significance_sub, out)
    # Clean up artifacts left by word deletion.
    out = out.replace(" ,", ",").replace(" .", ".").replace(" ;", ";").replace(" :", ":")
    out = _re.sub(r",\s*,", ",", out)          # doubled commas
    out = _re.sub(r"\s{2,}", " ", out)          # collapsed double spaces
    out = _re.sub(r"\(\s+", "(", out).replace(" )", ")")
    out = out.strip(" ,;:")
    # Re-capitalize sentence starts a leading-word deletion may have lowercased.
    out = _re.sub(
        r"(^|[.!?]\s+)([a-z])",
        lambda mm: mm.group(1) + mm.group(2).upper(),
        out,
    )
    return out
