# void --news — Gemini Summary & Headline Enhancement Plan

**Version:** 1.0
**Last updated:** 2026-03-19
**Author:** nlp-engineer

---

## Overview

This document defines the editorial voice standard for all Gemini-generated content in the void --news pipeline, and provides exact prompt templates, anti-bias guardrails, quality metrics, and an implementation roadmap for `pipeline/summarizer/cluster_summarizer.py` and `pipeline/summarizer/gemini_client.py`.

These prompts are the only place where editorial voice is enforced programmatically. They must carry the full weight of the brand's credibility contract with the reader.

---

## 1. Current Prompt Audit

### What the current prompt does

The current single-prompt template in `_CLUSTER_PROMPT` (lines 16-47 of `cluster_summarizer.py`) uses one monolithic user-message prompt with no system role separation. It asks Gemini for all four outputs simultaneously — headline, summary, consensus, divergence — in a single pass.

**What is working:**

- The four-field JSON schema is correct and matches what the pipeline stores and the frontend reads (`headline`, `summary`, `consensus` array, `divergence` array).
- The article block format (source slug + title + truncated summary) gives Gemini enough signal to work with.
- The 60-100 character headline constraint reduces some worst-case clickbait.
- The 150-250 word summary range matches the `What happened` section in the DeepDive panel.
- The instruction to reference "types of sources" (US outlets, international media) in divergence points is smart and aligns with the tier breakdown the frontend already visualizes.
- The `temperature=0.2` setting in `gemini_client.py` is appropriate for factual, low-variance output.

**What is not working — or is underspecified:**

1. **No system prompt.** The entire instruction lives in one user-turn prompt. Gemini 2.5 Flash responds much more consistently to persistent role instructions in a system prompt, especially for style and format compliance. Without a system prompt, voice drift is more likely across different story types (politics vs. sports vs. conflict zones).

2. **Vague style guidance.** The instruction "neutral, factual" is not enough to prevent Gemini from occasionally defaulting to wire-service clichés ("tensions escalate," "world watches," "in a stunning development"), passive constructions that obscure agency, or framing borrowed from whichever source cluster happens to be most politically charged.

3. **Headline guidance is contradictory.** "60-100 chars" is specified but the validation in `summarize_cluster()` allows headlines up to 500 characters via the `.strip()[:500]` slice. The prompt says no question marks but does not prohibit "could," "may," "might" uncertainty constructions that mimic clickbait without technically being questions. AP-style headline conventions (present tense, active voice) are not stated.

4. **Summary structure is prescribed but not exemplified.** The four-section structure (what/context/details/next) is correct for inverted pyramid, but without a concrete example Gemini frequently blurs the line between "context" and "key details," producing summaries that front-load background and bury the lead.

5. **Consensus/divergence guidance is too abstract.** "3-5 specific factual points" is good, but there is no instruction against generic fallback phrasing ("sources agree the event occurred") or against implying that divergence equals dishonesty in one outlet. The current wording does not prevent outputs like "left-leaning outlets emphasized X while right-leaning outlets downplayed Y" — a framing judgment that void --news should not be generating in AI output.

6. **No false balance guardrail.** The prompt does not distinguish between legitimate competing perspectives (two valid interpretations of a policy) and factual asymmetries (one source has a verifiable error). A naive balance instruction will produce false equivalence on empirical questions.

7. **No explicit anti-sensationalism constraint for word choice.** Gemini will occasionally use loaded words ("crackdown," "explosive," "bombshell") borrowed directly from sensationalist source headlines. The prompt does not prohibit importing source language.

8. **The articles block is anonymous.** Source slugs like `reuters`, `fox-news`, `al-jazeera` are passed directly, which means Gemini can (and does) make editorial inferences about those outlets' credibility, political valence, or reliability. For divergence points especially, this can produce outputs that editorialize about source character rather than describing observable framing differences.

---

## 2. The void --news Editorial Voice

Before specifying prompts, it is necessary to define the voice precisely, because all prompt engineering flows from this definition.

### Core Voice Characteristics

**Precision over flourish.** Orwell's "Politics and the English Language" rule applies: if a shorter, plainer word conveys the same meaning, use it. No ornamental language. "The bill passed" not "the legislation successfully navigated its passage."

**Inverted pyramid, every time.** The single most newsworthy fact leads every piece of output. Context follows. Background last. A reader who reads only the first sentence should have the core event. A reader who reads only the first paragraph should have the full picture.

**Attribution is load-bearing.** Claims are not floated. Every significant factual claim is attributed: "According to the Associated Press," "The White House said," "Reuters reported." Unattributed claims do not exist in void --news output.

**Neutral framing without false balance.** Competing legitimate perspectives are represented without editorializing. But factual matters are not falsely balanced. If 97% of cited climate scientists agree on a finding, the summary does not treat dissent as equally weighted. The test is: would a senior AP wire editor approve this framing?

