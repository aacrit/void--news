"""
Audio producer for the void --news daily brief.

Uses Gemini 2.5 Flash TTS for native LLM-powered multi-speaker dialogue.
Both speakers generated in a single API call — no per-turn stitching.

Post-processing via pydub:
  - Intro: ~2s D major 9th bloom chord (Glass & Gravity sonic identity)
  - Section breaks: glass-bell chimes overlaid at detected silence gaps
    between stories (gaps >= 800ms at <= -45dB)
  - News-to-opinion: deliberate editorial page-turn transition
  - Outro: ~1.8s resolving chord — intro bloom returning to root
  - Subharmonic presence layer (D2/D3/A3 at -34 to -42 dB)
  - MP3 96k mono export → Supabase Storage (voice-optimized)
"""

import io
import os
import re
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Optional

GEMINI_TTS_AVAILABLE = False
PYDUB_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_TTS_AVAILABLE = True
except ImportError:
    pass

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    pass

try:
    from briefing.generate_assets import generate_headline_underscore
except ImportError:
    try:
        from pipeline.briefing.generate_assets import generate_headline_underscore
    except ImportError:
        generate_headline_underscore = None

try:
    from briefing.voice_rotation import get_opinion_host
except ImportError:
    try:
        from pipeline.briefing.voice_rotation import get_opinion_host
    except ImportError:
        get_opinion_host = None

# Allow running from pipeline root
sys.path.insert(0, str(Path(__file__).parent.parent))

ASSETS_DIR = Path(__file__).parent / "assets"
_TTS_MODEL = "gemini-2.5-flash-preview-tts"


# ---------------------------------------------------------------------------
# Script conversion
# ---------------------------------------------------------------------------

def _script_to_dialogue(audio_script: str) -> str:
    """Convert broadcast script (A:/B: + [MARKER]) to Gemini TTS dialogue format.

    Maps A→One, B→Two. Strips structural markers and Gemini artifacts.
    """
    lines = []
    for line in audio_script.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Skip pure marker lines
        if re.match(r"^\[([A-Z_0-9]+)\]$", stripped):
            continue

        # Strip inline markers
        stripped = re.sub(r"^\[([A-Z_0-9]+)\]\s*", "", stripped)

        # Map speaker tags
        sp_match = re.match(r"^([AB]):\s*(.+)$", stripped)
        if sp_match:
            speaker = "One" if sp_match.group(1) == "A" else "Two"
            text = sp_match.group(2)
        else:
            speaker = "One"
            text = stripped

        # Clean artifacts
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"\[(\d+)\]", "", text)
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"`+", "", text)
        text = re.sub(r"\(\s*\)", "", text)
        text = re.sub(r"  +", " ", text).strip()

        if text:
            lines.append(f"{speaker}: {text}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gemini TTS synthesis
# ---------------------------------------------------------------------------

def _chunk_dialogue(dialogue: str, max_words: int = 400) -> list[str]:
    """Split dialogue into chunks at natural speaker-turn boundaries.

    Gemini TTS can truncate long inputs. Splitting at ~400 words per chunk
    keeps each call within limits. Chunks split between speaker turns
    so no line is cut mid-sentence.
    """
    lines = dialogue.strip().splitlines()
    chunks: list[str] = []
    current_lines: list[str] = []
    current_words = 0

    for line in lines:
        line_words = len(line.split())
        # If adding this line exceeds limit and we have content, start new chunk
        if current_words + line_words > max_words and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_words = 0
        current_lines.append(line)
        current_words += line_words

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def _synthesize_single_chunk(
    client,
    dialogue_chunk: str,
    voice_a: str,
    voice_b: str,
    tts_preamble: str = "",
) -> Optional[bytes]:
    """Synthesize a single dialogue chunk via Gemini TTS. Returns raw PCM or None."""
    # Prepend style preamble (director's notes) if provided.
    # Gemini TTS uses this to adjust pacing, tone, and delivery.
    content = f"{tts_preamble}\n\n{dialogue_chunk}" if tts_preamble else dialogue_chunk
    try:
        response = client.models.generate_content(
            model=_TTS_MODEL,
            contents=content,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="One",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_a,
                                    )
                                ),
                            ),
                            types.SpeakerVoiceConfig(
                                speaker="Two",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_b,
                                    )
                                ),
                            ),
                        ]
                    )
                ),
            ),
        )

        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if hasattr(part, "inline_data") and part.inline_data:
                return part.inline_data.data
    except Exception as e:
        print(f"  [warn][audio] Gemini TTS chunk failed: {e}")

    return None


