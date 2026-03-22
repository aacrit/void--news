"""
Audio producer for the void --news daily brief.

Multi-engine TTS: edge-tts (free, $0) primary, Google Cloud TTS Neural2
fallback. Parses broadcast script into segments, synthesizes per-speaker
with SSML prosody, stitches with pydub, exports MP3 128kbps mono, uploads
to Supabase Storage.

Engine priority: edge-tts → Google Cloud TTS → skip (text-only brief).
"""

import asyncio
import io
import random
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# TTS engines — try edge-tts first ($0, no API key), then Google Cloud
EDGE_TTS_AVAILABLE = False
GCLOUD_TTS_AVAILABLE = False
PYDUB_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass

try:
    from google.cloud import texttospeech
    GCLOUD_TTS_AVAILABLE = True
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

# Speaker-specific prosody — Host A (anchor) is steady, Host B (analyst) warmer
_SPEAKER_PROSODY: dict[str, dict[str, str]] = {
    "A": {"rate": "92%",  "pitch": "-0.5st"},   # Measured, authoritative
    "B": {"rate": "96%",  "pitch": "+0.5st"},   # Slightly warmer, conversational
}

# Inter-turn silence ranges (ms) — randomized for natural feel
_INTER_TURN_SILENCE = {
    "same_speaker": (60, 120),     # Continuation — short breath
    "speaker_switch": (120, 280),  # Handoff — natural pause before next speaker
}


def _wrap_ssml(text: str, speaker: str) -> str:
    """Wrap cleaned text in SSML with speaker-specific prosody and micro-pauses.

    Adds:
    - Speaker rate/pitch via <prosody>
    - Sentence-boundary <break> tags (100-250ms) for natural breathing
    - Slightly longer pause before em-dashes (editorial pause)
    """
    # Escape XML special characters before adding SSML markup
    text = text.replace("&", "&amp;").replace('"', "&quot;")

    pros = _SPEAKER_PROSODY.get(speaker, _SPEAKER_PROSODY["A"])

    # Insert micro-pauses at sentence boundaries (. ! ?) for breathing
    # but not inside abbreviations like "U.S." or "Dr."
    def _add_sentence_breaks(t: str) -> str:
        # Split on sentence-ending punctuation followed by space + capital
        parts = re.split(r'([.!?])\s+(?=[A-Z])', t)
        result = []
        i = 0
        while i < len(parts):
            result.append(parts[i])
            if i + 1 < len(parts) and parts[i + 1] in ".!?":
                result.append(parts[i + 1])
                pause_ms = random.randint(100, 250)
                result.append(f' <break time="{pause_ms}ms"/> ')
                i += 2
            else:
                i += 1
        return "".join(result)

    text = _add_sentence_breaks(text)

    # Add editorial pause before em-dashes
    text = text.replace(" — ", f' <break time="{random.randint(150, 300)}ms"/> — ')

    return (
        f'<speak>'
        f'<prosody rate="{pros["rate"]}" pitch="{pros["pitch"]}">'
        f'{text}'
        f'</prosody>'
        f'</speak>'
    )


def _random_inter_turn_silence(prev_speaker: str, current_speaker: str) -> int:
    """Return a randomized silence duration (ms) based on speaker transition type."""
    if prev_speaker == current_speaker:
        lo, hi = _INTER_TURN_SILENCE["same_speaker"]
    else:
        lo, hi = _INTER_TURN_SILENCE["speaker_switch"]
    return random.randint(lo, hi)


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
        marker_match = re.match(r"^\[([A-Z_0-9]+)\](.*)$", stripped)
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


def _synthesize_edge_tts(
    text: str,
    voice_id: str,
    speaker: str,
) -> Optional[bytes]:
    """Synthesize via edge-tts (Microsoft Neural, free, $0).

    edge-tts does not support full SSML — only basic <prosody> inside a
    single <voice> tag. We pass rate/pitch per speaker through the
    edge-tts rate/pitch parameters instead.

    Returns raw MP3 bytes, or None on failure.
    """
    if not EDGE_TTS_AVAILABLE:
        return None

    pros = _SPEAKER_PROSODY.get(speaker, _SPEAKER_PROSODY["A"])
    # edge-tts rate format: "+10%" or "-8%"; convert from "92%" → "-8%"
    rate_pct = int(pros["rate"].rstrip("%")) - 100
    rate_str = f"{rate_pct:+d}%"
    # edge-tts pitch format: "+0.5st" → "+50Hz" (approx; 1 semitone ≈ 50Hz)
    pitch_st = float(pros["pitch"].rstrip("st"))
    pitch_hz = int(pitch_st * 50)
    pitch_str = f"{pitch_hz:+d}Hz"

    try:
        communicate = edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str)
        mp3_chunks = []

        async def _synth():
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_chunks.append(chunk["data"])

        # Run in existing or new event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(lambda: asyncio.run(_synth())).result(timeout=30)
        else:
            asyncio.run(_synth())

        if mp3_chunks:
            return b"".join(mp3_chunks)
        return None

    except Exception as e:
        print(f"  [warn][audio] edge-tts synthesis failed: {e}")
        return None


def _synthesize_gcloud(
    text: str,
    voice_id: str,
    language_code: str,
    ssml: bool = False,
) -> Optional[bytes]:
    """Synthesize via Google Cloud TTS Neural2 (fallback, costs money).

    Returns raw MP3 bytes, or None on failure.
    """
    if not GCLOUD_TTS_AVAILABLE:
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

        # When using SSML, prosody is controlled per-speaker via <prosody> tags.
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0 if ssml else 0.9,
            pitch=0.0 if ssml else -1.0,
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        return response.audio_content

    except Exception as e:
        print(f"  [warn][audio] Google Cloud TTS failed: {e}")
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


