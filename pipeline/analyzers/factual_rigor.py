"""
Factual rigor scorer for the void --news bias engine.

Scores each article on a 0-100 factual rigor spectrum:
    0   = no sourcing, unsubstantiated claims
    100 = heavily sourced, data-backed, well-cited

Uses rule-based NLP heuristics (no LLM API calls):
    - Quote and attribution density ("said", "according to", "reported")
    - Named source count (named individuals, organizations cited)
    - Data/statistics presence (numbers, percentages, dollar amounts)
    - Hedging language ("allegedly", "reportedly" = appropriate caution)
    - Link/reference density
    - Vague sourcing penalties ("sources say", "people familiar with")
    - Document/study citations

Phase 2 implementation.
"""


def analyze_factual_rigor(article: dict) -> int:
    """
    Score the factual rigor of an article.

    Args:
        article: Dict with keys: full_text, title, summary.

    Returns:
        Integer score 0-100 (0=no sourcing, 100=heavily sourced).
    """
    raise NotImplementedError("Phase 2: Factual rigor analysis not yet implemented.")