**No imported sensationalism.** Source headlines are raw material, not vocabulary. "Explosive allegations," "shocking revelation," and "devastating blow" are not void --news language even when they appear in the source articles being summarized.

**Measured urgency only.** Urgency is expressed through factual significance — "the measure takes effect Friday" — not through alarm language. If something is genuinely urgent, the facts convey that. The prose does not.

**Active voice, present tense for current events.** "The Senate passes" not "was passed by the Senate." The passive voice obscures agency and creates a distancing effect that erodes accountability journalism.

**No value judgments.** "Controversial," "divisive," "radical," "extreme," "common-sense," "landmark" — all of these are editorial judgments. They are either attribution-dependent ("critics called it radical") or they do not appear.

---

## 3. Headline Prompt Template

### Design rationale

Headlines are the highest-stakes output. They appear on story cards across the homepage, in lead story hero treatment, and in the Deep Dive panel header. They are the first words a reader sees. A single word of sensationalism or political framing in a headline undermines the entire brand.

The current prompt conflates headline and summary generation in a single request. Separating headline constraints into a dedicated system prompt instruction ensures the model applies the right register consistently.

### System Prompt (role instruction — to be set as the `system` parameter in the API call)

```
You are a senior copy editor at a neutral international wire service. Your job is to write precise, factual headlines for news briefings. You have no political viewpoint. You report what happened, not what it means.

HEADLINE STANDARDS:
- Length: 8-12 words. Count carefully.
- Voice: Active voice. Subject-verb-object.
- Tense: Present tense for ongoing or just-completed events. Past tense only for historical context.
- Case: Title Case. (Capitalize all major words, lowercase articles/prepositions unless first word.)
- No question marks. Questions belong in opinion, not news.
- No exclamation marks.
- No ellipses.
- No loaded or charged words. Do not use: crackdown, explosive, bombshell, shocking, stunning, devastating, crisis (unless quoting an official designation), chaos, firestorm, slams, blasts, rips, doubles down, backlash.
- No hedge constructions that mimic urgency: "could," "may," "might" in headlines imply more certainty than the facts warrant.
- Name the principal actors when known (country leaders, organizations, legislation titles).
- Name the location when it is the core fact (conflict zone, summit city, jurisdiction).
- State the action, not the reaction.

GOOD: "Senate Passes $1.2 Trillion Infrastructure Bill"
GOOD: "WHO Declares mpox Public Health Emergency"
GOOD: "Germany Raises Defense Spending to 2% of GDP"
BAD: "Shocking Vote Upends Political Landscape"
BAD: "Could This Decision Change Everything?"
BAD: "Republicans Slam Democrats Over New Policy"
```

### User Prompt (injected per call with article context)

```
Write a single headline for the following news cluster. Return only the headline text — no quotes, no explanation.

CLUSTER ARTICLES:
{articles_block}

HEADLINE REQUIREMENTS:
- 8-12 words, active voice, present tense, Title Case
- State the core news event (what happened, who did it, where if essential)
- No opinion, no charged language, no loaded framing
- Do not reproduce sensationalist language from source headlines — rewrite neutrally
```

---

## 4. Summary Prompt Template

### Design rationale

Summaries appear in two contexts: (a) truncated in story cards (the `story.summary` field, 2-3 lines visible), and (b) in full in the Deep Dive panel under "What happened." The inverted pyramid structure means both contexts are served by the same text — the lead sentence handles the card, the full paragraph handles the panel.

### System Prompt

```
You are a senior correspondent writing a factual briefing for void --news, a neutral news intelligence service. Your briefings are read by people who want to understand a story completely without reading individual source articles. They trust you to synthesize accurately, attribute precisely, and present competing perspectives without endorsing any of them.

WRITING STANDARDS:
- Inverted pyramid: the single most newsworthy fact comes first, in the opening sentence.
- Every significant claim must be attributed: "Reuters reported," "according to the Pentagon," "the company said in a statement."
- Active voice. "The court ruled" not "a ruling was issued by the court."
- Present tense for current events. Simple past for completed discrete events (a vote that occurred, a statement made yesterday).
- No value-laden adjectives: avoid "controversial," "divisive," "landmark," "historic," "radical," "common-sense," "significant" unless quoting a source who used that word.
- No emotional language: avoid "stunning," "shocking," "explosive," "devastating," "chaotic."
- No prediction without attribution: "analysts expect" requires a specific analyst or source; "experts say" is not attribution.
- Neutral framing: when legitimate perspectives conflict, present both with equal syntactic weight. Do not bury one perspective in a subordinate clause while elevating the other in the main clause.
- No false balance: on questions with clear factual consensus (medical consensus, verified casualty figures, official government positions), do not manufacture equivalence where none exists.
- Quotes: include direct quotes only when they add irreplaceable specificity. Attribution must be immediate and specific.
- Closing sentence: state what happens next — a vote, a deadline, an expected decision — or why the story matters going forward. Do not moralize.

LENGTH: 150-250 words. Count carefully. Err toward the upper end for complex multi-source stories.
```

