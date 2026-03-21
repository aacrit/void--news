"""
Audio producer for the void --news daily brief.

Parses the audio broadcast script into segments, synthesizes speech via
Google Cloud TTS Neural2, stitches segments with pre-recorded assets and
silence gaps using pydub, exports as MP3 128kbps mono, and uploads to
Supabase Storage.

Returns None gracefully if google-cloud-texttospeech or pydub are not
installed, or if credentials are missing. TL;DR text still works without
this module.
"""

import io
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Both google-cloud-texttospeech and pydub are optional
TTS_AVAILABLE = False
PYDUB_AVAILABLE = False

try:
    from google.cloud import texttospeech
    TTS_AVAILABLE = True
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

# Segment markers in order of broadcast
_SEGMENT_ORDER = [
    "COUNTDOWN",
    "GREETING",
    "HEADLINES",
    "STORY_1",
    "STORY_2",
    "STORY_3",
    "EDITORIAL_NOTE",
    "SIGNOFF",
]

# Silence gaps (ms) inserted AFTER each segment in the stitch sequence
_SILENCE_AFTER: dict[str, int] = {
    "PIPS": 200,
    "COUNTDOWN": 0,      # ident follows immediately after countdown TTS
    "IDENT": 300,
    "GREETING": 500,
    "HEADLINES": 600,
    "STORY_1": 400,
    "STORY_2": 400,
    "STORY_3": 500,
    "EDITORIAL_NOTE": 400,
    "SIGNOFF": 300,
    "OUTRO": 0,
}

# SSML wrapper for countdown — slow prosody for gravitas
_COUNTDOWN_SSML_TEMPLATE = (
    '<speak><prosody rate="slow">{text}</prosody></speak>'
)


def _parse_script(script: str) -> dict[str, str]:
    """
    Parse the audio script into a dict of marker -> segment text.

    Markers are lines in the format [MARKER_NAME] followed by text
    on subsequent lines until the next marker or end of script.
    The marker name is stored without brackets.
    """
    segments: dict[str, str] = {}
    current_marker: Optional[str] = None
    current_lines: list[str] = []

    for line in script.splitlines():
        # Detect [MARKER] lines (bracket-enclosed, uppercase)
        marker_match = re.match(r"^\[([A-Z_]+)\](.*)$", line.strip())
        if marker_match:
            # Save previous segment
            if current_marker is not None:
                segments[current_marker] = " ".join(current_lines).strip()
            current_marker = marker_match.group(1)
            # Text may appear on the same line as the marker
            inline_text = marker_match.group(2).strip()
            current_lines = [inline_text] if inline_text else []
        elif current_marker is not None:
            text = line.strip()
            if text:
                current_lines.append(text)

    # Save last segment
    if current_marker is not None:
        segments[current_marker] = " ".join(current_lines).strip()

    return segments


def _synthesize_segment(
    text: str,
    voice_id: str,
    language_code: str,
    ssml: bool = False,
) -> Optional[bytes]:
    """
    Synthesize a text segment via Google Cloud TTS Neural2.

    Args:
        text: Plain text or SSML string.
        voice_id: Neural2 voice name (e.g. "en-GB-Neural2-B").
        language_code: BCP-47 language code (e.g. "en-GB").
        ssml: If True, text is treated as SSML.

    Returns raw MP3 bytes, or None on failure.
    """
    if not TTS_AVAILABLE:
        return None

    try:
        client = texttospeech.TextToSpeechClient()

        if ssml:
            synthesis_input = texttospeech.SynthesisInput(ssml=text)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_id,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0,
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return response.audio_content

    except Exception as e:
        print(f"  [warn][audio] TTS synthesis failed: {e}")
        return None


def _load_asset(filename: str) -> Optional["AudioSegment"]:
    """
    Load a pre-recorded audio asset from the assets directory.

    Returns None if the file does not exist (asset not yet generated).
    """
    if not PYDUB_AVAILABLE:
        return None
    path = ASSETS_DIR / filename
    if not path.exists():
        return None
    try:
        return AudioSegment.from_mp3(str(path))
    except Exception as e:
        print(f"  [warn][audio] Failed to load asset {filename}: {e}")
        return None


def _silence(ms: int) -> "AudioSegment":
    """Return a silent AudioSegment of the given duration."""
    return AudioSegment.silent(duration=ms)


def _bytes_to_segment(mp3_bytes: bytes) -> Optional["AudioSegment"]:
    """Convert raw MP3 bytes to an AudioSegment."""
    if not PYDUB_AVAILABLE:
        return None
    try:
        buf = io.BytesIO(mp3_bytes)
        return AudioSegment.from_mp3(buf)
    except Exception as e:
        print(f"  [warn][audio] Failed to decode MP3 bytes: {e}")
        return None


def _upload_to_supabase(
    audio_bytes: bytes,
    edition: str,
) -> Optional[str]:
    """
    Upload the audio file to Supabase Storage.

    Bucket: audio-briefs
    Path: {edition}/latest.mp3

    Returns the public URL on success, None on failure.
    """
    try:
        # Import supabase client from pipeline utils
        from utils.supabase_client import supabase

        path = f"{edition}/latest.mp3"
        supabase.storage.from_("audio-briefs").upload(
            path,
            audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )
        public_url = supabase.storage.from_("audio-briefs").get_public_url(path)
        return public_url
    except Exception as e:
        print(f"  [warn][audio] Supabase upload failed for {edition}: {e}")
        return None