def _inject_disfluencies(text: str, speaker: str, marker: str) -> str:
    """Add natural speech patterns to make TTS output sound less robotic.

    Host B gets more disfluencies (analyst reacting); Host A stays cleaner
    (anchor delivering facts). Applied before TTS synthesis.
    """
    # Don't touch very short turns (reactions like "Mm.", "Right.")
    if len(text) < 20:
        return text

    # Host B: occasional filler at sentence start (~30% chance)
    if speaker == "B" and random.random() < 0.3:
        fillers = ["Well, ", "You know, ", "Now, ", "Look, ", "So, "]
        # Only prepend if text doesn't already start with a filler
        if not any(text.startswith(f) for f in fillers):
            text = random.choice(fillers) + text[0].lower() + text[1:]

    # Both hosts: add comma pauses at conjunctions (~25% chance per occurrence)
    if random.random() < 0.25:
        # Add breathing comma before "and" / "but" / "or" in mid-sentence
        text = re.sub(r'(?<=[a-z]) (and|but|or) ', lambda m: f', {m.group(1)} ', text, count=1)

    # Host A in editorial/signoff: slightly warmer trailing comma
    if speaker == "A" and marker in ("EDITORIAL_NOTE", "SIGNOFF"):
        # Avoid redundancy — skip if text already contains the softener phrase
        has_time_ref = any(w in text.lower() for w in ["this hour", "tonight", "this evening", "for now"])
        if random.random() < 0.4 and ", " not in text[-30:] and not has_time_ref:
            last_period = text.rfind(".")
            if last_period > 20:
                softeners = [", at this hour", ", for now", ", it seems"]
                text = text[:last_period] + random.choice(softeners) + text[last_period:]

    return text


def _detect_tts_engine() -> Optional[str]:
    """Detect the best available TTS engine. Returns 'edge' or 'gcloud' or None."""
    if EDGE_TTS_AVAILABLE:
        return "edge"
    if GCLOUD_TTS_AVAILABLE:
        return "gcloud"
    return None


def produce_audio(
    audio_script: str,
    voices: dict,
    edition: str,
) -> Optional[dict]:
    """
    Synthesize a two-host broadcast from the script and upload to Supabase.

    Engine priority: edge-tts ($0) → Google Cloud TTS (paid fallback).

    Args:
        audio_script: Full broadcast script with [MARKER] + A:/B: speaker tags.
        voices: {"host_a": {"id": ..., "language_code": ...},
                 "host_b": {"id": ..., "language_code": ...}}
        edition: Edition slug (world/us/india), used for storage path.

    Returns dict with audio_url, duration_seconds, file_size (bytes),
    or None if synthesis is unavailable or fails.
    """
    engine = _detect_tts_engine()
    if engine is None:
        print("  [audio] No TTS engine available (need edge-tts or google-cloud-texttospeech)")
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
    print(f"  [audio] Synthesizing {len(turns)} turns for {edition} via {engine} "
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
        """Remove leaked markers, speaker tags, and Gemini artifacts from TTS text.
        Ensures only clean prose reaches the TTS engine — no random characters."""
        # Strip structural markers and speaker tags
        text = re.sub(r"\[/?[A-Z_]+\]", "", text)
        text = re.sub(r"^[AB]:\s*", "", text)
        text = re.sub(r"\b(?:STORY|HEADLINE|GREETING|SIGNOFF|EDITORIAL)[_ ]?\d*:?\s*", "", text, flags=re.IGNORECASE)
        # Strip Gemini artifacts: asterisks, citation brackets, markdown
        text = re.sub(r"\*+", "", text)                  # **bold** or *italic*
        text = re.sub(r"\[(\d+)\]", "", text)            # [1], [2] citations
        text = re.sub(r"#{1,6}\s*", "", text)            # ### headings
        text = re.sub(r"`+", "", text)                   # `code`
        text = re.sub(r"[<>]", "", text)                 # stray HTML angle brackets
        text = re.sub(r"\(\s*\)", "", text)               # empty parens ()
        text = re.sub(r"—{2,}", "—", text)               # collapsed em-dashes
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

    # 2. Two-host narration — alternate voices per speaker tag, SSML prosody
    prev_marker = None
    prev_speaker = None
    for marker, speaker, text in turns:
        text = _clean_tts_text(text)
        if not text:
            continue

        # Add natural speech disfluencies
        text = _inject_disfluencies(text, speaker, marker)

        # Add section pause when marker changes
        if prev_marker is not None and marker != prev_marker:
            _append_silence(_SILENCE_AFTER.get(prev_marker, 400))

        # Select voice based on speaker
        voice = voice_a if speaker == "A" else voice_b

        # Synthesize with active engine
        if engine == "edge":
            # edge-tts handles prosody via rate/pitch params, not SSML
            mp3_bytes = _synthesize_edge_tts(text, voice["id"], speaker)
        else:
            # Google Cloud TTS uses full SSML with prosody tags
            ssml_text = _wrap_ssml(text, speaker)
            mp3_bytes = _synthesize_gcloud(
                ssml_text, voice["id"], voice["language_code"], ssml=True,
            )
        if mp3_bytes:
            seg = _bytes_to_segment(mp3_bytes)
            _append(seg, f"{marker}:{speaker}")
        else:
            print(f"  [warn][audio] TTS failed for [{marker}:{speaker}] — skipped")

        # Variable inter-turn silence based on speaker transition
        gap = _random_inter_turn_silence(
            prev_speaker or speaker, speaker,
        )
        _append_silence(gap)
        prev_marker = marker
        prev_speaker = speaker

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
