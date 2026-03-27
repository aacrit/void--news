"""Voice rotation for two-voice daily audio briefs.

Uses Gemini 2.5 Flash TTS prebuilt voices. Each edition gets a distinct
voice pair. Voices swap on alternate days for variety.

30 available voices: Achernar, Achird, Algenib, Algieba, Alnilam, Aoede,
Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux,
Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi,
Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr,
Zubenelgenubi.
"""

from datetime import datetime, timezone

VOICE_PAIRS: dict[str, dict[str, dict]] = {
    "world": {
        "voice_a": {"id": "Charon"},
        "voice_b": {"id": "Aoede"},
        "voice_opinion": {"id": "Fenrir"},
    },
    "us": {
        "voice_a": {"id": "Enceladus"},
        "voice_b": {"id": "Kore"},
        "voice_opinion": {"id": "Sadachbia"},
    },
    "india": {
        "voice_a": {"id": "Puck"},
        "voice_b": {"id": "Leda"},
        "voice_opinion": {"id": "Gacrux"},
    },
    "uk": {
        "voice_a": {"id": "Achird"},
        "voice_b": {"id": "Rasalgethi"},
        "voice_opinion": {"id": "Sulafat"},
    },
    "canada": {
        "voice_a": {"id": "Algieba"},
        "voice_b": {"id": "Umbriel"},
        "voice_opinion": {"id": "Vindemiatrix"},
    },
}


def get_voices_for_today(edition: str) -> dict:
    """Return voice config for today's broadcast.

    News hosts swap daily (UTC day-of-year parity) for variety.
    Opinion voice stays fixed per edition for brand consistency.
    """
    day = datetime.now(timezone.utc).timetuple().tm_yday
    pair = VOICE_PAIRS.get(edition, VOICE_PAIRS["world"])

    if day % 2 == 0:
        return {
            "host_a": pair["voice_a"],
            "host_b": pair["voice_b"],
            "opinion": pair["voice_opinion"],
        }
    else:
        return {
            "host_a": pair["voice_b"],
            "host_b": pair["voice_a"],
            "opinion": pair["voice_opinion"],
        }


def get_voice_for_today(edition: str) -> dict:
    """Return a single voice for backward compatibility."""
    return get_voices_for_today(edition)["host_a"]