def _synthesize_gemini_tts(
    dialogue: str,
    voice_a: str,
    voice_b: str,
    tts_preamble: str = "",
) -> Optional[bytes]:
    """Generate two-speaker audio via Gemini 2.5 Flash TTS.

    Chunks long dialogues to avoid TTS truncation. Each chunk is synthesized
    separately and the raw PCM bytes are concatenated (same sample rate/format).

    Args:
        dialogue: Two-speaker dialogue (One:/Two: format).
        voice_a: Gemini voice ID for speaker One.
        voice_b: Gemini voice ID for speaker Two.
        tts_preamble: Director's notes for TTS style (pacing, tone, cadence).

    Returns raw PCM audio bytes (24kHz 16-bit mono), or None on failure.
    """
    if not GEMINI_TTS_AVAILABLE:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  [warn][audio] GEMINI_API_KEY not set")
        return None

    client = genai.Client(api_key=api_key)
    chunks = _chunk_dialogue(dialogue)

    if len(chunks) == 1:
        return _synthesize_single_chunk(client, chunks[0], voice_a, voice_b, tts_preamble)

    print(f"  [audio] Long script — synthesizing in {len(chunks)} chunks")
    all_pcm = bytearray()
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(5)  # Rate-limit buffer between TTS chunks
        # Only prepend preamble to first chunk — consistent style across chunks
        preamble = tts_preamble if i == 0 else ""
        pcm = _synthesize_single_chunk(client, chunk, voice_a, voice_b, preamble)
        if pcm is None:
            print(f"  [warn][audio] Chunk {i+1}/{len(chunks)} failed — aborting")
            return None
        all_pcm.extend(pcm)
        chunk_dur = len(pcm) / (24000 * 2)
        print(f"  [audio] Chunk {i+1}/{len(chunks)}: {chunk_dur:.1f}s")

    return bytes(all_pcm) if all_pcm else None


# ---------------------------------------------------------------------------
# Audio post-processing
# ---------------------------------------------------------------------------

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Convert raw PCM (16-bit mono) to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _load_asset(filename: str) -> Optional["AudioSegment"]:
    """Load an audio asset from the assets directory."""
    if not PYDUB_AVAILABLE:
        return None
    path = ASSETS_DIR / filename
    if not path.exists():
        return None
    try:
        fmt = "wav" if filename.endswith(".wav") else "mp3"
        return AudioSegment.from_file(str(path), format=fmt)
    except Exception as e:
        print(f"  [warn][audio] Failed to load asset {filename}: {e}")
        return None


# ---------------------------------------------------------------------------
# Silence detection & section break overlay
# ---------------------------------------------------------------------------

