"""
Claim extraction for void --verify (Claim Consensus engine).

Extracts factual claims from article text using spaCy dependency parsing.
Claims are Subject-Verb-Object triples anchored by named entities or
quantitative data patterns. Rule-based, $0 cost.

Output feeds into claim_verifier.py for cross-source verification.
"""

import re
from dataclasses import dataclass, field

from utils.nlp_shared import get_nlp


# ---------------------------------------------------------------------------
# Claim anchors — entity types and quantitative patterns that qualify a
# sentence as a factual claim (not opinion or filler).
# ---------------------------------------------------------------------------
CLAIM_ENTITY_TYPES = frozenset({
    "PERSON", "ORG", "GPE", "NORP", "FAC", "EVENT",
})

# Reuse data patterns from factual_rigor for consistency
QUANTITATIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d+(\.\d+)?%"),
    re.compile(r"\d+(\.\d+)?\s*percent\b", re.I),
    re.compile(r"\$\d[\d,]*(\.\d+)?"),
    re.compile(r"\d[\d,]*\s*(million|billion|trillion)", re.I),
    re.compile(r"(rose|fell|increased|decreased|grew|dropped|declined|surged|plummeted)\s+by\s+\d", re.I),
    re.compile(r"(rose|fell|increased|decreased|grew|dropped|declined|surged)\s+to\s+\d", re.I),
    re.compile(r"\d{4}\s*(study|survey|poll|report|analysis)", re.I),
    re.compile(r"\d[\d,]+\s+(people|workers|citizens|soldiers|patients|refugees|cases|deaths|killed|wounded|displaced|arrested)\b", re.I),
]

ATTRIBUTION_VERBS = frozenset({
    "said", "says", "told", "stated", "reported", "confirmed", "announced",
    "testified", "explained", "noted", "argued", "claimed", "contended",
    "acknowledged", "insisted", "emphasized", "stressed", "warned",
    "cautioned", "added", "remarked", "commented", "responded", "replied",
    "wrote", "published", "revealed", "disclosed", "found", "concluded",
    "determined", "estimated", "forecast", "released", "issued",
})

TEMPORAL_PATTERN = re.compile(
    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\b",
    re.I,
)

# Word count bounds for valid claims
_MIN_WORDS = 8
_MAX_WORDS = 60


@dataclass
class Claim:
    claim_text: str
    subject_entity: str = ""
    subject_entity_type: str = ""
    claim_type: str = "statement"  # quantitative | attribution | event | statement
    has_quantitative: bool = False
    source_sentence: str = ""
    article_id: str = ""
    source_slug: str = ""
    source_name: str = ""


def _has_quantitative(text: str) -> bool:
    """Check if text contains any quantitative data pattern."""
    for pat in QUANTITATIVE_PATTERNS:
        if pat.search(text):
            return True
    return False


def _classify_claim(text: str, verb_lemma: str) -> str:
    """Classify claim type based on content signals."""
    if _has_quantitative(text):
        return "quantitative"
    if verb_lemma in ATTRIBUTION_VERBS:
        return "attribution"
    if TEMPORAL_PATTERN.search(text):
        return "event"
    return "statement"


def _get_primary_entity(sent) -> tuple[str, str]:
    """Extract the most prominent named entity from a spaCy Span/Doc."""
    for ent in sent.ents:
        if ent.label_ in CLAIM_ENTITY_TYPES:
            return ent.text, ent.label_
    return "", ""


def _has_claim_anchor(sent) -> bool:
    """Check if sentence has at least one named entity or quantitative pattern."""
    for ent in sent.ents:
        if ent.label_ in CLAIM_ENTITY_TYPES:
            return True
    if _has_quantitative(sent.text):
        return True
    return False


def _has_svo_structure(sent) -> tuple[bool, str]:
    """
    Check if sentence has Subject-Verb-Object structure via dependency parse.
    Returns (has_svo, root_verb_lemma).
    """
    root = None
    for token in sent:
        if token.dep_ == "ROOT" and token.pos_ == "VERB":
            root = token
            break

    if root is None:
        return False, ""

    has_subject = False
    has_complement = False
    for child in root.children:
        if child.dep_ in ("nsubj", "nsubjpass", "csubj"):
            has_subject = True
        if child.dep_ in ("dobj", "attr", "prep", "oprd", "acomp", "xcomp", "ccomp"):
            has_complement = True

    return (has_subject and has_complement), root.lemma_


def extract_claims(doc, article_id: str, source_slug: str = "",
                   source_name: str = "") -> list[Claim]:
    """
    Extract factual claims from a spaCy Doc.

    Walks sentences, checks for SVO structure with named entities or
    quantitative anchors, deduplicates by (entity, verb_lemma).
    """
    claims: list[Claim] = []
    seen: set[tuple[str, str]] = set()  # (entity_lower, verb_lemma)

    for sent in doc.sents:
        text = sent.text.strip()
        word_count = len(text.split())

        # Skip too short/long
        if word_count < _MIN_WORDS or word_count > _MAX_WORDS:
            continue

        # Must have claim anchor (entity or quantitative)
        if not _has_claim_anchor(sent):
            continue

        # Must have SVO structure
        has_svo, verb_lemma = _has_svo_structure(sent)
        if not has_svo:
            continue

        # Extract primary entity
        entity_text, entity_type = _get_primary_entity(sent)

        # Deduplicate within article by (entity, verb)
        dedup_key = (entity_text.lower() if entity_text else "", verb_lemma)
        if dedup_key in seen and dedup_key[0]:  # only dedup if entity exists
            continue
        if dedup_key[0]:
            seen.add(dedup_key)

        # Classify
        claim_type = _classify_claim(text, verb_lemma)
        quant = _has_quantitative(text)

        claims.append(Claim(
            claim_text=text,
            subject_entity=entity_text,
            subject_entity_type=entity_type,
            claim_type=claim_type,
            has_quantitative=quant,
            source_sentence=text,
            article_id=article_id,
            source_slug=source_slug,
            source_name=source_name,
        ))

    return claims


def extract_claims_batch(articles: list[dict], nlp=None) -> dict[str, list[Claim]]:
    """
    Extract claims from multiple articles.

    Args:
        articles: List of article dicts with 'id', 'full_text',
                  'source_slug', 'source_name' keys.
        nlp: Optional spaCy model (loaded if not provided).

    Returns:
        Dict mapping article_id -> list of Claims.
    """
    if nlp is None:
        nlp = get_nlp()

    results: dict[str, list[Claim]] = {}
    total_claims = 0

    for art in articles:
        art_id = art.get("id", "")
        text = art.get("full_text", "") or ""
        if not art_id or not text or len(text) < 100:
            continue

        # Truncate to avoid spaCy memory issues on very long articles
        doc = nlp(text[:15000])
        slug = art.get("source_slug", "") or art.get("source_id", "")
        name = art.get("source_name", "")

        claims = extract_claims(doc, art_id, source_slug=slug, source_name=name)
        if claims:
            results[art_id] = claims
            total_claims += len(claims)

    print(f"  Claim extraction: {total_claims} claims from {len(results)} articles")
    return results
