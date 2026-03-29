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
    "comprehensive", "amidst", "landscape", "breaking",

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
