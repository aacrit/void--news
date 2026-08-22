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
                          temperature: float = 0.0,
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

    temperature defaults to 0.0 here (the summary path): summaries are grounded
    extraction, not creative writing, so greedy decoding removes sampling-induced
    invention and makes output reproducible for the content-hash cache. The daily
    brief path calls gemini_client.generate_json directly and keeps its 0.2.
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
                model=m, temperature=temperature,
            )
            if result and isinstance(result, dict):
                label = "gemini-flash" if m == GEMINI_FLASH_MODEL else "gemini-flash-lite"
                return result, label
    return None, "none"


# Summarizer length policy. Restored 2026-08-11: the 2026-08-10 hygiene commit
# had shrunk summaries from the original 250-350 word standard to a 90-word cap;
# this restores a 200-300 word full-brief target. _SUMMARY_PROMPT_VERSION is
# folded into the content hash so a policy change regenerates every summary
# instead of serving one written under the old (short) policy.
_MAX_SUMMARY_ARTICLES = 25
_SUMMARY_PROMPT_VERSION = "2026-08-11-longform"

# Below this many usable articles a cluster is "thin": the prompt's length band
# relaxes to a 100-word floor so the model is never pressured to invent facts
# to reach the full 200-300-word brief (CEO 2026-08-11).
_THIN_CLUSTER_ARTICLES = 5


def _article_sort_key(a: dict) -> tuple:
    """Newest-first sort key shared by selection, hash, and prompt block:
    (published_at, id) with id as the deterministic tiebreak."""
    return (a.get("published_at") or "", str(a.get("id") or a.get("article_id") or ""))


def _lean_bucket_of(art: dict) -> str:
    """Left/center/right bucket from the article's source lean baseline label
    (7-point strings like 'far-left', 'center-left', 'center', 'right').
    Missing/unknown labels bucket as center — never a hard failure."""
    label = str(art.get("source_lean_baseline") or "").strip().lower()
    if "left" in label:
        return "left"
    if "right" in label:
        return "right"
    return "center"


def _tier_weight(art: dict) -> int:
    """Outlet-reputation weight for selection: wires/majors first."""
    t = (art.get("tier") or "").strip().lower().replace("-", "_")
    return {"us_major": 2, "international": 1, "independent": 0}.get(t, 0)


def _select_articles_for_summary(articles: list[dict],
                                 max_articles: int = _MAX_SUMMARY_ARTICLES) -> list[dict]:
    """Pick the articles that feed the summary prompt (CEO spec 2026-08-11):
    when a cluster exceeds max_articles, select for SPREAD and REPUTATION,
    not just recency — bucket by source lean (left/center/right), round-robin
    across the buckets so all covered sides are represented, and rank within
    a bucket by outlet tier (us_major > international > independent) then
    recency. Clusters at or under the cap use ALL articles. The returned list
    is newest-first (the prompt opens on the freshest development), and the
    same selection feeds _content_hash so cache-key semantics track exactly
    what the model saw. Deterministic: stable sort keys, id tiebreaks."""
    arts = [a for a in articles if a]
    if len(arts) <= max_articles:
        return sorted(arts, key=_article_sort_key, reverse=True)
    buckets: dict[str, list[dict]] = {"left": [], "center": [], "right": []}
    for a in arts:
        buckets[_lean_bucket_of(a)].append(a)
    for b in buckets.values():
        b.sort(key=lambda a: (_tier_weight(a),) + _article_sort_key(a), reverse=True)
    picked: list[dict] = []
    idx = {k: 0 for k in buckets}
    while len(picked) < max_articles:
        progressed = False
        for k in ("left", "center", "right"):
            if len(picked) >= max_articles:
                break
            if idx[k] < len(buckets[k]):
                picked.append(buckets[k][idx[k]])
                idx[k] += 1
                progressed = True
        if not progressed:
            break
    return sorted(picked, key=_article_sort_key, reverse=True)


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
    # Hash the SAME stratified selection the prompt block uses (spread + tier +
    # recency, via _select_articles_for_summary) so the cache key always tracks
    # exactly what the model saw. IDs sorted for order-independence.
    selected = _select_articles_for_summary(articles)
    ids = sorted(str(a.get("id") or a.get("article_id") or "") for a in selected)
    # Include total membership count so going from 5→6 articles still
    # invalidates, plus the prompt-policy version so a length/format policy
    # change (the 2026-08-11 restore to 200-300 word briefs) regenerates every
    # summary rather than serving one written under the old policy.
    return hashlib.sha256(
        ("|".join(ids) + f"|n={len(articles)}|p={_SUMMARY_PROMPT_VERSION}").encode("utf-8")
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
establishes; never add facts from memory or prior knowledge. NEVER state a \
person's age, title, rank, or tenure unless that exact detail appears verbatim in \
the article text. Do not infer, estimate, or round an age. If an age or title is \
not written in the articles, leave it out.

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
- ATTRIBUTION (mandatory): Any claim about a named individual's conduct, \
character, statements, or beliefs that is contested, criminal, or reputationally \
damaging MUST carry in-text attribution to the reporting outlet or official \
source named in the provided articles (for example: "according to the New York \
Post", "prosecutors said"). Never state such a claim as fact in void --news's \
own voice. If the provided articles contain no such attribution for the claim, \
omit the claim entirely. This mandatory attribution is a deliberate exception to \
the outlet-naming limits above: for a reputationally damaging claim about a named \
person, naming the reporting outlet or official source is REQUIRED, not optional.
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

TASK 2 — summary (string, 200 to 300 words)
Write a comprehensive factual briefing of 200 to 300 words that reads like a \
complete news intelligence brief: structured as an inverted pyramid (most \
important first) and dense with concrete specifics. Every sentence must carry a \
new concrete fact: a name, a number, a date, a place, or an action. SHOW, DON'T \
TELL: juxtapose facts and let the reader see the pattern; never assert that \
something is significant. The house standard for density is this: "A lawyer who'd \
never been to India drew the border in five weeks. 15 million crossed it." Every \
sentence should carry that weight; length is never an excuse to pad. Give the \
reader, in order: the freshest development, what happened with its full scale \
(names, numbers, places), how it developed, the essential background, the sharpest \
points of contention between the principal actors, and what remains unresolved. A \
well-covered story earns the full 200 to 300 words; write what the coverage \
genuinely supports rather than padding, but never stop at a wire line when the \
reporting carries a full brief.

IMPORTANT: Articles are sorted newest-first and include publication timestamps. \
Open on the MOST RECENT development, the freshest reported fact: who, what, when, \
where. Older articles are context; use the background a reader genuinely needs to \
understand the development, and give it the space it warrants.

DOMINANT STORY ONLY: Summarize ONLY the single story about the entities named in \
the DOMINANT TOPIC / ENTITIES line above; ignore any article whose subject is a \
different event, person, or place than those entities. These articles were \
grouped automatically and one or two may concern a DIFFERENT event. Never stitch \
two unrelated stories into one briefing, and never reference a person, place, or \
event that does not belong to the dominant story.

ARRIVE LATE: start inside the action. Do not open with "In a move that...", \
"Following weeks of...", or "As tensions grew..." The first sentence should name a \
concrete action, actor, or figure. Then build out the context and the range of \
disagreement between the principal actors. Stop when the facts are stated, not \
before the story is told.

HARD RULES for the summary (a reader sees violations instantly):
- TARGET 200 to 300 words. Give a reader who came for depth the full picture: the \
development, its scale, the background, the range of stated positions, and what is \
still unresolved. Do not pad with filler, repetition, or restatement to reach the \
length; every sentence must add a new fact. A one or two sentence summary of a \
well-covered story is a failure. (350 words is a hard runaway ceiling, not a \
target.)
- NO TERMINAL RESTATEMENT. Never close on a sentence that repeats the opening in \
other words ("Firefighters continue to battle the fires day and night.", \
"Authorities are continuing their investigation.", "The campaign continues."). \
The last sentence must carry a fact the summary has not already stated. If you \
have nothing new to add, end on the previous sentence.
- SAY UNKNOWNS ONCE. If a fact is not yet established (a cause, a toll, a motive), \
state that a SINGLE time, or leave it out. Do not spend two or three consecutive \
sentences saying the investigation is ongoing or the cause is not yet known.
- NO REPETITION. State each fact, figure, name, and quote exactly once. Do not \
restate a claim in different words later in the summary (for example, do not say \
three times that a strait stays closed until conditions are met).
- NEVER state a person's age, title, rank, or tenure unless it appears VERBATIM in \
the article text above. Do not infer, estimate, or round an age. If the articles \
do not give the age, the summary does not give the age.
- WRITE AS AN INDEPENDENT CORRESPONDENT, in void --news's own voice. Name no news \
outlet, wire service, or aggregator. Do not write "sources report," "sources \
say," "according to reports," "multiple outlets," "as reported," or any tier \
label. State each fact directly and attribute statements only to the people and \
institutions who made them (a named official, agency, company, or court).
- Active voice, plain declarative sentences. Do not hedge with "reportedly," \
"apparently," or "seemingly" unless the fact is genuinely contested.

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
been reported. Choose this ONLY when articles primarily describe a reaction, a \
minor announcement, a procedural step, or a scheduled event within a larger \
continuing story. Examples: a spokesperson declining comment, a scheduled hearing \
date, a routine status update. Do NOT choose this for a DECISIVE one-time outcome \
that resolves a question, even when it caps a longer-running story: an election or \
referendum RESULT, a court VERDICT or sentencing, an extradition or arrest, a \
confirmed appointment or resignation, a major accident or disaster, or a signed \
agreement. Those ARE the event, not an update to it; classify them by their nature \
(policy_action, breaking_crisis, investigation, etc.).
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


# ---------------------------------------------------------------------------
# Phase-3 summary hygiene post-checks (deterministic, $0, conservative).
# Applied to the SAME summary text the frontend renders, on BOTH the LLM path
# (summarize_cluster) and the rule-based floor (ensure_top50_summary_floor).
# Each check is precision-first: it must never corrupt an already-clean summary.
#   3a  hard 90-word trim to a sentence boundary
#   3b  drop a terminal sentence that only restates the lead
#   3c  collapse consecutive "unknown / ongoing investigation" padding to one
#   3d  drop a sentence that near-duplicates an earlier claim (high Jaccard)
#   3e  drop an ungrounded age (not present verbatim in the source article text)
# ---------------------------------------------------------------------------

# House standard: summaries sit in a 55-to-90-word band. The cap is a HARD ceiling
# (enforced by the deterministic trim); the floor is a SOFT target (enforced by the
# prompt only — a post-check can never invent grounded facts to lengthen a summary,
# so under-length output is surfaced as a warning, not padded). Shared by the trim,
# _check_quality, and the batch instrumentation so the numbers live in one place.
_SUMMARY_WORD_CAP = 350  # runaway guard ONLY, not an editorial target: a model
                         # failure must never dump 1000 words into a card.
_SUMMARY_WORD_FLOOR = 150  # soft: a well-covered story should be a full brief,
                           # not a clipped wire line (restored 2026-08-11)

# Stopwords for the content-word comparisons in 3b/3d. Deliberately broad
# (articles, auxiliaries, prepositions, pronouns, continuation verbs) so that a
# "subset" / "near-duplicate" test keys on the SPECIFIC nouns, names, numbers,
# and verbs that carry a claim, not on grammatical scaffolding.
_POSTCHECK_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "for", "nor", "so", "yet",
    "of", "to", "in", "on", "at", "by", "with", "from", "into", "onto",
    "over", "under", "after", "before", "during", "amid", "amidst", "about",
    "as", "than", "then", "that", "this", "these", "those", "it", "its",
    "he", "she", "his", "her", "they", "them", "their", "we", "our", "us",
    "you", "your", "who", "whom", "whose", "which", "what", "when", "where",
    "why", "how", "is", "are", "was", "were", "be", "been", "being", "am",
    "has", "have", "had", "having", "do", "does", "did", "will", "would",
    "shall", "should", "can", "could", "may", "might", "must", "not", "no",
    "there", "here", "also", "still", "just", "only", "both", "each", "any",
    "some", "all", "more", "most", "such", "up", "out", "off", "down", "again",
    "continue", "continues", "continued", "continuing", "remain", "remains",
    "remained", "ongoing", "amp", "said", "says", "say", "told", "according",
})