def _detect_silence_gaps(
    audio: "AudioSegment",
    min_gap_ms: int = 800,
    silence_thresh_db: float = -45.0,
    chunk_ms: int = 50,
    min_spacing_ms: int = 45000,
    max_breaks: int = 4,
) -> list[int]:
    """Find silence gaps in audio suitable for section break insertion.

    Scans the audio in fixed-size chunks and identifies contiguous silent
    regions that last at least `min_gap_ms`. Returns the midpoint (in ms)
    of each detected gap.

    Parameters:
        audio: The AudioSegment to scan.
        min_gap_ms: Minimum gap duration to qualify as a section boundary.
        silence_thresh_db: dBFS threshold below which audio is "silent."
            -45dB is strict — only true silence, not low-level speech.
        chunk_ms: Scanning granularity. Smaller = more precise, slower.
        min_spacing_ms: Minimum distance between section breaks (default 45s).
        max_breaks: Maximum number of breaks to return.

    Returns:
        List of midpoint positions (ms) for each detected gap, sorted ascending.
    """
    raw_midpoints: list[int] = []
    in_silence = False
    silence_start = 0

    total_ms = len(audio)
    pos = 0

    while pos + chunk_ms <= total_ms:
        chunk = audio[pos : pos + chunk_ms]
        if chunk.dBFS < silence_thresh_db or chunk.dBFS == float("-inf"):
            if not in_silence:
                in_silence = True
                silence_start = pos
        else:
            if in_silence:
                gap_duration = pos - silence_start
                if gap_duration >= min_gap_ms:
                    midpoint = silence_start + gap_duration // 2
                    raw_midpoints.append(midpoint)
                in_silence = False
        pos += chunk_ms

    # Handle trailing silence
    if in_silence:
        gap_duration = total_ms - silence_start
        if gap_duration >= min_gap_ms:
            midpoint = silence_start + gap_duration // 2
            raw_midpoints.append(midpoint)

    # Enforce minimum spacing between breaks
    spaced: list[int] = []
    for mp in raw_midpoints:
        if not spaced or (mp - spaced[-1]) >= min_spacing_ms:
            spaced.append(mp)

    # Cap total count
    return spaced[:max_breaks]


def _overlay_section_breaks(
    audio: "AudioSegment",
    section_break: "AudioSegment",
) -> "AudioSegment":
    """Detect silence gaps in speech audio and overlay section break chimes.

    The section break asset is centered at the midpoint of each detected
    silence gap. This creates natural "next topic" markers without
    interrupting the speech flow.

    Returns the audio with section breaks overlaid. If no gaps are found
    or the section break asset is None, returns the original audio unchanged.
    """
    if section_break is None:
        return audio

    gaps = _detect_silence_gaps(audio)
    if not gaps:
        print("  [audio] No silence gaps detected for section breaks")
        return audio

    print(f"  [audio] Detected {len(gaps)} silence gap(s) — overlaying section breaks")

    break_half_len = len(section_break) // 2
    result = audio

    for midpoint in gaps:
        # Center the break asset at the gap midpoint
        overlay_start = max(0, midpoint - break_half_len)
        # Don't overlay past the end of the audio
        if overlay_start + len(section_break) > len(result):
            continue
        result = result.overlay(section_break, position=overlay_start)

    return result


# ---------------------------------------------------------------------------
# Word-count proportional placement (replaces silence detection)
# ---------------------------------------------------------------------------

def _snap_to_quiet(
    audio: "AudioSegment",
    target_ms: int,
    window_ms: int = 3000,
    grain_ms: int = 200,
) -> int:
    """Find the quietest grain_ms chunk within +/- window_ms of target_ms.

    Instead of scanning the entire audio for silence (which fails on
    continuous Gemini TTS), this searches a narrow window around a known
    approximate boundary position to find the best placement point.

    Returns the midpoint (ms) of the quietest chunk in the window.
    """
    start = max(0, target_ms - window_ms)
    end = min(len(audio), target_ms + window_ms)

    best_pos = target_ms
    best_rms = float('inf')

    pos = start
    while pos + grain_ms <= end:
        chunk = audio[pos : pos + grain_ms]
        if chunk.rms < best_rms:
            best_rms = chunk.rms
            best_pos = pos + grain_ms // 2
        pos += grain_ms // 2  # 50% overlap for precision

    return best_pos


