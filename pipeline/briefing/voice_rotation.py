"""Voice rotation for two-host daily audio briefs.

Uses Gemini 2.5 Flash TTS prebuilt voices. Each edition gets a distinct
voice pair. Roles (anchor vs analyst) swap on alternate days.

30 available voices: Achernar, Achird, Algenib, Algieba, Alnilam, Aoede,
Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux,
Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi,
Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr,
Zubenelgenubi.
"""

from datetime import datetime, timezone

# Gemini TTS voice pairs per edition — chosen for broadcast clarity + contrast
VOICE_PAIRS: dict[str, dict[str, dict]] = {
    "world": {
        "anchor": {"id": "Charon",  "label": "Charon (deep, authoritative)"},
        "analyst": {"id": "Aoede",  "label": "Aoede (warm, conversational)"},
    },
    "us": {
        "anchor": {"id": "Enceladus", "label": "Enceladus (steady, clear)"},
        "analyst": {"id": "Kore",     "label": "Kore (bright, analytical)"},
    },
    "india": {
        "anchor": {"id": "Puck",     "label": "Puck (measured, precise)"},
        "analyst": {"id": "Leda",     "label": "Leda (warm, engaging)"},
    },
}


def get_voices_for_today(edition: str) -> dict:
    """
    Return a two-host voice pair for today's broadcast.

    On even days: first voice = Anchor (Host A), second = Analyst (Host B).
    On odd days: roles swap for variety.

    Returns:
        {
            "host_a": {"id": "Charon", "label": "...", ...},
            "host_b": {"id": "Aoede", "label": "...", ...},
        }
    """
    day = datetime.now(timezone.utc).timetuple().tm_yday
    pair = VOICE_PAIRS.get(edition, VOICE_PAIRS["world"])

    if day % 2 == 0:
        return {"host_a": pair["anchor"], "host_b": pair["analyst"]}
    else:
        return {"host_a": pair["analyst"], "host_b": pair["anchor"]}


# Backward compat
def get_voice_for_today(edition: str) -> dict:
    """Return a single voice for backward compatibility."""
    return get_voices_for_today(edition)["host_a"]