# 3c: sentences that narrate an ABSENCE of information / an open process. A run
# of consecutive such sentences is padding; collapse it to the first one only.
_UNKNOWN_PADDING_RE = _re.compile(
    r"(?:"
    r"investigation[s]?\s+(?:is|are|remain|remains|continue|continues|ongoing)"
    r"|under\s+investigation"
    r"|(?:continue|continuing)\s+to\s+investigate"
    r"|(?:cause|motive|circumstances|toll|number|extent|reason|details?|"
    r"identit(?:y|ies)|origin)\b[^.?!]{0,60}?"
    r"(?:not\s+(?:yet\s+)?(?:been\s+)?(?:known|clear|confirmed|determined|"
    r"established|disclosed|released|identified|available)|"
    r"remain[s]?\s+(?:unknown|unclear|under)|unclear|unknown)"
    r"|(?:no|not)\s+(?:immediate\s+)?(?:cause|explanation|comment|word|"
    r"information|details?)\b[^.?!]{0,40}?"
    r"(?:known|available|given|provided|released|yet)"
    r"|authorities\s+(?:are\s+)?(?:still\s+)?(?:looking\s+into|investigating|"
    r"working\s+to\s+determine)"
    r"|it\s+(?:is|remains)\s+(?:not\s+(?:yet\s+)?clear|unclear|unknown)"
    r")",
    _re.IGNORECASE,
)

# 3e: age assertions. Group 1 (when present) is the numeric age.
_AGE_YEAR_OLD_RE = _re.compile(r"\b(\d{1,3})[- ]year[- ]old\b", _re.IGNORECASE)
_AGE_AGED_RE = _re.compile(r"\baged\s+(\d{1,3})\b", _re.IGNORECASE)
# "... is 80 ..." near a name — require it NOT be a measurement/unit to avoid
# false positives ("is 80 percent", "is 80 million").
_AGE_IS_RE = _re.compile(
    r"\bis\s+(\d{2})\b(?!\s*(?:percent|per\s?cent|%|million|billion|thousand|"
    r"hundred|point|points|degree|degrees|dollar|dollars|euro|euros|pound|"
    r"pounds|kilomet|mile|miles|metre|meter|feet|foot|inch|kg|km|years?))",
    _re.IGNORECASE,
)

# Grounding audit (3f, warning-only). Numeric tokens: integers, decimals,
# percentages, money, 4-digit years, with optional thousands separators and a
# leading $ / trailing %. Candidate proper nouns: runs of two or more
# capitalized words (a leading determiner is stripped before the check so
# "The Strait" tests as "Strait"). A word ends at any period, so a run can never
# span a sentence boundary ("Tuesday. Reyes" is two separate words, not a run).
_GROUNDING_NUMBER_RE = _re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")
_GROUNDING_PROPER_NOUN_RE = _re.compile(
    r"\b[A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+)+\b"
)
_GROUNDING_LEADING_DETERMINERS = {
    "the", "a", "an", "this", "that", "these", "those",
    "his", "her", "its", "their", "our", "your", "my",
}


def _flag_ungrounded_tokens(summary: str, source_text: str) -> list[str]:
    """Warning-only grounding audit. Generalizes _drop_ungrounded_ages from the
    person-age case to ALL figures and named entities. Returns a sorted list of
    tokens that appear in the summary but NOT in the concatenated source article
    text: numeric tokens (integers, decimals, percentages, money, 4-digit years)
    and candidate proper nouns (capitalized multi-word runs).

    Never mutates the summary — the hit rate is logged so we can measure the
    hallucination rate over a few runs before escalating to sentence drops.
    Conservative (a token counts as grounded whenever it appears anywhere in the
    source), matching the age check, so the warning under-reports rather than
    cries wolf. Deterministic."""
    if not summary or not summary.strip() or not source_text:
        return []
    src = source_text.lower()
    # Source digits with thousands separators removed so "1,200" grounds "1200".
    src_num = _re.sub(r"(?<=\d),(?=\d)", "", src)
    flagged: set[str] = set()

    # --- numeric tokens ---
    for m in _GROUNDING_NUMBER_RE.finditer(summary):
        raw = m.group(0).strip()
        digits = _re.sub(r"[^0-9]", "", raw)
        if not digits:
            continue
        # Grounded if the exact digit run (no adjacent digits) appears in source.
        if _re.search(r"(?<!\d)" + _re.escape(digits) + r"(?!\d)", src_num):
            continue
        flagged.add(raw)

    # --- candidate proper nouns (capitalized multi-word runs) ---
    for m in _GROUNDING_PROPER_NOUN_RE.finditer(summary):
        words = m.group(0).split()
        if words and words[0].lower() in _GROUNDING_LEADING_DETERMINERS:
            words = words[1:]
        if len(words) < 2:
            continue  # a determiner + single name is not a multi-word entity run
        phrase = " ".join(words)
        if phrase.lower() in src:
            continue
        flagged.add(phrase)

    return sorted(flagged)


def _split_sentences(text: str) -> list[str]:
    """Split into sentences on terminal punctuation. Shares the regex the
    existing dedupe uses so behavior is consistent across the module."""
    if not text or not text.strip():
        return []
    return [p.strip() for p in _re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]


