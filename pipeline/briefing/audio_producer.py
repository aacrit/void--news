"""
Audio producer for the void --news daily brief.

Uses Gemini 2.5 Flash TTS for native LLM-powered multi-speaker dialogue.
Both speakers generated in a single API call — no per-turn stitching.

Post-processing via pydub:
  - Intro: ~2s D major 9th bloom chord (Glass & Gravity sonic identity)
  - Transition: glass-bell pulse between news and opinion segments
  - Outro: ~1.8s resolving chord — intro bloom returning to root
  - No background bed — the voices carry the broadcast
  - MP3 192k mono export → Supabase Storage
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
) -> Optional[bytes]:
    """Synthesize a single dialogue chunk via Gemini TTS. Returns raw PCM or None."""
    try:
        response = client.models.generate_content(
            model=_TTS_MODEL,
            contents=dialogue_chunk,
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
) -> Optional[bytes]:
    """Generate two-speaker audio via Gemini 2.5 Flash TTS.

    Chunks long dialogues to avoid TTS truncation. Each chunk is synthesized
    separately and the raw PCM bytes are concatenated (same sample rate/format).

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
        return _synthesize_single_chunk(client, chunks[0], voice_a, voice_b)

    print(f"  [audio] Long script — synthesizing in {len(chunks)} chunks")
    all_pcm = bytearray()
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(5)  # Rate-limit buffer between TTS chunks
        pcm = _synthesize_single_chunk(client, chunk, voice_a, voice_b)
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
# Upload
# ---------------------------------------------------------------------------

def _upload_to_supabase(audio_bytes: bytes, edition: str) -> Optional[str]:
    """Upload MP3 to Supabase Storage. Returns public URL with cache-bust param."""
    try:
        from utils.supabase_client import supabase

        path = f"{edition}/latest.mp3"
        supabase.storage.from_("audio-briefs").upload(
            path,
            audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )
        base_url = supabase.storage.from_("audio-briefs").get_public_url(path)
        # Cache-bust: append timestamp so browsers/CDNs don't serve stale audio
        import hashlib
        fingerprint = hashlib.md5(audio_bytes[:1024]).hexdigest()[:8]
        return f"{base_url}?v={fingerprint}"
    except Exception as e:
        print(f"  [warn][audio] Supabase upload failed for {edition}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _synthesize_opinion_monologue(
    opinion_audio_script: str,
    voice: str,
) -> Optional[bytes]:
    """Synthesize a single-voice opinion editorial monologue.

    Uses the same Gemini TTS but with a single speaker format.
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

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=_TTS_MODEL,
            contents=dialogue,
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
    """
    if not GEMINI_TTS_AVAILABLE:
        print("  [audio] google-genai SDK not installed — skipping")
        return None

    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping")
        return None

    voice_a_name = voices["host_a"]["id"]
    voice_b_name = voices["host_b"]["id"]

    # --- Step 1: Synthesize news dialogue (2 speakers) ---
    dialogue = _script_to_dialogue(audio_script)
    word_count = len(dialogue.split())
    print(f"  [audio] News TTS: {word_count} words, voices {voice_a_name}+{voice_b_name}")

    pcm_data = _synthesize_gemini_tts(dialogue, voice_a_name, voice_b_name)
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
        print(f"  [audio] Opinion TTS: {opinion_words} words, voice {opinion_voice_name}")

        # Wait 20s between news and opinion TTS to avoid rate limits.
        # Free tier is aggressive — 10s was insufficient; most opinion
        # failures were 429 rate-limit errors on the first attempt.
        print("  [audio] Rate-limit pause (20s) before opinion TTS...")
        time.sleep(20)

        # Retry up to 3 times with increasing backoff
        opinion_pcm = None
        for attempt in range(3):
            opinion_pcm = _synthesize_opinion_monologue(opinion_audio_script, opinion_voice_name)
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

    # --- Step 3: Assemble final audio ---
    combined = AudioSegment.empty()

    ident = _load_asset("ident.wav")
    if ident:
        combined += ident

    combined += AudioSegment.silent(duration=250)
    combined += news_seg
    combined += AudioSegment.silent(duration=350)

    # Opinion section (after transition)
    if opinion_seg:
        transition = _load_asset("transition.wav")
        if transition:
            combined += transition
        else:
            combined += AudioSegment.silent(duration=800)
        combined += AudioSegment.silent(duration=200)
        combined += opinion_seg
        combined += AudioSegment.silent(duration=350)

    # Outro: the resolve
    outro = _load_asset("outro.wav")
    if outro:
        combined += outro

    if len(combined) == 0:
        print("  [warn][audio] Combined audio is empty — aborting")
        return None

    has_opinion = opinion_seg is not None
    print(f"  [audio] OPINION IN FINAL AUDIO: {'YES' if has_opinion else 'NO'}")

    duration_seconds = round(len(combined) / 1000.0, 1)
    print(f"  [audio] Assembled {duration_seconds}s total for {edition}")

    # 6. Export to MP3 192kbps mono
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        combined.export(
            tmp_path,
            format="mp3",
            bitrate="192k",
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
    return {
        "audio_url": public_url,
        "duration_seconds": duration_seconds,
        "file_size": file_size,
    }