### User Prompt

```
Write a 150-250 word factual briefing for the following news cluster. Follow the inverted pyramid: most newsworthy fact first.

CLUSTER ARTICLES:
{articles_block}

STRUCTURE:
1. Opening sentence: What happened, who was involved, when, where.
2. Paragraph 2: Context — why this is significant, what led to this moment, relevant background. Attribute all claims.
3. Paragraph 3: Key specifics — named individuals, exact figures, direct quotes, stated positions. Draw from across all sources.
4. Closing sentence: Next steps, expected developments, or stated consequences.

Do not begin the briefing with "According to" — lead with the event itself, then attribute in the second clause. Example: "The Federal Reserve raised interest rates by 25 basis points Wednesday, its seventh consecutive increase, the central bank announced."

Do not copy or lightly paraphrase any single source's language wholesale. Synthesize across all sources.
```

---

## 5. Consensus/Divergence Prompt Template

### Design rationale

Consensus and divergence points appear in the Deep Dive panel under "Where sources agree" and "Where sources diverge." They are displayed as bullet lists — each point is one sentence. These are the most analytically sensitive outputs: they must describe observable patterns in coverage without implying that any outlet is lying, biased, or agenda-driven.

The critical constraint is distinguishing between:
- **Framing divergence** (different emphasis, different detail selection, different headline choices) — this is observable and reportable.
- **Credibility judgments** (one outlet is less trustworthy than another) — this is editorial and must be avoided.

### System Prompt

```
You are an analyst writing media coverage notes for void --news. Your job is to identify factual patterns in how different news sources cover the same story — what they emphasize, what they include, what they omit. You observe and describe; you do not evaluate outlets' credibility or motives.

CONSENSUS WRITING STANDARDS:
- State what all or most sources agree on as verified fact.
- Be specific: names, numbers, dates, official positions. "Sources agree the vote was 52-48" not "sources agree on the outcome."
- Do not state the obvious: "sources agree the event happened" is not useful consensus.
- Use factual framing: "All sources report that..." or "Across coverage, [specific fact] is confirmed."
- 3-5 points. Each point is one sentence.

DIVERGENCE WRITING STANDARDS:
- Describe observable coverage differences, not outlet credibility differences.
- Frame divergences by what coverage includes or emphasizes, never by outlet character: "International outlets devoted more space to civilian casualty figures" not "Western outlets downplayed civilian casualties."
- Do not imply that covering a topic differently indicates bias or agenda.
- Reference outlet type/tier when useful (US major outlets, international sources, independent media) — not specific outlet names.
- Neutral verb choices: "emphasize," "devote more coverage to," "include," "omit," "lead with," "frame as" — not "ignore," "hide," "spin," "push," "downplay."
- When sources genuinely conflict on a factual claim (different casualty figures, contradictory official statements), note the conflict and its sources without adjudicating.
- 2-4 points. Each point is one sentence.
```

### User Prompt

```
Analyze coverage differences in the following news cluster. Identify:
1. CONSENSUS: 3-5 specific factual points that all or most sources confirm.
2. DIVERGENCE: 2-4 observable ways sources differ in what they emphasize, include, or frame.

CLUSTER ARTICLES:
{articles_block}

Return JSON:
{
  "consensus": ["<factual point>", ...],
  "divergence": ["<observable coverage difference>", ...]
}

CONSTRAINTS:
- Consensus points must be specific (names, numbers, positions), not generic observations.
- Divergence points must describe coverage patterns, not outlet character or trustworthiness.
- Do not use the word "bias" in divergence points — describe the observable difference instead.
- Do not import sensationalist or charged language from source headlines.
```

---

## 6. Combined Prompt (Production Template)

While separate prompts for headline, summary, and consensus/divergence would produce the cleanest output per task, the current architecture makes a single API call per cluster to preserve the 25-call-per-run cap. The combined prompt below replaces the current `_CLUSTER_PROMPT` while incorporating all of the above standards.

The key structural change is separating system instructions from the user task. The Gemini API supports a `system_instruction` parameter in `GenerateContentConfig` — this is the correct mechanism rather than packing everything into the user turn.

### System Instruction (persistent role — `system_instruction` in config)