def _content_words(sentence: str) -> set[str]:
    """Specific content tokens of a sentence: 3+ char alphanumerics (numbers
    kept, e.g. "102"), minus grammatical stopwords. Used for the subset (3b) and
    Jaccard (3d) comparisons so they key on names / numbers / actions."""
    return {
        w for w in _re.findall(r"[a-z0-9]{3,}", (sentence or "").lower())
        if w not in _POSTCHECK_STOPWORDS
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def _trim_summary_to_word_cap(summary: str, cap: int = _SUMMARY_WORD_CAP) -> str:
    """3a: hard-trim an over-length summary to the last complete sentence at or
    under `cap` words. No-op when already within cap. If even the first sentence
    exceeds the cap, hard-truncate that sentence to `cap` words and close it."""
    if not summary or not summary.strip():
        return summary
    words = summary.split()
    if len(words) <= cap:
        return summary
    parts = _split_sentences(summary)
    out: list[str] = []
    count = 0
    for p in parts:
        wc = len(p.split())
        if count + wc <= cap:
            out.append(p)
            count += wc
        else:
            break
    if out:
        return " ".join(out)
    # First sentence alone blows the cap: keep the first `cap` words, close it.
    trimmed = " ".join(parts[0].split()[:cap]).rstrip(",;:") if parts else ""
    if trimmed and trimmed[-1] not in ".!?":
        trimmed += "."
    return trimmed or summary


def _drop_terminal_restatement(summary: str) -> str:
    """3b: drop the FINAL sentence when its content words are a subset of the
    union of content words in the earlier sentences (it adds no new fact, only
    restates the lead). Conservative: needs >= 3 sentences (never reduces a two-
    sentence summary to one), the final sentence must have >= 1 content word, and
    every one of those words must already appear earlier."""
    parts = _split_sentences(summary)
    if len(parts) < 3:
        return summary
    last_words = _content_words(parts[-1])
    if not last_words:
        return summary
    earlier: set[str] = set()
    for p in parts[:-1]:
        earlier |= _content_words(p)
    if last_words <= earlier:
        return " ".join(parts[:-1])
    return summary


def _collapse_unknown_padding(summary: str) -> str:
    """3c: within a run of CONSECUTIVE "unknown / ongoing investigation"
    sentences, keep only the first. Non-consecutive such sentences are each
    kept (the spec targets consecutive padding). Conservative: only touches
    sentences the padding regex matches."""
    parts = _split_sentences(summary)
    if len(parts) < 2:
        return summary
    kept: list[str] = []
    prev_unknown = False
    dropped = False
    for p in parts:
        is_unknown = bool(_UNKNOWN_PADDING_RE.search(p))
        if is_unknown and prev_unknown:
            dropped = True
            continue  # consecutive unknown sentence — collapse away
        kept.append(p)
        prev_unknown = is_unknown
    return " ".join(kept) if dropped else summary


def _drop_repeated_claim_sentences(summary: str) -> str:
    """3d: drop a sentence whose content-word set is a near-duplicate (Jaccard
    >= 0.7) of an EARLIER kept sentence. Conservative: only judges substantial
    sentences (>= 4 content words), so short factual lines are never removed."""
    parts = _split_sentences(summary)
    if len(parts) < 2:
        return summary
    kept: list[str] = []
    kept_sets: list[set[str]] = []
    dropped = False
    for p in parts:
        w = _content_words(p)
        if len(w) >= 4 and any(_jaccard(w, prev) >= 0.7 for prev in kept_sets):
            dropped = True
            continue
        kept.append(p)
        kept_sets.append(w)
    return " ".join(kept) if dropped else summary


def _sentence_word_seq(sentence: str) -> list[str]:
    """Ordered lowercase word tokens of a sentence (dotted initialisms split to
    their letters: "U.S." -> ["u", "s"]). Used by the contiguous key-phrase
    dedup, which keys on word ORDER rather than the unordered content-word set."""
    return _re.findall(r"[a-z0-9']+", (sentence or "").lower())


def _shares_long_run(a: list[str], b: list[str], n: int = 5) -> bool:
    """True when word sequences `a` and `b` share a contiguous run of >= n words.
    A 5-word verbatim run almost never recurs by chance across two DISTINCT facts,
    so it is a reliable restatement signal."""
    if len(a) < n or len(b) < n:
        return False
    a_grams = {tuple(a[i:i + n]) for i in range(len(a) - n + 1)}
    return any(tuple(b[i:i + n]) in a_grams for i in range(len(b) - n + 1))


def _drop_repeated_keyphrase_sentences(summary: str) -> str:
    """3d-bis: drop a later sentence that repeats a >= 5-word CONTIGUOUS phrase
    from an earlier kept sentence. Catches restatements the content-word Jaccard
    (3d) misses when the two sentences wrap the same verbatim clause in different
    filler, e.g. "Hundreds of people have been killed in the year since ..." vs
    "... Hundreds of people have been killed in the interim." (Jaccard ~0.6, under
    the 0.7 gate). A 5-word verbatim run is the conservative floor; single-sentence
    summaries are never touched."""
    parts = _split_sentences(summary)
    if len(parts) < 2:
        return summary
    kept: list[str] = []
    kept_seqs: list[list[str]] = []
    dropped = False
    for p in parts:
        seq = _sentence_word_seq(p)
        if any(_shares_long_run(prev, seq) for prev in kept_seqs):
            dropped = True
            continue
        kept.append(p)
        kept_seqs.append(seq)
    return " ".join(kept) if dropped else summary


def _normalize_abbrev_spacing(text: str) -> str:
    """Collapse a spaced dotted initialism ("U. S.", "U. N.", "E. U.") back to its
    tight form ("U.S."). Some source excerpts and model outputs carry the spaced
    form, which both reads poorly AND fragments the sentence splitter (each "X."
    looks like a sentence end). Only touches a run of single capital letters each
    followed by a period, so ordinary sentence boundaries ("... left. She arrived.")
    are never affected. Run FIRST in the chain so downstream splits see the glued
    form."""
    if not text:
        return text
    prev = None
    out = text
    # Iterate so chained initialisms (U. S. A.) fully collapse.
    while prev != out:
        prev = out
        out = _re.sub(r"\b([A-Z]\.)\s+(?=[A-Z]\.)", r"\1", out)
    return out


def _concat_source_text(articles: list[dict]) -> str:
    """Concatenate all available member text (title + summary + full_text) into
    one lowercase blob used to ground the age post-check (3e). Broad on purpose:
    an age is only dropped when it appears in NO member text, minimizing false
    drops of a legitimately reported age."""
    parts: list[str] = []
    for a in articles or []:
        for k in ("title", "summary", "full_text"):
            v = a.get(k)
            if v:
                parts.append(str(v))
    return " ".join(parts).lower()


def _excise_age_phrase(sentence: str, number: str) -> str:
    """Cleanly remove an age phrase carrying `number` from a sentence, preferring
    excision of just the phrase (with any leading article) over dropping the
    whole sentence. Handles "an 80-year-old", "aged 80", ", aged 80,"."""
    n = _re.escape(number)
    s = sentence
    # ", aged 80," / ", aged 80" -> drop the parenthetical age clause.
    s = _re.sub(r",\s*aged\s+" + n + r"\b\s*,?", ", ", s, flags=_re.IGNORECASE)
    s = _re.sub(r"\baged\s+" + n + r"\b", "", s, flags=_re.IGNORECASE)
    # "an/a/the 80-year-old " -> drop article + adjective together.
    s = _re.sub(r"\b(?:an|a|the)\s+" + n + r"[- ]year[- ]old\b\s*", "", s,
                flags=_re.IGNORECASE)
    # bare "80-year-old " adjective.
    s = _re.sub(r"\b" + n + r"[- ]year[- ]old\b\s*", "", s, flags=_re.IGNORECASE)
    # punctuation / whitespace cleanup after excision.
    s = _re.sub(r"\s+([.,;:!?])", r"\1", s)
    s = _re.sub(r",\s*,", ",", s)
    s = _re.sub(r"\(\s*\)", "", s)
    s = _re.sub(r"\s{2,}", " ", s).strip()
    s = _re.sub(r"^[,;:\s]+", "", s)
    # Recapitalize a sentence start left lowercase by removing a leading article.
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return s


def _drop_ungrounded_ages(summary: str, source_text: str) -> str:
    """3e: remove any person-age assertion whose number does NOT appear in the
    concatenated source article text. Prefer excising just the age phrase; when
    it cannot be cleanly excised (e.g. "X is 80"), drop the whole sentence.
    Conservative: an age is kept whenever its number appears anywhere in the
    source text, so legitimately reported ages are never dropped."""
    if not summary or not summary.strip():
        return summary
    src = source_text or ""

    def grounded(num: str) -> bool:
        return _re.search(r"\b" + _re.escape(num) + r"\b", src) is not None

    parts = _split_sentences(summary)
    if not parts:
        return summary
    out: list[str] = []
    for sent in parts:
        # Collect ungrounded ages in this sentence.
        excisable = {m.group(1) for m in _AGE_YEAR_OLD_RE.finditer(sent)}
        excisable |= {m.group(1) for m in _AGE_AGED_RE.finditer(sent)}
        non_excisable = {m.group(1) for m in _AGE_IS_RE.finditer(sent)}
        ung_excisable = {n for n in excisable if not grounded(n)}
        ung_isform = {n for n in non_excisable if not grounded(n)}
        if not ung_excisable and not ung_isform:
            out.append(sent)
            continue
        if ung_isform:
            # "X is 80" cannot be cleanly excised — drop the whole sentence.
            continue
        new = sent
        for n in ung_excisable:
            new = _excise_age_phrase(new, n)
        # If excision failed to remove the age (still ungrounded), drop sentence.
        residual = {m.group(1) for m in _AGE_YEAR_OLD_RE.finditer(new)}
        residual |= {m.group(1) for m in _AGE_AGED_RE.finditer(new)}
        if any(not grounded(n) for n in residual):
            continue
        if new.strip():
            out.append(new.strip())
    cleaned = " ".join(out).strip()
    cleaned = _re.sub(r"\s{2,}", " ", cleaned)
    # Safety: never blank a card. If every sentence was dropped, keep original.
    return cleaned if cleaned else summary


def _tail_ends_in_abbrev(chunk: str) -> bool:
    """Delegate to the sanitizer's abbreviation test; fall back to a small local
    check if the import is unavailable (keeps this module importable standalone)."""
    try:
        from utils.text_sanitizer import _ends_in_abbrev
        return _ends_in_abbrev(chunk)
    except Exception:
        m = _re.search(r"([A-Za-z][A-Za-z.'\-]*)\.[\"')\]]?\s*$", chunk or "")
        if not m:
            return False
        w = m.group(1).lower().rsplit("-", 1)[-1].rsplit(".", 1)[-1]
        return w in {"rep", "sen", "gov", "gen", "st", "mr", "mrs", "ms", "dr",
                     "jr", "sr", "no", "vs", "inc", "ltd", "co", "corp"} or bool(
            _re.fullmatch(r"[a-z](?:\.[a-z])*", m.group(1).lower()))


def _trim_incomplete_tail_sentence(summary: str) -> str:
    """3g completeness gate: drop a trailing INCOMPLETE final sentence so a
    token-limit-truncated LLM summary never ships a dangling fragment. Two
    signatures, both conservative to avoid trimming a genuinely complete sentence:

      * the tail has NO terminal punctuation at all (cut mid-clause), or
      * the tail is SHORT (<= 4 words) and ends on an abbreviation period that is
        not a real sentence end ('...Florida Rep.', 'primary. Rep.').

    A long sentence that legitimately ends on an abbreviation ('...met at the
    U.N.') is left alone. Never drops the ONLY sentence, and never returns empty:
    a fully-degenerate row is left for the raw-excerpt / pending guards."""
    s = (summary or "").strip()
    if not s:
        return summary
    parts = _split_sentences(s)
    if len(parts) <= 1:
        return s
    tail = parts[-1].rstrip()
    terminated = tail.endswith((".", "!", "?", "”", '"', "’", "'", ")"))
    short_abbrev = (len(tail.split()) <= 4) and _tail_ends_in_abbrev(tail)
    if terminated and not short_abbrev:
        return s  # tail is a complete sentence
    trimmed = " ".join(parts[:-1]).strip()
    return trimmed if trimmed else s


_ORPHAN_SUBORDINATE_RE = _re.compile(
    r"^(?:when|where|which|who|whom|whose|that|because|although|though|while|"
    r"since|unless|whereas|wherein|whereby|after|before|as|if)\b"
)


def _drop_orphan_fragments(summary: str) -> str:
    """3h: drop a non-first sentence that opens on a lowercase subordinating
    conjunction / relative pronoun (a dependent clause left standing as a
    "sentence" by a truncation or a broken boundary: '...PAC. when she won a
    seat in 2018.'), and strip a stray straight quote left by a dropped figure
    ('announced a " investment')."""
    s = (summary or "").strip()
    if not s:
        return summary
    cleaned = _re.sub(r'\s"\s+', " ", s)
    cleaned = _re.sub(r'\s"(?=[a-z])', " ", cleaned)
    parts = _split_sentences(cleaned)
    if len(parts) < 2:
        return cleaned.strip()
    kept = [parts[0]]
    dropped = False
    for p in parts[1:]:
        if _ORPHAN_SUBORDINATE_RE.match(p.lstrip()):
            dropped = True
            continue
        kept.append(p)
    out = " ".join(kept) if dropped else cleaned
    return _re.sub(r"\s{2,}", " ", out).strip()


def _apply_summary_postchecks(summary: str, source_text: str = "") -> str:
    """Run the Phase-3 hygiene chain on a summary. Deterministic, order matters:
    content-level drops first (exact dup, near-dup, unknown padding, ungrounded
    age, terminal restatement), then the hard 90-word trim last so the cap is
    measured on the cleaned text. Every step is a no-op on already-clean input.
    Used by BOTH the LLM path and the rule-based floor."""
    if not summary or not summary.strip():
        return summary
    s = _normalize_abbrev_spacing(summary)        # glue "U. S." -> "U.S." first
    s = _dedupe_summary_sentences(s)              # exact duplicate sentences
    s = _drop_repeated_claim_sentences(s)          # 3d near-duplicate claims
    s = _drop_repeated_keyphrase_sentences(s)      # 3d-bis verbatim key-phrase repeat
    s = _collapse_unknown_padding(s)               # 3c unknown/ongoing padding
    if source_text:
        s = _drop_ungrounded_ages(s, source_text)  # 3e ungrounded ages
    s = _drop_terminal_restatement(s)              # 3b terminal restatement
    s = _trim_summary_to_word_cap(s)               # 3a hard 90-word trim
    s = _trim_incomplete_tail_sentence(s)          # 3g completeness (drop truncation)
    s = _drop_orphan_fragments(s)                  # 3h orphan subordinate-clause + stray quote
    s = s.strip()
    # 3f grounding audit (warning-only, no drops yet). Logs figures / proper
    # nouns in the FINAL summary that are absent from the source text so we can
    # measure the hallucination hit rate before escalating to sentence removal.
    if source_text:
        ungrounded = _flag_ungrounded_tokens(s, source_text)
        if ungrounded:
            print(
                f"  [grounding] tokens not found in source text "
                f"(warning only, no drop): {ungrounded}"
            )
    return s


# ---------------------------------------------------------------------------
# P0 LEGAL SAFETY (2026-08-11): defamation attribution post-check + CSAM gate.
# Durable, deterministic guards that run at GENERATION time so the stored
# story_clusters.summary is fixed in the DB, not merely masked at render (the
# frontend render-time half is committed separately on this branch). Regexes
# ported verbatim from the validated frontend logic (JS -> Python, IGNORECASE).
#
# (1) DEFAMATION: any claim about a NAMED individual's conduct, character, or
#     beliefs that is reputationally damaging, criminal, or a criminal
#     allegation must carry in-text attribution to a reporting outlet / official
#     source, or a direct quote. A sentence that makes such a claim WITHOUT an
#     attribution cue or a quote is DROPPED; the rest of the summary is kept.
#     If dropping empties the summary, "" is stored (the frontend drops an
#     empty-summary body).
#
# (2) CSAM: a cluster about child sexual abuse material renders headline +
#     sources ONLY. Its article bodies are NEVER sent to the LLM and no body
#     summary is generated; the stored summary is forced to "".
# ---------------------------------------------------------------------------

_REPUTATIONAL_HARM_RE = _re.compile(
    r"\b(celebrat|applaud|prais|laud|endors|glorif|justif|condon|cheer|support|"
    r"back|defend|champion)\w*\s+(?:\w+\s+){0,4}"
    r"(terror|terrorism|terrorist|attack|massacre|genocide|jihad|extremis|"
    r"antisemit|nazism|nazi|hamas|hezbollah|rape|molest|p(?:a?e)dophil|abuse|"
    r"assault|insurrection)",
    _re.IGNORECASE,
)
_CRIMINAL_FACT_RE = _re.compile(
    r"\b(?:is|was|are|were)\s+(?:a\s+|an\s+|the\s+)?"
    r"(?:convicted\s+|alleged\s+|suspected\s+)?"
    r"(terrorist|rapist|p(?:a?e)dophile|murderer|fraudster|abuser|molester|"
    r"criminal|extremist)\b",
    _re.IGNORECASE,
)
_CRIMINAL_ALLEGATION_RE = _re.compile(
    r"\b(accused of|charged with|indicted (?:for|on)|convicted of|"
    r"found guilty of|arrested for|perpetrat(?:ed|or))\b",
    _re.IGNORECASE,
)
_ATTRIBUTION_CUE_RE = _re.compile(
    r"\b(accord(?:ing) to|reported by|as reported|reportedly|said|says|stated|"
    r"told\s+[A-Z]|per\s+[A-Z]|alleged by|prosecutors|indictment|police said|"
    r"court (?:documents|filings|records)|lawsuit|complaint|according)\b",
    _re.IGNORECASE,
)
_QUOTE_PRESENT_RE = _re.compile(r'["“][^"”]{3,}["”]')

# Reputational-harm ASSOCIATION terms (nouns/phrases), distinct from the verb-led
# claims above. These impute wrongdoing by association ("terror ties", "linked to
# al-Qaeda", "blacklisted", "designated a terrorist") and are dangerous when they
# float in a subject-less truncation fragment. Bare org names (Hamas, Taliban) are
# NOT listed on their own — they appear constantly in legitimate reporting ("Hamas
# affirmed its commitment") — only their wrongdoing-association phrasings are.
_REPUTATIONAL_TERM_RE = _re.compile(
    r"\b(?:"
    r"blacklist(?:ed|ing)?|"
    r"(?:terror|terrorist|al[\s-]?qaeda|taliban|hamas|hezbollah|isis|isil|jihad|"
    r"militant|extremist)\s+(?:ties|links?|affiliation|connections?)|"
    r"(?:ties|links?|affiliation|connections?)\s+to\s+(?:terror|terrorist|"
    r"al[\s-]?qaeda|taliban|hamas|hezbollah|isis|isil|jihad|militants?|extremis)|"
    r"link(?:ed|s)?\s+to\s+(?:terror|al[\s-]?qaeda|taliban|hamas|hezbollah|isis|"
    r"jihad|extremis)|"
    r"designat(?:ed|ion)\s+(?:as\s+)?(?:a\s+)?(?:foreign\s+)?terrorist|"
    r"sympath(?:iser|izer)|radicali[sz]ed"
    r")\b",
    _re.IGNORECASE,
)

# A plausible grammatical subject opens the sentence: a proper noun or subject
# pronoun / article-led noun phrase. FAILS on a bare-numeral or lowercase /
# dangling-preposition opening ("375 million into ... blacklisted ..."), which is
# the truncation fingerprint that strips a claim of its subject and attribution.
_SUBJECT_START_RE = _re.compile(
    r"^[\"'“(]*\s*(?:He|She|They|It|The|A|An|This|That|Those|These|His|Her|Their|"
    r"[A-Z][A-Za-z][A-Za-z.'’-]*)\b"
)


def _has_identifiable_subject(sentence: str) -> bool:
    """True if the sentence opens on a plausible subject (proper noun / pronoun /
    article-led noun phrase). A sentence that opens on a bare numeral or a
    lowercase dangling preposition has been severed from its subject."""
    s = (sentence or "").strip()
    if not s:
        return False
    if _re.match(r"^[\"'“(]*\s*\$?\d", s):  # opens on a figure -> no subject
        return False
    return bool(_SUBJECT_START_RE.match(s))


# Broader negative-association signal used ONLY to arm the 3b verification/relative
# rules below (not the existing attributed-claim logic). Catches reputational
# associations the harm-verb patterns miss ("worked for a group that funded Bin
# Laden", "juvenile record", "racist").
_NEGATIVE_ASSOCIATION_RE = _re.compile(
    r"\b(?:bin\s+laden|al[-\s]?qaeda|taliban|hamas|hezbollah|isis|isil|jihad|"
    r"terror|terrorist|extremis|militant|funded|financed|bankrolled|blacklist|"
    r"accused|alleged|indicted|convicted|criminal|felony|racist|neo[-\s]?nazi|"
    r"juvenile\s+record|rap\s+sheet|ties\s+to|linked\s+to)\b",
    _re.IGNORECASE,
)
_VERIFICATION_ASSERTION_RE = _re.compile(
    r"\b(?:verified|confirmed|corroborated|substantiated|proven|proved)\s+by\b|"
    r"\b(?:independently|separately)\s+(?:verified|confirmed|corroborated|substantiated)\b",
    _re.IGNORECASE,
)
_RELATIVE_OF_PERSON_RE = _re.compile(
    r"\b(?:birth\s+|step[-\s]?|half[-\s]?|adoptive\s+|foster\s+)?"
    r"(?:mother|father|mom|dad|parent|son|daughter|child|brother|sister|sibling|"
    r"wife|husband|spouse|cousin|aunt|uncle|nephew|niece|"
    r"grand(?:mother|father|son|daughter)|in[-\s]?law)\b",
    _re.IGNORECASE,
)


def _sentence_makes_reputational_claim(sentence: str) -> bool:
    """True if the sentence asserts a reputational-harm, criminal-status, or
    criminal-allegation claim (about a named individual)."""
    return bool(
        _REPUTATIONAL_HARM_RE.search(sentence)
        or _CRIMINAL_FACT_RE.search(sentence)
        or _CRIMINAL_ALLEGATION_RE.search(sentence)
    )


def _sentence_has_attribution(sentence: str) -> bool:
    """True if the sentence carries an attribution cue or a direct quote."""
    return bool(
        _ATTRIBUTION_CUE_RE.search(sentence) or _QUOTE_PRESENT_RE.search(sentence)
    )


def _strip_unattributed_reputational_claims(summary: str) -> tuple[str, list[str]]:
    """Defamation post-check. Split the summary into sentences and DROP any
    sentence that makes a reputational-harm / criminal claim without an
    attribution cue or a direct quote; keep every other sentence verbatim.
    Returns (cleaned_summary, dropped_sentences). When nothing is dropped the
    input is returned unchanged. When every sentence is dropped the cleaned
    summary is "" (the frontend drops an empty body). Deterministic; $0."""
    if not summary or not summary.strip():
        return summary, []
    sentences = _re.findall(r"[^.!?]+[.!?]*", summary)
    kept: list[str] = []
    dropped: list[str] = []
    for s in sentences:
        if not s.strip():
            continue
        reputational = bool(
            _sentence_makes_reputational_claim(s)
            or _REPUTATIONAL_TERM_RE.search(s)
            or _NEGATIVE_ASSOCIATION_RE.search(s)
        )
        # (3b-1) A reputational claim the summary VOUCHES for ("verified by ...").
        # Corroborating a smear is worse than asserting one; drop it outright.
        if reputational and _VERIFICATION_ASSERTION_RE.search(s):
            dropped.append(s.strip())
            continue
        # (3b-3) A reputational claim about a relative (a private individual).
        if reputational and _RELATIVE_OF_PERSON_RE.search(s):
            dropped.append(s.strip())
            continue
        # (1) Verb-led reputational/criminal claim: drop unless attributed.
        if _sentence_makes_reputational_claim(s) and not _sentence_has_attribution(s):
            dropped.append(s.strip())
            continue
        # (2) Reputational-harm ASSOCIATION term (e.g. "blacklisted over alleged
        # al-Qaeda ... ties"): a truncation can strip such a claim of BOTH its
        # subject and its attribution and leave it dangling next to a named
        # person. Require an identifiable subject AND attribution, else drop.
        if _REPUTATIONAL_TERM_RE.search(s) and not (
            _has_identifiable_subject(s) and _sentence_has_attribution(s)
        ):
            dropped.append(s.strip())
            continue
        kept.append(s)
    if not dropped:
        return summary, []
    cleaned = _re.sub(r"\s{2,}", " ", "".join(kept)).strip()
    return cleaned, dropped


_CSAM_TOPIC_RE = _re.compile(
    r"\b(child (?:sexual abuse|sex abuse|pornography|porn|exploitation)|csam|"
    r"sexually explicit (?:video|image|photo|material|content)s?\s+"
    r"(?:involving|of|depicting)\s+(?:a\s+)?minors?|"
    r"minors?\b[^.]{0,40}\b(?:sexual(?:ly)?\s+(?:abus|explicit|exploit)|molest|"
    r"raped|sexually abused)|"
    r"underage\s+(?:sex|porn|nude|explicit))",
    _re.IGNORECASE,
)


def is_csam_topic(text: str) -> bool:
    """True if `text` describes child sexual abuse material. Drives the CSAM gate:
    a matching cluster renders headline + sources only, never sends article
    bodies to the LLM, and stores an empty body summary. Deterministic; $0."""
    if not text:
        return False
    return bool(_CSAM_TOPIC_RE.search(text))


def _cluster_is_csam(cluster_title: str | None, articles: list[dict]) -> bool:
    """A cluster is CSAM-topic when its title OR any member article's title /
    summary / full_text matches is_csam_topic."""
    if is_csam_topic(cluster_title or ""):
        return True
    for a in articles or []:
        for k in ("title", "summary", "full_text"):
            if is_csam_topic(str(a.get(k) or "")):
                return True
    return False


def _csam_blocked_result(cluster_title: str | None, articles: list[dict]) -> dict:
    """The stored result for a CSAM cluster: keep the existing news headline,
    FORCE the body summary to "". No LLM call is made and no article body is
    sent to any model. Stamped with a flash-tier generator so the content-hash
    cache treats the cluster as done (it is not re-summarized every run)."""
    headline = (cluster_title or "").strip()
    if not headline:
        for a in articles or []:
            t = str(a.get("title") or "").strip()
            if t:
                headline = t
                break
    return {
        "headline": (headline or "News")[:500],
        "summary": "",
        "consensus": [],
        "divergence": [],
        "editorial_importance": None,
        "story_type": None,
        "has_binding_consequences": None,
        "claims": None,
        "consensus_ratio": None,
        "consensus_summary": None,
        # tier 'flash' -> the cache marks it done, so the block is not re-run.
        "_generator": "gemini-flash",
        "_csam_blocked": True,
    }


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

    Checks headline word count (8-12), summary word count (<= 90 words),
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

    # Summary word count (target band: 55-90 words; a little slack before warning).
    summary = result.get("summary", "")
    summary_wc = len(summary.split())
    if summary_wc > _SUMMARY_WORD_CAP + 5:
        print(
            f"  [quality]{cid_str} Summary word count {summary_wc} (expected <= "
            f"{_SUMMARY_WORD_CAP}): first 80 chars: {summary[:80]!r}"
        )
    elif summary and summary_wc < _SUMMARY_WORD_FLOOR:
        # Under-length: the model over-compressed to a clipped fragment. Surface
        # it so drift toward one-sentence summaries is visible (warning only — a
        # deterministic pass cannot pad without inventing ungrounded facts).
        print(
            f"  [quality]{cid_str} Summary word count {summary_wc} under the "
            f"{_SUMMARY_WORD_FLOOR}-word soft floor: {summary[:80]!r}"
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
_ONTOPIC_FLOOR = 3            # blend back up to at least this many members
# Minimum total member source-text (chars, across the kept set) needed to write
# a full 200-400 word summary. Below this the title-anchored filter is judged to
# have STARVED the summary and blends the next-most-relevant members back so a
# coherent cluster never collapses to a one-line summary (BUG 1, 2026-08-07).
_ONTOPIC_MIN_TEXT_CHARS = 500

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
    # MIN-CONTENT GUARD: title-anchored filtering can STARVE the summary when the
    # title's specific tokens appear literally in only a member or two (a coherent
    # cluster whose members use varied headline vocabulary, mis-read as a bag),
    # producing a one-line summary. If it leaves too little to write a full
    # summary, widen to the broad core (title + shared spine, generic-stripped):
    # this restores the coherent members without re-admitting a true bag's
    # off-topic pile, which only ever shared GENERIC words with the title.
    if mode == "title-anchored" and len(kept) < 3:
        broad_core = (title_specific | shared) - generic
        if broad_core:
            widened = [
                art for art, toks in zip(articles, member_tokens)
                if (toks - generic) & broad_core
            ]
            if len(widened) > len(kept):
                kept = widened
                mode = "title-anchored->broad"
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
    # Same stratified selection + order as _build_articles_block, so the
    # [n] indices here point at the same articles the block numbers.
    for i, art in enumerate(_select_articles_for_summary(articles)):
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


# Per-article body budget in the prompt. ~1800 chars is roughly 300-350 words
# of real reporting per source; 10 sources keep the whole cluster a few thousand
# tokens, well within a single free-tier request (the free-tier cap is
# REQUESTS/day, not input tokens), so feeding real bodies stays $0 and adds no
# extra call.
_ARTICLE_BODY_MAX_CHARS = 2200


def _sentence_bounded_excerpt(text: str, max_chars: int = _ARTICLE_BODY_MAX_CHARS) -> str:
    """Return a leading slice of `text` no longer than ~max_chars, cut on the
    LAST sentence terminator ('.', '!' or '?') at or before the limit so no
    sentence is severed mid-fact. Returns the whole text when already within the
    limit. No trailing ellipsis is added, so the summarizer never mistakes a hard
    cut for a mid-sentence continuation. Deterministic."""
    t = (text or "").strip()
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    window = t[:max_chars]
    # Prefer a terminator followed by whitespace (a real sentence break) over a
    # bare period, which may sit inside an abbreviation ("U.S.") or a decimal.
    cut = max(
        window.rfind(". "), window.rfind("! "), window.rfind("? "),
        window.rfind(".\n"), window.rfind("!\n"), window.rfind("?\n"),
    )
    if cut == -1:
        cut = max(window.rfind("."), window.rfind("!"), window.rfind("?"))
    # Only honor the sentence cut when it keeps a substantial excerpt; otherwise
    # fall back to the hard character window (still no ellipsis).
    if cut != -1 and cut >= max_chars // 2:
        return window[: cut + 1].strip()
    return window.strip()


def _build_articles_block(articles: list[dict], max_articles: int = _MAX_SUMMARY_ARTICLES) -> str:
    """
    Build the articles context block for the prompt.

    Uses tier-based labels in the article block itself (to prevent Gemini
    from weighting outlets by brand recognition), but real outlet names are
    provided separately via _build_source_names_line for attribution use.

    Articles are sorted newest-first so Gemini sees the most recent
    developments at the top of the context window. Each article includes
    its publication timestamp so Gemini can distinguish fresh developments
    from older background.

    Limits to max_articles and feeds the article BODY (full_text), sentence-
    bounded to ~_ARTICLE_BODY_MAX_CHARS, so the model summarizes real reporting
    rather than a 400-char RSS excerpt. Falls back to the RSS `summary` field
    when full_text is empty. Grounds the summary in the actual articles, which
    the grounding post-check (_flag_ungrounded_tokens) then audits.
    """
    _TIER_LABEL_MAP = {
        "us_major": "US Source",
        "international": "International Source",
        "independent": "Independent Source",
    }

    # Stratified selection (spread + tier + recency) shared with _content_hash
    # and _build_source_names_line, so the prompt inputs, the outlet-name
    # indices, and the cache key all describe the same article set in the same
    # newest-first order.
    sorted_articles = _select_articles_for_summary(articles, max_articles)

    lines = []
    for i, art in enumerate(sorted_articles):
        title = (art.get("title", "") or "").strip()
        full_text = (art.get("full_text", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()
        pub_date = (art.get("published_at", "") or "")[:16]  # YYYY-MM-DDTHH:MM

        # Use tier as source label in the article block.
        # Normalize tier value: lowercase + replace hyphens with underscores.
        tier_raw = (art.get("tier", "") or "").strip().lower().replace("-", "_")
        source_label = _TIER_LABEL_MAP.get(tier_raw, f"Source {i + 1}")

        header = f"[{i + 1}] {source_label}: {title}"
        if pub_date:
            header += f"  ({pub_date})"

        # Feed the actual article BODY when we have it (sentence-bounded so no
        # fact is severed), falling back to the RSS summary excerpt otherwise.
        # This is the grounding win: the model summarizes real reporting instead
        # of a 400-char RSS teaser it has to extrapolate from.
        if full_text:
            body = _sentence_bounded_excerpt(full_text)
        else:
            body = summary

        lines.append(header)
        if body:
            lines.append(f"    {body}")
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

    # CSAM GATE (P0 legal): a cluster about child sexual abuse material renders
    # headline + sources ONLY. Never build a prompt from its article bodies and
    # never call the LLM; return a forced empty-summary result. This is the
    # single-cluster chokepoint (solo batches, the floor upgrade, and the flash
    # reconcile all reach the LLM through here); the multi-story batch path is
    # gated separately in _send_one_batch before any body enters a shared prompt.
    if _cluster_is_csam(cluster_title, articles):
        print("  [csam-gate] cluster blocked from LLM summarization "
              "(headline + sources only)")
        return _csam_blocked_result(cluster_title, articles)

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

    # Thin-material adaptation (CEO 2026-08-11): a cluster with only a few
    # usable articles cannot honestly support a 200-300-word brief. All its
    # articles are already fed (selection only strat-samples ABOVE the cap);
    # relax the band to a 100-word floor so length pressure never turns into
    # invention. Grounding rules are unchanged either way.
    if len(summ_articles) < _THIN_CLUSTER_ARTICLES:
        prompt = prompt.replace("200 to 300 words", "100 to 250 words")

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

    # Validation + hygiene are shared with the batched path so both apply an
    # identical chain (_finalize_cluster_result). `articles` is the FULL member
    # list so grounding (3e/3f) and the outlet-leak scan see every source.
    return _finalize_cluster_result(result, articles, _generator_label)


def _finalize_cluster_result(result: dict, articles: list[dict],
                             generator_label: str) -> dict | None:
    """Validate + clean ONE cluster's raw LLM JSON into the stored schema.

    Shared by the single-cluster path (summarize_cluster) and the batched path
    (_summarize_cluster_batch) so a batched story receives byte-for-byte the same
    hygiene as a solo one: shape validation, exact/near-duplicate sentence drops,
    em-dash + significance-word sanitize, source-material meta-commentary strip,
    the Phase-3 postcheck chain (grounded against the FULL member text), the
    source-agnostic outlet-leak warning, consensus/divergence sanitize, and the
    editorial-intelligence field extraction. `articles` is the cluster's FULL
    membership (not the on-topic-filtered prompt subset) so a legitimately
    reported age / figure is never dropped as "ungrounded". Returns the validated
    dict (with `_generator` set to `generator_label`) or None when the headline
    or summary is missing/empty."""
    if not result or not isinstance(result, dict):
        return None

    # Show-don't-tell post-check: assertions of significance ("notable",
    # "significantly", "crucially", etc.) violate the Cardinal Rule.
    #
    # 2026-05-21 nlp-engineer cost-cut: the forbidden-word list is now
    # encoded directly in _SYSTEM_INSTRUCTION (FORBIDDEN SIGNIFICANCE-
    # ASSERTIONS section). The model follows it without needing a retry
    # call on every violation. We keep the post-check as a warning log only so
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
    # Phase-3 hygiene: drop near-duplicate claims, collapse unknown/ongoing
    # padding, strip ungrounded ages (checked against the FULL member text, not
    # the on-topic-filtered subset, so a legitimately reported age is never
    # dropped), drop a terminal restatement of the lead, then hard-trim to the
    # runaway ceiling at a sentence boundary. Deterministic; a no-op on clean text.
    summary = _apply_summary_postchecks(summary, _concat_source_text(articles))
    # P0 DEFAMATION GUARD: drop any sentence that asserts a reputational-harm or
    # criminal claim about a named individual WITHOUT in-text attribution or a
    # direct quote (Void must never state such a claim in its own voice). Keeps
    # every other sentence; if this empties the summary, "" is stored and the
    # frontend drops the empty body (headline + sources remain).
    summary, _defam_dropped = _strip_unattributed_reputational_claims(summary)
    if _defam_dropped:
        print(f"  [defamation-guard] dropped unattributed reputational claim(s): "
              f"{_defam_dropped}")
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
        # Callers map this to summary_tier.
        "_generator": generator_label,
    }

    # Quality gate: log warnings for out-of-spec output (no discards).
    # Cluster index is not available here; caller passes cluster id when needed.
    _check_quality(validated)

    return validated


# ===========================================================================
# Batched summarization (2026-08-11) — fit the top-50 into the free-tier cap.
# ===========================================================================
# Gemini free tier is bound by REQUESTS/DAY (RPD), not tokens: flash AND
# flash-lite each allow 20 requests/DAY, while TPM (250K INPUT tokens/min) has
# huge headroom (a real run peaked ~30K). One-request-per-cluster (~50/run) blew
# the 20 RPD cap after ~20 stories, dropping the tail to raw excerpts. Batching
# many clusters into ONE request cuts the top-50 to ~8 requests, all on
# gemini-2.5-flash (the premium tier); flash-lite is used only as overflow.
#
# SHARED FLASH BUDGET: flash's 20 requests/DAY is shared across the WHOLE
# pipeline. Daily summaries (~8, this schedule) + the daily brief TL;DR +
# opinion (~3) = ~11, leaving ~9 of 20 as buffer for retries and the Sunday
# weekly / Saturday monthly marquee calls. This summarizer MUST stay near 8
# flash requests and must not balloon: the graduated schedule FIXES the flash
# request count at (at most) len(schedule) regardless of how many stories fail,
# and the failure retry path spends flash-lite (its own separate 20/day), never
# more flash, and is itself bounded (_MAX_OVERFLOW_RETRY_REQUESTS).
#
# GRADUATED BATCH SIZES (single tunable constant). Summary quality dips as
# stories-per-call rises (attention dilution / lost-in-the-middle / output-token
# squeeze); that dip matters most for the top stories readers actually read, so
# the lead stories get small (even solo) batches and the tail packs denser.
# Sizes are consumed IN ORDER over the cache-MISS clusters (rank order); cached
# clusters are skipped and never consume a slot, so a run with cache hits just
# packs the remaining misses into the next group's size and the schedule
# degrades gracefully. Sum = 50, so a full miss run = exactly 8 flash requests:
#   rank 1 -> solo, rank 2 -> solo, ranks 3-6 -> 4, ranks 7-14 -> 8,
#   ranks 15-24 -> 10, ranks 25-34 -> 10, ranks 35-44 -> 10, ranks 45-50 -> 6.
_SUMMARY_BATCH_SCHEDULE = [1, 1, 4, 8, 10, 10, 10, 6]

# Per-batch INPUT-token budget. TPM (250K input tokens/min) is the loose ceiling;
# keep every request well under it, split the budget across the batch's clusters,
# and let per-cluster article DEPTH graduate: a solo lead gets the full 25-article
# stratified selection, a batch of 8 gets ~21 each, a batch of 10 ~17 each. So the
# top stories are sourced deepest and no batch can breach TPM.
_BATCH_INPUT_TOKEN_BUDGET = 120_000
_BATCH_TOKEN_CEILING = 150_000        # hard per-request input ceiling; shrink depth
_TPM_INPUT_LIMIT = 250_000
_TPM_SAFE_CEILING = 230_000           # pace so no rolling 60s window's input exceeds this
_APPROX_CHARS_PER_TOKEN = 4           # rough English char:token ratio for estimation
_APPROX_TOKENS_PER_ARTICLE = 700      # ~_ARTICLE_BODY_MAX_CHARS body + header per article
_BATCH_MIN_ARTICLES_PER_CLUSTER = 6   # floor: keep enough grounding even when dense
_SOLO_INPUT_TOKEN_EST = 22_000        # ~25 articles + template, for TPM accounting only
_MAX_OVERFLOW_RETRY_REQUESTS = 2      # BOUNDED flash-lite retries for failed stories


def _estimate_tokens(text: str) -> int:
    """Rough token count from character length (English ~4 chars/token). Used only
    to keep a batch under the input-token ceiling / TPM window; never billed."""
    return max(1, len(text or "") // _APPROX_CHARS_PER_TOKEN)


def _batch_article_cap(n_clusters: int) -> int:
    """Per-cluster article depth for a batch of `n_clusters`: split the input-token
    budget across the batch and convert to an article count, clamped to
    [_BATCH_MIN_ARTICLES_PER_CLUSTER, _MAX_SUMMARY_ARTICLES]. Solo -> 25; batch of
    8 -> ~21; batch of 10 -> ~17. Deterministic."""
    n = max(1, n_clusters)
    per_cluster_budget = _BATCH_INPUT_TOKEN_BUDGET / n
    cap = int(per_cluster_budget / _APPROX_TOKENS_PER_ARTICLE)
    return max(_BATCH_MIN_ARTICLES_PER_CLUSTER, min(_MAX_SUMMARY_ARTICLES, cap))


def _schedule_chunks(records: list, schedule: list[int] = _SUMMARY_BATCH_SCHEDULE) -> list[list]:
    """Chunk `records` (cache-MISS clusters, already in rank order) by consuming
    `schedule` sizes IN ORDER. After the schedule is exhausted the LAST size
    repeats (so an unexpectedly large miss set still packs into full-width tail
    batches). Cached clusters are absent from `records`, so a cache-heavy run
    simply packs the remaining misses into the next group's size."""
    chunks: list[list] = []
    i = 0
    si = 0
    n = len(records)
    while i < n:
        size = schedule[si] if si < len(schedule) else schedule[-1]
        size = max(1, size)
        chunks.append(records[i:i + size])
        i += size
        si += 1
    return chunks


# --- batch prompt assembly ------------------------------------------------
# Reuse the SINGLE-cluster template's TASK 1-7 block verbatim as the one source
# of truth for the editorial task rules; only the wrapper (multi-story delimiters
# + JSON-array output spec) differs. Sliced once at module load.
_TASKS_START_IDX = _USER_PROMPT_TEMPLATE.find("TASK 1 —")
_TASKS_END_IDX = _USER_PROMPT_TEMPLATE.find("Return JSON only", _TASKS_START_IDX)
_BATCH_TASKS_BLOCK = _USER_PROMPT_TEMPLATE[_TASKS_START_IDX:_TASKS_END_IDX].rstrip()
if _BATCH_TASKS_BLOCK.endswith("---"):
    _BATCH_TASKS_BLOCK = _BATCH_TASKS_BLOCK[:-3].rstrip()

_BATCH_SEPARATION_RULE = (
    "ABSOLUTE SEPARATION RULE: treat every story in complete isolation. A fact, "
    "name, number, figure, quote, date, or place from one story must NEVER appear "
    "in another story's output. Each story's brief is grounded ONLY in that "
    "story's own ARTICLES. Never merge, compare, or cross-reference two stories. "
    "If two stories look related, they are still separate: keep them separate."
)


def _build_batch_story_block(articles: list[dict], title: str | None,
                             k: int, cap: int) -> str:
    """Render ONE delimited story block for the batch prompt. Applies the same
    on-topic member filter as the single path, then a stratified selection capped
    at `cap` articles (graduated depth). All four line builders receive the SAME
    selected list so the [n] SOURCE NAMES indices align with the ARTICLES block.
    Thin clusters get a per-story length relaxation note (the shared TASK text
    can't be per-story edited)."""
    summ = _filter_ontopic_articles(articles, cluster_title=title)
    selected = _select_articles_for_summary(summ, cap)
    dominant = _build_dominant_topic_line(selected, title)
    context = _build_context_line(selected)
    names = _build_source_names_line(selected)
    block = _build_articles_block(selected, max_articles=cap)

    parts = [f"===== STORY {k} =====", ""]
    if dominant:
        parts.append(dominant.rstrip("\n"))
    parts.append(context.rstrip("\n"))
    if names:
        parts.append(names.rstrip("\n"))
    if len(selected) < _THIN_CLUSTER_ARTICLES:
        parts.append(
            f"NOTE: STORY {k} has limited source material; a 100 to 250 word brief "
            f"is acceptable for THIS story only (do not pad to reach 200)."
        )
    parts.append("ARTICLES:")
    parts.append(block)
    parts.append("")
    return "\n".join(parts)


def _build_batch_prompt(story_blocks: list[str], n: int) -> str:
    """Assemble the full multi-story prompt: separation-first header, the N
    delimited story blocks, the shared TASK 1-7 rules, and a JSON-array output
    spec keyed by story index. String-concatenated (not str.format) so the JSON
    braces in the output spec need no escaping."""
    header = (
        f"You are given {n} SEPARATE news stories below, each delimited by a "
        f'"===== STORY k =====" banner and running until the next banner. For '
        f"EACH story, INDEPENDENTLY perform the full analysis described in the "
        f"TASKS section that follows the stories.\n\n"
        f"{_BATCH_SEPARATION_RULE}\n\n"
    )
    stories = "\n".join(story_blocks)
    tail = (
        "\n===== END OF STORIES =====\n\n"
        "TASKS (apply INDEPENDENTLY to every story above, using ONLY that "
        "story's own ARTICLES):\n\n"
        + _BATCH_TASKS_BLOCK
        + "\n\n---\n\n"
        "Return JSON only. No markdown fences. No text outside the JSON object. "
        f"Return a single JSON object with a \"stories\" array holding EXACTLY {n} "
        "entries, one per story, in the SAME ORDER as the stories above. Each "
        "entry carries its story number as \"index\" plus the seven fields:\n\n"
        '{"stories": [{"index": 1, "headline": "...", "summary": "...", '
        '"consensus": ["..."], "divergence": ["..."], "editorial_importance": N, '
        '"story_type": "...", "has_binding_consequences": true/false}, ...]}'
    )
    return header + stories + tail


def _extract_batch_entries(raw: dict, n: int) -> list[dict | None]:
    """Split a batched JSON response into an ordered list of N per-story entries
    (None where a story is missing). Tolerant of shape drift: prefers a
    "stories"/"results"/"summaries" array (mapping each entry by its explicit
    1-based "index" when present, else by array position), and falls back to
    numeric / "story_k" top-level keys. A missing story yields None so the caller
    can retry it rather than silently dropping a card."""
    out: list[dict | None] = [None] * n
    if not isinstance(raw, dict):
        return out
    seq = None
    for key in ("stories", "results", "summaries", "briefs"):
        if isinstance(raw.get(key), list):
            seq = raw[key]
            break
    if seq is not None:
        for pos, entry in enumerate(seq):
            if not isinstance(entry, dict):
                continue
            idx = entry.get("index")
            if isinstance(idx, bool):
                idx = None
            if isinstance(idx, int) and 1 <= idx <= n:
                out[idx - 1] = entry
            elif pos < n and out[pos] is None:
                out[pos] = entry
        return out
    # Fallback: object keyed by "1".."N" or "story_1".. / "STORY 1"..
    for k in range(1, n + 1):
        for key in (str(k), f"story_{k}", f"story{k}", f"STORY {k}", f"story {k}"):
            v = raw.get(key)
            if isinstance(v, dict):
                out[k - 1] = v
                break
    return out


def _tpm_wait(window: list[tuple[float, int]], need: int) -> None:
    """Rolling-60s input-token pacer. `window` is a shared list of (sent_at,
    input_tokens); before sending a request needing `need` input tokens, prune
    entries older than 60s and sleep until the window plus `need` fits under
    _TPM_SAFE_CEILING, so no 60s span's input tokens breach the 250K TPM limit.
    Then record this send. Real runtime only sleeps on genuinely large back-to-
    back batches; small/spaced calls never wait (tests stay instant)."""
    import time
    now = time.time()
    window[:] = [(t, tok) for (t, tok) in window if now - t < 60.0]
    guard = 0
    while window and sum(tok for _, tok in window) + need > _TPM_SAFE_CEILING and guard < 120:
        oldest_t = window[0][0]
        sleep_for = 60.0 - (now - oldest_t) + 0.05
        if sleep_for > 0:
            time.sleep(sleep_for)
        now = time.time()
        window[:] = [(t, tok) for (t, tok) in window if now - t < 60.0]
        guard += 1
    window.append((time.time(), need))


def _send_one_batch(records: list[dict], model: str | None,
                    prefer_provider: str | None,
                    tpm_window: list) -> tuple[dict[str, dict], list[dict]]:
    """Send EXACTLY ONE LLM request for `records` (each {cid, articles, title,...})
    and return (results_by_cid, failed_records). A solo batch uses the proven
    single-cluster path (full template, 25 articles); a multi-story batch uses the
    batched prompt. Graduated per-cluster article depth keeps the request under
    the input-token ceiling (depth is shrunk once, never split into more requests,
    so the flash request count stays fixed by the schedule). Missing / invalid
    per-story entries are returned as failures for the caller's bounded retry."""
    if not records:
        return {}, []

    # CSAM GATE (P0 legal): partition out any CSAM cluster BEFORE it can enter a
    # batch prompt (its article bodies must never be sent to the LLM). Each
    # blocked cluster gets a forced headline+sources-only (empty-summary) result;
    # the remaining clean records proceed to the LLM as normal.
    csam_results: dict[str, dict] = {}
    clean_records: list[dict] = []
    for rec in records:
        if _cluster_is_csam(rec.get("title"), rec.get("articles") or []):
            print(f"  [csam-gate] story {rec.get('cid')} blocked from batch "
                  f"(headline + sources only)")
            csam_results[rec["cid"]] = _csam_blocked_result(
                rec.get("title"), rec.get("articles") or [])
        else:
            clean_records.append(rec)
    records = clean_records
    if not records:
        return csam_results, []

    # Solo: the lead stories get the single-cluster path unchanged (deepest
    # sourcing, most-proven prompt). Still exactly one request.
    if len(records) == 1:
        rec = records[0]
        _tpm_wait(tpm_window, _SOLO_INPUT_TOKEN_EST)
        r = summarize_cluster(rec["articles"], model=model,
                              prefer_provider=prefer_provider,
                              cluster_title=rec.get("title"))
        got = {rec["cid"]: r} if r else {}
        got.update(csam_results)
        return got, ([] if r else [rec])

    n = len(records)
    cap = _batch_article_cap(n)
    story_blocks = [
        _build_batch_story_block(r["articles"], r.get("title"), i + 1, cap)
        for i, r in enumerate(records)
    ]
    prompt = _build_batch_prompt(story_blocks, n)
    input_est = _estimate_tokens(prompt) + len(_SYSTEM_INSTRUCTION) // _APPROX_CHARS_PER_TOKEN

    # Ceiling guard: shrink per-cluster article depth (ONE rebuild) rather than
    # splitting into more requests, so the schedule's flash request count holds.
    if input_est > _BATCH_TOKEN_CEILING and cap > _BATCH_MIN_ARTICLES_PER_CLUSTER:
        shrunk = max(_BATCH_MIN_ARTICLES_PER_CLUSTER,
                     int(cap * (_BATCH_TOKEN_CEILING / input_est)))
        if shrunk < cap:
            cap = shrunk
            story_blocks = [
                _build_batch_story_block(r["articles"], r.get("title"), i + 1, cap)
                for i, r in enumerate(records)
            ]
            prompt = _build_batch_prompt(story_blocks, n)
            input_est = (_estimate_tokens(prompt)
                         + len(_SYSTEM_INSTRUCTION) // _APPROX_CHARS_PER_TOKEN)

    max_out = min(65000, 8000 + 4500 * n)
    _tpm_wait(tpm_window, input_est)
    result, label = _smart_generate_json(
        prompt, system_instruction=_SYSTEM_INSTRUCTION,
        max_output_tokens=max_out, model=model, prefer_provider=prefer_provider,
    )
    if not result:
        return dict(csam_results), list(records)

    entries = _extract_batch_entries(result, n)
    got: dict[str, dict] = {}
    failed: list[dict] = []
    for i, rec in enumerate(records):
        entry = entries[i] if i < len(entries) else None
        validated = (_finalize_cluster_result(entry, rec["articles"], label)
                     if entry else None)
        if validated:
            got[rec["cid"]] = validated
        else:
            failed.append(rec)
    got.update(csam_results)
    return got, failed


def _run_summary_batches(records: list[dict],
                         prefer_provider: str | None = "gemini") -> dict[str, dict]:
    """Summarize all cache-MISS clusters (in rank order) via the graduated
    schedule, entirely on gemini-2.5-flash (flash-lite is the automatic overflow
    inside _smart_generate_json when flash's daily cap is spent). Returns a dict
    cid -> validated summary result.

    Flash request budget is FIXED by the schedule (at most len(schedule) requests
    for a full miss run); it never inflates on failure. Stories the batched JSON
    omits or that fail validation are collected and retried ONCE on flash-lite in
    at most _MAX_OVERFLOW_RETRY_REQUESTS requests (protecting the shared flash
    20/day), never rule-based. Anything still unresolved keeps its prior summary
    and is picked up by the floor pass / next run."""
    results: dict[str, dict] = {}
    if not records:
        return results
    tpm_window: list[tuple[float, int]] = []
    overflow: list[dict] = []

    for chunk in _schedule_chunks(records):
        if calls_remaining() <= 0:
            overflow.extend(chunk)   # flash budget spent — divert to flash-lite
            continue
        got, failed = _send_one_batch(chunk, GEMINI_FLASH_MODEL,
                                      prefer_provider, tpm_window)
        results.update(got)
        overflow.extend(failed)

    if overflow:
        results.update(_retry_overflow(overflow, prefer_provider, tpm_window))
    return results


# Cap the per-overflow-group cluster count so a group never needs deeper packing
# than a normal tail batch. 10 mirrors the schedule's max group size.
_MAX_OVERFLOW_GROUP_CLUSTERS = 10


def _pack_overflow(overflow: list[dict], max_requests: int) -> list[list[dict]]:
    """Pack failed stories into at most `max_requests` groups (each still bounded
    by _batch_article_cap depth). Fewer, fuller groups so the retry spends the
    minimum number of requests."""
    if not overflow:
        return []
    import math
    groups = min(max_requests,
                 max(1, math.ceil(len(overflow) / _MAX_OVERFLOW_GROUP_CLUSTERS)))
    size = max(1, math.ceil(len(overflow) / groups))
    return [overflow[i:i + size] for i in range(0, len(overflow), size)]


def _retry_overflow(overflow: list[dict], prefer_provider: str | None,
                    tpm_window: list) -> dict[str, dict]:
    """BOUNDED retry for stories the flash batches missed. Spends flash-lite
    (model=None -> flash-lite, its own 20/day), NOT more flash, in at most
    _MAX_OVERFLOW_RETRY_REQUESTS requests. Never rule-based; unresolved stories
    keep their prior summary (the floor pass guarantees display safety)."""
    results: dict[str, dict] = {}
    if not overflow:
        return results
    print(f"  [batch] {len(overflow)} story(ies) missing from flash batches — "
          f"bounded flash-lite retry (<= {_MAX_OVERFLOW_RETRY_REQUESTS} requests)")
    for chunk in _pack_overflow(overflow, _MAX_OVERFLOW_RETRY_REQUESTS):
        if calls_remaining() <= 0:
            break
        # model=None routes to flash-lite only (no flash spend on the retry).
        got, _failed = _send_one_batch(chunk, None, prefer_provider, tpm_window)
        results.update(got)
    return results


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
        over_cap_s = sum(1 for wc in summary_lens if wc > _SUMMARY_WORD_CAP + 5)
        print(f"  Headline avg {avg_h:.1f} words, "
              f"{out_of_range_h}/{len(headline_lens)} out of 8-12 range")
        print(f"  Summary avg {avg_s:.1f} words, "
              f"{over_cap_s}/{len(summary_lens)} over the {_SUMMARY_WORD_CAP}-word cap")

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


def _store_cluster_summary(supabase, cid: str, result: dict, h: str,
                           metrics: dict) -> None:
    """Persist one summarize result to story_clusters + record it in `metrics`.
    Shared by the batched write loop so the update payload (title, hard-capped
    summary, content-hash, tier from the provider that answered, consensus /
    divergence / editorial fields) is identical to the pre-batch inline path."""
    update_payload = {
        "title": result["headline"],
        # Storage-boundary hard cap (runaway guard). summarize/finalize already
        # trim (no-op here); wrapping the stored value guarantees the invariant
        # regardless of which path produced result.
        "summary": _trim_summary_to_word_cap(result["summary"]),
        "summary_article_hash": h,
        # Stamp the tier that ACTUALLY answered (migration 063): 'flash' for
        # gemini-2.5-flash, 'flash-lite' when a batch fell back to flash-lite
        # (flash's daily cap spent) so the next run retries the flash upgrade.
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


def summarize_top50_after_rerank(supabase, edition: str = "world", limit: int = 50,
                                 prefer_provider: str | None = "gemini",
                                 flash_top_n: int = 10,
                                 force_resummarize: bool = False) -> dict:
    """
    Post-rerank summarization for the final feed top N — BATCHED (2026-08-11).

    Reads the top-N clusters by rank_{edition} (rank DESC), fetches their article
    membership, and summarizes every cache MISS on gemini-2.5-flash in GRADUATED
    BATCHES (_SUMMARY_BATCH_SCHEDULE): the lead stories get solo / small batches,
    the tail packs denser. Batching drops the whole top-50 from ~50 requests to
    ~8, so it fits inside flash's shared 20-requests/DAY free-tier cap (the binding
    limit; TPM has huge headroom). flash-lite is used ONLY as overflow — the
    automatic flash → flash-lite fallback inside _smart_generate_json when flash's
    daily cap is spent, plus a bounded flash-lite retry for stories a batch omits
    (never rule-based). See the _SUMMARY_BATCH_SCHEDULE block for the request-budget
    reasoning.

    Cache logic (upgrade-aware, migration 063): a cluster is a cache HIT when its
    article-membership hash is unchanged AND its stored summary_tier is 'sonnet'
    or 'flash' (already flash-quality); a legacy 'flash-lite' row is a MISS so it
    is regenerated / UPGRADED to flash. force_resummarize bypasses the cache.

    `flash_top_n` is retained for signature compatibility but no longer selects a
    tier band: all summaries now target flash (the schedule + shared-budget math
    make a per-story tier split unnecessary).

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
        "trimmed_cached": 0,
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
            .select("id, title, content_type, source_count, "
                    "summary_article_hash, summary_tier, summary")
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
                .select("id, name, tier, political_lean_baseline")
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
        # Drives the stratified lean-spread selection of prompt articles.
        art.setdefault("source_lean_baseline", src.get("political_lean_baseline", ""))

    # `rows` is ordered by rank_{edition} DESC. Window accounting mirrors the
    # homepage: only rows with source_count >= 3 occupy display slots, and we
    # stop once `limit` displayed slots are covered. Cache HITS are handled
    # inline (below); cache MISSES are COLLECTED in rank order and summarized in
    # graduated BATCHES on gemini-2.5-flash (_run_summary_batches) so the whole
    # displayed top-50 fits inside flash's shared 20-requests/DAY cap.
    misses: list[dict] = []   # {cid, articles, title, hash} in rank order
    window_used = 0
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

        h = _content_hash(articles)
        # Cache: every displayed summary now targets flash quality (all batches
        # run on gemini-2.5-flash), so a prior 'sonnet'/'flash' summary of
        # unchanged membership is a hit; a legacy 'flash-lite' row is a MISS so it
        # is UPGRADED to flash. force_resummarize (editorial re-run) bypasses the
        # cache entirely.
        if (not force_resummarize
                and h == row.get("summary_article_hash")
                and row.get("summary_tier") in ("sonnet", "flash")):
            metrics["cached"] += 1
            # Belt-and-suspenders: a summary cached from BEFORE the runaway cap
            # existed (or any over-cap stored value from any path) never re-runs
            # the trim, because a cache hit skips regeneration. Deterministically
            # trim an over-cap cached summary in place here: NO LLM call, and the
            # cache KEY (summary_article_hash + summary_tier) is unchanged, so
            # cache semantics are preserved. Only the summary text is corrected.
            cached_summary = (row.get("summary") or "").strip()
            if cached_summary and len(cached_summary.split()) > _SUMMARY_WORD_CAP:
                trimmed = _trim_summary_to_word_cap(cached_summary)
                if trimmed and trimmed != cached_summary:
                    try:
                        supabase.table("story_clusters").update(
                            {"summary": trimmed}
                        ).eq("id", cid).execute()
                        metrics["trimmed_cached"] += 1
                    except Exception as e:
                        print(f"  [warn] summarize_top50_after_rerank: cached-summary "
                              f"trim write failed for {cid}: {e}")
            continue

        misses.append({"cid": cid, "articles": articles,
                       "title": row.get("title"), "hash": h})

    # Batched flash summarization of every cache miss, in rank order (the lead
    # stories get solo / small batches, the tail packs denser — see the graduated
    # _SUMMARY_BATCH_SCHEDULE). Flash request count is fixed by the schedule;
    # failures retry on flash-lite (bounded), never rule-based.
    if misses:
        batch_results = _run_summary_batches(misses, prefer_provider=prefer_provider)
        for m in misses:
            result = batch_results.get(m["cid"])
            if not result:
                # No LLM summary this run (parse miss survived the bounded
                # retry, or flash+flash-lite both spent). Keep the prior summary;
                # the floor pass (8d.6) guarantees the card is never a raw excerpt.
                metrics["failed"] += 1
                continue
            _store_cluster_summary(supabase, m["cid"], result, m["hash"], metrics)

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
        needs = _floor_needs_summary(row.get("summary"), row.get("summary_tier"),
                                     _is_raw_excerpt)
        # Op-eds normally preserve their original voice, but a DISPLAYED op-ed
        # whose summary is null/empty/raw would render BLANK on the card, which is
        # worse than a clean rule-based summary. So skip an op-ed only when its
        # summary is already display-safe; otherwise regenerate it like any card.
        if (row.get("content_type") or "").lower() == "opinion" and not needs:
            continue
        if not needs:
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

    # Backfill source_name + tier + lean baseline so a re-summarize gets proper
    # attribution and the stratified lean-spread article selection.
    src_ids = sorted({a.get("source_id") for a in articles_by_id.values() if a.get("source_id")})
    src_info_by_id: dict[str, dict] = {}
    for i in range(0, len(src_ids), 200):
        batch = src_ids[i:i + 200]
        try:
            src_res = (
                supabase.table("sources")
                .select("id, name, tier, political_lean_baseline")
                .in_("id", batch).execute()
            )
            for s in (src_res.data or []):
                src_info_by_id[s["id"]] = s
        except Exception:
            continue
    for art in articles_by_id.values():
        src = src_info_by_id.get(art.get("source_id") or "", {})
        art.setdefault("source_name", src.get("name", ""))
        art.setdefault("tier", src.get("tier", ""))
        art.setdefault("source_lean_baseline", src.get("political_lean_baseline", ""))

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

        # CSAM GATE (P0 legal): a CSAM cluster renders headline + sources ONLY.
        # Never rebuild a body from the member article text (which would surface
        # the abuse description on the card) and never queue it for the LLM
        # upgrade. Force the stored summary to "" and move on.
        if _cluster_is_csam(title, articles):
            print(f"  [csam-gate] floor: blanking summary for {cid} "
                  f"(headline + sources only)")
            try:
                supabase.table("story_clusters").update(
                    {"summary": ""}).eq("id", cid).execute()
            except Exception as e:
                print(f"  [warn] ensure_top50_summary_floor: CSAM blank write "
                      f"failed for {cid}: {e}")
            continue

        prior_summary = (row.get("summary") or "").strip()
        prior_was_raw = bool(prior_summary) and _is_raw_excerpt(prior_summary)

        clean_title = (normalize_headline(title) or title).strip()
        cleaned_title_by_id[cid] = clean_title or title
        if _generate_cluster_summary is not None and articles:
            clean_summary = _generate_cluster_summary(articles, clean_title or title)
        else:
            clean_summary = sanitize_summary(row.get("summary", "") or "")
        clean_summary = (clean_summary or "").strip()

        # Phase-3 hygiene on the rule-based text too (same chain as the LLM path):
        # near-dup / unknown-padding / ungrounded-age / terminal-restatement drops
        # then a hard <= 90-word trim. Ages are grounded against the member text.
        if clean_summary:
            clean_summary = _apply_summary_postchecks(
                clean_summary, _concat_source_text(articles)
            ).strip()
            # P0 defamation guard on the rule-based text too: drop an
            # unattributed reputational-harm / criminal claim a member excerpt
            # may carry, so the deterministic floor never surfaces one either.
            clean_summary, _floor_defam = _strip_unattributed_reputational_claims(
                clean_summary)
            if _floor_defam:
                print(f"  [defamation-guard] floor dropped unattributed "
                      f"reputational claim(s) for {cid}: {_floor_defam}")
            clean_summary = clean_summary.strip()

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
                supabase.table("sources")
                .select("id, name, tier, political_lean_baseline")
                .in_("id", batch).execute()
            )
            for s in (src_res.data or []):
                src_info_by_id[s["id"]] = s
        except Exception:
            continue
    for art in articles_by_id.values():
        src = src_info_by_id.get(art.get("source_id") or "", {})
        art.setdefault("source_name", src.get("name", ""))
        art.setdefault("tier", src.get("tier", ""))
        art.setdefault("source_lean_baseline", src.get("political_lean_baseline", ""))

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
            # Storage-boundary hard cap (no-op on summarize_cluster's already-
            # trimmed output; guarantees the invariant on the flash top-10).
            "summary": _trim_summary_to_word_cap(result["summary"]),
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


# ---------------------------------------------------------------------------
# P0 legal audit (read-only). Runs the defamation post-check + CSAM gate over
# the STORED summaries of today's displayed feed and reports every offending
# cluster. Never mutates the DB.
# ---------------------------------------------------------------------------
def audit_p0_legal(supabase, edition: str = "world", limit: int = 50) -> dict:
    """Read-only report over the displayed top-`limit` clusters. For each cluster
    whose STORED summary (a) has a sentence the defamation post-check would drop,
    or (b) is CSAM-topic, print the cluster title and the exact offending
    sentence(s). Returns {defamation: [...], csam: [...]} for programmatic use."""
    rank_col = f"rank_{edition.replace('-', '_')}"
    findings = {"defamation": [], "csam": []}
    try:
        res = (
            supabase.table("story_clusters")
            .select("id, title, summary, source_count")
            .contains("sections", [edition])
            .order(rank_col, desc=True)
            .limit(60)
            .execute()
        )
    except Exception as e:
        print(f"  [audit] fetch failed: {e}")
        return findings

    rows = [r for r in (res.data or []) if (r.get("source_count") or 0) >= 3][:limit]
    print(f"\n=== P0 LEGAL AUDIT: edition={edition}, {len(rows)} displayed clusters ===")
    for r in rows:
        title = (r.get("title") or "").strip()
        summary = r.get("summary") or ""
        _cleaned, dropped = _strip_unattributed_reputational_claims(summary)
        is_csam = is_csam_topic(title) or is_csam_topic(summary)
        if dropped:
            findings["defamation"].append({"id": r["id"], "title": title,
                                           "sentences": dropped})
            print(f"\n[DEFAMATION] {title!r}")
            for s in dropped:
                print(f"    offending: {s!r}")
        if is_csam:
            findings["csam"].append({"id": r["id"], "title": title})
            print(f"\n[CSAM] {title!r}")
    if not findings["defamation"] and not findings["csam"]:
        print("  clean: no defamation drops, no CSAM matches.")
    print("=== END AUDIT ===\n")
    return findings


if __name__ == "__main__":
    # Offline self-test for the P0 defamation post-check. Proves the live Duwaji
    # case is dropped (unattributed) and an attributed version is kept.
    _duwaji = ("Rama Duwaji celebrated the October 7 terror attacks. "
               "The city council met on Tuesday to discuss the budget.")
    _cleaned, _dropped = _strip_unattributed_reputational_claims(_duwaji)
    assert len(_dropped) == 1, f"expected 1 drop, got {_dropped}"
    assert "celebrated the October 7 terror attacks" in _dropped[0]
    assert "celebrated the October 7 terror attacks" not in _cleaned
    assert "city council met on Tuesday" in _cleaned

    _attributed = ("Rama Duwaji celebrated the October 7 terror attacks, "
                   "according to the New York Post. "
                   "The city council met on Tuesday to discuss the budget.")
    _cleaned2, _dropped2 = _strip_unattributed_reputational_claims(_attributed)
    assert not _dropped2, f"attributed sentence must be kept, dropped {_dropped2}"
    assert "New York Post" in _cleaned2

    # A quoted claim is also kept (quote counts as attribution).
    _quoted = 'The mayor said the suspect "is a terrorist" during the briefing.'
    _c3, _d3 = _strip_unattributed_reputational_claims(_quoted)
    assert not _d3, f"quoted/attributed claim must be kept, dropped {_d3}"

    # CSAM topic detection.
    assert is_csam_topic("Police seize child sexual abuse material from suspect")
    assert is_csam_topic("Report describes a sexually explicit video involving minors")
    assert not is_csam_topic("Senate passes infrastructure bill after weekend vote")

    print("cluster_summarizer P0 self-test: OK")
