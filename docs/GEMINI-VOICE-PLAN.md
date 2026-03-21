# void --news — Gemini Voice & Editorial Intelligence

**Version:** 2.0 | **Updated:** 2026-03-21

---

## 1. Editorial Voice Definition

All Gemini output must follow these standards. The system instruction in `cluster_summarizer.py` enforces them.

**Precision over flourish.** Orwell's rule: shorter, plainer word wins. "The bill passed" not "the legislation successfully navigated its passage."

**Inverted pyramid.** Most newsworthy fact leads. Context follows. Background last.

**Attribution is load-bearing.** Every claim attributed: "Reuters reported," "the Pentagon said." No "experts say" without a named expert.

**Neutral framing, no false balance.** Competing perspectives get equal weight. Factual consensus is not falsely balanced.

**No imported sensationalism.** Source headlines are raw material, not vocabulary. Prohibited: "explosive," "shocking," "devastating," "bombshell," "crackdown," "chaos," "slams," "doubles down."

**Active voice, present tense.** "The Senate passes" not "was passed by the Senate."

**No value judgments.** "Controversial," "divisive," "landmark," "radical," "common-sense" are editorial — attribution-dependent or excluded.

---

## 2. Production Prompt Architecture

Single API call per cluster. System instruction sets role/voice. User prompt defines 7 tasks.

### System Instruction (`_SYSTEM_INSTRUCTION` in `cluster_summarizer.py`)

```
Senior correspondent and copy editor at void --news. Analyzes article clusters,
produces seven outputs. No political perspective. Describes what sources say;
does not editorialize.

Standards: active voice, present tense, every claim attributed, no loaded/charged
language, no value judgments, no predictions without attribution, neutral framing,
precise language (names, figures, locations).
```

### User Prompt (`_USER_PROMPT_TEMPLATE`) — 7 Tasks

| Task | Field | Format | Key Constraints |
|------|-------|--------|-----------------|
| 1 | `headline` | string, 8-12 words | Title Case, active voice, present tense, no loaded words |
| 2 | `summary` | string, 250-350 words | Inverted pyramid (P1: event, P2: context, P3: specifics, P4: next steps) |
| 3 | `consensus` | array, 3-5 strings | Specific verified facts (names, numbers, dates), not generic observations |
| 4 | `divergence` | array, 2-4 strings | Observable coverage patterns, neutral verbs only, no outlet credibility judgments |
| 5 | `editorial_importance` | integer, 1-10 | "Would a senior NYT editor front-page this?" (10=once-in-decade, 1=trivial) |
| 6 | `story_type` | string enum | breaking_crisis, policy_action, investigation, ongoing_crisis, incremental_update, human_interest, ceremonial, entertainment |
| 7 | `has_binding_consequences` | boolean | Changes legal/military/economic status quo? True for action, false for speculation |

### JSON Return Shape
```json
{
  "headline": "...", "summary": "...",
  "consensus": ["...", ...], "divergence": ["...", ...],
  "editorial_importance": N, "story_type": "...",
  "has_binding_consequences": true/false
}
```

---

## 3. Editorial Triage (v5.0)

Separate from summarization. 3 calls/run (1 per section), own budget (`_MAX_TRIAGE_CALLS=5`).

**System instruction:** Senior front-page editor role. Selection by consequence scale, novelty, institutional authority, global scope, source consensus. Bias-blind.

**Input:** Top 30 cluster titles+summaries per section.

**Output:**
```json
{
  "ranked_ids": ["id1", "id2", ...],        // top 10 in editorial order
  "duplicate_flags": [["idA", "idB"], ...],  // potential same-event clusters
  "incremental_flags": ["id3", ...]          // incremental updates
}
```

**Budget:** ~6 RPD (0.4% of 1500 free limit). Falls back to deterministic ranking if unavailable.

---

## 4. Anti-Bias Guardrails

| Guardrail | Problem | Technique |
|-----------|---------|-----------|
| Political lean leakage | Framing follows majority-lean sources | Prohibited value judgments + outlet-type labels (not names) |
| Sensationalist framing | Imports loaded source headline language | Explicit prohibited word list + "no imported language" rule |
| False balance | Treats fringe position as co-equal | "No false balance on empirical questions" principle |
| Attribution-free claims | "Experts say" without named expert | Must attribute to specific source |
| Credibility judgments in divergence | "Fringe outlets promoted conspiracies" | Neutral verb list + no outlet character descriptions |

---

## 5. Quality Metrics

| # | Metric | Target | Method |
|---|--------|--------|--------|
| 1 | Inverted pyramid compliance | >1.7/2.0 | First-sentence test: does it contain core event? |
| 2 | Attribution density | >0.7 ratio | Attributed claims / total factual claims |
| 3 | Loaded language frequency | 0 per run | Keyword scan against prohibited list |
| 4 | Headline length | 100% in 8-12 words | Whitespace token count |
| 5 | Consensus specificity | >1.5/2.0 | Names/numbers/dates present per point |
| 6 | Divergence neutrality | 0 flags | Scan for "bias," "ignore," "spin," credibility language |
| 7 | Summary length | 90% in 250-350 words | Word count before truncation |

Validation runs in `_check_quality()` post-generation. Warnings logged, results never discarded (zero API waste).

---

## 6. Source Handling

- Article text truncated to 400 chars in prompt context
- Max 10 articles per cluster in prompt
- **Use real outlet names** in articles block (not tier labels) — per user feedback
- Attribution uses outlet names inline, not bracketed citations
- Context line describes cluster size + tier distribution

---

## 7. Op-Ed Handling

Op-eds (single-source, `content_type=opinion`) are **not** sent to Gemini. They use original article text directly. No clustering, no summarization. Author/publication attribution shown when available.

---

## 8. Files

| File | Role |
|------|------|
| `pipeline/summarizer/cluster_summarizer.py` | Prompt templates, field extraction, quality validation |
| `pipeline/summarizer/gemini_client.py` | API client, rate limiting, call caps, `editorial_triage()` |

### API Configuration
- Model: `gemini-2.5-flash`
- Temperature: 0.2
- max_output_tokens: 8192
- Summarization cap: 25 calls/run (`_MAX_CALLS_PER_RUN`)
- Triage cap: 5 calls/run (`_MAX_TRIAGE_CALLS`)
- Rate limit: 4.2s between calls (~14 RPM)
- Total budget: ~156 RPD (10.4% of 1500 free limit)