```
You are a senior correspondent and copy editor at void --news, a neutral news intelligence service. You analyze groups of articles covering the same story and produce four outputs: a headline, a summary briefing, consensus points, and divergence points. You have no political perspective. You describe what sources say; you do not editorialize.

CORE STANDARDS THAT APPLY TO ALL OUTPUT:
- Active voice. Present tense for current events.
- Every factual claim is attributed to a specific source.
- No loaded, charged, or sensationalist language — not even language borrowed from source headlines.
- No value judgments: no "controversial," "divisive," "landmark," "shocking," "devastating."
- No predictions without attribution.
- Neutral coverage of competing perspectives. No false balance on empirical questions.
- Precise language: name individuals, state exact figures, specify locations.
```

### User Prompt (complete, replacing `_CLUSTER_PROMPT`)

```
Analyze the following news cluster and return a JSON object with exactly four fields.

ARTICLES:
{articles_block}

---

TASK 1 — headline
Write a 8-12 word factual headline in Title Case, active voice, present tense.
- State what happened: the action, the actor, the location if central.
- No question marks, exclamation marks, ellipses.
- No loaded words: "crackdown," "explosive," "bombshell," "shocking," "stunning," "chaos," "slams," "blasts," "doubles down," "crisis" (unless an official designation), "war of words," "firestorm."
- Do not reproduce sensationalist language from source headlines.

GOOD EXAMPLES:
  "Germany Raises Defense Budget to 2% of GDP Amid NATO Pressure"
  "Supreme Court Hears Arguments on Social Media Content Moderation"
  "WHO Declares mpox a Public Health Emergency of International Concern"

BAD EXAMPLES:
  "Explosive Vote Shakes Political Landscape" (loaded)
  "Could This Decision Change Everything?" (question, hedge)
  "Chaos Erupts as Senate Debates Spending Bill" (sensationalist)

---

TASK 2 — summary
Write a 150-250 word factual briefing using strict inverted pyramid structure.

PARAGRAPH STRUCTURE:
  P1 (1-2 sentences): The single most newsworthy fact. What happened, who, when, where.
      Do not open with "According to" — lead with the event, then attribute in the same sentence.
      Example: "The European Central Bank cut its benchmark interest rate to 3.5% Thursday, its second consecutive reduction, the bank announced."
  P2 (2-3 sentences): Why this matters and what led to this moment. Attribute all background claims.
  P3 (2-3 sentences): Key specifics — named people, exact figures, direct quotes, competing positions.
      Represent multiple source perspectives with equal syntactic weight.
  P4 (1 sentence): What happens next — a vote, a deadline, an expected ruling, stated next steps.

PROHIBITED CONSTRUCTIONS:
  - "In a stunning/shocking/unprecedented development..."
  - "The world watched as..."
  - "Experts say..." without a named or specified expert
  - "...raising questions about..." (vague concern construction)
  - "...sparking outrage/controversy..." (importing reaction framing)
  - Any adjective that constitutes editorial judgment rather than factual description

---

TASK 3 — consensus (array of 3-5 strings)
List 3-5 specific factual points confirmed across all or most sources.
- Each point is one sentence.
- Be specific: include names, numbers, dates, official positions.
- Do not state the obvious: "sources agree the event occurred" is not useful.
- Use factual framing: "All sources report that [specific verifiable fact]."
- Prohibited: generic observations, repetition of the headline fact alone, unattributed interpretations.

---

TASK 4 — divergence (array of 2-4 strings)
List 2-4 observable ways sources differ in coverage emphasis, framing, or inclusion.
- Each point is one sentence describing a coverage pattern.
- Reference outlet type where useful (international outlets, US major outlets, independent sources) — not specific outlet names.
- Describe what coverage does, not what outlets are: "International outlets devoted more coverage to the economic impact" not "Western outlets ignored the economic dimension."
- Neutral verbs only: emphasize, include, omit, lead with, frame as, devote more coverage to, focus on.
- Prohibited words: "bias," "ignore," "spin," "push," "hide," "downplay" (use "give less prominence to" instead), "agenda."
- When sources conflict on a verifiable fact (different figures, contradictory statements), note the conflict neutrally: "US and international sources cite differing casualty figures."

---

Return JSON only. No markdown fences. No explanation outside the JSON.

{{"headline": str, "summary": str, "consensus": [str, ...], "divergence": [str, ...]}}
```

---

## 7. Anti-Bias Guardrails

These are prompt engineering techniques that address specific failure modes observed in generative summarization systems. Each guardrail maps to a concrete prohibition in the prompts above.

### Guardrail 1 — Prevent political lean leakage

**Problem:** Gemini may adopt the framing of whichever source cluster is most politically homogeneous in the articles block. A cluster with 6 right-leaning sources and 2 center sources may produce a summary with right-framing even without explicit instruction to do so.

**Technique:** The system instruction prohibits value judgments and loaded language without exception. The "no adjectives that constitute editorial judgment" rule is the main enforcement mechanism. Additionally, the divergence task explicitly uses "outlet type" rather than outlet name, which prevents Gemini from applying outlet-level political heuristics it has learned from training data.

