"""Shared spaCy NLP instance for the void --news pipeline.

All modules should import get_nlp() from here instead of maintaining
their own lazy singletons. Saves ~250MB RAM and ~10s startup.
"""

import spacy

_nlp = None


def get_nlp():
    """Get the shared spaCy English model (lazy-loaded singleton)."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp
