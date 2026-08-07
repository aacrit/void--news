"""
Cluster-level headline and summary generation.

Primary path: Gemini (flash-lite for the bulk of cluster summaries, flash for
the premium top-N highest-impact stories). Falls back to rule-based generation.
Claude (retired 2026-06-22) and Groq (retired 2026-06-24) are gone.

Minimizes API usage by only summarizing high-value clusters:
    - 3+ sources (2-source clusters use rule-based — sufficient quality)
    - Sorted by source_count descending (most-covered stories first)
    - Stops when the per-run call cap is reached

Content-hash caching: clusters whose article membership has not changed
since their last Gemini summary are skipped (no API call).
"""

import hashlib
import re

from .gemini_client import (
    generate_json as gemini_generate_json,
    is_available as gemini_is_available,
    calls_remaining as gemini_calls_remaining,
    _FLASH_MODEL as GEMINI_FLASH_MODEL,
)


def _smart_generate_json(prompt: str,
                          system_instruction: str | None = None,
                          max_output_tokens: int = 8192,
                          prefer_provider: str | None = None,
                          model: str | None = None,
                          ) -> tuple[dict | None, str]:
    """Route a summary call to Gemini. Returns (result, label).

    Gemini is the sole LLM (Claude retired 2026-06-22, Groq 2026-06-24).
    Two-model quality hierarchy, picked by the caller via `model`:
        gemini-2.5-flash      → top-N highest-impact stories (premium).
        gemini-2.5-flash-lite → the rest of the displayed top-50 (high-RPD
                                 tier; flash itself is only 20 requests/DAY).

    A flash (premium) request degrades to flash-lite within Gemini if flash's
    20/day cap is spent: flash → flash-lite. A flash-lite request is flash-lite
    only — there is no further fallback now that Groq is gone; a failed slot
    keeps its prior/rule-based summary rather than risk a low-quality provider.

    prefer_provider is retained for signature compatibility; every value now
    routes to Gemini.
    """
    if gemini_is_available():
        # Premium requests try flash first, then degrade to flash-lite within
        # Gemini (e.g. flash's 20/day cap is spent). `None` resolves to the
        # flash-lite default inside the Gemini client.
        wants_flash = (model or "") == GEMINI_FLASH_MODEL
        models_to_try = [GEMINI_FLASH_MODEL, None] if wants_flash else [None]
        for m in models_to_try:
            result = gemini_generate_json(
                prompt, system_instruction=system_instruction,
                count_call=True, max_output_tokens=max_output_tokens,
                model=m,
            )
            if result and isinstance(result, dict):
                label = "gemini-flash" if m == GEMINI_FLASH_MODEL else "gemini-flash-lite"
                return result, label
    return None, "none"


def _content_hash(articles: list[dict]) -> str:
    """
    Hash of cluster's article membership. Used to skip re-summarization
    when nothing has changed since the last successful Sonnet call.

    2026-05-21 nlp-engineer cost-cut: hash only the 10 newest article ids
    actually used by _build_articles_block(max_articles=10), not the full
    membership. Without this, adding a 51st source to an existing 50-source
    cluster invalidates the hash and triggers a fresh Sonnet call — even
    though the summarizer only ever looks at the 10 newest articles in the
    cluster. Cache hit rate on stable days lifts from ~70% to ~88%,
    saving ~9 Sonnet calls/day on the post-rerank top-50 pass.
    """
    # Newest-first by published_at (matches _build_articles_block ordering);
    # ties broken by article id for determinism. Fall back to natural order
    # when published_at is missing on either side.
    def _sort_key(a: dict) -> tuple:
        pub = a.get("published_at") or ""
        return (pub, str(a.get("id") or a.get("article_id") or ""))

    newest = sorted([a for a in articles if a], key=_sort_key, reverse=True)[:10]
    ids = [str(a.get("id") or a.get("article_id") or "") for a in newest]
    # Include total membership count so going from 5→6 articles still
    # invalidates (we may switch from per-article to summarized prose).
    return hashlib.sha256(
        ("|".join(ids) + f"|n={len(articles)}").encode("utf-8")
    ).hexdigest()


# Backwards-compatible aliases used by existing callsites in this module.
# Existing code calls generate_json() / is_available() / calls_remaining()
# without knowing which provider answered.
def generate_json(prompt, system_instruction=None, max_retries=1, count_call=True, max_output_tokens=8192):
    result, _ = _smart_generate_json(prompt, system_instruction=system_instruction, max_output_tokens=max_output_tokens)
    return result

def is_available():
    return gemini_is_available()

def calls_remaining():
    # Gemini is the sole LLM (Groq retired 2026-06-24). Report its remaining
    # per-run budget so the summarization loop knows when to stop.
    return gemini_calls_remaining()

# Import shared prohibited terms — single canonical source.
try:
    from utils.prohibited_terms import (
        PROHIBITED_TERMS as _SHARED_PROHIBITED,
        check_prohibited_terms as _shared_check,
        sanitize_editorial_text as _sanitize_editorial,
    )
    _USE_SHARED_PROHIBITED = True
except ImportError:
    _USE_SHARED_PROHIBITED = False
    def _sanitize_editorial(text):  # no-op fallback if utils not on path
        return text


# ---------------------------------------------------------------------------
# System instruction — persistent editorial voice, set once per API call.
# Defines void --news tone: neutral, attribution-heavy, no sensationalism.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are a senior correspondent at void --news, a neutral news intelligence \
service. You read the day's coverage of a story from many outlets, then report \
the story yourself, in your own words and in void --news's own voice, with the \
authority of a seasoned correspondent. You have no political perspective and you \
do not editorialize.

GROUNDING RULE: Every fact, figure, name, quote, date, and claim in your output \
MUST appear in the provided articles. Do not supplement with prior knowledge, \
background context you recall, or facts not present in the text above. If the \
articles don't say it, you don't write it. Report only what the provided coverage \
establishes; never add facts from memory or prior knowledge.

Cardinal rule: SHOW, DON'T TELL. Place facts next to each other and let the \
reader see the pattern. "The central bank cut rates Tuesday. The last time it \
moved this fast, three lenders collapsed within six months." — significance \
emerges from evidence, never from adjectives. Never assert significance — show \
the evidence that makes it self-evident.

Core standards that apply to all output:
- Active voice. Present tense for current and recent events.
- Attribute every statement or claim to the person or institution who made it \
(a named official, agency, company, or court), not to the outlet that reported \
it. Prohibited pseudo-attribution: "it was widely reported," "it is understood \
that," "sources close to" (unless followed by a specific entity).
- No loaded, charged, or sensationalist language — including language borrowed \
from source headlines.
- No value judgments. Prohibited adjectives: controversial, divisive, landmark, \
historic, shocking, stunning, explosive, devastating, unprecedented (as rhetorical \
emphasis), radical, extreme, common-sense.
- FORBIDDEN SIGNIFICANCE-ASSERTIONS (Cardinal Rule enforcement). Do not use \
any form of: notable, notably, significant, significantly, crucial, crucially, \
interesting, interestingly, importantly, remarkably, strikingly, "it should be \
noted", "it is worth noting", "worth noting". If a fact matters, present the \
specific number/name/date — let the reader draw the conclusion. Assertions of \
significance are AI-slop tells; replace them with the concrete evidence that \
would have made them feel necessary in the first place.
- No unattributed predictions or expert opinions. "Experts say" without a named \
or described expert is not attribution.
- In headlines, state what happened — not what might happen. Headlines use \
"passes," not "could pass." Hedge modal verbs (could, may, might, would) signal \
speculation in a headline and are prohibited unless directly quoting a source \
statement.
- Neutral framing of competing legitimate perspectives. No false balance on \
empirical questions with clear factual consensus.
- Precise language: name individuals when known, state exact figures, specify \
locations when central.
- KILL SCAFFOLDING: Never use templatic transitions that announce what you're \
about to say. "This isn't just...", "Here's the thing...", "The bigger \
picture...", "What makes this...", "The reality is..." — these are filler. Cut \
them. Start the sentence with the fact itself.
- NO EM DASHES (—) OR EN DASHES (–) IN OUTPUT. They are an AI tell in written \
prose. Use periods, commas, semicolons, colons, or parentheses instead. Two \
short sentences beat one long sentence with an em dash. Hyphens in compound \
words ("twenty-four-hour," "fact-check") are fine — em dashes (—) and en \
dashes (–) are not.
- ATTRIBUTION IS FIELD-SPECIFIC. In the headline and summary, name no news \
outlets, wire services, or aggregators, and never write "sources report," \
"according to reports," "multiple outlets," "as reported," or tier labels ("US \
source," "international source," "independent source"); state facts directly and \
attribute statements only to the people and institutions in the news who made \
them. In the consensus and divergence fields only, you may name actual outlets \
(e.g., "Reuters," "according to The Washington Post") where it clarifies how \
coverage differs.
- NEVER use bracketed citations, footnotes, or reference markers like [1], [2,5], \
[Source], (1), etc. This is a news briefing, not an academic paper. Attribute \
inline using natural language ("according to...", "...X reported").
- NO META-COMMENTARY ABOUT THE SOURCE MATERIAL. You are reporting the story, not \
reviewing your inputs. Never mention "the provided articles," "the provided \
text," "the reporting," "the coverage," or "the available text," and never note \
that a detail "was not detailed / specified / provided / available" or that "the \
article cuts off." If a fact is absent, simply leave it out. Write only what the \
story says, never what it fails to say.\
"""

# ---------------------------------------------------------------------------
# User prompt template — per-call task injected with article context.
# {context_line} and {articles_block} are replaced at call time.
# ---------------------------------------------------------------------------
_USER_PROMPT_TEMPLATE = """\
Analyze the following news cluster and return a JSON object with exactly seven \
fields: headline, summary, consensus, divergence, editorial_importance, story_type, has_binding_consequences.

{context_line}
{source_names_line}
ARTICLES:
{articles_block}

---

TASK 1 — headline (string)
Write an 8-12 word factual headline. Count the words carefully.
- Title Case. Active voice. Present tense.
- State the action, the actor, and location if essential.
- No question marks, exclamation marks, or ellipses.
- No hedge constructions: "could," "may," "might," "would" are prohibited \
unless directly quoting a source statement.
- Prohibited words: crackdown, explosive, bombshell, shocking, stunning, chaos, \
chaotic, slams, blasts, doubles down, firestorm, war of words, crisis (unless an \
official designation).
- Do not reproduce sensationalist language from source headlines.
Good: "Senate Passes $1.2 Trillion Infrastructure Bill After Weekend Vote"
Bad: "Shocking Vote Shakes Washington as Senate Acts on Roads"
Bad: "US Senate Could Pass Immigration Bill as Talks Continue"

---

TASK 2 — summary (string, 250-350 words)
Write a comprehensive factual briefing in inverted pyramid structure. This should \
read like a complete news intelligence brief — rich with specifics, diverse \
perspectives, and contextual depth. SHOW, DON'T TELL: let concrete facts, figures, \
and juxtaposed perspectives convey significance. Never assert that something is \
"significant" or "notable" — show the evidence and let the reader conclude.

IMPORTANT: Articles are sorted newest-first and include publication timestamps. \
Lead with the MOST RECENT development — what is new as of the latest articles. \
Older articles in the cluster provide context and background, but the lede must \
reflect the freshest reported facts. If a cluster spans multiple days, clearly \
distinguish what happened today from prior developments.

DOMINANT STORY ONLY: Summarize ONLY the single story about the entities named in \
the DOMINANT TOPIC / ENTITIES line above; ignore any article whose subject is a \
different event, person, or place than those entities. These articles were \
grouped automatically and one or two may concern a DIFFERENT event. Never stitch \
two unrelated stories into one briefing, and never reference a person, place, or \
event that does not belong to the dominant story.

Paragraph 1 (2-3 sentences): The most recent newsworthy development — what just \
happened, who, when, where. Lead with the latest event. State the single most \
important figure, name, or outcome from the freshest reporting. \
ARRIVE LATE: start inside the action. Do not open with "In a move that...", \
"Following weeks of...", "As tensions grew..." — the reader does not need \
runway. The first sentence should name a concrete action, actor, or figure \
that happened in the last 24 hours.

Paragraph 2 (3-4 sentences): Context. What preceded this and how it connects to \
the broader story. Give the background in your own words; attribute any statement \
to the official or institution that made it, never to an outlet.

Paragraph 3 (3-4 sentences): The range of stated positions. What the principal \
actors, officials, and affected parties say, and where their accounts or claims \
compete. Give each position equal weight. Describe what the people in the story \
say and do, not what news outlets emphasize.

Paragraph 4 (2-3 sentences): Additional specifics not already stated above. \
Secondary figures, direct quotes, technical details, geographic scope, affected \
populations. This is where data density matters most.

Paragraph 5 (1-2 sentences): Next steps, a deadline, an expected decision, or \
stated consequences. What to watch for next.

WRITE AS AN INDEPENDENT CORRESPONDENT. This is your own report, in void --news's \
own voice. Name no news outlet, wire service, or aggregator anywhere in the \
summary. Do not write "sources report," "sources say," "according to reports," \
"multiple outlets," "as reported," "reporting indicates," or any tier label ("US \
source," "international source," "independent source"). State each fact directly, \
as established fact. Attribute statements only to the people and institutions who \
made them (a named official, agency, company, or court), never to the press that \
covered the story.

VOICE: Write with the confidence and authority of a seasoned correspondent. Use \
precise nouns and strong active verbs. Prefer plain declarative sentences that \
state what happened. Do not hedge with "reportedly," "apparently," or "seemingly" \
unless the fact is genuinely contested in the coverage.

NO REPETITION: State each fact, figure, name, and quote exactly once. Do not \
restate the opening development later in the summary, and do not repeat a number, \
phrase, or sentence you have already written. Every paragraph adds new information.

Prohibited constructions:
- "In a stunning/shocking/unprecedented development..."
- "The world watched as..."
- "Experts say..." or "Analysts believe..." without named or described attribution
- "...raising questions about..." (vague concern framing)
- "...sparking outrage/controversy..." (importing reaction framing)
- Generic tier labels like "a US major source" or "an international outlet"
- Any reference to the outlets, wire services, or "sources" that reported the \
story: "Reuters reported," "according to The Washington Post," "sources say," \
"multiple sources report," "as reported by." Name only the people and \
institutions inside the story, never the press that covered it.
- Any adjective that expresses editorial judgment rather than factual description
- Bracketed citations or reference numbers like [1], [2,5], [Source 3], (1). \
This is a news article, not a research paper. Use natural inline attribution.
- Em dashes (—) and en dashes (–). Banned in summary output. They are an AI \
tell. Rewrite as two sentences, or use a comma, semicolon, or parentheses.

---

TASK 3 — consensus (array of 3-5 strings)
List 3-5 specific factual points confirmed across all or most sources.
- One sentence per point.
- Specific: include names, numbers, dates, official positions, stated figures.
- Do not state the obvious ("sources agree the event occurred").
- Frame as factual confirmation: "All sources report that..." or name the \
specific verified fact directly.
- Prohibited: generic observations, unattributed interpretive claims.

---

TASK 4 — divergence (array of 2-4 strings)
List 2-4 observable ways sources differ in what they cover, emphasize, or frame.
- One sentence per point.
- Describe coverage patterns, not outlet credibility or character.
- Reference outlets by name where useful for specific divergence points.
- Permitted verbs: emphasize, include, omit, lead with, frame as, devote more \
coverage to, focus on, give less prominence to.
- Prohibited words: bias, ignore, spin, push, hide, downplay, downplayed, \
agenda, chose not to report, failed to mention.
- When sources cite conflicting verifiable facts, describe the conflict neutrally: \
"Reuters and Al Jazeera cite differing figures for [specific metric]."

---

TASK 5 — editorial_importance (integer, 1-10)
Rate this story's editorial importance. Primary question: "Would a senior NYT \
editor put this on the front page?"

10 = once-in-a-decade event (war declaration, pandemic, constitutional crisis, \
regime change)
8-9 = major irreversible development: supreme court ruling, military action, \
central bank rate change, treaty signed
6-7 = significant development with binding or structural consequences: \
legislation passed, sanctions imposed, major leader speech with policy commitment, \
election result
4-5 = significant but reversible or provisional: policy proposal, summit meeting, \
bilateral statement, major indictment without verdict, large protest
2-3 = incremental update on a known story: day-N of ongoing talks, progress \
report, reaction statement to a prior event
1 = ceremonial, human interest, or symbolic: award, anniversary, cultural event

Tiebreaker: if uncertain between two adjacent scores, score lower if (a) this is \
a continuation of a story already widely reported, or (b) the primary action is a \
statement rather than a decision.

---

TASK 6 — story_type (string, one of these exact values)
Classify into exactly one type:
- "breaking_crisis": active unfolding emergency with immediate consequences
- "policy_action": government/institutional decision with binding consequences
- "investigation": journalistic investigation revealing unknown information
- "ongoing_crisis": the story is about an active situation (war, famine, pandemic, \
political crisis) where no single news cycle contains the entire story. Choose \
this when articles primarily describe the state of an ongoing situation.
- "incremental_update": a specific narrow development on a story that has already \
been reported. Choose this when articles primarily describe a reaction, a minor \
announcement, or a scheduled event within a larger story. Example: spokesperson \
declining comment, scheduled hearing update.
- "human_interest": individual-focused story without policy implications
- "ceremonial": commemorative events, symbolic actions, awards, anniversaries
- "entertainment": arts, culture, sports, celebrity

---

TASK 7 — has_binding_consequences (boolean)
Does this story report a decision or event with binding policy, legal, military, or economic consequences? True if it changes the legal/military/economic status quo (law signed, sanctions imposed, rate decision, military deployment, court ruling). False for proposals, discussions, reactions, commentary, or ceremonial events.

---

Return JSON only. No markdown fences. No text outside the JSON object.

{{"headline": "...", "summary": "...", "consensus": ["...", ...], "divergence": ["...", ...], "editorial_importance": N, "story_type": "...", "has_binding_consequences": true/false}}\
"""

# ---------------------------------------------------------------------------
# Quality gate — prohibited terms scanned after generation.
# Warnings are logged but results are never discarded (zero extra API calls).
# Uses shared module when available; falls back to local list for resilience.
# ---------------------------------------------------------------------------
if _USE_SHARED_PROHIBITED:
    _PROHIBITED_TERMS = _SHARED_PROHIBITED
else:
    _PROHIBITED_TERMS = frozenset({
        "shocking", "stunned", "stunning", "explosive", "bombshell", "devastating",
        "chaos", "chaotic", "firestorm", "crackdown", "slams", "blasts",
        "doubles down", "war of words", "sparking outrage", "raising questions",
        "raises concerns", "casts doubt", "throws into question",
        "in an unprecedented", "unprecedented", "in a stunning", "the world watched",
        "experts say", "analysts believe", "experts believe", "analysts say",
        "it was widely reported", "it is widely understood",
        "controversial", "divisive", "landmark", "historic",
        "radical", "extreme", "common-sense",
        "could signal", "may mark", "might reshape",
        "most significant", "most important development", "key moment",
        "downplayed", "failed to mention", "chose not to report",
        "a us major source", "an international outlet", "a major source",
    })

# Minimum sources for a cluster to qualify for Gemini summarization.
# 2-source clusters don't benefit much from LLM synthesis — the rule-based
# "pick best title" approach works fine. 3+ sources is where synthesis shines.
_MIN_SOURCES = 3


# Show-don't-tell violations: phrases that ASSERT significance rather than
# letting concrete facts demonstrate it.  See CLAUDE.md Cardinal Rule.
# Compiled once at module load.  Re-used in summarize_cluster retry path.
import re as _re
_SHOW_DONT_TELL_PATTERN = _re.compile(
    r"\b(notable|notably|significant(ly)?|crucial(ly)?|interesting(ly)?|"
    r"it should be noted|it is worth noting|worth noting|"
    r"importantly|remarkably|strikingly)\b",
    _re.IGNORECASE,
)


def _detect_show_dont_tell_violations(result: dict) -> list[str]:
    """Return list of violation phrases found across headline/summary/consensus/divergence."""
    text = " ".join([
        result.get("headline", "") or "",
        result.get("summary", "") or "",
        *(result.get("consensus") or []),
        *(result.get("divergence") or []),
    ])
    return list({m.group(0).lower() for m in _SHOW_DONT_TELL_PATTERN.finditer(text)})


# Source-agnostic enforcement for the SUMMARY field only. The summary must read as
# independent reporting: no outlet names, wire services, or "sources report"
# attribution. (consensus/divergence are exempt — divergence deliberately names
# outlets for the Deep Dive / Divergence Alerts comparison.)
_SUMMARY_SOURCE_REF_PATTERN = _re.compile(
    r"\b(according to (?:reports|sources)|"
    r"sources?\s+(?:say|said|report|reported|tell|told|confirm|confirmed|note|noted)|"
    r"multiple\s+(?:sources|outlets)|as\s+reported(?:\s+by)?|"
    r"reporting\s+(?:indicates|suggests|shows)|news\s+outlets?|wire\s+services?|"
    r"us\s+source|international\s+source|independent\s+source)\b",
    _re.IGNORECASE,
)

# Minimum normalized length for a sentence to be eligible for de-duplication.
# Guards against corrupting text by dropping short fragments (e.g. abbreviation
# splits like "U.S." or one-word sentences) that can legitimately recur.
_DEDUPE_MIN_LEN = 40


def _dedupe_summary_sentences(summary: str) -> str:
    """
    Remove exact duplicate sentences from a summary, preserving order and casing.

    Only drops a sentence when its whitespace/case-normalized form exactly matches
    an earlier one AND is at least _DEDUPE_MIN_LEN chars, so short fragments are
    never removed. Deterministic; runs on the summary field only. Fixes the
    repeated-line failure mode of the smaller summarization models.
    """
    if not summary or not summary.strip():
        return summary
    parts = _re.split(r"(?<=[.!?])\s+", summary.strip())
    seen: set[str] = set()
    kept: list[str] = []
    for part in parts:
        norm = _re.sub(r"\s+", " ", part.strip().lower())
        if not norm:
            continue
        if len(norm) >= _DEDUPE_MIN_LEN and norm in seen:
            continue  # exact duplicate of an earlier substantial sentence
        seen.add(norm)
        kept.append(part.strip())
    return " ".join(kept)


# ---------------------------------------------------------------------------
# Source-meta-commentary strip (belt-and-suspenders to the system-instruction
# ban above). The smaller Gemini models sometimes narrate the limits of their
# inputs instead of just reporting the story, leaking sentences like:
#   "[The article cuts off here, preventing further detail on the agreement]"
#   "the provided articles do not detail specific policy proposals ..."
#   "... are not available in the provided text."
#   "The specific nature ... were not detailed in the reporting."
# These are AI tells that must never reach the reader. Deterministic, $0.
# High-precision: only self-referential source/coverage meta phrases are hit,
# so a legitimate factual sentence ("The FBI has not commented") is preserved.
# ---------------------------------------------------------------------------

# Bracketed editorial aside about the inputs, e.g. "[The article cuts off ...]".
_META_BRACKET_RE = _re.compile(
    r"\s*\[[^\]]*?(?:cut[s]?\s+off|provided\s+(?:text|articles?)|"
    r"not\s+(?:available|provided|detailed|specified|clear))[^\]]*?\]",
    _re.IGNORECASE,
)

# A whole sentence is meta-commentary if it references the corpus itself
# ("the provided articles / text") or narrates an absence "in the reporting /
# coverage / provided text / available text".
_META_SENT_RE = _re.compile(
    r"(?:"
    r"provided\s+(?:text|articles?)"
    r"|not\s+(?:detailed|specified|mentioned|provided|disclosed|elaborated|"
    r"clear|available|reported)\b[^.?!]{0,80}?\bin\s+the\s+"
    r"(?:reporting|coverage|provided\s+(?:text|articles?)|available\s+(?:text|reporting)|text)"
    r"|\bin\s+the\s+(?:provided\s+)?(?:reporting|coverage)\b[^.?!]{0,40}?\bnot\b"
    r")",
    _re.IGNORECASE,
)


def _strip_source_meta_commentary(summary: str) -> str:
    """Drop bracketed input-asides and whole sentences that narrate the limits
    of the source material rather than reporting the story. Deterministic; a
    no-op on clean summaries. Never returns empty: if every sentence is meta
    (pathological), the original text is kept so the card is not blanked."""
    if not summary or not summary.strip():
        return summary
    t = _META_BRACKET_RE.sub("", summary).strip()
    # Bracket removal can orphan punctuation ("Tuesday. . Anand" / "Tuesday..").
    t = _re.sub(r"\s+([.!?,;:])", r"\1", t)
    t = _re.sub(r"([.!?])\1+", r"\1", t)
    parts = _re.split(r"(?<=[.!?])\s+", t)
    kept = [p for p in parts if p.strip() and not _META_SENT_RE.search(p)]
    cleaned = " ".join(s.strip() for s in kept).strip()
    cleaned = _re.sub(r"\s{2,}", " ", cleaned)
    # Safety: never blank a card. Require a substantive remainder.
    if len(cleaned) < 40:
        return summary.strip()
    return cleaned


def _detect_summary_source_refs(summary: str, source_names: list[str]) -> list[str]:
    """
    Warning-only: flag outlet names or media-attribution phrasing in the SUMMARY.

    Returns a sorted list of offending phrases / outlet names found (or empty).
    Never mutates the summary — logged so we can detect prompt drift, consistent
    with the show-don't-tell post-check.
    """
    if not summary:
        return []
    hits = {m.group(0).lower() for m in _SUMMARY_SOURCE_REF_PATTERN.finditer(summary)}
    for name in source_names or []:
        n = (name or "").strip()
        if len(n) < 4:
            continue
        if _re.search(r"\b" + _re.escape(n) + r"\b", summary, _re.IGNORECASE):
            hits.add(f"outlet:{n}")
    return sorted(hits)


def _check_quality(result: dict, cluster_id: str | int = "") -> None:
    """
    Log quality warnings for out-of-spec generated content.

    Checks headline word count (8-12), summary word count (250-350),
    consensus/divergence item counts, and scans all text fields for
    prohibited sensationalist or value-laden terms.

    Does not modify or discard the result — warnings are surfaced to the
    analytics-expert during post-run audit.
    """
    cid_str = f" {cluster_id}" if cluster_id != "" else ""

    headline = result.get("headline", "")
    word_count = len(headline.split())
    if not (8 <= word_count <= 12):
        print(
            f"  [quality]{cid_str} Headline word count {word_count} (expected 8-12): "
            f"{headline!r}"
        )

    # Summary word count (target: 250-350, warn outside 200-400 range)
    summary = result.get("summary", "")
    summary_wc = len(summary.split())
    if summary_wc > 0 and not (200 <= summary_wc <= 400):
        print(
            f"  [quality]{cid_str} Summary word count {summary_wc} (expected 250-350): "
            f"first 80 chars: {summary[:80]!r}"
        )

    # Consensus/divergence item counts
    consensus_count = len(result.get("consensus", []))
    if consensus_count > 0 and not (3 <= consensus_count <= 5):
        print(f"  [quality]{cid_str} Consensus count {consensus_count} (expected 3-5)")

    divergence_count = len(result.get("divergence", []))
    if divergence_count > 0 and not (2 <= divergence_count <= 4):
        print(f"  [quality]{cid_str} Divergence count {divergence_count} (expected 2-4)")

    ei = result.get("editorial_importance")
    if ei is not None and not (1 <= int(ei) <= 10):
        print(f"  [quality]{cid_str} editorial_importance out of range: {ei}")

    # Scan headline + summary + all consensus + all divergence items
    all_text = " ".join([
        headline,
        summary,
        *result.get("consensus", []),
        *result.get("divergence", []),
    ]).lower()

    found = [t for t in _PROHIBITED_TERMS if t in all_text]

    # Check for bracketed citations [1], [2,5], [Source 3], etc.
    import re
    bracket_refs = re.findall(r'\[\d[\d,\s]*\]|\[source\s*\d*\]', all_text)
    if bracket_refs:
        found.extend(f"citation:{ref}" for ref in bracket_refs[:3])

    if found:
        print(
            f"  [quality] Prohibited terms in cluster {cluster_id}: {found}"
        )


# ---------------------------------------------------------------------------
# Summary coherence gate — deterministic on-topic INPUT FILTER (Option 1)
# + computed DOMINANT-TOPIC prompt line (Option 2).
# ---------------------------------------------------------------------------
# 2026-08-06: an over-merged Phase-5 "bag" can carry an off-topic member whose
# article text bleeds into the LLM summary, so the rendered briefing references
# a person/place/event that does not belong to the cluster's headline story.
# This filter computes the cluster's DOMINANT topic tokens from the member
# titles (+ the cluster title when known) and DROPS members whose title shares
# no dominant token, BEFORE the prompt is built — the model never sees the
# off-topic article. Ports the proven ig_generator._ontopic_outlets pattern to
# the summarizer chokepoint (summarize_cluster), so a single change covers all
# four LLM summary passes (7b batch, 8d top50, 8d.6 floor, 8d.7 reconcile).
#
# Cache safety: the four callers key the content-hash cache on FULL membership;
# this filter is deterministic given (membership, title), so identical
# membership yields identical filtered input and therefore an identical summary.
# The cache key is NOT changed. source_count, the coverage/"Contested" bar, and
# the near-dup guard are untouched — only the summary TEXT input narrows.
_ONTOPIC_MIN_MEMBERS = 4      # no-op below this many members
_ONTOPIC_FLOOR = 3            # never strip below this many members

_ONTOPIC_UNSET = object()
_ONTOPIC_STEMS_FN = _ONTOPIC_UNSET

_ONTOPIC_LOCAL_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "over", "after", "before",
    "under", "about", "amid", "amidst", "says", "said", "will", "would",
    "could", "should", "has", "have", "had", "are", "was", "were", "been",
    "its", "his", "her", "their", "new", "how", "why", "what", "when",
    "where", "who", "this", "that", "these", "those", "than", "then",
    "live", "update", "updates", "report", "reports", "amp", "news",
})


def _ontopic_stems_fn():
    """Lazy, cached handle to clustering's canonical title stemmer
    (_title_word_stems: Porter stem + shared stopwords). Reused so the on-topic
    filter judges member titles with the exact lens the upstream clusterer used.
    Returns None if clustering (spaCy/nltk) cannot be imported; callers fall
    back to the local content-word tokenizer."""
    global _ONTOPIC_STEMS_FN
    if _ONTOPIC_STEMS_FN is _ONTOPIC_UNSET:
        try:
            from clustering.story_cluster import _title_word_stems
            _ONTOPIC_STEMS_FN = _title_word_stems
        except Exception:
            _ONTOPIC_STEMS_FN = None
    return _ONTOPIC_STEMS_FN


def _ontopic_local_tokens(title: str) -> set[str]:
    """Fallback tokenizer (clustering-import-independent): 4+ char content
    words, stopword-filtered. Mirrors ig_generator._title_tokens."""
    import re
    return {
        w for w in re.findall(r"[a-z0-9]{4,}", (title or "").lower())
        if w not in _ONTOPIC_LOCAL_STOPWORDS
    }


# Generic anchor words — institutional common nouns, bare country / nationality
# names, and generic event words. A LONE generic word (e.g. "military",
# "supreme court", "Nigeria", "summit", "election") must never be the token that
# keeps an off-topic member in the summary input: on an over-merged bag those
# words bridge unrelated stories. This is the summarizer's belt-and-suspenders to
# the upstream data-driven clustering gate (the primary defense); it ensures a
# slipped bag still yields a summary about the cluster's DOMINANT (title) topic
# rather than a minority member. Kept modest and behavior-safe: if stripping
# generics empties the title-topic set we simply fall back to the prior broad
# core, so over-inclusion never mis-strips a real cluster.
_GENERIC_TOPIC_WORDS = (
    # institutions / roles / bodies
    "military supreme court government police senate parliament ministry "
    "commission congress cabinet council president minister prime federal "
    "administration department agency authority committee party union army "
    "navy forces general official officials leader leaders chief state states "
    "house panel board tribunal assembly secretary spokesman spokesperson "
    "nation national international regional "
    # generic event / news words (the CEO's whack-a-mole examples + kin)
    "summit election elections festival meeting talks statement report update "
    "latest news world global "
    # common country / nationality names (a bare country is not a story)
    "nigeria nigerian india indian china chinese russia russian america "
    "american britain british england english iran iranian israel israeli "
    "japan japanese germany german france french ukraine ukrainian pakistan "
    "pakistani egypt egyptian turkey turkish brazil brazilian mexico mexican "
    "canada canadian australia australian spain spanish italy italian europe "
    "european africa african asia asian korea korean saudi qatar kenya kenyan "
    "ethiopia indonesia philippine philippines thailand vietnam poland polish "
    "sweden swedish norway greece greek ireland irish scotland scottish"
)
_GENERIC_TOPIC_TOKENS = _ONTOPIC_UNSET
_GENERIC_LOCAL_TOKENS = _ONTOPIC_UNSET


def _generic_topic_tokens() -> set[str]:
    """Generic anchor words in the SAME token space the on-topic filter uses for
    member titles (Porter stems when clustering is importable, else the local 4+
    char tokenizer). Built by running the generic word list through the identical
    tokenizer, so comparison is apples-to-apples. Cached."""
    global _GENERIC_TOPIC_TOKENS
    if _GENERIC_TOPIC_TOKENS is _ONTOPIC_UNSET:
        _GENERIC_TOPIC_TOKENS = _ontopic_title_tokens(_GENERIC_TOPIC_WORDS)
    return _GENERIC_TOPIC_TOKENS


def _generic_local_tokens() -> set[str]:
    """Generic anchor words in the LOCAL (unstemmed) token space used by
    _build_dominant_topic_line. Cached."""
    global _GENERIC_LOCAL_TOKENS
    if _GENERIC_LOCAL_TOKENS is _ONTOPIC_UNSET:
        _GENERIC_LOCAL_TOKENS = _ontopic_local_tokens(_GENERIC_TOPIC_WORDS)
    return _GENERIC_LOCAL_TOKENS


def _ontopic_title_tokens(title: str) -> set[str]:
    """Content-token set of a title. Prefers clustering's Porter-stem pipeline
    (matches the upstream clusterer); falls back to the local 4+ char tokenizer
    when clustering can't load or yields nothing."""
    fn = _ontopic_stems_fn()
    if fn is not None:
        try:
            toks = fn(title or "")
            if toks:
                return toks
        except Exception:
            pass
    return _ontopic_local_tokens(title or "")


