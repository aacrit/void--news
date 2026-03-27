"""Voice rotation for the void --news audio broadcast.

Uses Gemini 2.5 Flash TTS prebuilt voices. Newsroom model: 5 male hosts
and 5 female hosts rotate across runs so each broadcast sounds fresh.
Opinion voice is a separate fixed pool per edition.

Rotation: pipeline_run_count (4x daily) cycles through host pairs.
Day 1 run 1 gets pair 0, run 2 gets pair 1, etc. 5 pairs = 20 runs
(5 days) before repeating.

30 available voices: Achernar, Achird, Algenib, Algieba, Alnilam, Aoede,
Autonoe, Callirrhoe, Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux,
Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi,
Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr,
Zubenelgenubi.
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Host pools — 5 male-presenting, 5 female-presenting voices.
# Categorized by perceived vocal timbre in Gemini TTS output.
# ---------------------------------------------------------------------------
MALE_HOSTS: list[str] = [
    "Charon",       # deep, authoritative
    "Fenrir",       # warm baritone
    "Orus",         # measured, calm
    "Puck",         # lighter, energetic
    "Enceladus",    # crisp, analytical
]

FEMALE_HOSTS: list[str] = [
    "Aoede",        # warm, grounded
    "Kore",         # clear, articulate
    "Leda",         # smooth, composed
    "Zephyr",       # bright, dynamic
    "Achernar",     # rich, resonant
]

# 5 host pairs — each broadcast gets a unique male+female combination.
# Pairs are designed for vocal contrast (deep+bright, warm+crisp, etc.)
HOST_PAIRS: list[tuple[str, str]] = [
    ("Charon", "Aoede"),        # pair 0: deep anchor + warm analyst
    ("Fenrir", "Kore"),         # pair 1: warm baritone + clear articulate
    ("Orus", "Zephyr"),         # pair 2: measured calm + bright dynamic
    ("Puck", "Leda"),           # pair 3: energetic + smooth composed
    ("Enceladus", "Achernar"),  # pair 4: crisp analytical + rich resonant
]

# Opinion voices — one per edition, never used as news hosts.
# Fixed for brand consistency: opinion always sounds the same per edition.
OPINION_VOICES: dict[str, str] = {
    "world": "Sulafat",
    "us": "Sadachbia",
    "india": "Gacrux",
    "uk": "Rasalgethi",
    "canada": "Vindemiatrix",
}


def _get_rotation_index() -> int:
    """Get the current rotation index based on UTC time.

    4 runs per day × 5 pairs = cycles every 5 days (20 runs).
    Uses UTC hour buckets: 0-5=run0, 6-11=run1, 12-17=run2, 18-23=run3.
    """
    now = datetime.now(timezone.utc)
    day_of_year = now.timetuple().tm_yday
    run_of_day = now.hour // 6  # 0, 1, 2, or 3
    total_runs = (day_of_year * 4) + run_of_day
    return total_runs % len(HOST_PAIRS)


def get_voices_for_today(edition: str) -> dict:
    """Return voice config for the current broadcast.

    News hosts rotate across runs — 5 distinct male+female pairs cycle
    every 20 runs (5 days at 4x/day). Each broadcast sounds different.
    Opinion voice stays fixed per edition for brand consistency.
    """
    idx = _get_rotation_index()
    male, female = HOST_PAIRS[idx]

    # Alternate who leads (host_a) vs. who responds (host_b) each run
    if idx % 2 == 0:
        host_a, host_b = male, female
    else:
        host_a, host_b = female, male

    opinion_voice = OPINION_VOICES.get(edition, OPINION_VOICES["world"])

    return {
        "host_a": {"id": host_a},
        "host_b": {"id": host_b},
        "opinion": {"id": opinion_voice},
    }


def get_voice_for_today(edition: str) -> dict:
    """Return a single voice for backward compatibility."""
    return get_voices_for_today(edition)["host_a"]