def _place_proportional_elements(
    news_seg: "AudioSegment",
    dialogue: str,
) -> "AudioSegment":
    """Place section breaks and headline sting using word-count proportional positions.

    Uses the known script structure (deterministic percentages from the system
    prompt) to estimate boundary positions in the TTS audio, then snaps each
    estimate to the nearest quiet point for clean placement.

    Falls back to silence-based _overlay_section_breaks if the dialogue is
    too short (<200 words) or audio too brief (<60s) to estimate reliably.

    Returns the news audio with musical elements overlaid.
    """
    total_words = len(dialogue.split())
    total_ms = len(news_seg)

    # Fallback guard: if script is too short, use silence detection
    if total_words < 200 or total_ms < 60000:
        print(f"  [audio] Short script ({total_words}w, {total_ms}ms) — falling back to silence detection")
        section_break = _load_asset("section_break.wav")
        return _overlay_section_breaks(news_seg, section_break)

    # Cumulative proportional positions from script structure
    headlines_end_pct = 0.08
    story1_end_pct = 0.38
    story2_end_pct = 0.63

    # Compute raw ms positions
    raw_headlines_end = int(total_ms * headlines_end_pct)
    raw_story1_end = int(total_ms * story1_end_pct)
    raw_story2_end = int(total_ms * story2_end_pct)

    # Snap to quiet points
    headlines_end = _snap_to_quiet(news_seg, raw_headlines_end)
    story1_end = _snap_to_quiet(news_seg, raw_story1_end)
    story2_end = _snap_to_quiet(news_seg, raw_story2_end)

    # Enforce 30s minimum spacing between adjacent placements
    placements = [("headline_sting", headlines_end)]

    if story1_end - headlines_end >= 30000:
        placements.append(("section_break_1", story1_end))

    if len(placements) >= 2:
        last_pos = placements[-1][1]
    else:
        last_pos = headlines_end

    if story2_end - last_pos >= 30000:
        placements.append(("section_break_2", story2_end))

    # Load assets
    headline_sting = _load_asset("headline_sting.wav")
    section_break = _load_asset("section_break.wav")

    result = news_seg
    for label, pos_ms in placements:
        if label == "headline_sting" and headline_sting:
            overlay_start = max(0, pos_ms - len(headline_sting) // 2)
            if overlay_start + len(headline_sting) <= len(result):
                result = result.overlay(headline_sting, position=overlay_start)
                print(f"  [audio] Headline sting at {pos_ms}ms (raw {raw_headlines_end}ms)")
        elif label.startswith("section_break") and section_break:
            overlay_start = max(0, pos_ms - len(section_break) // 2)
            if overlay_start + len(section_break) <= len(result):
                result = result.overlay(section_break, position=overlay_start)
                print(f"  [audio] Section break at {pos_ms}ms (raw {raw_story1_end if '1' in label else raw_story2_end}ms)")

    print(f"  [audio] Placed {len(placements)} musical element(s) via proportional positioning")
    return result


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def _upload_to_supabase(audio_bytes: bytes, edition: str) -> Optional[str]:
    """Upload MP3 to Supabase Storage.

    Uploads twice:
      1. ``{edition}/{YYYY-MM-DD}-{am|pm}.mp3`` — persistent URL for podcast feeds
      2. ``{edition}/latest.mp3`` — overwritten each run for web player

    Returns the persistent URL (with cache-bust param) so ``daily_briefs.audio_url``
    always points to a stable file that podcast directories can reference.
    """
    try:
        from utils.supabase_client import supabase
        from datetime import datetime, timezone
        import hashlib

        now = datetime.now(timezone.utc)
        slot = "am" if now.hour < 12 else "pm"
        persistent_path = f"{edition}/{now.strftime('%Y-%m-%d')}-{slot}.mp3"
        latest_path = f"{edition}/latest.mp3"

        opts = {"content-type": "audio/mpeg", "upsert": "true"}

        # 1. Persistent copy (podcast feeds reference this)
        supabase.storage.from_("audio-briefs").upload(persistent_path, audio_bytes, opts)

        # 2. Latest copy (web player uses this)
        supabase.storage.from_("audio-briefs").upload(latest_path, audio_bytes, opts)

        base_url = supabase.storage.from_("audio-briefs").get_public_url(persistent_path)
        fingerprint = hashlib.md5(audio_bytes[:1024]).hexdigest()[:8]
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}v={fingerprint}"
    except Exception as e:
        print(f"  [warn][audio] Supabase upload failed for {edition}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _synthesize_opinion_monologue(
    opinion_audio_script: str,
    voice: str,
    opinion_tts_preamble: str = "",
) -> Optional[bytes]:
    """Synthesize a single-voice opinion editorial monologue.

    Uses the same Gemini TTS but with a single speaker format.
    The opinion_tts_preamble provides scene-setting / director's notes
    that shape the voice delivery (pace, conviction, dynamics).
    Returns raw PCM bytes or None.
    """
    if not GEMINI_TTS_AVAILABLE:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    # Wrap as single-speaker dialogue for Gemini TTS
    # The opinion script is flowing text, convert to One: lines
    lines = []
    for line in opinion_audio_script.splitlines():
        stripped = line.strip()
        if stripped:
            # If already has speaker tag, normalize it
            if re.match(r"^(One|Two|A|B):\s*", stripped):
                stripped = re.sub(r"^(One|Two|A|B):\s*", "", stripped)
            lines.append(f"One: {stripped}")

    dialogue = "\n".join(lines)
    if not dialogue:
        return None

    # Prepend editorial voice direction if provided
    content = f"{opinion_tts_preamble}\n\n{dialogue}" if opinion_tts_preamble else dialogue

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=_TTS_MODEL,
            contents=content,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="One",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice,
                                    )
                                ),
                            ),
                            # Gemini requires exactly 2 speakers in multi_speaker config.
                            # "Two" is never referenced in the dialogue — silent placeholder.
                            types.SpeakerVoiceConfig(
                                speaker="Two",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice,
                                    )
                                ),
                            ),
                        ]
                    )
                ),
            ),
        )

        if response.candidates and response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]
            if hasattr(part, "inline_data") and part.inline_data:
                return part.inline_data.data
    except Exception as e:
        print(f"  [warn][audio] Opinion TTS failed: {e}")

    return None


