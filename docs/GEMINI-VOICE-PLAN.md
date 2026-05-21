# void --news — Editorial LLM & Voice Plan

Last updated: 2026-04-29 (rev 2 — Sonnet 4.6 primary)

**Version:** 5.0

LLM voice covers summarization, daily brief, opinion, weekly digest. Audio synthesis is separate (edge-tts, $0).

---

## 1. Editorial Voice Definition

All LLM output (Claude Sonnet primary, Gemini Flash fallback) follows these standards. The system instruction in `cluster_summarizer.py` and `daily_brief_generator.py` enforces them.

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

For Claude calls, the system block is wrapped with `cache_control: {"type":"ephemeral"}` (5-min TTL, 1024-token minimum) via `claude_client._build_system_block()`.

### User Prompt (`_USER_PROMPT_TEMPLATE`) — 7 Tasks

| Task | Field | Format | Constraints |
|---|---|---|---|
| 1 | `headline` | string, 8-12 words | Title Case, active voice, present tense |
| 2 | `summary` | string, 250-350 words | Inverted pyramid (P1 event, P2 context, P3 specifics, P4 next) |
| 3 | `consensus` | array, 3-5 strings | Specific verified facts (names, numbers, dates) |
| 4 | `divergence` | array, 2-4 strings | Observable coverage patterns, neutral verbs only |
| 5 | `editorial_importance` | int 1-10 | "Would a senior NYT editor front-page this?" |
| 6 | `story_type` | enum | breaking_crisis, policy_action, investigation, ongoing_crisis, incremental_update, human_interest, ceremonial, entertainment |
| 7 | `has_binding_consequences` | bool | Changes legal/military/economic status quo? |

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

## 3. Smart Routing & Cache

`cluster_summarizer._smart_generate_json()`:
1. If `claude_is_available()` (ANTHROPIC_API_KEY set + SDK importable + within 80-call cap), call Sonnet 4.6.
2. On Claude failure or unavailability, fall back to `gemini_client.generate_json()`.
3. On both failures, return None — caller uses rule-based lead extraction.

`_content_hash(articles)` = sha256(sorted article_ids + "|" + count). Used by step 8d (`summarize_top50_after_rerank`) to skip clusters with unchanged membership since last Sonnet summary. Stored on `story_clusters.summary_article_hash` + `summary_tier='sonnet'` (migration 049).

---

## 4. Editorial Triage (v5.0)

Separate from summarization. 3 calls/run (1 per section), own budget (`_MAX_TRIAGE_CALLS=5`). Gemini-driven (not yet Sonnet-routed).

**System:** Senior front-page editor. Selection by consequence scale, novelty, institutional authority, global scope, source consensus. Bias-blind.

**Input:** Top 30 cluster titles+summaries per section.

**Output:**
```json
{
  "ranked_ids": ["id1", "id2", ...],
  "duplicate_flags": [["idA", "idB"], ...],
  "incremental_flags": ["id3", ...]
}
```

Falls back to deterministic ranking if API unavailable.

---

## 5. Anti-Bias Guardrails

| Guardrail | Problem | Technique |
|---|---|---|
| Political lean leakage | Framing follows majority-lean sources | Prohibited value judgments + outlet-type labels (not names) |
| Sensationalist framing | Imports loaded source headline language | Explicit prohibited word list + "no imported language" rule |
| False balance | Treats fringe as co-equal | "No false balance on empirical questions" principle |
| Attribution-free claims | "Experts say" without named expert | Must attribute to specific source |
| Credibility judgments in divergence | "Fringe outlets promoted conspiracies" | Neutral verb list + no outlet character descriptions |

---

## 6. Quality Metrics

| # | Metric | Target | Method |
|---|---|---|---|
| 1 | Inverted pyramid compliance | >1.7/2.0 | First-sentence test |
| 2 | Attribution density | >0.7 ratio | Attributed / total factual claims |
| 3 | Loaded language frequency | 0/run | Keyword scan against prohibited list |
| 4 | Headline length | 100% in 8-12 words | Whitespace token count |
| 5 | Consensus specificity | >1.5/2.0 | Names/numbers/dates per point |
| 6 | Divergence neutrality | 0 flags | Scan for "bias," "ignore," "spin," credibility language |
| 7 | Summary length | 90% in 250-350 words | Word count before truncation |

`_check_quality()` runs post-generation. Warnings logged, results never discarded (zero API waste).

---

## 7. Source Handling

- Article text truncated to 400 chars in prompt context
- Max 10 articles per cluster in prompt
- Real outlet names in articles block (not tier labels)
- Attribution uses outlet names inline, not bracketed citations
- Context line describes cluster size + tier distribution

---

## 8. Op-Ed Handling

Op-eds (single-source, `content_type=opinion`) bypass all LLM rewriting. Original article text preserved. No clustering, no summarization. Author/publication shown when available.

---

## 9. Files

| File | Role |
|---|---|
| `pipeline/summarizer/claude_client.py` | Anthropic SDK client, `_MODEL = "claude-sonnet-4-6"`, ephemeral prompt caching, 80 calls/run cap |
| `pipeline/summarizer/gemini_client.py` | Gemini Flash client, fallback role, `editorial_triage()` |
| `pipeline/summarizer/cluster_summarizer.py` | Prompt templates, `_smart_generate_json()`, `_content_hash()`, `summarize_top50_after_rerank()`, quality validation |
| `pipeline/briefing/daily_brief_generator.py` | TL;DR + opinion generation, Claude primary / Gemini fallback |
| `pipeline/briefing/weekly_digest_generator.py` | Weekly magazine, Claude primary |
| `pipeline/briefing/claude_brief_generator.py` | Manual standalone Claude CLI brief regen |

