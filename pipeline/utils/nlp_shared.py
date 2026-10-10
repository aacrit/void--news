"""Shared spaCy NLP instances for the void --news pipeline, one per language.

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

# One loaded model per language, not one model. Keyed by the language code the
# caller asks for, so a French article is parsed by a French model rather than
# by an English one that will silently mis-tag every sentence.
_nlp: dict = {}

# language code -> spaCy model name. Small models only: they are what the
# pipeline already runs for English and what fits the Actions runner. A code
# that is not here has no model, and get_nlp raises rather than falling back to
# English, because parsing French with an English model does not fail loudly,
# it just returns confident nonsense.
MODELS = {
    "en": "en_core_web_sm",
    "fr": "fr_core_news_sm",
    "de": "de_core_news_sm",
    "es": "es_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
    "da": "da_core_news_sm",
    "sv": "sv_core_news_sm",
    "nb": "nb_core_news_sm",
    "fi": "fi_core_news_sm",
    "pl": "pl_core_news_sm",
    "ro": "ro_core_news_sm",
    "el": "el_core_news_sm",
    "uk": "uk_core_news_sm",
    "ru": "ru_core_news_sm",
    "ja": "ja_core_news_sm",
    "ko": "ko_core_news_sm",
    "zh": "zh_core_web_sm",
}

DEFAULT_LANG = "en"


class ModelUnavailable(RuntimeError):
    """The language has a model name but it is not installed on this machine."""


def get_nlp(lang: str = DEFAULT_LANG):
    """Get the shared spaCy model for `lang` (lazy-loaded, one per language).

    Defaults to English so every existing caller keeps working unchanged.

    Raises on an unknown language rather than degrading to English. A wrong
    model is worse than no model here: spaCy will happily tag French text with
    an English pipeline and return a parse that looks fine and is wrong, and
    every bias signal downstream (entity sentiment, framing, the attribution
    verbs) would then be measuring an artefact. The bias engine's contract is a
    deterministic rationale, and a rationale built on a mis-parse is not one.
    """
    code = (lang or DEFAULT_LANG).lower().split("-")[0]
    if code not in MODELS:
        raise ValueError(
            f"no spaCy model configured for language {code!r}. "
            f"Configured: {', '.join(sorted(MODELS))}. Add it to MODELS in "
            f"pipeline/utils/nlp_shared.py and install it with "
            f"`python -m spacy download <model>` before scoring that language."
        )
    if code not in _nlp:
        import spacy
        name = MODELS[code]
        try:
            _nlp[code] = spacy.load(name)
        except OSError as exc:
            raise ModelUnavailable(
                f"spaCy model {name!r} for language {code!r} is not installed. "
                f"Install it with: python -m spacy download {name}"
            ) from exc
    return _nlp[code]


def available_languages() -> list:
    """Language codes whose model is actually installed here.

    Used by the roster and the harvest to decide what they may score, rather
    than discovering it mid-run on a specific article.
    """
    import importlib.util
    out = []
    for code, name in sorted(MODELS.items()):
        if importlib.util.find_spec(name) is not None:
            out.append(code)
    return out
