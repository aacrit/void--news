"""
Audio producer for the void --news daily brief.

Uses Gemini 2.5 Flash TTS for native LLM-powered multi-speaker dialogue
synthesis. The model generates both speakers in a single API call with
natural turn-taking, prosody, and conversational rhythm — no per-turn
stitching needed.

Pipeline: broadcast script → Gemini Flash TTS (PCM 24kHz) → pydub
(pips intro + outro + MP3 export) → Supabase Storage upload.

Falls back gracefully if google-genai SDK or pydub are unavailable.
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

# Gemini TTS model
_TTS_MODEL = "gemini-2.5-flash-preview-tts"


def _script_to_dialogue(audio_script: str) -> str:
    """Convert broadcast script (A:/B: + [MARKER]) to Gemini TTS dialogue format.

    Gemini TTS expects: "SpeakerName: dialogue text" with newlines between turns.
    Strips structural markers, cleans artifacts, maps A→Anchor, B→Analyst.
    """
    lines = []
    for line in audio_script.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Skip pure marker lines
        if re.match(r"^\[([A-Z_0-9]+)\]$", stripped):
            continue

        # Strip inline markers: "[STORY_1] A: text" → "A: text"
        stripped = re.sub(r"^\[([A-Z_0-9]+)\]\s*", "", stripped)

        # Map speaker tags
        sp_match = re.match(r"^([AB]):\s*(.+)$", stripped)
        if sp_match:
            speaker = "Anchor" if sp_match.group(1) == "A" else "Analyst"
            text = sp_match.group(2)
        else:
            # Continuation or untagged — assign to Anchor
            speaker = "Anchor"
            text = stripped

        # Clean Gemini artifacts
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"\[(\d+)\]", "", text)
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"`+", "", text)
        text = re.sub(r"\(\s*\)", "", text)
        text = re.sub(r"  +", " ", text).strip()

        if text:
            lines.append(f"{speaker}: {text}")

    return "\n".join(lines)


def _synthesize_gemini_tts(
    dialogue: str,
    voice_a: str,
    voice_b: str,
) -> Optional[bytes]:
    """Generate two-speaker audio via Gemini 2.5 Flash TTS.

    Args:
        dialogue: "Anchor: ...\nAnalyst: ..." formatted dialogue.
        voice_a: Gemini prebuilt voice name for Anchor (e.g., "Charon").
        voice_b: Gemini prebuilt voice name for Analyst (e.g., "Aoede").

    Returns raw PCM audio bytes (24kHz 16-bit mono), or None on failure.
    """
    if not GEMINI_TTS_AVAILABLE:
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  [warn][audio] GEMINI_API_KEY not set")
        return None

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=_TTS_MODEL,
            contents=dialogue,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker="Anchor",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_a,
                                    )
                                ),
                            ),
                            types.SpeakerVoiceConfig(
                                speaker="Analyst",
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

        print("  [warn][audio] Gemini TTS returned no audio data")
        return None

    except Exception as e:
        print(f"  [warn][audio] Gemini TTS synthesis failed: {e}")
        return None


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Convert raw PCM (16-bit mono) to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _load_asset(filename: str) -> Optional["AudioSegment"]:
    """Load a pre-recorded audio asset from the assets directory."""
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


def produce_audio(
    audio_script: str,
    voices: dict,
    edition: str,
) -> Optional[dict]:
    """
    Synthesize a two-host broadcast via Gemini Flash TTS and upload to Supabase.

    Uses LLM-native multi-speaker synthesis — the model generates both speakers
    in a single pass with natural conversational rhythm. No per-turn stitching.

    Args:
        audio_script: Full broadcast script with [MARKER] + A:/B: speaker tags.
        voices: {"host_a": {"id": "Charon", ...}, "host_b": {"id": "Aoede", ...}}
        edition: Edition slug (world/us/india).

    Returns dict with audio_url, duration_seconds, file_size, or None.
    """
    if not GEMINI_TTS_AVAILABLE:
        print("  [audio] google-genai SDK not installed — skipping")
        return None

    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping")
        return None

    voice_a_name = voices["host_a"]["id"]
    voice_b_name = voices["host_b"]["id"]

    # Convert script to Gemini dialogue format
    dialogue = _script_to_dialogue(audio_script)
    word_count = len(dialogue.split())
    print(f"  [audio] Gemini TTS: {word_count} words, voices {voice_a_name}+{voice_b_name}")

    # Synthesize via Gemini Flash TTS
    pcm_data = _synthesize_gemini_tts(dialogue, voice_a_name, voice_b_name)
    if not pcm_data:
        print("  [warn][audio] Gemini TTS synthesis failed — no audio")
        return None

    dialogue_duration = len(pcm_data) / (24000 * 2)
    print(f"  [audio] Gemini TTS returned {dialogue_duration:.1f}s of dialogue")

    # Convert PCM to WAV AudioSegment
    wav_data = _pcm_to_wav(pcm_data)
    dialogue_seg = AudioSegment.from_wav(io.BytesIO(wav_data))

    # Assemble: pips + countdown + dialogue + outro
    combined = AudioSegment.empty()

    pips = _load_asset("pips.wav")
    if pips:
        combined += pips
    combined += AudioSegment.silent(duration=300)

    countdown = _load_asset("countdown.wav")
    if countdown:
        combined += countdown
    combined += AudioSegment.silent(duration=500)

    combined += dialogue_seg

    combined += AudioSegment.silent(duration=300)
    outro = _load_asset("outro.wav")
    if outro:
        combined += outro

    if len(combined) == 0:
        print("  [warn][audio] Combined audio is empty — aborting")
        return None

    duration_seconds = round(len(combined) / 1000.0, 1)
    print(f"  [audio] Assembled {duration_seconds}s total for {edition}")

    # Export to MP3 128kbps mono
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        combined.export(
            tmp_path,
            format="mp3",
            bitrate="128k",
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