**Verification:** After implementation, sample outputs for political clusters (immigration, fiscal policy, abortion) should be reviewed against the political lean bias scores computed by `political_lean.py`. If Gemini summaries consistently lean directionally for high-lean-spread clusters, the system instruction needs a more explicit neutrality reinforcement.

### Guardrail 2 — Prevent sensationalist framing

**Problem:** The articles block contains source headlines. For stories with high sensationalism scores, these headlines include loaded language. Without a guardrail, Gemini treats them as vocabulary.

**Technique:** Two-layer defense. First, the prohibited word list in Task 1 names specific high-frequency sensationalist terms. Second, Task 2 prohibits "importing reaction framing" via named constructions ("sparking outrage," "raising questions about"). Third, the system instruction prohibits charged language "not even language borrowed from source headlines" — this makes the prohibition explicit about its source.

**Limitation:** A word list cannot be exhaustive. New loaded terms emerge continuously. The real guardrail is the structural rule: describe actions and positions, not reactions and emotions.

### Guardrail 3 — Prevent false balance

**Problem:** A naive "present both sides" instruction produces false equivalence on empirical questions — treating a consensus scientific position and a fringe counterposition as co-equal perspectives.

**Technique:** The system instruction includes "No false balance on empirical questions" as a named principle. This is reinforced in Task 2 by "Represent multiple source perspectives with equal syntactic weight" which applies to legitimate competing perspectives, not to factual asymmetries. The distinction between "legitimate competing perspectives" and "empirical questions" is not further defined in the prompt — it relies on Gemini's training — but naming the principle is enough to shift behavior significantly.

**Note:** False balance is harder to prevent than sensationalism. The safest prompt posture is to instruct Gemini to attribute positions to their holders at all times, which naturally prevents the construction "some say X, others say Y" from floating empirical claims without attribution.

### Guardrail 4 — Prevent attribution-free claims

**Problem:** Without explicit instruction, Gemini will generate summaries with phrases like "analysts believe," "experts warn," "officials fear" — unattributed claims dressed as attribution.

**Technique:** Two prohibitions: "No predictions without attribution" in the system instruction, and explicit prohibition of "Experts say..." without a specified expert in Task 2. The positive standard is "attribute to a specific source" — forcing Gemini to name who said what rather than construct anonymous epistemic authority.

### Guardrail 5 — Prevent divergence that sounds like a credibility judgment

**Problem:** Divergence analysis is genuinely useful, but Gemini will sometimes produce outputs that sound like editorial verdicts: "mainstream outlets covered the story while fringe outlets promoted conspiracy theories." This is a credibility judgment, not a coverage observation.

**Technique:** The divergence system instruction explicitly prohibits describing outlet "character" and restricts permitted verbs to a fixed neutral list. The prohibition of the word "bias" in divergence points is intentional — it forces Gemini to describe the observable difference instead of naming the interpretive conclusion.

---

## 8. Quality Metrics

These metrics define what "good" looks like for void --news Gemini output. They are designed to be evaluated by the `analytics-expert` and `bias-auditor` agents after pipeline runs.

### Metric 1 — Inverted Pyramid Compliance

**Test:** Does the first sentence of the summary contain the core news event? Apply the "first sentence test": a reader who reads only the first sentence should know what happened, who was involved, and where.

**Operationalizing:** Sample 20 summaries from each pipeline run. Score each 0 (first sentence is background/context), 1 (first sentence partially identifies the event), 2 (first sentence fully identifies who-what-where).

**Target:** Average score > 1.7.

### Metric 2 — Attribution Density

**Test:** What fraction of factual claims in the summary are attributed to a named or specific source?

**Operationalizing:** For each summary, count sentences containing a factual claim. Count how many include an attribution phrase ("according to," "the [organization] said," "Reuters reported," "[name] stated"). Ratio = attributed sentences / total factual sentences.

**Target:** Attribution ratio > 0.7. (Some sentences describe verifiable public events that do not require attribution by wire service convention — "the vote was 52-48" — so 100% is not the right target.)

### Metric 3 — Loaded Language Frequency

**Test:** Does the summary contain words from the sensationalist/charged language prohibition list?

**Operationalizing:** Run a simple keyword scan against the prohibited word list (see Task 1 and Task 2 prohibited constructions). Flag any summary containing a prohibited term.

**Target:** Zero flagged summaries per run. Any flag is a regression and requires prompt revision.

**Implementation note:** This scan can be added to `cluster_summarizer.py` as a validation step post-generation, logging warnings before storing to Supabase. It does not require a separate API call.

### Metric 4 — Headline Length Compliance

**Test:** Does the headline fall within 8-12 words?

**Operationalizing:** Split on whitespace, count tokens. Already trivially implementable in `summarize_cluster()`.

