#!/usr/bin/env python3
"""The NLP layer must never parse one language with another language's model.

WHY THIS GATE EXISTS. Until 2026-09-22 `get_nlp()` hardcoded
`spacy.load("en_core_web_sm")` in a single singleton, which was correct while
every source was English. Adding non-English sources makes a silent fallback
the most dangerous possible behaviour: spaCy will happily tag French text with
an English pipeline and return a parse that LOOKS fine and is wrong. Every bias
signal downstream reads that parse (entity sentiment, framing phrases, the
attribution verbs), so a mis-parse does not surface as an error, it surfaces as
a confident score. The bias engine's public promise is a deterministic
rationale per axis, and a rationale built on a mis-parse is not one.

So the contract is: a language with no configured model RAISES, and a language
whose model is not installed RAISES a distinguishable error. It never degrades.

CONVENTION ON THE ROSTER: a source with no `content_language` is English.
`data/sources.json` carries no such field today because every source in it is
fetched in English, so the absence is the truth rather than a gap. The field is
set only when a non-English source is added, which is what makes the diff for
Le Figaro or Sueddeutsche Zeitung a one-line change rather than a migration.

Stdlib plus spaCy only; no DB, no VOID_SQLITE_PATH.

    python3 tests/test_nlp_languages.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"[ ok ] {name}")
    else:
        failures.append(name)
        print(f"[FAIL] {name}{': ' + detail if detail else ''}")


from utils.nlp_shared import (  # noqa: E402
    MODELS, DEFAULT_LANG, ModelUnavailable, get_nlp, available_languages,
)

# ---- the contract ---------------------------------------------------------

check("English is the default language", DEFAULT_LANG == "en")
check("English has a configured model", MODELS.get("en") == "en_core_web_sm")

try:
    get_nlp("xx-not-a-language")
    check("an unknown language raises", False, "it returned a model instead")
except ValueError:
    check("an unknown language raises ValueError", True)
except ModelUnavailable:
    check("an unknown language raises", False,
          "raised ModelUnavailable, so it resolved to a model name it should not have")

# The dangerous case, stated as an assertion: a configured-but-absent model must
# not quietly become English.
absent = [c for c in MODELS if c not in available_languages() and c != "en"]
if absent:
    code = absent[0]
    try:
        nlp = get_nlp(code)
        check(f"an uninstalled model ({code}) does not fall back", False,
              "it returned a model, which means it silently used another language")
    except ModelUnavailable:
        check(f"an uninstalled model ({code}) raises ModelUnavailable", True)
    except ValueError:
        check(f"an uninstalled model ({code}) raises", False,
              "raised ValueError, so it is not in MODELS after all")
else:
    print("[ ok ] every configured model is installed here, fallback case not exercisable")

# ---- English still works, and is still a singleton ------------------------

if "en" in available_languages():
    a = get_nlp()
    b = get_nlp("en")
    check("English loads", a is not None)
    check("one model per language, not one per call", a is b)
    doc = a("Senator Smith condemned the tax bill in Washington on Tuesday.")
    check("English parse produces tags", any(t.pos_ for t in doc))
    check("English parse produces entities", len(doc.ents) > 0,
          f"entities: {[e.text for e in doc.ents]}")
else:
    print("[skip] en_core_web_sm not installed here, parse checks skipped")

# ---- the roster convention ------------------------------------------------

with open(os.path.join(ROOT, "data", "sources.json"), encoding="utf-8") as fh:
    srcs = json.load(fh)
langs = {s.get("content_language") for s in srcs if s.get("content_language")}
unknown = sorted(l for l in langs if str(l).lower().split("-")[0] not in MODELS)
check("every content_language on the roster has a configured model",
      not unknown, f"unconfigured: {unknown}")
print(f"       roster carries {len(langs)} explicit content_language value(s); "
      f"absence means {DEFAULT_LANG}")

print()
if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    raise SystemExit(1)
print("OK: no silent language fallback; English unchanged")