### API Configuration

**Claude (primary)**
- Model: `claude-sonnet-4-6`
- Pricing: $3/MTok in, $15/MTok out
- Per-call avg: ~3500 in × 800 out → ~$0.0225/call
- Cap: 80 calls/run (`_MAX_CALLS_PER_RUN`)
- Prompt caching: 5-min ephemeral, 1024-token minimum on system block

**Gemini (fallback + triage)**
- Model: `gemini-2.5-flash`
- Temperature: 0.2, max_output_tokens: 8192
- Summarization cap: 70/run, triage cap: 5/run, 4.2s rate limit (~14 RPM)

**Daily LLM cost**: ~$1/day (Sonnet primary, ~57 calls × 1 run/day). Anthropic budget cap recommended at $50/mo (60% buffer over $30 target).

---

## 10. Audio Broadcast — edge-tts (Microsoft Neural, $0)

Audio synthesis is **fully decoupled** from editorial LLM choice. Same edge-tts stack regardless of whether scripts came from Claude or Gemini.

```
LLM (Claude/Gemini, text) → edge-tts (per-turn synthesis) → pydub (sonic identity) → MP3 96k mono → Supabase Storage
   3 calls/run                 $0 Microsoft Neural             intro chord + chimes +
   (TL;DR + opinion +                                          page-turn + outro +
    audio_script)                                              subharmonic layer
```

Gemini TTS was used in v3 (2026-03-22) but permanently removed in v4 (2026-04-11) — NOT free tier (~$3.70/day, hit $40 cap).

### Voice Configuration — 4 Multilingual Neural Voices

As of 2026-04-19, all first-gen Neural voices retired. Four en-US Multilingual Neural voices only. Each news pair preserves male/female contrast across 6 personas.

**News host rotation (6 personas → 4 voices):**

| Host Role | Persona Name | edge-tts Voice | Character |
|---|---|---|---|
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

Canonical mapping in `_GEMINI_TO_EDGE_VOICE` in `audio_producer.py`. Defaults (`_DEFAULT_EDGE_VOICE_A/B`) Andrew + Emma.

### Sonic Identity (pydub Post-Processing)

| Element | Description |
|---|---|
| Intro | ~2s D major 9th bloom chord (Glass & Gravity) |
| Section breaks | Glass-bell chimes at silence gaps (≥800ms at ≤−45dB) |
| News→opinion | Editorial page-turn transition |
| Outro | ~1.8s resolving chord (intro bloom → root) |
| Subharmonic | D2/D3/A3 presence layer at −34 to −42 dB |
| Export | MP3 96k mono (voice-optimized) |

### Audio Files

| File | Role |
|---|---|
| `pipeline/briefing/audio_producer.py` | Per-turn edge-tts via `_synthesize_edge_tts()`, pydub stitching + sonic identity, MP3 export, Supabase upload. Canonical 4-voice mapping. |
| `pipeline/briefing/voice_rotation.py` | 6-host newsroom, 3 pairs rotating across editions, opinion voice per edition |
| `pipeline/history/audio_script_generator.py` | Gemini history-audio scripts; writes canonical to `data/history/scripts/{slug}.txt`; `reuse_cached=True` skips Gemini |
| `pipeline/history/generate_audio.py` | Per-event synthesizer; `--voices-only` (implies `--force`) reuses cached scripts |
| `data/history/scripts/{slug}.txt` | Canonical script store — generate once, reuse indefinitely for voice iteration |

### Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-03-22 | Replace edge-tts + Google Cloud TTS with Gemini Flash TTS | Single API call, LLM-native prosody, $0 (at the time) |
| 2026-03-22 | Delete SSML prosody, disfluency, per-turn stitching | Unnecessary with LLM-native dialogue synthesis |
| 2026-04-11 | **Permanently revert to edge-tts, remove Gemini TTS** | Not free tier — $3.70/day, hit $40 cap. edge-tts is $0 with Microsoft Neural. Gemini text remains free. |
| 2026-04-11 | Remove DISABLE_AUDIO gate from pipeline.yml | Audio runs every scheduled pipeline run at $0 (world only) |
| 2026-04-19 | **Consolidate to 4 Multilingual Neural voices** | Multilingual delivers warmer, more natural prosody at same $0 cost; news pairs preserve male/female contrast |
| 2026-04-19 | **Script cache + `--voices-only` flag** | Decouples Gemini script gen from TTS. Voice sweeps for all 58 history events cost $0 in Gemini quota, complete in ~6 min. |
| 2026-04-29 | **Editorial LLM stack moves to Claude Sonnet 4.6 (~$30/mo)** | Sonnet quality justifies broken $0 ceiling. Smart-routed Claude→Gemini, content-hash cache on top-50 post-rerank, ephemeral prompt caching. Pipeline cadence drops to 1x/day. Audio stack unchanged ($0). |

### Limitations & Risks

| Risk | Mitigation |
|---|---|
| edge-tts depends on Microsoft availability | Skip audio, text brief still generated |
| Per-turn synthesis less natural than LLM-native | Sonic identity (chimes, subharmonic, bloom) adds cohesion |
| ffmpeg required for MP3 export | Already in GitHub Actions (`apt-get install ffmpeg`) |
| Anthropic API outage breaks editorial LLM | Smart-routed fallback to Gemini Flash; rule-based summary if both down |