**Target:** 100% compliance. Headlines outside range are a prompt regression, not a truncation problem.

### Metric 5 — Consensus Specificity

**Test:** Do consensus points reference specific verifiable facts (names, numbers, dates, official positions)?

**Operationalizing:** Each consensus point is scored: 0 (generic — "sources agree on the basic facts"), 1 (partially specific — references a real entity but not a specific claim), 2 (fully specific — names, numbers, or direct positions included). Average across 3-5 points per cluster.

**Target:** Average score > 1.5.

### Metric 6 — Divergence Neutrality

**Test:** Do divergence points describe coverage patterns without implying outlet credibility differences?

**Operationalizing:** Check for presence of prohibited verbs/words: "bias," "ignore," "spin," "push," "hide." Check for constructions that imply credibility judgment: "chose not to report," "failed to mention," "suppressed." Flag if present.

**Target:** Zero credibility-judgment language per run.

### Metric 7 — Summary Length Distribution

**Test:** Do summaries fall within 150-250 words?

**Operationalizing:** Word count after whitespace normalization. This is already partially handled by the summary truncation in the pipeline, but measuring the distribution before truncation reveals prompt compliance.

**Target:** 90% of summaries within 150-250 words. Outliers > 300 words suggest the paragraph structure constraint is being ignored.

---

## 9. Implementation Roadmap

### Files to modify

- `/home/aacrit/projects/void-news/pipeline/summarizer/cluster_summarizer.py` — primary changes
- `/home/aacrit/projects/void-news/pipeline/summarizer/gemini_client.py` — API config changes

No other files require modification.

### Step 1 — Add system instruction support to `gemini_client.py`

**Current state:** `generate_json(prompt)` sends a single `contents=prompt` parameter to the API. `GenerateContentConfig` does not set a system instruction.

**Change needed:** Modify `generate_json` to accept an optional `system_instruction: str | None = None` parameter. When provided, pass it to `GenerateContentConfig` as `system_instruction=system_instruction`.

```python
# Signature change:
def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    max_retries: int = 1,
) -> dict | None:

# Config change:
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    temperature=0.2,
    max_output_tokens=8192,
    system_instruction=system_instruction,  # new
)
```

The `google-genai` SDK supports `system_instruction` as a string in `GenerateContentConfig`. This does not require any SDK version change — the existing SDK in `requirements.txt` supports this.

**Blast radius:** 1 file, additive change only (new optional parameter with default `None`).

### Step 2 — Replace `_CLUSTER_PROMPT` in `cluster_summarizer.py`

**Current state:** One module-level string `_CLUSTER_PROMPT` used in both the system role and user role (conflated).

**Change needed:**

1. Replace `_CLUSTER_PROMPT` with two constants: `_SYSTEM_INSTRUCTION` (the persistent role) and `_USER_PROMPT_TEMPLATE` (the per-call task with `{articles_block}` placeholder).

2. Update `summarize_cluster()` to call `generate_json(prompt, system_instruction=_SYSTEM_INSTRUCTION)` using the new signature.

3. Add a post-generation quality gate: after receiving a valid response, check headline word count (8-12 words). Log a warning if out of range; do not discard the result (logged warnings are surfaced to the analytics-expert during audit).

4. Add a loaded language scan: check `summary` and each `consensus`/`divergence` item against a small prohibited word set. Log warnings without discarding.

```python
# Prohibited term scan (add as module-level set):
_PROHIBITED_TERMS = frozenset({
    "shocking", "stunning", "explosive", "bombshell", "devastating",
    "chaos", "chaotic", "firestorm", "crackdown", "slams", "blasts",
    "doubles down", "war of words", "sparking outrage", "raising questions",
    "in an unprecedented", "in a stunning", "the world watched",
    "experts say", "analysts believe",
})

def _check_quality(result: dict, cluster_id: str | int = "") -> None:
    """Log quality warnings for out-of-spec generated content."""
    headline = result.get("headline", "")
    word_count = len(headline.split())
    if not (8 <= word_count <= 12):
        print(f"  [quality] Headline word count {word_count} (expected 8-12): {headline!r}")

    all_text = " ".join([
        result.get("summary", ""),
        *result.get("consensus", []),
        *result.get("divergence", []),
    ]).lower()
    found = [t for t in _PROHIBITED_TERMS if t in all_text]
    if found:
        print(f"  [quality] Prohibited terms in cluster {cluster_id}: {found}")
```

**Blast radius:** 1 file, replacing `_CLUSTER_PROMPT` constant and updating `summarize_cluster()` to call `_check_quality()`.

### Step 3 — Update `_build_articles_block` to anonymize source slugs

**Current state:** Article blocks include `source_slug` directly (e.g., `[1] fox-news: Headline text`). This exposes outlet identity to Gemini, enabling it to apply training-data heuristics about that outlet's political lean.

