# void --news — Gemini Voice & Editorial Intelligence

**Version:** 4.1 | **Updated:** 2026-04-19

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

---

## 9. Audio Broadcast — edge-tts (Microsoft Neural, $0)

### Architecture (v4.1)

Gemini is used for **text only** (script generation). Audio synthesis uses **edge-tts** (Microsoft Neural voices, $0). Gemini TTS was used in v3 (2026-03-22) but permanently removed in v4 (2026-04-11) because it is NOT on the free tier (~$3.70/day, hit $40 billing cap on day 11 of April).

```
Gemini Flash (text) ──▶ edge-tts (per-turn synthesis) ──▶ pydub (sonic identity) ──▶ MP3 96k mono ──▶ Supabase Storage
   3 calls/run              $0 Microsoft Neural              intro chord + chimes +
   (TL;DR + opinion +                                        page-turn + outro +
    audio_script)                                             subharmonic layer
```

### Voice Configuration — 4 Multilingual Neural Voices

As of 2026-04-19, all first-gen Neural voices (Aria, Jenny, Davis, Christopher, Nancy, Roger, Michelle, Sara) are retired. The system runs on **four** en-US Multilingual Neural voices only. Each news pair preserves male/female contrast across the 6 personas.

**News host rotation (6 personas → 4 voices):**

| Host Role | Gemini Name | edge-tts Voice | Character |
|-----------|-------------|----------------|-----------|
| Correspondent | Kore | en-US-EmmaMultilingualNeural | Authoritative female |
| Structuralist | Charon | en-US-BrianMultilingualNeural | Conversational male |
| Investigator | Orus | en-US-AndrewMultilingualNeural | Measured male |
| Pragmatist | Gacrux | en-US-AvaMultilingualNeural | Smooth female |
| Editor | Sadaltager | en-US-AndrewMultilingualNeural | Warm scholarly male |
| Realist | Achernar | en-US-EmmaMultilingualNeural | Editorial-gravity female |

**History pair** (void --history companion audio):
- Chronicler (Sadaltager) → `en-US-AndrewMultilingualNeural`
- Witness (Achernar) → `en-US-EmmaMultilingualNeural`

**Opinion voices per edition** (fixed; all 4 Multilingual voices represented):
- World (Sulafat) → `en-US-AvaMultilingualNeural`
- US (Schedar) → `en-US-AndrewMultilingualNeural`
- India (Despina) → `en-US-AvaMultilingualNeural`
- UK (Rasalgethi) → `en-US-BrianMultilingualNeural`
- Canada (Vindemiatrix) → `en-US-EmmaMultilingualNeural`

Canonical mapping lives in `_GEMINI_TO_EDGE_VOICE` in `pipeline/briefing/audio_producer.py`. Defaults (`_DEFAULT_EDGE_VOICE_A/B`) are Andrew + Emma.

### Sonic Identity (Post-Processing via pydub)

| Element | Description |
|---------|-------------|
| Intro | ~2s D major 9th bloom chord (Glass & Gravity) |
| Section breaks | Glass-bell chimes at detected silence gaps (>= 800ms at <= -45dB) |
| News-to-opinion | Editorial page-turn transition |
| Outro | ~1.8s resolving chord (intro bloom returning to root) |
| Subharmonic | D2/D3/A3 presence layer at -34 to -42 dB |
| Export | MP3 96k mono (voice-optimized) |

### Gemini API Budget (Combined)

```
Daily Gemini Free Tier Usage (250 RPD)

Function                  Model     RPD     % of 250 limit
Cluster summarization     flash     ~100    40%
Gemini reasoning (6c)     flash     ~100    40%
Editorial triage (7c)     flash     ~12     5%
Daily brief script (7d)   flash     ~4      2%
Audio TTS                 --        0       0% (edge-tts, $0)
TOTAL                               ~216    86%
Remaining headroom                   ~34    14%
```

Audio uses edge-tts ($0, no Gemini RPD consumed).

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-22 | Replace edge-tts + Google Cloud TTS with Gemini Flash TTS | Single API call, LLM-native prosody, $0 (at the time) |
| 2026-03-22 | Delete SSML prosody, disfluency injection, per-turn stitching | Unnecessary with LLM-native dialogue synthesis |
| 2026-04-11 | **Permanently revert to edge-tts, remove Gemini TTS** | Gemini TTS is NOT free tier -- $3.70/day, hit $40 billing cap. edge-tts is $0 with Microsoft Neural voices. Gemini text generation remains free tier. |
| 2026-04-11 | Remove DISABLE_AUDIO gate from pipeline.yml | Audio runs on every scheduled pipeline run at $0 cost (world edition only) |
| 2026-04-19 | **Consolidate to 4 Multilingual Neural voices (Andrew/Brian/Ava/Emma)** | First-gen Neural voices (Aria, Jenny, Davis, Christopher, Nancy, Roger, Michelle, Sara) retired. Multilingual Neural delivers noticeably warmer, more natural prosody at same $0 cost; every news pair still preserves male/female contrast across 6 personas. |
| 2026-04-19 | **Script cache at `data/history/scripts/{slug}.txt` + `--voices-only` flag** | Decouples Gemini script generation from TTS synthesis. Voice sweeps (re-synthesize all 58 history events with a new voice) now cost $0 in Gemini quota and complete in ~6 min. `generate_audio.py --voices-only` reuses cached scripts; `generate-history-audio.yml` workflow accepts a `voices_only` dispatch input. |

### Files

| File | Role |
|------|------|
| `pipeline/briefing/audio_producer.py` | Per-turn edge-tts synthesis via `_synthesize_edge_tts()`, pydub stitching + sonic identity, MP3 export, Supabase upload. Canonical `_GEMINI_TO_EDGE_VOICE` mapping (4 Multilingual voices). |
| `pipeline/briefing/voice_rotation.py` | 6-host newsroom model, 3 pairs rotating across editions, opinion voice per edition |
| `pipeline/briefing/daily_brief_generator.py` | Gemini script generation (TL;DR + audio_script), 3-call budget |
| `pipeline/briefing/claude_brief_generator.py` | Optional Claude CLI premium script (manual 1x/day) |
| `pipeline/history/audio_script_generator.py` | Gemini history-audio script generation; writes canonical scripts to `data/history/scripts/{slug}.txt`; `reuse_cached=True` skips Gemini entirely |
| `pipeline/history/generate_audio.py` | Per-event synthesizer; `--voices-only` flag (implies `--force`) reuses cached scripts for zero-Gemini voice sweeps |
| `data/history/scripts/{slug}.txt` | Canonical script store — generated once via Gemini, reused indefinitely for voice iteration |

### Limitations & Risks

| Risk | Mitigation |
|------|------------|
| edge-tts depends on Microsoft service availability | Fallback: skip audio, text brief still generated |
| Per-turn synthesis less natural than LLM-native | Sonic identity (chimes, subharmonic, bloom) adds cohesion |
| ffmpeg required for MP3 export | Already in GitHub Actions (`apt-get install ffmpeg`) |
