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

# Segment markers in order of broadcast (clean BBC style — no sound effects)
_SEGMENT_ORDER = [
    "GREETING",
    "HEADLINES",
    "STORY_1",
    "STORY_2",
    "STORY_3",
    "EDITORIAL_NOTE",
    "SIGNOFF",
]

# Silence gaps (ms) inserted AFTER each segment — deliberate broadcast pacing
_SILENCE_AFTER: dict[str, int] = {
    "GREETING": 900,          # Pause before headlines — gravitas
    "HEADLINES": 1000,        # Pause after headlines before first story
    "STORY_1": 800,           # Breath between stories
    "STORY_2": 800,
    "STORY_3": 900,           # Longer pause before editorial note
    "EDITORIAL_NOTE": 700,    # Pause before sign-off
    "SIGNOFF": 0,
}


def _parse_script(script: str) -> list[tuple[str, str, str]]:
    """
    Parse a two-host audio script into a list of (marker, speaker, text) tuples.

    Input format:
        [GREETING]
        A: Good evening. This is void news.
        B: Good evening. Plenty to cover.
        [STORY_1]
        A: Our lead story...
        B: What's notable here...

    Returns:
        [("GREETING", "A", "Good evening. This is void news."),
         ("GREETING", "B", "Good evening. Plenty to cover."),
         ("STORY_1", "A", "Our lead story..."),
         ("STORY_1", "B", "What's notable here...")]

    Lines without A:/B: prefix are assigned to "A" (anchor) by default.
    """
    turns: list[tuple[str, str, str]] = []
    current_marker: str = "GREETING"
    current_speaker: str = "A"
    current_lines: list[str] = []

    def _flush():
        text = " ".join(current_lines).strip()
        if text:
            turns.append((current_marker, current_speaker, text))
        current_lines.clear()

    for line in script.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Detect [MARKER] lines
        marker_match = re.match(r"^\[([A-Z_]+)\](.*)$", stripped)
        if marker_match:
            _flush()
            current_marker = marker_match.group(1)
            inline = marker_match.group(2).strip()
            if inline:
                # Check if inline text has speaker tag
                sp_match = re.match(r"^([AB]):\s*(.+)$", inline)
                if sp_match:
                    current_speaker = sp_match.group(1)
                    current_lines.append(sp_match.group(2))
                else:
                    current_speaker = "A"
                    current_lines.append(inline)
            continue

        # Detect speaker tags: "A: ..." or "B: ..."
        sp_match = re.match(r"^([AB]):\s*(.+)$", stripped)
        if sp_match:
            _flush()
            current_speaker = sp_match.group(1)
            current_lines.append(sp_match.group(2))
        else:
            # Continuation of current speaker's turn
            current_lines.append(stripped)

    _flush()
    return turns


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
            speaking_rate=0.9,   # Slower, measured BBC broadcast pace
            pitch=-1.0,          # Slightly deeper — authoritative
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
        fmt = "wav" if filename.endswith(".wav") else "mp3"
        return AudioSegment.from_file(str(path), format=fmt)
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
    voices: dict,
    edition: str,
) -> Optional[dict]:
    """
    Synthesize a two-host broadcast from the script and upload to Supabase.

    Args:
        audio_script: Full broadcast script with [MARKER] + A:/B: speaker tags.
        voices: {"host_a": {"id": ..., "language_code": ...},
                 "host_b": {"id": ..., "language_code": ...}}
        edition: Edition slug (world/us/india), used for storage path.

    Returns dict with audio_url, duration_seconds, file_size (bytes),
    or None if synthesis is unavailable or fails.
    """
    if not TTS_AVAILABLE:
        print("  [audio] google-cloud-texttospeech not installed — skipping")
        return None

    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping")
        return None

    # Parse script into speaker-tagged turns
    turns = _parse_script(audio_script)
    if not turns:
        print("  [warn][audio] Script parsing produced no turns")
        return None

    voice_a = voices["host_a"]
    voice_b = voices["host_b"]
    print(f"  [audio] Synthesizing {len(turns)} turns for {edition} "
          f"(A: {voice_a['id']}, B: {voice_b['id']})")

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

    def _clean_tts_text(text: str) -> str:
        """Remove leaked marker names or speaker tags from TTS text."""
        text = re.sub(r"\[/?[A-Z_]+\]", "", text)
        text = re.sub(r"^[AB]:\s*", "", text)
        text = re.sub(r"\b(?:STORY|HEADLINE|GREETING|SIGNOFF|EDITORIAL)[_ ]?\d*:?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"  +", " ", text).strip()
        return text

    # ── Stitching sequence ──────────────────────────────────────────────────

    # 1. BBC pips + countdown intro
    pips = _load_asset("pips.wav")
    _append(pips, "pips")
    _append_silence(300)

    countdown = _load_asset("countdown.wav")
    _append(countdown, "countdown")
    _append_silence(500)

    # 2. Two-host narration — alternate voices per speaker tag
    prev_marker = None
    for marker, speaker, text in turns:
        text = _clean_tts_text(text)
        if not text:
            continue

        # Add section pause when marker changes
        if prev_marker is not None and marker != prev_marker:
            _append_silence(_SILENCE_AFTER.get(prev_marker, 400))

        # Select voice based on speaker
        voice = voice_a if speaker == "A" else voice_b
        mp3_bytes = _synthesize_segment(text, voice["id"], voice["language_code"])
        if mp3_bytes:
            seg = _bytes_to_segment(mp3_bytes)
            _append(seg, f"{marker}:{speaker}")
        else:
            print(f"  [warn][audio] TTS failed for [{marker}:{speaker}] — skipped")

        # Short gap between speaker turns within the same section
        _append_silence(150)
        prev_marker = marker

    # Final section pause
    if prev_marker:
        _append_silence(_SILENCE_AFTER.get(prev_marker, 0))

    # 3. Soft chime + bass outro
    _append_silence(300)
    outro = _load_asset("outro.wav")
    _append(outro, "outro")

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
