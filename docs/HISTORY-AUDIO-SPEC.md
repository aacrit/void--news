# void --history Audio Companion Spec

> Design doc. No implementation yet.

## 1. Format

Each event gets a single audio companion: **2-4 minutes** (400-700 words script). Two hosts walk through the perspectives as equals -- same dynamic as void --onair news segments. Not a lecture. Not a summary. The product is the *divergence* between perspectives, presented through concrete facts that contradict each other.

Structure: ident (existing) + perspective walkthrough + outro (existing). No opinion segment -- history events do not take an editorial position. The hosts surface what each side claims, what each side omits, and where the numbers disagree. The listener draws conclusions.

## 2. Prompt Structure

Input to script generation: the event YAML's `perspectives[]` array (each with `narrative`, `keyNarratives`, `omissions`, `disputed`), plus `summary` and `key_figures`.

System instruction reuses `_SYSTEM_INSTRUCTION` from `daily_brief_generator.py` with a history-specific addendum: no present-tense framing (these are past events), no significance assertion (the facts demonstrate it), attribute claims to the perspective that makes them.

Script format: `A:`/`B:` speaker tags, same as daily brief. The two hosts alternate perspectives -- Host A does not "own" one viewpoint. Both hosts present facts from multiple perspectives, building the divergence through juxtaposition. Target: 3-5 perspective passes (not one block per perspective).

Host pair: same rotation as daily brief (`voice_rotation.get_voices_for_today`), keyed to a synthetic "edition" string (`history`). Same 6 hosts, same 3 pairs.

## 3. Pipeline Integration

History audio is **not part of the 3x-daily pipeline run**. It is a one-time generation per event, triggered manually or by a dedicated GitHub Actions workflow (`generate-history-audio.yml`). Each event produces one MP3 that persists indefinitely.

Generation function: `produce_history_audio(event_slug)` in `audio_producer.py`. Calls Gemini for script generation (1 call), then TTS (1-2 calls depending on length). Budget: ~3 calls per event, well within free tier for batch runs of 10 events.

Post-processing: identical pipeline -- ident, background bed, outro, RMS-based ducking, MP3 96k mono. No section breaks or headline stings (single continuous topic). No opinion segment or transition.

## 4. Storage

Supabase Storage, same `audio-briefs` bucket: `history/{slug}.mp3`. No `latest.mp3` pattern (not ephemeral). Metadata: new `audio_url` and `audio_duration_seconds` columns on the history events table (or a dedicated `history_audio` table if events stay in YAML).

If events remain YAML-only (no Supabase table), store the audio URL in a sidecar JSON: `data/history/audio-manifest.json` mapping slug to public URL + duration.

## 5. Frontend

The audio player appears on the `EventDetail` component (the `[slug]` event page). Position: below the subtitle, above the summary -- the same prominence as void --onair on the homepage. Uses the existing `FloatingPlayer` component (already global). Play button styled to match the history page's archival cinema palette (`--hist-*` tokens) rather than the main feed's amber.

No autoplay. No separate podcast feed for history (too few episodes). If the event has no audio yet, the button is absent -- no "coming soon" placeholder.
