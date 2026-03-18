"""
Opinion vs. reporting classifier for the void --news bias engine.

Scores each article on a 0-100 opinion-fact spectrum:
    0   = purely factual reporting
    100 = purely opinion/editorial

Uses rule-based NLP heuristics (no LLM API calls):
    - First-person pronoun usage ("I believe", "in my view")
    - Subjective adjective frequency (TextBlob subjectivity)
    - Attribution patterns ("according to", "officials said" = more factual)
    - Modal verb usage ("should", "must", "ought to" = more opinion)
    - Section/tag metadata (op-ed, editorial, analysis labels)
    - Imperative sentences (calls to action)

Phase 2 implementation.
"""


def analyze_opinion_fact(article: dict) -> int:
    """
    Score where an article falls on the opinion-fact spectrum.

    Args:
        article: Dict with keys: full_text, title, summary, section.

    Returns:
        Integer score 0-100 (0=factual reporting, 100=pure opinion).
    """
    raise NotImplementedError("Phase 2: Opinion detection not yet implemented.")
