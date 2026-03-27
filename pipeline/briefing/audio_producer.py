"""
Audio producer for the void --news daily brief.

Uses Gemini 2.5 Flash TTS for native LLM-powered multi-speaker dialogue.
Both speakers generated in a single API call — no per-turn stitching.

Post-processing via pydub:
  - Intro: ~2s D major 9th bloom chord (Glass & Gravity sonic identity)
  - Story transitions: glass-bell dyad at detected silence gaps
  - Outro: ~1.8s resolving chord — intro bloom returning to root
  - No background bed — the voices carry the broadcast
  - MP3 192k mono export → Supabase Storage
"""

import io
import os
import re
import sys
import tempfile
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
    """Upload MP3 to Supabase Storage. Returns public URL or None."""
    try:
        from utils.supabase_client import supabase

        path = f"{edition}/latest.mp3"
        supabase.storage.from_("audio-briefs").upload(
            path,
            audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )
        return supabase.storage.from_("audio-briefs").get_public_url(path)
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
    Synthesize a two-voice news update via Gemini Flash TTS.

    Pipeline:
      1. Script → dialogue format (One:/Two:)
      2. Gemini Flash TTS → PCM output (chunked if long)
      3. PCM → WAV → AudioSegment
      4. Assemble: ident + news dialogue + [transition + opinion] + outro
      5. Export MP3 → Supabase upload

    The opinion segment is appended AFTER the main news, separated by the
    transition asset (glass-bell pulse). This makes it clearly optional —
    the main broadcast is complete, then void --opinion begins.
    """
    if not GEMINI_TTS_AVAILABLE:
        print("  [audio] google-genai SDK not installed — skipping")
        return None

    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping")
        return None

    voice_a_name = voices["host_a"]["id"]
    voice_b_name = voices["host_b"]["id"]

    # 1. Convert script to Gemini dialogue format
    dialogue = _script_to_dialogue(audio_script)
    word_count = len(dialogue.split())
    print(f"  [audio] Gemini TTS: {word_count} words, voices {voice_a_name}+{voice_b_name}")

    # 2. Synthesize via Gemini Flash TTS
    pcm_data = _synthesize_gemini_tts(dialogue, voice_a_name, voice_b_name)
    if not pcm_data:
        print("  [warn][audio] Gemini TTS synthesis failed — no audio")
        return None

    dialogue_duration = len(pcm_data) / (24000 * 2)
    print(f"  [audio] Gemini TTS returned {dialogue_duration:.1f}s of dialogue")

    # 3. PCM → WAV → AudioSegment
    wav_data = _pcm_to_wav(pcm_data)
    dialogue_seg = AudioSegment.from_wav(io.BytesIO(wav_data))

    # 4. Assemble: ident + breath + news dialogue + breath + [transition + opinion] + outro
    combined = AudioSegment.empty()

    ident = _load_asset("ident.wav")
    if ident:
        combined += ident

    combined += AudioSegment.silent(duration=250)
    combined += dialogue_seg
    combined += AudioSegment.silent(duration=350)

    # --- Opinion segment (optional, after main news) ---
    if not opinion_audio_script:
        print("  [audio] No opinion_audio_script — broadcast ends after news")
    if opinion_audio_script:
        # Use dedicated opinion voice — distinct from both news hosts
        opinion_voice_name = voices.get("opinion", voices["host_a"])["id"]
        print(f"  [audio] Synthesizing opinion monologue ({len(opinion_audio_script.split())} words, voice {opinion_voice_name})")
        opinion_pcm = _synthesize_opinion_monologue(opinion_audio_script, opinion_voice_name)
        if opinion_pcm:
            opinion_duration = len(opinion_pcm) / (24000 * 2)
            print(f"  [audio] Opinion TTS: {opinion_duration:.1f}s")
            opinion_wav = _pcm_to_wav(opinion_pcm)
            opinion_seg = AudioSegment.from_wav(io.BytesIO(opinion_wav))

            # Insert transition asset between news and opinion
            transition = _load_asset("transition.wav")
            if transition:
                combined += transition
            else:
                combined += AudioSegment.silent(duration=800)

            combined += AudioSegment.silent(duration=200)
            combined += opinion_seg
            combined += AudioSegment.silent(duration=350)
        else:
            print("  [audio] Opinion TTS failed — main broadcast unaffected")

    # Outro: the resolve
    outro = _load_asset("outro.wav")
    if outro:
        combined += outro

    if len(combined) == 0:
        print("  [warn][audio] Combined audio is empty — aborting")
        return None

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