def produce_audio(
    audio_script: str,
    voice_id: str,
    language_code: str,
    edition: str,
) -> Optional[dict]:
    """
    Synthesize the broadcast audio from the script and upload to Supabase.

    Stitching sequence:
      pips.mp3 → 200ms silence
      → TTS: Countdown (SSML slow rate)
      → ident.mp3 → 300ms silence
      → TTS: Greeting → 500ms silence
      → TTS: Headlines → 600ms silence
      → TTS: Story 1 → 400ms silence
      → TTS: Story 2 → 400ms silence
      → TTS: Story 3 → 500ms silence
      → TTS: Editorial note → 400ms silence
      → TTS: Sign-off → 300ms silence
      → outro.mp3

    Args:
        audio_script: Full broadcast script with [MARKER] segments.
        voice_id: Google Cloud TTS Neural2 voice name.
        language_code: BCP-47 code matching the voice.
        edition: Edition slug (world/us/india), used for storage path.

    Returns dict with audio_url, duration_seconds, file_size (bytes),
    or None if synthesis is unavailable or fails.
    """
    if not TTS_AVAILABLE:
        print("  [audio] google-cloud-texttospeech not installed — skipping audio production")
        return None

    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping audio production")
        return None

    # Parse script into segments
    segments = _parse_script(audio_script)
    if not segments:
        print("  [warn][audio] Script parsing produced no segments")
        return None

    print(f"  [audio] Synthesizing {len(segments)} segments for {edition} edition "
          f"(voice: {voice_id})")

    # Build stitch sequence
    combined: AudioSegment = AudioSegment.empty()

    def _append(segment: Optional["AudioSegment"], label: str) -> None:
        nonlocal combined
        if segment is None:
            print(f"  [warn][audio] Missing segment '{label}' — skipping")
            return
        combined += segment

    def _append_silence(ms: int) -> None:
        nonlocal combined
        if ms > 0:
            combined += _silence(ms)

    def _append_tts(marker: str, ssml: bool = False) -> None:
        """Synthesize and append a script segment."""
        text = segments.get(marker, "").strip()
        if not text:
            print(f"  [warn][audio] No text for marker [{marker}] — skipping")
            return
        if ssml:
            text = _COUNTDOWN_SSML_TEMPLATE.format(text=text)
        mp3_bytes = _synthesize_segment(text, voice_id, language_code, ssml=ssml)
        if mp3_bytes:
            seg = _bytes_to_segment(mp3_bytes)
            _append(seg, marker)
        else:
            print(f"  [warn][audio] TTS failed for [{marker}] — segment omitted")

    # ── Stitching sequence ──────────────────────────────────────────────────

    # 1. Pips asset
    pips = _load_asset("pips.mp3")
    _append(pips, "pips")
    _append_silence(_SILENCE_AFTER["PIPS"])

    # 2. Countdown (slow SSML)
    _append_tts("COUNTDOWN", ssml=True)
    _append_silence(_SILENCE_AFTER["COUNTDOWN"])

    # 3. Ident asset
    ident = _load_asset("ident.mp3")
    _append(ident, "ident")
    _append_silence(_SILENCE_AFTER["IDENT"])

    # 4. Greeting
    _append_tts("GREETING")
    _append_silence(_SILENCE_AFTER["GREETING"])

    # 5. Headlines
    _append_tts("HEADLINES")
    _append_silence(_SILENCE_AFTER["HEADLINES"])

    # 6. Stories 1-3
    for story_marker in ("STORY_1", "STORY_2", "STORY_3"):
        _append_tts(story_marker)
        _append_silence(_SILENCE_AFTER[story_marker])

    # 7. Editorial note
    _append_tts("EDITORIAL_NOTE")
    _append_silence(_SILENCE_AFTER["EDITORIAL_NOTE"])

    # 8. Sign-off
    _append_tts("SIGNOFF")
    _append_silence(_SILENCE_AFTER["SIGNOFF"])

    # 9. Outro asset
    outro = _load_asset("outro.mp3")
    _append(outro, "outro")
    _append_silence(_SILENCE_AFTER["OUTRO"])

    if len(combined) == 0:
        print("  [warn][audio] Combined audio is empty — aborting")
        return None

    duration_seconds = round(len(combined) / 1000.0, 1)
    print(f"  [audio] Assembled {duration_seconds}s of audio for {edition}")

    # Export to MP3 128kbps mono
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        combined.export(
            tmp_path,
            format="mp3",
            bitrate="128k",
            parameters=["-ac", "1"],  # mono
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

    # Upload to Supabase Storage
    public_url = _upload_to_supabase(audio_bytes, edition)
    if not public_url:
        return None

    print(f"  [audio] Uploaded: {public_url}")
    return {
        "audio_url": public_url,
        "duration_seconds": duration_seconds,
        "file_size": file_size,
    }
