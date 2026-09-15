"""Shared spaCy NLP instance for the void --news pipeline.

All modules should import get_nlp() from here instead of maintaining
their own lazy singletons. Saves ~250MB RAM and ~10s startup.

The spaCy import is deferred into get_nlp() rather than taken at module
scope. Several modules that import this one are mostly pure text code:
importance_ranker's disaster lexicon and death-toll patterns are plain
regex, and the offline test that covers them runs in a CI job that
installs nltk only. A module-scope import made that job fail on
ModuleNotFoundError before a single assertion ran. Deferring it changes
nothing for the pipeline (the only caller is inside a function) and the
same error still surfaces, with the same message, on the first real use.
"""

_nlp = None


def get_nlp():
    """Get the shared spaCy English model (lazy-loaded singleton)."""
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp
