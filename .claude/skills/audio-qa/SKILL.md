---
name: audio-qa
description: "Audio Quality Cycle: audio-engineer produces/reviews broadcast + pipeline-tester validates output + bug-fixer patches. For daily brief audio and sonic branding."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /audio-qa — Audio Quality Cycle

You are the workflow orchestrator for the **Audio Quality Cycle** — ensuring void --news broadcast audio meets BBC World Service production standards. Covers the "void --onair" daily brief audio: Gemini 2.5 Flash TTS multi-speaker dialogue with Glass & Gravity sonic identity.

## Objective

Validate and improve audio production pipeline: script generation, TTS synthesis, post-processing (bloom intro, glass-bell transitions, resolving outro), MP3 export, and Supabase Storage upload.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — AUDIO REVIEW (read + write)                   │
│  audio-engineer: review/produce broadcast audio           │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — PIPELINE VALIDATION (parallel, read-only)     │
│  pipeline-tester: validate audio pipeline output          │
│  db-reviewer: check daily_briefs table + storage          │
├──────────────────────────────────────────────────────────┤
│  GATE: If Stage 2 passes → DONE                          │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — FIX (write)                                   │
│  bug-fixer: patch audio pipeline issues                   │
│  → Re-run Stage 2 for confirmation                        │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Audio Review

Launch **audio-engineer** for the specified task. Depending on what the CEO requests:

**Production review**:
- Script quality: BBC World Service two-host format (Host A facts, Host B context)
- `[MARKER]` structural delimiters present and correct
- `A:`/`B:` speaker tags → `One:`/`Two:` conversion for TTS
- Glass & Gravity sonic identity (D major 9th bloom intro, glass-bell transitions, resolving outro)
- Voice pairs correct per edition (world=Charon/Aoede, us=Enceladus/Kore, india=Puck/Leda)
- Voice rotation: roles swap on alternate days (UTC day-of-year parity)

**Code changes**:
- Modify `pipeline/briefing/audio_producer.py` (TTS synthesis, PCM→MP3)
- Modify `pipeline/briefing/daily_brief_generator.py` (script generation)
- Modify `pipeline/briefing/voice_rotation.py` (voice pairs)
- Modify `pipeline/briefing/generate_assets.py` (sonic assets)

### Stage 2 — Validate (Parallel)

Launch **pipeline-tester** and **db-reviewer** in parallel:

1. **pipeline-tester**:
   - Daily brief exists for each requested edition
   - `audio_script` field populated, `audio_url` populated
   - Script has proper `[MARKER]` structure
   - Audio duration reasonable (2-8 minutes)

2. **db-reviewer**:
   - `daily_briefs` table has latest records
   - `audio_url` points to valid Supabase Storage path
   - `duration_seconds` and `file_size` populated
   - `voice` field matches expected voice pair
   - No orphaned audio files in storage bucket

### Stage 3 — Fix (if needed)

Launch **bug-fixer** with combined failure reports:
- Script generation failures → fix `daily_brief_generator.py`
- TTS synthesis failures → fix `audio_producer.py`
- Storage upload failures → fix Supabase Storage config
- Post-processing failures → fix pydub pipeline or asset generation

### Final Report

```
## Audio QA Report
- **Result**: PASS / FAIL
- **Editions checked**: [world/us/india]
- **Script quality**: [assessment]
- **TTS synthesis**: PASS / FAIL
- **Sonic identity**: Bloom intro / Transitions / Outro — all present
- **Voice rotation**: Correct for today (day parity: [even/odd])
- **Storage**: audio_url valid, file_size [X]KB, duration [X]s
- **Issues**: [count] found → [count] fixed
```

## Reference Standards

- **BBC World Service**: Two-host format, authoritative + analytical voices
- **NPR Morning Edition**: Conversational pacing, natural transitions
- **Gemini 2.5 Flash TTS**: Native multi-speaker, single API call, LLM-native prosody
- **MP3 192k mono**: Broadcast standard for voice-primary content
