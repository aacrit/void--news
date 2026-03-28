# void --news — Gemini Voice & Editorial Intelligence

**Version:** 3.0 | **Updated:** 2026-03-22

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

## 9. Audio Broadcast — Gemini 2.5 Flash TTS

### Architecture (v3.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                    void --onair Audio Pipeline                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────────┐     ┌────────────┐  │
│  │  Gemini 2.5   │     │  Gemini 2.5 Flash │     │   pydub    │  │
│  │  Flash (text) │────▶│  TTS (audio)      │────▶│  assembly  │  │
│  │              │     │                  │     │            │  │
│  │ Script gen:  │     │ Native 2-speaker │     │ BBC pips + │  │
│  │ TL;DR +      │     │ dialogue in ONE  │     │ countdown +│  │
│  │ audio_script │     │ API call         │     │ dialogue + │  │
│  │              │     │                  │     │ outro      │  │
│  │ 3 calls/run  │     │ 1 call/edition   │     │            │  │
│  └──────────────┘     └──────────────────┘     └─────┬──────┘  │
│                                                       │         │
│                                                       ▼         │
│                                                 ┌──────────┐   │
│                                                 │ MP3 128k │   │
│                                                 │ mono     │   │
│                                                 └─────┬────┘   │
│                                                       │         │
│                                                       ▼         │
│                                               ┌────────────┐   │
│                                               │  Supabase  │   │
│                                               │  Storage   │   │
│                                               │ audio-     │   │
│                                               │ briefs/    │   │
│                                               └────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Before vs After (v2 → v3)

```
v2 (DELETED):                              v3 (CURRENT):
┌──────────────────────────┐               ┌──────────────────────────┐
│ Gemini Flash → script    │               │ Gemini Flash → script    │
│         │                │               │         │                │
│         ▼                │               │         ▼                │
│ Parse 20+ speaker turns  │               │ Convert A:/B: → Anchor:/ │
│         │                │               │ Analyst: dialogue format │
│         ▼                │               │         │                │
│ For EACH turn:           │               │         ▼                │
│   ├─ Clean text          │               │ ONE Gemini Flash TTS     │
│   ├─ Inject disfluency   │               │ API call                 │
│   ├─ Wrap SSML prosody   │               │         │                │
│   ├─ edge-tts/GCloud TTS │               │         ▼                │
│   ├─ Variable silence    │               │ PCM 24kHz → WAV →       │
│   └─ Append to pydub     │               │ pydub (pips + outro) →  │
│         │                │               │ MP3 128k mono            │
│         ▼                │               │         │                │
│ 20+ API calls            │               │         ▼                │
│ 592 lines of code        │               │ Supabase upload          │
│ Robotic turn-taking      │               │                          │
│ Fixed silence gaps       │               │ 1 API call               │
│ No contextual prosody    │               │ 231 lines of code        │
└──────────────────────────┘               │ Natural turn-taking      │
                                           │ LLM-native prosody       │
                                           └──────────────────────────┘
```

### Why LLM-Native TTS

Traditional TTS synthesizes each speaker turn in isolation — it has no idea what came before
or what the other speaker just said. The result is mechanically stitched audio with fixed
silence gaps. Even with SSML prosody hints and disfluency injection, it sounds robotic.

Gemini 2.5 Flash TTS is fundamentally different: the **LLM generates both speakers in a
single forward pass.** It understands the dialogue context — that "Right." after a dramatic
fact should sound different than "Right." in a casual greeting. It handles turn-taking,
emphasis, pacing, and conversational rhythm natively.

```
Traditional TTS (edge-tts, Google Cloud):
  "Right."  →  [synthesize in isolation]  →  same flat audio every time

Gemini Flash TTS:
  "...14 outlets track this across the spectrum."
  "Right. What stands out is the divergence."
                                     ↑
                   Model knows this follows a dramatic fact,
                   so "Right." gets weight and emphasis
```

### Script Format Conversion

The pipeline generates scripts with `A:`/`B:` speaker tags only (no `[MARKER]` segment
labels — the prompt explicitly bans them). The audio producer converts to Gemini's
`SpeakerName: text` format before synthesis, and defensively strips any `[MARKER]`
tags if present in legacy or malformed output.

```
INPUT (from daily_brief_generator.py):        OUTPUT (to Gemini Flash TTS):

A: Good evening. This is void                 Anchor: Good evening. This is void
news, world edition.                          news, world edition.
B: Good evening. Quite a day.                 Analyst: Good evening. Quite a day.
A: Here are the headlines...           →      Anchor: Here are the headlines...
B: Meanwhile, the ECB holds                   Analyst: Meanwhile, the ECB holds
rates.                                        rates.
...                                           ...
```

### Voice Configuration

```
┌─────────────────────────────────────────────────────┐
│              Gemini Prebuilt Voice Pairs             │
├──────────┬────────────────────┬──────────────────────┤
│ Edition  │ Anchor (Host A)    │ Analyst (Host B)     │
├──────────┼────────────────────┼──────────────────────┤
│ world    │ Charon             │ Aoede                │
│          │ deep, authoritative│ warm, conversational │
├──────────┼────────────────────┼──────────────────────┤
│ us       │ Enceladus          │ Kore                 │
│          │ steady, clear      │ bright, analytical   │
├──────────┼────────────────────┼──────────────────────┤
│ india    │ Puck               │ Leda                 │
│          │ measured, precise  │ warm, engaging        │
└──────────┴────────────────────┴──────────────────────┘

  Roles swap daily (UTC day-of-year parity).
  30 prebuilt voices available for future tuning.
```

### Benchmark

```
┌──────────────────────────────────────────────────────┐
│                  Performance (v3.0)                   │
├──────────────────┬───────────────────────────────────┤
│ Script input     │ 211 words (full broadcast)        │
│ Audio output     │ 75.8 seconds (1.3 min)            │
│ API latency      │ 42.2 seconds                      │
│ Realtime factor  │ 1.8x                              │
│ API calls        │ 1 (was 20+ in v2)                 │
│ Output format    │ PCM 24kHz 16-bit → MP3 128k mono  │
│ Cost per run     │ $0 (Gemini free tier)              │
│ Code lines       │ 231 (was 592 in v2)               │
│ Dependencies     │ google-genai, pydub (was +2 more) │
└──────────────────┴───────────────────────────────────┘
```

### Gemini API Budget (Combined)

```
┌──────────────────────────────────────────────────────────────┐
│              Daily Gemini Free Tier Usage (250 RPD)           │
├────────────────────────┬──────────┬────────┬─────────────────┤
│ Function               │ Model    │ RPD    │ % of 250 limit  │
├────────────────────────┼──────────┼────────┼─────────────────┤
│ Cluster summarization  │ flash    │ ~100   │ 40%             │
│ Gemini reasoning (6c)  │ flash    │ ~100   │ 40%             │
│ Editorial triage (7c)  │ flash    │ ~12    │ 5%              │
│ Daily brief script (7d)│ flash    │ ~4     │ 2%              │
│ Audio TTS (7d)         │ flash-tts│ ~4     │ 2%              │
├────────────────────────┼──────────┼────────┼─────────────────┤
│ TOTAL                  │          │ ~220   │ 88%             │
│ Remaining headroom     │          │ ~30    │ 12%             │
└────────────────────────┴──────────┴────────┴─────────────────┘

  4 runs/day × 1 TTS call/run = 4 RPD for audio.
  Well within free tier limits.
```

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-22 | Replace edge-tts + Google Cloud TTS with Gemini Flash TTS | Single API call, LLM-native prosody, $0, -361 lines |
| 2026-03-22 | Delete SSML prosody, disfluency injection, per-turn stitching | Unnecessary with LLM-native dialogue synthesis |
| 2026-03-22 | Remove edge-tts and google-cloud-texttospeech dependencies | No longer needed; Gemini Flash TTS uses existing google-genai SDK |
| 2026-03-22 | Gemini prebuilt voices over Neural2/edge-tts voices | Consistent with single-vendor approach, 30 voice options |

### Files

| File | Role |
|------|------|
| `pipeline/briefing/audio_producer.py` | Script→dialogue conversion, Gemini TTS call, PCM→WAV→MP3, Supabase upload |
| `pipeline/briefing/voice_rotation.py` | Gemini prebuilt voice pairs per edition, daily role swap |
| `pipeline/briefing/daily_brief_generator.py` | Gemini script generation (TL;DR + audio_script), 3-call budget |
| `pipeline/briefing/claude_brief_generator.py` | Optional Claude CLI premium script (manual 1x/day) |

### Limitations & Risks

| Risk | Mitigation |
|------|------------|
| Preview model (`-preview-tts`) may change | Monitor for deprecation; model name is a single constant |
| ~5 min audio cutoff reported on free tier | Briefs target 4-6 min; chunking at segment boundaries if needed |
| Free tier rate limits could change | Currently using 2% of 250 RPD; large buffer |
| No SSML control (LLM decides prosody) | Trade-off: less control but better natural results |
| PCM output requires ffmpeg for MP3 export | Already in GitHub Actions (`apt-get install ffmpeg`) |