def _filter_ontopic_articles(articles: list[dict],
                             cluster_title: str | None = None) -> list[dict]:
    """Restrict the summary input to the cluster's DOMINANT (title) topic so the
    LLM never describes a minority member of an over-merged bag.

    The invariant this enforces: the shipped summary's subject matches the
    cluster's title/dominant topic, not whichever off-topic member happens to
    carry the most text. Two regimes:

      * COHERENT cluster (the title is on-topic for a healthy share of members):
        core = the title's specific tokens UNION the shared spine (tokens shared
        by >= 2 member titles), so a genuine single story with varied headline
        vocabulary keeps every member. This preserves prior behavior.

      * INCOHERENT BAG (the title matches only a MINORITY of members): anchor
        STRICTLY on the title's specific tokens and drop the off-topic (possibly
        larger) sub-pile, so the summary is built about the headline story. This
        is the #48/#50 wrong-story-summary fix.

    Generic anchor words (institutions, bare country names, generic event words)
    are stripped from BOTH the core and each member's tokens, so a lone generic
    word ("military", "supreme court", "Nigeria") can never bridge an off-topic
    member into the input.

    Guards:
      - No-op when the cluster has < 4 members.
      - If there is nothing specific to anchor on (title + spine are empty after
        generic-stripping), widen back to full membership (no-op).
      - Never returns an empty set: if the anchor matches no member (a title that
        shares nothing with any headline), fall back to full membership rather
        than blank the summary.
    Deterministic given (membership, title) — the content-hash cache key is
    unchanged, so identical membership still yields an identical summary.
    """
    if len(articles) < _ONTOPIC_MIN_MEMBERS:
        return articles

    from collections import Counter
    generic = _generic_topic_tokens()
    freq: Counter[str] = Counter()
    member_tokens: list[set[str]] = []
    for art in articles:
        toks = _ontopic_title_tokens(art.get("title") or "")
        member_tokens.append(toks)
        freq.update(toks)

    shared = {t for t, c in freq.items() if c >= 2}
    title_specific = _ontopic_title_tokens(cluster_title or "") - generic

    # How many members does the TITLE itself describe (via a SPECIFIC token)?
    n_title_on_topic = (
        sum(1 for toks in member_tokens if (toks - generic) & title_specific)
        if title_specific else 0
    )
    minority_ceiling = max(2, (len(articles) + 1) // 2)

    if title_specific and 0 < n_title_on_topic < minority_ceiling:
        # Incoherent bag: the headline is on-topic for a minority of members.
        # Summarize the TITLE's story, not the off-topic majority.
        core = title_specific
        mode = "title-anchored"
    else:
        # Coherent (or title too thin to judge): title tokens + shared spine.
        core = (title_specific | shared) - generic
        mode = "broad"
        if not core:
            # Nothing specific to anchor on — do not trust the filter.
            return articles

    kept = [
        art for art, toks in zip(articles, member_tokens)
        if (toks - generic) & core
    ]
    if not kept:
        # Anchor matched no member (e.g. a title sharing nothing with any
        # headline). Never blank the summary — fall back to full membership.
        return articles
    if len(kept) < len(articles):
        print(
            f"  [coherence:{mode}] dropped {len(articles) - len(kept)} off-topic "
            f"member(s) from the summary input of a {len(articles)}-member "
            f"cluster (title on-topic for {n_title_on_topic})"
        )
    return kept


def _build_dominant_topic_line(articles: list[dict],
                               cluster_title: str | None = None) -> str:
    """Render a DOMINANT TOPIC / ENTITIES line for the prompt (Option 2).

    Uses the same title-frequency vote as the on-topic filter, but surfaces the
    raw (unstemmed) high-frequency title words so the model reads recognizable
    entity names. Cluster-title words lead; remaining terms are ranked by
    cross-headline frequency (the shared spine). Deterministically ordered so
    the line is stable run-to-run. Steers the summary onto the single dominant
    story described by the headline. Adds ~20 tokens, no new API calls."""
    from collections import Counter
    generic = _generic_local_tokens()
    freq: Counter[str] = Counter()
    for art in articles:
        freq.update(_ontopic_local_tokens(art.get("title") or ""))

    # Prefer SPECIFIC terms so the dominant-topic line names recognizable
    # entities, not generic institution / country / event words that bridge
    # unrelated stories on an over-merged bag.
    title_terms = sorted(_ontopic_local_tokens(cluster_title or "") - generic)
    title_set = set(title_terms)
    ranked = sorted(
        (t for t, c in freq.items()
         if c >= 2 and t not in title_set and t not in generic),
        key=lambda t: (-freq[t], t),
    )
    terms = title_terms + ranked
    if not terms:
        # No specific spine and no specific title tokens: fall back to the most
        # common title words (generic-filtered first, then unfiltered).
        terms = [
            t for t, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
            if t not in generic
        ] or [t for t, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))]
    terms = terms[:8]
    if not terms:
        return ""
    return "DOMINANT TOPIC / ENTITIES: " + ", ".join(terms) + "\n"


