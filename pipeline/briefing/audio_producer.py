"""
Audio producer for the void --news daily brief.

Uses Gemini 2.5 Flash TTS for native LLM-powered multi-speaker dialogue.
Both speakers generated in a single API call — no per-turn stitching.

Post-processing via pydub:
  - Intro ident (0.8s ascending A-major triad)
  - Background bed (85/170/520 Hz sine layers, barely audible)
  - Section transitions (descending two-note at detected silence gaps)
  - Outro ident (1.2s reversed intro motif)
  - MP3 128k mono export → Supabase Storage
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
    from pydub.silence import detect_silence
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

def _synthesize_gemini_tts(
    dialogue: str,
    voice_a: str,
    voice_b: str,
) -> Optional[bytes]:
    """Generate two-speaker audio via Gemini 2.5 Flash TTS.

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

        print("  [warn][audio] Gemini TTS returned no audio data")
        return None

    except Exception as e:
        print(f"  [warn][audio] Gemini TTS synthesis failed: {e}")
        return None


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


def _insert_section_transitions(dialogue_seg: "AudioSegment") -> "AudioSegment":
    """Detect silence gaps (story breaks) and overlay transition tones.

    Looks for silence ≥800ms at -35dB — these are structural breaks between
    stories, not natural speech pauses (which are 200-500ms). Overlays a
    subtle descending two-note transition at the midpoint of each gap.

    If no gaps found, returns dialogue unchanged.
    """
    transition = _load_asset("transition.wav")
    if not transition:
        return dialogue_seg

    try:
        silences = detect_silence(dialogue_seg, min_silence_len=800, silence_thresh=-35)
    except Exception:
        return dialogue_seg

    if not silences:
        return dialogue_seg

    result = dialogue_seg
    inserted = 0
    for start_ms, end_ms in silences:
        midpoint = (start_ms + end_ms) // 2
        # Center the transition tone at the midpoint
        insert_pos = midpoint - len(transition) // 2
        if insert_pos > 0:
            result = result.overlay(transition, position=insert_pos)
            inserted += 1

    if inserted:
        print(f"  [audio] Inserted {inserted} section transition(s)")
    return result


def _apply_background_bed(audio_seg: "AudioSegment") -> "AudioSegment":
    """Overlay a broadcast-floor presence bed under the full audio.

    Three stacked sine layers at -32/-36/-40 dB: felt more than heard.
    Gives the audio a produced quality without competing with speech.
    """
    try:
        from briefing.generate_assets import build_background_bed
    except ImportError:
        # Inline fallback if import fails
        return audio_seg

    try:
        bed = build_background_bed(len(audio_seg))
        return audio_seg.overlay(bed)
    except Exception as e:
        print(f"  [warn][audio] Background bed failed: {e}")
        return audio_seg


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

def produce_audio(
    audio_script: str,
    voices: dict,
    edition: str,
) -> Optional[dict]:
    """
    Synthesize a two-voice news update via Gemini Flash TTS.

    Pipeline:
      1. Script → dialogue format (One:/Two:)
      2. Gemini Flash TTS → single PCM output
      3. PCM → WAV → AudioSegment
      4. Insert section transitions at detected silence gaps
      5. Apply background bed
      6. Assemble: ident + dialogue + outro
      7. Export MP3 → Supabase upload
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

    # 4. Insert section transitions at story breaks
    dialogue_seg = _insert_section_transitions(dialogue_seg)

    # 5. Apply background bed
    dialogue_seg = _apply_background_bed(dialogue_seg)

    # 6. Assemble: ident + gap + dialogue + gap + outro
    combined = AudioSegment.empty()

    ident = _load_asset("ident.wav")
    if ident:
        combined += ident
    combined += AudioSegment.silent(duration=200)

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

    # 7. Export to MP3 128kbps mono
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