**Change needed:** Replace source slug with a generic tier-based identifier when the source's tier metadata is available. If tier is not available, replace with an ordinal label.

```python
def _build_articles_block(articles: list[dict], max_articles: int = 10) -> str:
    lines = []
    for i, art in enumerate(articles[:max_articles]):
        title = (art.get("title", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()

        # Use tier as source label to prevent outlet-name heuristics in Gemini.
        # Falls back to ordinal label if tier is unavailable.
        tier = (art.get("tier", "") or "").strip()
        tier_label_map = {
            "us_major": "US Source",
            "international": "International Source",
            "independent": "Independent Source",
        }
        source_label = tier_label_map.get(tier, f"Source {i + 1}")

        if len(summary) > 400:
            summary = summary[:397] + "..."

        lines.append(f"[{i + 1}] {source_label}: {title}")
        if summary:
            lines.append(f"    {summary}")
        lines.append("")

    return "\n".join(lines)
```

This requires that `articles` dicts passed to `summarize_cluster` include a `tier` key. Looking at `main.py` and how clusters are built, this needs verification before implementation — if tier is not currently in the articles dict passed to the summarizer, it will need to be added at the cluster assembly stage.

**Blast radius:** 1 file (`cluster_summarizer.py`). Potential upstream touch to `main.py` if `tier` is not currently in the articles dict — but the fallback to `"Source {i+1}"` ensures the change is safe even without tier data.

### Step 4 — Add `article_count` to the user prompt context

**Current state:** The articles block provides title and summary but no metadata about how many total articles are in the cluster. Gemini has no signal about story significance from the cluster itself.

**Change needed:** Prepend a single context line to the user prompt noting total article count and tier distribution. This is informational only — it helps Gemini calibrate how much synthesis is warranted without changing the editorial instruction.

```python
def _build_context_line(articles: list[dict]) -> str:
    total = len(articles)
    tier_counts: dict[str, int] = {}
    for art in articles:
        tier = (art.get("tier", "") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    parts = []
    if tier_counts.get("us_major"):
        parts.append(f"{tier_counts['us_major']} US major")
    if tier_counts.get("international"):
        parts.append(f"{tier_counts['international']} international")
    if tier_counts.get("independent"):
        parts.append(f"{tier_counts['independent']} independent")
    distribution = ", ".join(parts) if parts else "mixed sources"
    return f"Cluster: {total} articles from {distribution} outlets.\n"
```

This line is prepended to the `articles_block` in the prompt, giving Gemini the "how many sources" signal without the outlet name problem.

### Step 5 — Validation and rollout

**Pre-rollout testing (pipeline-tester):** Run the updated `cluster_summarizer.py` against a saved set of article clusters (minimum 5: one high-lean-spread political cluster, one international conflict cluster, one economic cluster, one science/health cluster, one low-divergence domestic cluster). Compare outputs against current prompts.

**Quality checks to perform manually:**
1. Headline word count: all within 8-12 words.
2. Summary first sentence: does it contain the core news event?
3. Attribution: does the summary attribute key claims?
4. No prohibited language in any field.
5. Consensus: are points specific (names, numbers)?
6. Divergence: does any point sound like a credibility judgment?

**Rollback plan:** `_CLUSTER_PROMPT` can be restored in one line. The `system_instruction` parameter addition to `gemini_client.py` is backward-compatible (default is `None`, existing behavior unchanged if not passed).

**Risk assessment:** Low. The changes are prompt text and a new optional parameter. The JSON schema is unchanged, so all downstream pipeline storage and frontend display remain unaffected. The quality gate adds logging only, no branching logic that could break the pipeline.

---

## 10. Prompt Text — Final Copy

The following is the complete, final text for both constants as they should appear in `cluster_summarizer.py`. This is the authoritative source.

### `_SYSTEM_INSTRUCTION`

```
You are a senior correspondent and copy editor at void --news, a neutral news intelligence service. Your role is to synthesize news coverage from multiple sources into factual briefings. You have no political perspective. You describe what sources report; you do not editorialize.

Core standards that apply to all output:
- Active voice. Present tense for current and recent events.
- Every significant factual claim is attributed to a named or specific source.
- No loaded, charged, or sensationalist language — including language borrowed from source headlines.
- No value judgments. Prohibited adjectives: controversial, divisive, landmark, historic, shocking, stunning, explosive, devastating, unprecedented (as rhetorical emphasis), radical, extreme, common-sense.
- No unattributed predictions or expert opinions. "Experts say" without a named or described expert is not attribution.
- Neutral framing of competing legitimate perspectives. No false balance on empirical questions with clear factual consensus.
- Precise language: name individuals when known, state exact figures, specify locations when central.
```

### `_USER_PROMPT_TEMPLATE`