def produce_audio(
    audio_script: str,
    voices: dict,
    edition: str,
    opinion_audio_script: str | None = None,
    opinion_lean: str | None = None,
) -> Optional[dict]:
    """
    Synthesize the full broadcast via Gemini Flash TTS.

    Pipeline:
      1. News script → dialogue format (One:/Two:) → Gemini TTS (2 speakers)
      2. Opinion script → dialogue format (One:) → Gemini TTS (1 speaker, separate call)
      3. PCM → WAV → AudioSegment
      4. Assemble: ident + news + transition + opinion + outro
      5. Export MP3 → Supabase upload

    News and opinion use SEPARATE TTS calls because Gemini multi-speaker
    TTS only supports 2 speakers. Opinion uses its own dedicated voice.

    Args:
        opinion_lean: The editorial lean ("left"/"center"/"right"). Used to
            look up the opinion host's TTS preamble for voice direction.
    """
    if not GEMINI_TTS_AVAILABLE:
        print("  [audio] google-genai SDK not installed — skipping")
        return None

    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping")
        return None

    voice_a_name = voices["host_a"]["id"]
    voice_b_name = voices["host_b"]["id"]

    # Build TTS style preamble from host personality data
    host_a_preamble = voices["host_a"].get("tts_preamble", "")
    host_b_preamble = voices["host_b"].get("tts_preamble", "")
    tts_preamble = ""
    if host_a_preamble or host_b_preamble:
        tts_preamble = (
            f"Scene: Two senior journalists in a newsroom studio. "
            f"Speaker One: {host_a_preamble} "
            f"Speaker Two: {host_b_preamble}"
        )

    # --- Step 1: Synthesize news dialogue (2 speakers) ---
    dialogue = _script_to_dialogue(audio_script)
    word_count = len(dialogue.split())
    print(f"  [audio] News TTS: {word_count} words, voices {voice_a_name}+{voice_b_name}")

    pcm_data = _synthesize_gemini_tts(dialogue, voice_a_name, voice_b_name, tts_preamble)
    if not pcm_data:
        print("  [warn][audio] News TTS synthesis failed — no audio")
        return None

    news_duration = len(pcm_data) / (24000 * 2)
    print(f"  [audio] News TTS: {news_duration:.1f}s")

    wav_data = _pcm_to_wav(pcm_data)
    news_seg = AudioSegment.from_wav(io.BytesIO(wav_data))

    # --- Step 2: Synthesize opinion monologue (1 speaker, separate call) ---
    opinion_seg = None
    if opinion_audio_script:
        opinion_voice_name = voices.get("opinion", voices["host_a"])["id"]
        opinion_words = len(opinion_audio_script.split())

        # Look up opinion host's TTS preamble for editorial voice direction
        opinion_preamble = ""
        if opinion_lean and get_opinion_host is not None:
            opinion_host = get_opinion_host(opinion_lean)
            opinion_preamble = opinion_host.get("opinion_tts_preamble", "")
            if opinion_preamble:
                print(f"  [audio] Opinion preamble: {opinion_host.get('name', 'unknown')} ({opinion_lean})")

        print(f"  [audio] Opinion TTS: {opinion_words} words, voice {opinion_voice_name}")

        # Wait 20s between news and opinion TTS to avoid rate limits.
        # Free tier is aggressive — 10s was insufficient; most opinion
        # failures were 429 rate-limit errors on the first attempt.
        print("  [audio] Rate-limit pause (20s) before opinion TTS...")
        time.sleep(20)

        # Retry up to 3 times with increasing backoff
        opinion_pcm = None
        for attempt in range(3):
            opinion_pcm = _synthesize_opinion_monologue(
                opinion_audio_script, opinion_voice_name, opinion_preamble
            )
            if opinion_pcm:
                opinion_dur = len(opinion_pcm) / (24000 * 2)
                print(f"  [audio] Opinion TTS: {opinion_dur:.1f}s (attempt {attempt + 1})")
                break
            wait = 20 * (attempt + 1)  # 20s, 40s, 60s
            print(f"  [warn][audio] Opinion TTS attempt {attempt + 1}/3 failed — "
                  f"{'retrying in ' + str(wait) + 's' if attempt < 2 else 'giving up'}")
            if attempt < 2:
                time.sleep(wait)

        if opinion_pcm:
            opinion_wav = _pcm_to_wav(opinion_pcm)
            opinion_seg = AudioSegment.from_wav(io.BytesIO(opinion_wav))
        else:
            print("  [WARN][audio] Opinion TTS FAILED after 3 attempts — NO OPINION IN BROADCAST")
    else:
        print("  [audio] No opinion_audio_script — broadcast ends after news")

    # --- Step 3: Place section breaks + headline sting via proportional positioning ---
    news_seg = _place_proportional_elements(news_seg, dialogue)

    # --- Step 3b: Overlay headline underscore on news audio ---
    if generate_headline_underscore is not None:
        total_news_ms = len(news_seg)
        headlines_end_ms = int(total_news_ms * 0.08)
        headlines_end_ms = max(10000, min(25000, headlines_end_ms))
        underscore = generate_headline_underscore(headlines_end_ms)
        news_seg = news_seg.overlay(underscore, position=0)
        print(f"  [audio] Headline underscore overlaid ({headlines_end_ms}ms)")
    else:
        print("  [audio] generate_headline_underscore not available — skipping")

    # --- Step 4: Assemble final audio ---
    combined = AudioSegment.empty()

    ident = _load_asset("ident.wav")
    if ident:
        # Overlap last 200ms of ident with first speech for smooth handoff
        # (inspired by The Daily's theme-to-voice overlap)
        ident_body = ident[:-200]
        ident_tail = ident[-200:]
        combined += ident_body
        # Create a crossfade zone: ident tail + silence, overlaid with news start
        crossfade = ident_tail + AudioSegment.silent(duration=50)
        news_start = news_seg[:250]
        news_rest = news_seg[250:]
        blended = crossfade.overlay(news_start)
        combined += blended
        combined += news_rest
    else:
        combined += AudioSegment.silent(duration=250)
        combined += news_seg

    # Brief breath before editorial transition (was 350ms)
    combined += AudioSegment.silent(duration=200)

    # Opinion section (after editorial page-turn transition)
    opinion_start_ms = None
    if opinion_seg:
        transition = _load_asset("news_to_opinion.wav")
        if transition is None:
            transition = _load_asset("transition.wav")
        if transition:
            combined += transition
        else:
            combined += AudioSegment.silent(duration=800)
        # Minimal gap after transition — Phase 3 handles the arrival (was 200ms)
        combined += AudioSegment.silent(duration=100)
        opinion_start_ms = len(combined)
        combined += opinion_seg

        # Opinion kicker: chord stab after editorial
        opinion_kicker = _load_asset("opinion_kicker.wav")
        if opinion_kicker:
            combined += AudioSegment.silent(duration=100)
            combined += opinion_kicker
            combined += AudioSegment.silent(duration=200)
        else:
            combined += AudioSegment.silent(duration=350)

    # Outro: the resolve
    outro = _load_asset("outro.wav")
    if outro:
        combined += outro

    # --- Step 5: Overlay background bed across entire broadcast ---
    bed_seg = _load_asset("background_bed.wav")
    if bed_seg and len(combined) > 0:
        # Tile the 10s bed segment to cover full broadcast length + margin
        total_len = len(combined)
        tiled_bed = AudioSegment.empty()
        while len(tiled_bed) < total_len:
            tiled_bed += bed_seg
        tiled_bed = tiled_bed[:total_len]
        # Fade bed in after ident, fade out before outro ends
        bed_fade_in = 1500   # 1.5s gentle entrance
        bed_fade_out = 2000  # 2s fade for smooth exit
        tiled_bed = tiled_bed.fade_in(bed_fade_in).fade_out(bed_fade_out)
        combined = combined.overlay(tiled_bed)
        print(f"  [audio] Background bed overlaid ({total_len}ms)")

    if len(combined) == 0:
        print("  [warn][audio] Combined audio is empty — aborting")
        return None

    has_opinion = opinion_seg is not None
    print(f"  [audio] OPINION IN FINAL AUDIO: {'YES' if has_opinion else 'NO'}")

    duration_seconds = round(len(combined) / 1000.0, 1)
    print(f"  [audio] Assembled {duration_seconds}s total for {edition}")

    # 6. Export to MP3 96kbps mono (voice-optimized; sufficient for speech)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        combined.export(
            tmp_path,
            format="mp3",
            bitrate="96k",
            parameters=["-ac", "1"],
        )
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        print(f"  [warn][audio] MP3 export failed: {e}")
        return None
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    file_size = len(audio_bytes)
    print(f"  [audio] Exported {file_size / 1024:.1f} KB MP3 — uploading to Supabase")

    public_url = _upload_to_supabase(audio_bytes, edition)
    if not public_url:
        return None

    print(f"  [audio] Uploaded: {public_url}")
    opinion_start_seconds = round(opinion_start_ms / 1000.0, 1) if opinion_start_ms else None
    return {
        "audio_url": public_url,
        "duration_seconds": duration_seconds,
        "file_size": file_size,
        "opinion_start_seconds": opinion_start_seconds,
    }