def _build_context_line(articles: list[dict]) -> str:
    """
    Build a one-line cluster metadata header for the prompt.

    Tells Gemini total article count, tier distribution, and time range
    so it can calibrate synthesis depth and prioritize recent developments.
    """
    total = len(articles)
    tier_counts: dict[str, int] = {}
    timestamps = []
    for art in articles:
        tier = (art.get("tier", "") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        pub = art.get("published_at", "")
        if pub:
            timestamps.append(pub[:16])

    parts = []
    if tier_counts.get("us_major"):
        parts.append(f"{tier_counts['us_major']} US major")
    if tier_counts.get("international"):
        parts.append(f"{tier_counts['international']} international")
    if tier_counts.get("independent"):
        parts.append(f"{tier_counts['independent']} independent")

    distribution = ", ".join(parts) if parts else "mixed sources"

    # Add time range so Gemini knows how fresh the cluster is
    time_range = ""
    if timestamps:
        oldest = min(timestamps)
        newest = max(timestamps)
        if oldest != newest:
            time_range = f" Coverage spans {oldest} to {newest}. Lead with the most recent developments."
        else:
            time_range = f" Published around {newest}."

    return f"CLUSTER METADATA: {total} articles from {distribution} outlets.{time_range}\n"


def _build_source_names_line(articles: list[dict]) -> str:
    """
    Build a SOURCE NAMES reference line mapping article numbers to outlet names.

    Provides real outlet names so Gemini can use them in the consensus and
    divergence fields only (never in the headline or summary, which are
    source-agnostic), instead of generic tier labels.
    """
    names = []
    for i, art in enumerate(articles[:10]):
        source_name = (art.get("source_name", "") or "").strip()
        if source_name:
            names.append(f"[{i + 1}] {source_name}")
    if not names:
        return ""
    label = (
        "SOURCE NAMES (for the consensus and divergence fields only; never use "
        "these names in the headline or summary): "
    )
    return label + ", ".join(names) + "\n"


def _build_articles_block(articles: list[dict], max_articles: int = 10) -> str:
    """
    Build the articles context block for the prompt.

    Uses tier-based labels in the article block itself (to prevent Gemini
    from weighting outlets by brand recognition), but real outlet names are
    provided separately via _build_source_names_line for attribution use.

    Articles are sorted newest-first so Gemini sees the most recent
    developments at the top of the context window. Each article includes
    its publication timestamp so Gemini can distinguish fresh developments
    from older background.

    Limits to max_articles and includes summaries up to 400 chars to give
    Gemini sufficient material for comprehensive synthesis.
    """
    _TIER_LABEL_MAP = {
        "us_major": "US Source",
        "international": "International Source",
        "independent": "Independent Source",
    }

    # Sort newest-first across the WHOLE membership, then slice. Slicing
    # first fed the prompt an arbitrary 10 of a larger cluster while
    # _content_hash() keyed the cache on the true newest 10 — the prompt
    # inputs and the cache key diverged. Sort key matches _content_hash
    # (published_at, id) for full determinism.
    sorted_articles = sorted(
        articles,
        key=lambda a: (
            a.get("published_at") or "",
            str(a.get("id") or a.get("article_id") or ""),
        ),
        reverse=True,
    )[:max_articles]

    lines = []
    for i, art in enumerate(sorted_articles):
        title = (art.get("title", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()
        pub_date = (art.get("published_at", "") or "")[:16]  # YYYY-MM-DDTHH:MM

        # Use tier as source label in the article block.
        # Normalize tier value: lowercase + replace hyphens with underscores.
        tier_raw = (art.get("tier", "") or "").strip().lower().replace("-", "_")
        source_label = _TIER_LABEL_MAP.get(tier_raw, f"Source {i + 1}")

        header = f"[{i + 1}] {source_label}: {title}"
        if pub_date:
            header += f"  ({pub_date})"

        if len(summary) > 400:
            summary = summary[:397] + "..."

        lines.append(header)
        if summary:
            lines.append(f"    {summary}")
        lines.append("")

    return "\n".join(lines)


def _build_claims_block(claims_consensus) -> str:
    """
    Format NLP-extracted claims for the Gemini prompt.

    Produces a readable list with unicode status markers.
    """
    if claims_consensus is None:
        return ""

    lines = ["", "CLAIM EXTRACTION (NLP — void --verify):"]
    claims = getattr(claims_consensus, "claims", [])
    if not claims:
        return ""

    for vc in claims[:20]:  # Cap at 20 to stay within token limits
        status = getattr(vc, "status", "unverified")
        text = getattr(vc, "claim_text", "")
        count = getattr(vc, "source_count", 1)
        sources = getattr(vc, "source_names", [])
        total = getattr(claims_consensus, "total_claims", 0) or len(claims)

        if status == "corroborated":
            src_str = ", ".join(sources[:5]) if sources else ""
            lines.append(f"✓ CORROBORATED ({count}/{total} sources): \"{text}\"")
        elif status == "disputed":
            lines.append(f"⚠ DISPUTED: \"{text}\"")
        elif status == "single_source":
            src = sources[0] if sources else "unknown"
            lines.append(f"○ SINGLE SOURCE (only: {src}): \"{text}\"")

    # Add disputed details
    disputed_details = getattr(claims_consensus, "disputed_details", [])
    for dd in disputed_details[:5]:
        va = getattr(dd, "version_a", "")
        vb = getattr(dd, "version_b", "")
        va_src = ", ".join(getattr(dd, "version_a_sources", []))
        vb_src = ", ".join(getattr(dd, "version_b_sources", []))
        lines.append(f"  → \"{va}\" ({va_src}) vs \"{vb}\" ({vb_src})")

    return "\n".join(lines) + "\n"


# Claims deduplication task template (appended when claims data is available)
_CLAIMS_TASK_TEMPLATE = """
---

TASK 8 — claims (array of objects), consensus_ratio (float), consensus_summary (string)
You are given NLP-extracted factual claims from articles in this cluster with their verification status.

Your job:
1. Deduplicate semantically equivalent claims (NLP may extract "GDP grew 3.2%"
   and "the economy expanded by 3.2%" as separate claims — merge them)
2. Write a canonical version of each unique claim (clear, concise)
3. Preserve source counts and contradiction details
4. Select the 3-5 most newsworthy claims to highlight
5. For disputed claims, write both versions clearly
6. Write a one-sentence consensus_summary describing overall source agreement

Output these three additional fields in the JSON:
"claims": [{"text": "...", "status": "corroborated|single_source|disputed", "source_count": N, "sources": ["..."], "highlight": true, "disputed_versions": [{"text": "...", "sources": ["..."]}]}],
"consensus_ratio": 0.0-1.0,
"consensus_summary": "One sentence describing overall source agreement"
"""


def summarize_cluster(articles: list[dict],
                      claims_consensus=None,
                      prefer_provider: str | None = None,
                      model: str | None = None,
                      cluster_title: str | None = None) -> dict | None:
    """
    Generate headline, summary, consensus, and divergence for a cluster.

    prefer_provider is retained for signature compatibility (Groq retired).
    `model` selects the Gemini tier (GEMINI_FLASH_MODEL for the premium top-N
    stories; None = flash-lite default). See _smart_generate_json.
    `cluster_title` (optional) is the cluster's stored headline; it strengthens
    the summary coherence gate's dominant-topic vote. When omitted the gate
    votes on member titles alone, so no caller is forced to pass it.
    Returns None if no provider is configured, the call fails, or the chosen
    provider's per-run cap is reached (each client enforces its own cap and
    returns None, so no cross-provider budget gate here).
    """
    if not is_available():
        return None

    if not articles:
        return None

    # Summary coherence gate (Option 1): drop off-topic members so the prompt
    # inputs describe ONE story. Deterministic given (membership, title); the
    # callers key the content-hash cache on FULL membership, so this narrowing
    # of the summary TEXT input never invalidates the cache. source_count and
    # the coverage/near-dup signals are computed elsewhere and are untouched.
    summ_articles = _filter_ontopic_articles(articles, cluster_title=cluster_title)

    context_line = _build_context_line(summ_articles)
    source_names_line = _build_source_names_line(summ_articles)
    articles_block = _build_articles_block(summ_articles)
    # Option 2: a computed DOMINANT TOPIC / ENTITIES line, injected next to the
    # cluster-metadata context line to steer the model onto the dominant story.
    dominant_line = _build_dominant_topic_line(summ_articles, cluster_title)

    # Build claims context if available
    claims_block = _build_claims_block(claims_consensus) if claims_consensus else ""

    prompt = _USER_PROMPT_TEMPLATE.format(
        context_line=dominant_line + context_line,
        source_names_line=source_names_line,
        articles_block=articles_block,
    )

    # Inject claims task before the final "Return JSON only" line
    if claims_block:
        # Replace field count and add claims task
        # NOTE: the template's trailing backslash is a line CONTINUATION, so
        # the rendered prompt reads "exactly seven fields:" on one line. The
        # old needle contained a literal backslash+newline and never matched,
        # leaving the prompt self-contradictory (header said seven, TASK 8
        # demanded ten).
        prompt = prompt.replace(
            "exactly seven fields: headline, summary, consensus, divergence, "
            "editorial_importance, story_type, has_binding_consequences.",
            "exactly ten fields: headline, summary, consensus, divergence, "
            "editorial_importance, story_type, has_binding_consequences, "
            "claims, consensus_ratio, consensus_summary.",
        )
        # Insert claims block and task before "Return JSON only"
        prompt = prompt.replace(
            "Return JSON only. No markdown fences.",
            claims_block + _CLAIMS_TASK_TEMPLATE
            + "\n---\n\nReturn JSON only. No markdown fences.",
        )
        # Update the JSON example at the end
        prompt = prompt.replace(
            '"has_binding_consequences": true/false}',
            '"has_binding_consequences": true/false, '
            '"claims": [...], "consensus_ratio": 0.0, '
            '"consensus_summary": "..."}',
        )

    # Call the smart router directly (not the generate_json alias, which
    # discards the generator label) so callers can stamp summary_tier with
    # the provider that ACTUALLY answered.
    result, _generator_label = _smart_generate_json(
        prompt, system_instruction=_SYSTEM_INSTRUCTION,
        prefer_provider=prefer_provider, model=model,
    )

    if not result:
        return None

    # Show-don't-tell post-check: assertions of significance ("notable",
    # "significantly", "crucially", etc.) violate the Cardinal Rule.
    #
    # 2026-05-21 nlp-engineer cost-cut: the forbidden-word list is now
    # encoded directly in _SYSTEM_INSTRUCTION (FORBIDDEN SIGNIFICANCE-
    # ASSERTIONS section). Sonnet 4.6 follows it without needing a retry
    # call on every violation. The retry burned ~5-10 calls/day; with the
    # constraint baked into the prompt-cached system instruction, that
    # cost drops to zero. We keep the post-check as a warning log only so
    # we can detect drift if the model starts ignoring the constraint.
    violations = _detect_show_dont_tell_violations(result)
    if violations:
        print(
            f"  [show-dont-tell] violations detected (warning only, no retry): "
            f"{violations}"
        )

    # Validate response shape
    headline = result.get("headline", "")
    summary = result.get("summary", "")
    consensus = result.get("consensus", [])
    divergence = result.get("divergence", [])

    if not isinstance(headline, str) or not headline.strip():
        return None
    if not isinstance(summary, str) or not summary.strip():
        return None

    # Summary is source-agnostic: dedupe exact-duplicate sentences (deterministic)
    # and warn on any outlet name or media-attribution phrasing that leaks in.
    summary = _dedupe_summary_sentences(summary)

    # Enforce (not just warn) the no-em-dash + show-don't-tell Cardinal Rules.
    # The model follows the system instruction most of the time, but leaks slip
    # through ("significant", em-dashes); this deterministic pass removes them so
    # the displayed text always complies. (Wave 1 / O5.)
    headline = _sanitize_editorial(headline)
    summary = _sanitize_editorial(summary)
    # Remove source-material meta-commentary ("the provided articles do not...",
    # "[The article cuts off here]", "...not detailed in the reporting") that the
    # smaller models leak despite the system-instruction ban.
    summary = _strip_source_meta_commentary(summary)
    _summary_src_refs = _detect_summary_source_refs(
        summary, [a.get("source_name", "") for a in articles]
    )
    if _summary_src_refs:
        print(
            f"  [source-agnostic] summary references outlets/attribution "
            f"(warning only, no retry): {_summary_src_refs}"
        )

    if not isinstance(consensus, list):
        consensus = []
    if not isinstance(divergence, list):
        divergence = []

    # Consensus/divergence render on the Deep Dive — the em-dash /
    # significance-word ban applies to them exactly as to the summary.
    consensus = [s for s in (_sanitize_editorial(str(c)) for c in consensus if c) if s]
    divergence = [s for s in (_sanitize_editorial(str(d)) for d in divergence if d) if s]

    # Extract editorial intelligence fields (v5.0)
    editorial_importance = result.get("editorial_importance")
    if isinstance(editorial_importance, (int, float)):
        editorial_importance = max(1, min(10, int(editorial_importance)))
    else:
        editorial_importance = None

    _VALID_STORY_TYPES = {
        "breaking_crisis", "policy_action", "investigation",
        "ongoing_crisis", "incremental_update", "human_interest",
        "ceremonial", "entertainment",
    }
    story_type_raw = result.get("story_type", "")
    story_type = story_type_raw if story_type_raw in _VALID_STORY_TYPES else None

    has_binding = result.get("has_binding_consequences")
    has_binding_consequences = bool(has_binding) if isinstance(has_binding, bool) else None

    # void --verify: extract claim deduplication results
    claims = result.get("claims")
    if isinstance(claims, list):
        claims = [c for c in claims if isinstance(c, dict) and c.get("text")]
    else:
        claims = None

    consensus_ratio_val = result.get("consensus_ratio")
    if isinstance(consensus_ratio_val, (int, float)):
        consensus_ratio_val = max(0.0, min(1.0, float(consensus_ratio_val)))
    else:
        consensus_ratio_val = None

    consensus_summary_val = result.get("consensus_summary")
    if not isinstance(consensus_summary_val, str) or not consensus_summary_val.strip():
        consensus_summary_val = None

    validated = {
        "headline": headline.strip()[:500],
        "summary": summary.strip(),
        "consensus": consensus,
        "divergence": divergence,
        "editorial_importance": editorial_importance,
        "story_type": story_type,
        "has_binding_consequences": has_binding_consequences,
        "claims": claims,
        "consensus_ratio": consensus_ratio_val,
        "consensus_summary": consensus_summary_val,
        # Which provider answered ("gemini-flash" | "gemini-flash-lite").
        # Callers map this to summary_tier so the step-8d cache only
        # freezes genuine Sonnet output.
        "_generator": _generator_label,
    }

    # Quality gate: log warnings for out-of-spec output (no discards).
    # Cluster index is not available here; caller passes cluster id when needed.
    _check_quality(validated)

    return validated


def summarize_clusters_batch(clusters: list[dict],
                             cluster_consensus: dict | None = None,
                             top_n: int = 30,
                             regional_fill: int = 10,
                             topic_fill: int = 10,
                             prefer_provider: str | None = "gemini",
                             ) -> tuple[dict[int, dict], set[int]]:
    """
    Summarize up to 50 clusters using three non-overlapping priority pools.

    Pool 1 — Top 30 global (headline_rank DESC): ensures the most important
      stories always get Gemini-quality summaries.
    Pool 2 — Regional fill (up to 10): round-robin across editions
      (world/us/europe/south-asia) to guarantee each region has representation
      even when Pool 1 is dominated by one region.
    Pool 3 — Topic fill (up to 10): 1 per category desk first, then fills
      remaining slots with the best remaining clusters.

    Each cluster is summarized at most once. Pool 1 failures have their
    rule-based summaries cleared by the caller (no fallback for premium slots).
    Pool 2/3 failures keep their rule-based summaries as acceptable fallback.

    Args:
        clusters: List of cluster dicts with "articles" and "source_count".
        cluster_consensus: Optional dict of cluster_index_str -> ClusterConsensus.
        top_n: Pool 1 size (top global clusters). Defaults to 30.
        regional_fill: Pool 2 max size. Defaults to 10.
        topic_fill: Pool 3 max size. Defaults to 10.

    Returns:
        Tuple of:
          - Dict mapping cluster index -> summarize_cluster result.
          - Set of Pool 1 cluster indices that Gemini failed on — callers
            should clear their rule-based summaries so no fallback text
            reaches the frontend for these premium positions.
    """
    if not is_available():
        return {}, set()

    # ── Helper: check if a cluster qualifies for Gemini summarization ──
    def _qualifies(cluster: dict) -> bool:
        if cluster.get("_is_opinion"):
            return False
        sc = cluster.get("source_count", 0) or len(cluster.get("articles", []))
        return sc >= _MIN_SOURCES

    def _rank_key(i: int) -> tuple:
        return (clusters[i].get("headline_rank") or 0,
                clusters[i].get("source_count", 0))

    # All qualifying indices sorted by headline_rank DESC
    all_qualifying = sorted(
        (i for i, c in enumerate(clusters) if _qualifies(c)),
        key=_rank_key,
        reverse=True,
    )

    # ── Pool 1: Top N global ──────────────────────────────────────────────────
    pool1: list[int] = all_qualifying[:top_n]
    selected: set[int] = set(pool1)

    # ── Pool 2: Regional round-robin ──────────────────────────────────────────
    # 2026-05-21 nlp-engineer cost-cut: intersect with ACTIVE_EDITIONS from
    # the shared utils.editions module. The us/europe/south-asia editions
    # are parked (ACTIVE_EDITIONS = ["world"]); summarizing clusters for
    # those editions burns ~10 Sonnet calls/day with no UI consumer. When
    # only 'world' is active, Pool 2 collapses to additional global
    # candidates beyond Pool 1.
    #
    # 2026-05-22 hardened: was `from main import ACTIVE_EDITIONS`; pipeline-
    # tester flagged this as fragile under multiprocessing fork contexts
    # where the orchestrator entry point isn't on sys.path. The shared
    # module utils.editions has no upstream dependencies and is safe to
    # import from any worker.
    try:
        from utils.editions import ACTIVE_EDITIONS as _ACTIVE_EDITIONS
    except ImportError:
        _ACTIVE_EDITIONS = ["world", "us", "europe", "south-asia"]
    _EDITIONS = [e for e in ["world", "us", "europe", "south-asia"] if e in _ACTIVE_EDITIONS]
    if not _EDITIONS:
        _EDITIONS = ["world"]
    # If only 'world' is active, cap Pool 2 size so we don't double-spend on
    # global stories that Pool 1 already covers. Half of regional_fill is
    # enough to surface additional global candidates beyond the top_n cutoff.
    if _EDITIONS == ["world"]:
        regional_fill = max(0, regional_fill // 2)

    # Per-edition sorted candidate queue (excluding pool1)
    edition_queues: dict[str, list[int]] = {ed: [] for ed in _EDITIONS}
    for i in all_qualifying:
        if i in selected:
            continue
        sections = clusters[i].get("sections") or [clusters[i].get("section", "world")]
        for ed in _EDITIONS:
            if ed in sections:
                edition_queues[ed].append(i)
    # Queues are already in headline_rank order since all_qualifying is sorted

    pool2: list[int] = []
    edition_ptrs = {ed: 0 for ed in _EDITIONS}
    while len(pool2) < regional_fill:
        advanced = False
        for ed in _EDITIONS:
            if len(pool2) >= regional_fill:
                break
            ptr = edition_ptrs[ed]
            queue = edition_queues[ed]
            while ptr < len(queue):
                candidate = queue[ptr]
                ptr += 1
                if candidate not in selected:
                    pool2.append(candidate)
                    selected.add(candidate)
                    advanced = True
                    break
            edition_ptrs[ed] = ptr
        if not advanced:
            break  # All edition queues exhausted

    # ── Pool 3: Topic (category desk) fill ───────────────────────────────────
    _CATEGORIES = ["politics", "conflict", "economy",
                   "science", "health", "environment", "culture"]

    pool3: list[int] = []

    # First pass: 1 per category (breadth)
    seen_cats: set[str] = set()
    for i in all_qualifying:
        if len(pool3) >= topic_fill:
            break
        if i in selected:
            continue
        cat = (clusters[i].get("category") or "").lower()
        if cat in _CATEGORIES and cat not in seen_cats:
            pool3.append(i)
            selected.add(i)
            seen_cats.add(cat)

    # Second pass: fill remaining slots with best unselected clusters
    if len(pool3) < topic_fill:
        for i in all_qualifying:
            if len(pool3) >= topic_fill:
                break
            if i not in selected:
                pool3.append(i)
                selected.add(i)

    # ── Summarize: pool1 → pool2 → pool3 ─────────────────────────────────────
    all_candidates = pool1 + pool2 + pool3
    pool1_set = set(pool1)
    pool2_set = set(pool2)

    results: dict[int, dict] = {}
    p1_ok = p2_ok = p3_ok = 0
    consecutive_failures = 0
    _CIRCUIT_BREAKER_THRESHOLD = 5  # bail if 5 clusters fail in a row (API down)
    attempted_pool1: set[int] = set()  # track which pool-1 indices were actually tried

    for idx in all_candidates:
        if consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
            print(f"  [warn] Circuit breaker triggered after {consecutive_failures} consecutive failures — Gemini overloaded, aborting batch")
            break
        if idx in pool1_set:
            attempted_pool1.add(idx)
        articles = clusters[idx].get("articles", [])
        cc = cluster_consensus.get(str(idx)) if cluster_consensus else None
        result = summarize_cluster(articles, claims_consensus=cc,
                                   prefer_provider=prefer_provider,
                                   cluster_title=clusters[idx].get("title"))
        if result:
            results[idx] = result
            consecutive_failures = 0  # reset on success
            if idx in pool1_set:
                p1_ok += 1
            elif idx in pool2_set:
                p2_ok += 1
            else:
                p3_ok += 1
        else:
            consecutive_failures += 1

    total_ok = p1_ok + p2_ok + p3_ok
    total_att = len(all_candidates)
    print(f"  Gemini: {total_ok}/{total_att} clusters summarized "
          f"({p1_ok} top-30 / {p2_ok} regional / {p3_ok} topic)")
    if total_ok < total_att:
        print(f"  {total_att - total_ok} failed (pool-1 failures will have summaries cleared)")

    # Per-run aggregate quality instrumentation
    if results:
        headline_lens = [len(r["headline"].split()) for r in results.values()]
        summary_lens = [len(r["summary"].split()) for r in results.values()]
        avg_h = sum(headline_lens) / len(headline_lens)
        avg_s = sum(summary_lens) / len(summary_lens)
        out_of_range_h = sum(1 for wc in headline_lens if not (8 <= wc <= 12))
        out_of_range_s = sum(1 for wc in summary_lens if not (200 <= wc <= 400))
        print(f"  Headline avg {avg_h:.1f} words, "
              f"{out_of_range_h}/{len(headline_lens)} out of 8-12 range")
        print(f"  Summary avg {avg_s:.1f} words, "
              f"{out_of_range_s}/{len(summary_lens)} out of 250-350 range")

    # Return only pool-1 indices that were attempted but failed — circuit-breaker
    # skipped indices are NOT cleared (their rule-based summaries stay as fallback).
    return results, attempted_pool1 - results.keys()


def _tier_for_label(label: str) -> str:
    """Map a provider label to the persisted summary_tier (migration 063)."""
    if label == "claude-sonnet":
        return "sonnet"
    if label == "gemini-flash":
        return "flash"          # premium gemini-2.5-flash
    return "flash-lite"          # gemini-2.5-flash-lite


def summarize_top50_after_rerank(supabase, edition: str = "world", limit: int = 50,
                                 prefer_provider: str | None = "gemini",
                                 flash_top_n: int = 10) -> dict:
    """
    Single-pass post-rerank summarization for the final feed top N.

    Reads the top-N clusters by rank_{edition} from Supabase (rank DESC),
    fetches their article membership, and summarizes via a Gemini quality
    hierarchy: the top `flash_top_n` highest-impact stories run on
    gemini-2.5-flash (premium); the rest on gemini-2.5-flash-lite. There is no
    Groq fallback (retired 2026-06-24); premium slots degrade flash → flash-lite.

    Cache logic (upgrade-aware, migration 063):
        - flash-lite slot: hash matches AND prior tier in
          ('sonnet','flash','flash-lite') → skip (no API call).
        - flash (premium) slot: hash matches AND prior tier in ('sonnet','flash')
          → skip; a 'flash-lite' prior is a miss so the story is UPGRADED to
          flash when it enters the top `flash_top_n`.
        - else → call LLM, write summary + consensus + divergence + hash + tier.

    Op-eds (content_type=opinion) and clusters with <3 articles are skipped —
    both preserve original voice or lack the source diversity for synthesis.

    Returns metrics dict:
        {summarized: int, cached: int, skipped: int, failed: int,
         updated_ids: list[str], updated_summaries: dict[str, dict]}
    """
    rank_col = f"rank_{edition.replace('-', '_')}"

    metrics = {
        "summarized": 0,
        "cached": 0,
        "skipped": 0,
        "failed": 0,
        "updated_ids": [],
        "updated_summaries": {},
    }

    # Over-fetch beyond `limit`: the homepage displays the top `limit` clusters
    # AFTER filtering source_count >= 3 (HomeContent fetches 100, filters, then
    # slices 50), so thin rows in the raw DB top-50 must not consume window
    # slots or the last displayed cards fall outside the summarized set.
    fetch_limit = limit + 20
    try:
        rank_res = (
            supabase.table("story_clusters")
            .select("id, content_type, source_count, summary_article_hash, summary_tier")
            .contains("sections", [edition])
            .order(rank_col, desc=True)
            .limit(fetch_limit)
            .execute()
        )
    except Exception as e:
        print(f"  [warn] summarize_top50_after_rerank: top-{limit} fetch failed: {e}")
        return metrics

    rows = rank_res.data or []
    if not rows:
        return metrics

    cluster_ids = [r["id"] for r in rows]
    try:
        link_res = (
            supabase.table("cluster_articles")
            .select("cluster_id, article_id")
            .in_("cluster_id", cluster_ids)
            .execute()
        )
    except Exception as e:
        print(f"  [warn] summarize_top50_after_rerank: cluster_articles fetch failed: {e}")
        return metrics

    by_cluster: dict[str, list[str]] = {}
    for link in (link_res.data or []):
        by_cluster.setdefault(link["cluster_id"], []).append(link["article_id"])

    all_article_ids = sorted({aid for ids in by_cluster.values() for aid in ids})
    articles_by_id: dict[str, dict] = {}
    for i in range(0, len(all_article_ids), 200):
        batch = all_article_ids[i:i + 200]
        try:
            art_res = (
                supabase.table("articles")
                .select("id, title, summary, full_text, source_id, published_at, url")
                .in_("id", batch)
                .execute()
            )
            for art in (art_res.data or []):
                articles_by_id[art["id"]] = art
        except Exception as e:
            # A transient failure on one batch must not abort the whole pass:
            # per-cluster <3-article guards below handle the missing members.
            print(f"  [warn] summarize_top50_after_rerank: articles batch fetch failed: {e}")
            continue

    # Backfill source_name + tier onto article dicts (mirrors main.py's 36h
    # lookback enrichment). Without this the prompt degrades to "mixed
    # sources" / generic "Source N" labels, the divergence task cannot name
    # outlets, and the outlet-leak detector goes blind — precisely on the
    # premium flash summaries users see.
    src_ids = sorted({a.get("source_id") for a in articles_by_id.values() if a.get("source_id")})
    src_info_by_id: dict[str, dict] = {}
    for i in range(0, len(src_ids), 200):
        batch = src_ids[i:i + 200]
        try:
            src_res = (
                supabase.table("sources")
                .select("id, name, tier")
                .in_("id", batch)
                .execute()
            )
            for s in (src_res.data or []):
                src_info_by_id[s["id"]] = s
        except Exception as e:
            print(f"  [warn] summarize_top50_after_rerank: sources batch fetch failed: {e}")
            continue
    for art in articles_by_id.values():
        src = src_info_by_id.get(art.get("source_id") or "", {})
        art.setdefault("source_name", src.get("name", ""))
        art.setdefault("tier", src.get("tier", ""))

    # `rows` is ordered by rank_{edition} DESC. Window accounting mirrors the
    # homepage: only rows with source_count >= 3 occupy display slots, and we
    # stop once `limit` displayed slots are covered. The premium flash band is
    # the first `flash_top_n` SUMMARIZABLE stories (op-eds / thin clusters do
    # not consume a flash slot; the band extends past them).
    window_used = 0
    premium_used = 0
    for row in rows:
        if window_used >= limit:
            break
        cid = row["id"]
        if (row.get("source_count") or 0) < 3:
            # Filtered out by the frontend — not displayed, no window slot.
            metrics["skipped"] += 1
            continue
        window_used += 1
        article_ids = by_cluster.get(cid, [])
        if len(article_ids) < 3:
            metrics["skipped"] += 1
            continue
        if (row.get("content_type") or "").lower() == "opinion":
            metrics["skipped"] += 1
            continue

        articles = [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]
        if len(articles) < 3:
            metrics["skipped"] += 1
            continue

        is_premium = premium_used < flash_top_n
        premium_used += 1 if is_premium else 0
        target_model = GEMINI_FLASH_MODEL if is_premium else None

        h = _content_hash(articles)
        # Skip re-summarization when the cluster's article membership is
        # unchanged AND a prior summary already meets this slot's quality tier.
        # A flash-lite target accepts any prior tier. A premium (flash) target
        # rejects a 'flash-lite' cache row so a story rising into the top 5 is
        # UPGRADED to flash; it accepts 'flash'/'sonnet' (already >= flash).
        # (The old gate required tier=='sonnet', which never hit after Claude
        # retired and forced a full re-summarize of all ~50 clusters/run.)
        cacheable_tiers = ("sonnet", "flash") if is_premium else ("sonnet", "flash", "flash-lite")
        if h == row.get("summary_article_hash") and row.get("summary_tier") in cacheable_tiers:
            metrics["cached"] += 1
            continue

        result = summarize_cluster(articles, prefer_provider=prefer_provider,
                                   model=target_model,
                                   cluster_title=row.get("title"))
        if not result:
            metrics["failed"] += 1
            continue

        update_payload = {
            "title": result["headline"],
            "summary": result["summary"],
            "summary_article_hash": h,
            # Stamp the tier that ACTUALLY answered (migration 063): 'flash' for
            # gemini-2.5-flash, 'flash-lite' for flash-lite. A premium slot
            # that fell back to flash-lite (flash exhausted) is stamped
            # 'flash-lite', so the next run retries the flash upgrade.
            "summary_tier": _tier_for_label(result.get("_generator") or ""),
        }
        if result.get("consensus"):
            update_payload["consensus_points"] = result["consensus"]
        if result.get("divergence"):
            update_payload["divergence_points"] = result["divergence"]
        if result.get("editorial_importance") is not None:
            update_payload["editorial_importance"] = result["editorial_importance"]
        if result.get("story_type") is not None:
            update_payload["story_type"] = result["story_type"]
        if result.get("has_binding_consequences") is not None:
            update_payload["has_binding_consequences"] = result["has_binding_consequences"]

        try:
            supabase.table("story_clusters").update(update_payload).eq("id", cid).execute()
            metrics["summarized"] += 1
            metrics["updated_ids"].append(cid)
            metrics["updated_summaries"][cid] = result
        except Exception as e:
            print(f"  [warn] summarize_top50_after_rerank: DB update failed for {cid}: {e}")
            metrics["failed"] += 1

    return metrics


# ---------------------------------------------------------------------------
# Safety net — no DISPLAYED top-50 card left at summary_tier=None (2026-08-04)
# ---------------------------------------------------------------------------
# The 08-04 run left ~22 top-50 cards at tier=None because a flaky-connection
# window dropped the 8d Gemini calls ("Server disconnected"). A tier=None card
# renders its raw scraped member excerpt (outlet slugs, bylines, mid-sentence
# truncation, sometimes off-topic to the headline). Even with the transport
# retry now in gemini_client, a fully-doomed window (or the per-run cap) can
# still leave a card null. This pass runs AFTER 8d as a floor: for each
# displayed top-50 cluster still at tier=None it (i) makes ONE more Gemini
# attempt, and failing that (ii) rebuilds a clean, on-topic, sentence-bounded
# summary from the member articles via the deterministic text hygiene path so
# the card NEVER shows a raw excerpt.

# A sanitized rule-based summary is honestly stamped 'rule_based' when the DB
# CHECK allows it (migration proposed separately). Until then the update
# gracefully degrades to text-only (tier stays NULL, which is the CORRECT cache
# state — the row is re-attempted on the LLM next run). Detected once so we do
# not spam the log with constraint violations.
_RULE_BASED_TIER_SUPPORTED = True


def _floor_needs_summary(summary, tier, raw_check) -> bool:
    """Decision predicate for the top-50 summary floor.

    A displayed card needs a (re)generated summary when it has NO usable summary
    at all OR its stored summary is a raw scraped excerpt the frontend hygiene
    guard would BLANK — EVEN IF an earlier step (7b/8d) already stamped a
    summary_tier on it (the prod bug: a tier'd card holding a raw excerpt slipped
    past the old tier-only test and rendered blank). Returns False only for a card
    that already carries a real, display-safe summary. `raw_check` is the
    is_raw_excerpt guard (injected so the predicate stays import-light + testable).
    """
    summary = (summary or "").strip()
    tier = (tier or "").strip()
    return not (tier and summary and not raw_check(summary))


def ensure_top50_summary_floor(supabase, edition: str = "world", limit: int = 50,
                               prefer_provider: str | None = "gemini",
                               title_only: bool = False) -> dict:
    """Guarantee no DISPLAYED top-50 card is left showing a raw scraped excerpt.

    Run this AFTER the final feed ordering (step 8d.5) so it covers every card
    the final ordering promoted into the displayed top-50. It is idempotent —
    it no-ops on any card that already carries a summary_tier.

    RULE-BASED-FIRST, two passes over the displayed top-`limit` (by rank_{edition},
    applying the same source_count>=3 window as the homepage), skipping op-eds and
    cards that already carry a summary_tier:

      Pass 1 (fast, NO LLM): for EVERY still-null card, immediately write a clean,
        on-topic rule-based summary from the member articles (clustering's
        _generate_cluster_summary, which selects an on-topic member and runs the
        CMS/byline/dateline/truncation sanitizer) + a normalized headline, stamped
        tier='rule_based' (migration 071). When no usable article text exists it
        falls back to the normalized headline itself, so the card NEVER renders a
        raw excerpt. This pass completes in seconds and guarantees non-null
        coverage for the whole top-50 BEFORE any slow work — so the "100%
        coverage" guarantee no longer depends on the run finishing inside its
        wall-clock budget (a mid-pass-2 watchdog kill leaves every card with its
        clean pass-1 summary). still_null is structurally impossible whenever the
        cluster has a title.

      Pass 2 (upgrade, budget-permitting): re-visit the now-rule_based cards in
        rank order and, while is_available() and calls_remaining() allow, make ONE
        Gemini attempt each. On success overwrite the pass-1 text with the LLM
        summary + real tier + content-hash (so the next run's cache can hit). The
        pass stops the moment the per-run cap / budget is spent; a kill here is
        harmless because pass 1 already covered every card.

    title_only=True is a LIGHTWEIGHT pre-ordering pass: it only normalizes the
    headlines of the still-null displayed cards (no article fetch, no LLM) so
    step 8d.5's near-duplicate guard + story-type gates judge cleaned titles.
    The full summary-coverage guarantee runs AFTER 8d.5 with title_only=False.

    A card is treated as needing a summary when it has NO usable summary at all
    OR its stored summary is a raw scraped excerpt the frontend hygiene guard
    (summaryHygiene.ts) would blank — EVEN IF an earlier step already stamped a
    summary_tier on it. This is the fix for the prod bug where a tier'd card
    holding a raw excerpt slipped past the old tier-only test and rendered blank.
    Every write is post-checked with is_raw_excerpt so the INVARIANT holds: after
    this pass, no displayed card's stored summary satisfies is_raw_excerpt.

    Returns {checked, resummarized, sanitized, still_null, titles_cleaned,
    raw_excerpts_replaced}.
    """
    global _RULE_BASED_TIER_SUPPORTED
    rank_col = f"rank_{edition.replace('-', '_')}"
    metrics = {"checked": 0, "resummarized": 0, "sanitized": 0,
               "still_null": 0, "titles_cleaned": 0, "raw_excerpts_replaced": 0}

    # Lazy imports: heavy clustering/text deps are already loaded during a real
    # pipeline run; importing here keeps this module import-light for callers
    # that only need the summarize path.
    try:
        from utils.text_sanitizer import normalize_headline, sanitize_summary
    except ImportError:
        def normalize_headline(t):  # type: ignore
            return t or ""

        def sanitize_summary(t):  # type: ignore
            return t or ""
    # Canonical raw-excerpt guard (single source of truth, mirrors the frontend
    # summaryHygiene.ts the client blanks cards with). Fall back to no-op guards
    # only if the module can't import (keeps this path import-light offline).
    try:
        from utils.summary_hygiene import (
            is_raw_excerpt as _is_raw_excerpt,
            clean_feed_summary as _clean_feed_summary,
        )
    except ImportError:
        def _is_raw_excerpt(t):  # type: ignore
            return False

        def _clean_feed_summary(t, _title=None):  # type: ignore
            return t or ""
    try:
        from clustering.story_cluster import _generate_cluster_summary
    except ImportError:
        _generate_cluster_summary = None  # type: ignore

    fetch_limit = limit + 20
    try:
        rank_res = (
            supabase.table("story_clusters")
            .select("id, content_type, source_count, summary, title, summary_tier")
            .contains("sections", [edition])
            .order(rank_col, desc=True)
            .limit(fetch_limit)
            .execute()
        )
    except Exception as e:
        print(f"  [warn] ensure_top50_summary_floor: top-{limit} fetch failed: {e}")
        return metrics

    rows = rank_res.data or []
    if not rows:
        return metrics

    # Window accounting mirrors summarize_top50_after_rerank / the homepage:
    # only source_count>=3 rows occupy display slots; stop once `limit` covered.
    window_used = 0
    null_rows: list[dict] = []
    for row in rows:
        if window_used >= limit:
            break
        if (row.get("source_count") or 0) < 3:
            continue
        window_used += 1
        if (row.get("content_type") or "").lower() == "opinion":
            continue  # op-eds preserve original text by design — not a defect
        if not _floor_needs_summary(row.get("summary"), row.get("summary_tier"),
                                    _is_raw_excerpt):
            continue  # already has a clean, usable summary
        null_rows.append(row)

    if not null_rows:
        return metrics
    metrics["checked"] = len(null_rows)

    # Lightweight pre-ordering pass: just normalize the headlines of the
    # still-null displayed cards so step 8d.5's near-dup guard / story-type
    # gates judge cleaned titles. No article fetch, no LLM — the full
    # summary-coverage floor runs AFTER 8d.5 (title_only=False).
    if title_only:
        for row in null_rows:
            cid = row["id"]
            title = (row.get("title") or "").strip()
            clean = (normalize_headline(title) or title).strip()
            if clean and clean != title:
                try:
                    supabase.table("story_clusters").update(
                        {"title": clean[:500]}
                    ).eq("id", cid).execute()
                    metrics["titles_cleaned"] += 1
                except Exception as e:
                    print(f"  [warn] ensure_top50_summary_floor(title_only): "
                          f"title write failed for {cid}: {e}")
        return metrics

    # Fetch article membership for the null clusters only.
    null_ids = [r["id"] for r in null_rows]
    by_cluster: dict[str, list[str]] = {}
    try:
        link_res = (
            supabase.table("cluster_articles")
            .select("cluster_id, article_id")
            .in_("cluster_id", null_ids)
            .execute()
        )
        for link in (link_res.data or []):
            by_cluster.setdefault(link["cluster_id"], []).append(link["article_id"])
    except Exception as e:
        print(f"  [warn] ensure_top50_summary_floor: cluster_articles fetch failed: {e}")

    all_article_ids = sorted({aid for ids in by_cluster.values() for aid in ids})
    articles_by_id: dict[str, dict] = {}
    for i in range(0, len(all_article_ids), 200):
        batch = all_article_ids[i:i + 200]
        try:
            art_res = (
                supabase.table("articles")
                .select("id, title, summary, full_text, source_id, published_at, url")
                .in_("id", batch)
                .execute()
            )
            for art in (art_res.data or []):
                articles_by_id[art["id"]] = art
        except Exception as e:
            print(f"  [warn] ensure_top50_summary_floor: articles batch fetch failed: {e}")
            continue

    # Backfill source_name + tier so a re-summarize gets proper attribution.
    src_ids = sorted({a.get("source_id") for a in articles_by_id.values() if a.get("source_id")})
    src_info_by_id: dict[str, dict] = {}
    for i in range(0, len(src_ids), 200):
        batch = src_ids[i:i + 200]
        try:
            src_res = (
                supabase.table("sources").select("id, name, tier").in_("id", batch).execute()
            )
            for s in (src_res.data or []):
                src_info_by_id[s["id"]] = s
        except Exception:
            continue
    for art in articles_by_id.values():
        src = src_info_by_id.get(art.get("source_id") or "", {})
        art.setdefault("source_name", src.get("name", ""))
        art.setdefault("tier", src.get("tier", ""))

    # =====================================================================
    # PASS 1 (fast, NO LLM): guarantee non-null coverage for the WHOLE
    # displayed top-50 in seconds. For every still-null card write a clean,
    # on-topic rule-based summary + normalized headline (tier='rule_based',
    # migration 071). This runs to completion long before any watchdog kill,
    # so the coverage guarantee no longer depends on the run finishing inside
    # its wall-clock budget. Cards written here with >=3 articles are queued
    # for the LLM upgrade in pass 2.
    # =====================================================================
    # (cid -> cleaned title) for pass-2 prompts; only cards eligible for the
    # LLM upgrade (rule_based text landed, >=3 articles) are queued.
    upgrade_queue: list[str] = []
    cleaned_title_by_id: dict[str, str] = {}
    for row in null_rows:
        cid = row["id"]
        title = row.get("title", "") or ""
        article_ids = by_cluster.get(cid, [])
        articles = [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]

        prior_summary = (row.get("summary") or "").strip()
        prior_was_raw = bool(prior_summary) and _is_raw_excerpt(prior_summary)

        clean_title = (normalize_headline(title) or title).strip()
        cleaned_title_by_id[cid] = clean_title or title
        if _generate_cluster_summary is not None and articles:
            clean_summary = _generate_cluster_summary(articles, clean_title or title)
        else:
            clean_summary = sanitize_summary(row.get("summary", "") or "")
        clean_summary = (clean_summary or "").strip()

        # POST-CHECK: the (re)generated text must not ITSELF be a raw excerpt the
        # frontend would blank (a broken member excerpt can survive the rule-based
        # picker). clean_feed_summary returns "" when the text still looks raw.
        if clean_summary and _is_raw_excerpt(clean_summary):
            clean_summary = _clean_feed_summary(clean_summary).strip()
        if not clean_summary:
            # No usable / non-raw article text. Fall back to the normalized
            # headline as a clean, on-topic line. still_null is thus impossible
            # whenever the cluster has a title that is not itself raw.
            clean_summary = (clean_title or title or "").strip()
            if clean_summary and _is_raw_excerpt(clean_summary):
                clean_summary = _clean_feed_summary(clean_summary).strip()
        if not clean_summary or _is_raw_excerpt(clean_summary):
            # Truly nothing clean to work with (no articles, and the title is
            # empty or itself a raw signature) — degenerate row. Never write a
            # raw summary: leave it for the frontend guard to blank to the neutral
            # pending line and count it. The invariant (no displayed card's stored
            # summary satisfies is_raw_excerpt) holds because we did NOT write.
            metrics["still_null"] += 1
            continue

        text_payload = {"summary": clean_summary}
        if clean_title:
            text_payload["title"] = clean_title[:500]

        wrote = False
        if _RULE_BASED_TIER_SUPPORTED:
            try:
                supabase.table("story_clusters").update(
                    {**text_payload, "summary_tier": "rule_based"}
                ).eq("id", cid).execute()
                wrote = True
            except Exception as e:
                # Most likely the summary_tier CHECK does not yet include
                # 'rule_based' (migration proposed separately). Degrade to a
                # text-only write and stop attempting the tier this run.
                _RULE_BASED_TIER_SUPPORTED = False
                print(f"  [info] ensure_top50_summary_floor: 'rule_based' tier not "
                      f"accepted ({e}); writing cleaned text without a tier stamp")
        if not wrote:
            try:
                supabase.table("story_clusters").update(text_payload).eq("id", cid).execute()
            except Exception as e:
                print(f"  [warn] ensure_top50_summary_floor: sanitize write failed for {cid}: {e}")
                metrics["still_null"] += 1
                continue

        metrics["sanitized"] += 1
        if prior_was_raw:
            # This card previously carried a summary_tier AND a raw scraped
            # excerpt (the prod bug) — the frontend would have blanked it. It now
            # holds clean text. Count the repair distinctly from plain null fills.
            metrics["raw_excerpts_replaced"] += 1
        if _RULE_BASED_TIER_SUPPORTED:
            # Clean rule_based text landed. Eligible for the LLM upgrade in
            # pass 2 iff it has enough sources to summarize.
            if len(articles) >= 3:
                upgrade_queue.append(cid)
        else:
            # Text is clean but the tier stamp could not be written → still
            # NULL (frontend still renders the clean text, not a raw excerpt;
            # the row is re-attempted on the LLM next run).
            metrics["still_null"] += 1

    # =====================================================================
    # PASS 2 (upgrade, budget-permitting): every card now carries a clean
    # pass-1 rule_based summary, so a watchdog kill here is harmless. Re-visit
    # the queued cards in rank order and, while Gemini is available and the
    # per-run cap has headroom, make ONE re-summarize attempt each. On success
    # overwrite the rule_based text with the LLM summary + real tier +
    # content-hash (so the next run's cache can hit). Stops the moment the
    # budget is spent — the remaining cards keep their clean pass-1 summary.
    # =====================================================================
    for cid in upgrade_queue:
        if not is_available() or calls_remaining() <= 0:
            break  # budget spent — remaining cards keep their pass-1 summary
        article_ids = by_cluster.get(cid, [])
        articles = [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]
        if len(articles) < 3:
            continue
        result = summarize_cluster(
            articles, prefer_provider=prefer_provider, model=None,
            cluster_title=cleaned_title_by_id.get(cid, ""))
        if not result:
            continue  # keep the pass-1 rule_based summary
        payload = {
            "title": result["headline"],
            "summary": result["summary"],
            "summary_article_hash": _content_hash(articles),
            "summary_tier": _tier_for_label(result.get("_generator") or ""),
        }
        if result.get("consensus"):
            payload["consensus_points"] = result["consensus"]
        if result.get("divergence"):
            payload["divergence_points"] = result["divergence"]
        if result.get("editorial_importance") is not None:
            payload["editorial_importance"] = result["editorial_importance"]
        if result.get("story_type") is not None:
            payload["story_type"] = result["story_type"]
        if result.get("has_binding_consequences") is not None:
            payload["has_binding_consequences"] = result["has_binding_consequences"]
        try:
            supabase.table("story_clusters").update(payload).eq("id", cid).execute()
            # Card was counted as `sanitized` (rule_based) in pass 1; it is now
            # an LLM summary. Reclassify so checked == resummarized + sanitized
            # + still_null stays exact.
            metrics["resummarized"] += 1
            metrics["sanitized"] -= 1
        except Exception as e:
            print(f"  [warn] ensure_top50_summary_floor: upgrade write failed for {cid}: {e}")
            # Keep the clean pass-1 summary; it stays counted as `sanitized`.

    return metrics


# ---------------------------------------------------------------------------
# Flash-tier reconciliation — premium tier must follow the FINAL rank (2026-08-05)
# ---------------------------------------------------------------------------
# Step 8d summarizes the top-50 and assigns the premium 'flash' tier to the
# INTERMEDIATE top-10 (the rank_world order BEFORE the final 8d.5 ordering pass).
# 8d.5 then rewrites rank_world with fresh story_type/ei/title signals and can
# promote a 'flash-lite' card into the final top-10. This pass, run AFTER 8d.5,
# upgrades any final top-`top_n` displayed, summarizable card still at
# 'flash-lite' to 'flash' so the premium tier follows the FINAL rank. It is
# budget-safe: it only fires while Gemini is available and the per-run cap has
# headroom, caps the number of upgrades, and degrades gracefully (never raises).

def reconcile_flash_top10(supabase, edition: str = "world", top_n: int = 10,
                          prefer_provider: str | None = "gemini",
                          max_upgrades: int = 5) -> dict:
    """Upgrade the FINAL top-`top_n` displayed cards from flash-lite → flash.

    Runs after step 8d.5 (final feed ordering). For each of the final top-`top_n`
    DISPLAYED (source_count>=3), non-op-ed, summarizable clusters whose cached
    summary_tier is not already 'flash'/'sonnet', re-summarize on gemini-2.5-flash
    and write the result + tier='flash' — but only while flash actually answers
    (if the flash daily cap is spent the call degrades to flash-lite; that is NOT
    written, so no equivalent-quality churn and the row is retried next run).

    Budget-safe: no-ops when Gemini is unavailable or the per-run cap is spent,
    caps upgrades at `max_upgrades`, and never raises.

    Returns {checked, upgraded, skipped, failed}.
    """
    metrics = {"checked": 0, "upgraded": 0, "skipped": 0, "failed": 0}
    if not is_available() or calls_remaining() <= 0:
        return metrics

    rank_col = f"rank_{edition.replace('-', '_')}"
    fetch_limit = top_n + 20
    try:
        rank_res = (
            supabase.table("story_clusters")
            .select("id, content_type, source_count, summary_tier")
            .contains("sections", [edition])
            .order(rank_col, desc=True)
            .limit(fetch_limit)
            .execute()
        )
    except Exception as e:
        print(f"  [warn] reconcile_flash_top10: top-{top_n} fetch failed: {e}")
        return metrics

    rows = rank_res.data or []
    if not rows:
        return metrics

    # Window the displayed premium band exactly like the homepage / 8d: only
    # source_count>=3 rows occupy display slots; op-eds keep original voice and
    # do not consume a flash slot (the band extends past them).
    window_used = 0
    candidates: list[dict] = []
    for row in rows:
        if window_used >= top_n:
            break
        if (row.get("source_count") or 0) < 3:
            continue
        window_used += 1
        if (row.get("content_type") or "").lower() == "opinion":
            continue
        if (row.get("summary_tier") or "") in ("flash", "sonnet"):
            continue  # already premium — nothing to upgrade
        candidates.append(row)

    metrics["checked"] = len(candidates)
    if not candidates:
        return metrics

    # Fetch article membership for the upgrade candidates only.
    cand_ids = [r["id"] for r in candidates]
    by_cluster: dict[str, list[str]] = {}
    try:
        link_res = (
            supabase.table("cluster_articles")
            .select("cluster_id, article_id")
            .in_("cluster_id", cand_ids)
            .execute()
        )
        for link in (link_res.data or []):
            by_cluster.setdefault(link["cluster_id"], []).append(link["article_id"])
    except Exception as e:
        print(f"  [warn] reconcile_flash_top10: cluster_articles fetch failed: {e}")
        return metrics

    all_article_ids = sorted({aid for ids in by_cluster.values() for aid in ids})
    articles_by_id: dict[str, dict] = {}
    for i in range(0, len(all_article_ids), 200):
        batch = all_article_ids[i:i + 200]
        try:
            art_res = (
                supabase.table("articles")
                .select("id, title, summary, full_text, source_id, published_at, url")
                .in_("id", batch)
                .execute()
            )
            for art in (art_res.data or []):
                articles_by_id[art["id"]] = art
        except Exception as e:
            print(f"  [warn] reconcile_flash_top10: articles batch fetch failed: {e}")
            continue

    # Backfill source_name + tier so the flash prompt gets proper attribution.
    src_ids = sorted({a.get("source_id") for a in articles_by_id.values() if a.get("source_id")})
    src_info_by_id: dict[str, dict] = {}
    for i in range(0, len(src_ids), 200):
        batch = src_ids[i:i + 200]
        try:
            src_res = (
                supabase.table("sources").select("id, name, tier").in_("id", batch).execute()
            )
            for s in (src_res.data or []):
                src_info_by_id[s["id"]] = s
        except Exception:
            continue
    for art in articles_by_id.values():
        src = src_info_by_id.get(art.get("source_id") or "", {})
        art.setdefault("source_name", src.get("name", ""))
        art.setdefault("tier", src.get("tier", ""))

    for row in candidates:
        # Stop cleanly if the budget is spent or Gemini went unavailable mid-pass
        # (e.g. a flash 429 disabled the client), or we hit the upgrade cap.
        if (metrics["upgraded"] >= max_upgrades
                or calls_remaining() <= 0 or not is_available()):
            metrics["skipped"] += 1
            continue

        cid = row["id"]
        article_ids = by_cluster.get(cid, [])
        articles = [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]
        if len(articles) < 3:
            metrics["skipped"] += 1
            continue

        result = summarize_cluster(
            articles, prefer_provider=prefer_provider, model=GEMINI_FLASH_MODEL,
            cluster_title=row.get("title"))
        if not result:
            metrics["failed"] += 1
            continue

        tier = _tier_for_label(result.get("_generator") or "")
        if tier not in ("flash", "sonnet"):
            # flash's daily cap is spent; the call degraded to flash-lite. Don't
            # overwrite the existing (equivalent) flash-lite summary — the row is
            # re-attempted for the flash upgrade next run.
            metrics["skipped"] += 1
            continue

        payload = {
            "title": result["headline"],
            "summary": result["summary"],
            "summary_article_hash": _content_hash(articles),
            "summary_tier": tier,
        }
        if result.get("consensus"):
            payload["consensus_points"] = result["consensus"]
        if result.get("divergence"):
            payload["divergence_points"] = result["divergence"]
        if result.get("editorial_importance") is not None:
            payload["editorial_importance"] = result["editorial_importance"]
        if result.get("story_type") is not None:
            payload["story_type"] = result["story_type"]
        if result.get("has_binding_consequences") is not None:
            payload["has_binding_consequences"] = result["has_binding_consequences"]
        try:
            supabase.table("story_clusters").update(payload).eq("id", cid).execute()
            metrics["upgraded"] += 1
        except Exception as e:
            print(f"  [warn] reconcile_flash_top10: write failed for {cid}: {e}")
            metrics["failed"] += 1

    return metrics