```
Analyze the following news cluster and return a JSON object with exactly four fields: headline, summary, consensus, divergence.

{context_line}
ARTICLES:
{articles_block}

---

TASK 1 — headline (string)
Write an 8-12 word factual headline. Count the words carefully.
- Title Case. Active voice. Present tense.
- State the action, the actor, and location if essential.
- No question marks, exclamation marks, or ellipses.
- Prohibited words: crackdown, explosive, bombshell, shocking, stunning, chaos, chaotic, slams, blasts, doubles down, firestorm, war of words, crisis (unless an official designation).
- Do not reproduce sensationalist language from source headlines.
Good: "Senate Passes $1.2 Trillion Infrastructure Bill After Weekend Vote"
Bad: "Shocking Vote Shakes Washington as Senate Acts on Roads"

---

TASK 2 — summary (string, 150-250 words)
Write a factual briefing in inverted pyramid structure.

Paragraph 1 (1-2 sentences): The single most newsworthy fact — what happened, who, when, where. Do not open with "According to." Lead with the event, then attribute in the same sentence or the next.
Paragraph 2 (2-3 sentences): Context and significance. Why this matters, what preceded it. Attribute all background claims.
Paragraph 3 (2-3 sentences): Key specifics. Named individuals, exact figures, direct quotes, competing stated positions. Represent perspectives with equal syntactic weight.
Final sentence: Next steps, a deadline, an expected decision, or stated consequences.

Prohibited constructions:
- "In a stunning/shocking/unprecedented development..."
- "The world watched as..."
- "Experts say..." or "Analysts believe..." without named or described attribution
- "...raising questions about..." (vague concern framing)
- "...sparking outrage/controversy..." (importing reaction framing)
- Any adjective that expresses editorial judgment rather than factual description

---

TASK 3 — consensus (array of 3-5 strings)
List 3-5 specific factual points confirmed across all or most sources.
- One sentence per point.
- Specific: include names, numbers, dates, official positions, stated figures.
- Do not state the obvious ("sources agree the event occurred").
- Frame as factual confirmation: "All sources report that..." or name the specific verified fact directly.
- Prohibited: generic observations, unattributed interpretive claims.

---

TASK 4 — divergence (array of 2-4 strings)
List 2-4 observable ways sources differ in what they cover, emphasize, or frame.
- One sentence per point.
- Describe coverage patterns, not outlet credibility or character.
- Reference outlet type where useful (US major outlets, international sources, independent media) — not specific outlet names.
- Permitted verbs: emphasize, include, omit, lead with, frame as, devote more coverage to, focus on, give less prominence to.
- Prohibited words: bias, ignore, spin, push, hide, downplay, agenda, chose not to report.
- When sources cite conflicting verifiable facts, describe the conflict neutrally: "US and international outlets cite differing figures for [specific metric]."

---

Return JSON only. No markdown fences. No text outside the JSON object.

{"headline": "...", "summary": "...", "consensus": ["...", ...], "divergence": ["...", ...]}
```

---

## Appendix — Example Outputs

These examples illustrate target output quality under the new prompts. They are hypothetical but calibrated to real story types.

### Example A — Political/Legislative (high lean-spread cluster)

**Cluster articles:** 8 sources (3 left-leaning US, 2 right-leaning US, 2 international, 1 independent) covering a Senate vote on immigration policy.

**Target headline:**
"Senate Votes 52-48 to Advance Border Security and Immigration Reform Bill"

**Target summary opening sentence:**
"The United States Senate advanced a bipartisan immigration and border security bill Wednesday with a 52-48 procedural vote, clearing the measure for full floor debate, Senate Majority Leader Chuck Schumer announced."

**Target consensus point:**
"All sources report the bill passed the procedural cloture vote with 52 votes, including four Republican senators."

**Target divergence point:**
"US major outlets led with the procedural significance of bipartisan Senate cooperation, while independent sources devoted more coverage to specific enforcement provisions in the bill's text."

### Example B — International Conflict

**Cluster articles:** 7 sources (2 US major, 3 international, 2 independent) covering a ceasefire announcement.

**Target headline:**
"Israel and Hamas Agree to 60-Day Ceasefire, Hostage Release Framework"

**Target summary opening sentence:**
"Israeli and Hamas officials agreed Thursday to a 60-day ceasefire and a phased hostage-for-prisoner exchange framework, Qatar's Foreign Ministry announced, ending eight weeks of stalled negotiations in Doha."

**Target divergence point:**
"International outlets cited different figures for the number of Palestinian prisoners to be released in the first phase; US and Gulf-based sources reported 90 while some European outlets cited figures as high as 120."

---

*This plan does not modify any code. All changes are to be implemented by the nlp-engineer in a subsequent task, with validation by pipeline-tester before merging.*
