"""Voice rotation for the void --news audio broadcast.

6-host newsroom model: 3 fixed pairs rotate across 3 editions so every
host works every day. Each host has a distinct personality that shapes
the script — not just the voice timbre.

Pairs:
  Alpha:   Correspondent (Charon) + Structuralist (Kore)
  Bravo:   Investigator (Orus) + Realist (Achernar)
  Charlie: Editor (Sadaltager) + Pragmatist (Gacrux)

Rotation: 4 runs/day × 3 editions. Each run assigns one pair per edition.
Over 6 runs (1.5 days), every pair has led every edition.

Opinion voice uses a fixed timbre per edition (brand recognition) but
the editorial *persona* rotates with the lean lens.

Official voice data from Google Cloud TTS docs:

Male (16): Achird (friendly), Algenib (gravelly), Algieba (smooth),
  Alnilam (firm), Charon (informative), Enceladus (breathy),
  Fenrir (excitable), Iapetus (clear), Orus (firm), Puck (upbeat),
  Rasalgethi (informative), Sadachbia (lively), Sadaltager (knowledgeable),
  Schedar (even), Umbriel (easy-going), Zubenelgenubi (casual).

Female (14): Achernar (soft), Aoede (breezy), Autonoe (bright),
  Callirrhoe (easy-going), Despina (smooth), Erinome (clear),
  Gacrux (mature), Kore (firm), Laomedeia (upbeat), Leda (youthful),
  Pulcherrima (forward), Sulafat (warm), Vindemiatrix (gentle),
  Zephyr (bright).
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Host definitions — 6 hosts, each with voice ID, personality, and lean.
# Personality traits shape the script prompt; lean activates in opinion only.
# ---------------------------------------------------------------------------
HOSTS = {
    "structuralist": {
        "id": "Kore",
        "name": "The Structuralist",
        "gender": "female",
        "lean": "center-left",
        "google_label": "firm",
        "trait": (
            "Sees systems, not events. Connects policy to outcome, incentive to "
            "behavior, structure to consequence. Measured pace. Builds sentences "
            "that layer — short setup, then a longer sentence that reveals the "
            "mechanism. Uses 'because' and 'which means' naturally."
        ),
        "tts_preamble": (
            "Firm, measured, authoritative. Mid-tempo with deliberate slowing on "
            "causal explanations. Clear emphasis on connecting phrases. Thoughtful, "
            "not rushed."
        ),
        "opinion_tts_preamble": (
            "Scene: A policy analyst at the editorial desk, laying out the structural "
            "argument. Speaker One builds layer by layer — short setup sentences, then "
            "a longer sentence that reveals the mechanism underneath. Measured, almost "
            "professorial, but never dry. Slows deliberately on causal chains: 'because' "
            "and 'which means' land with weight. Pace is steady until the structural "
            "insight clicks — then a brief pause to let it register. Conviction comes "
            "from connecting the dots, not raising the voice. The close is quiet and "
            "certain: the structure speaks for itself."
        ),
        "opinion_lean": "left",
    },
    "correspondent": {
        "id": "Charon",
        "name": "The Correspondent",
        "gender": "male",
        "lean": "center",
        "google_label": "informative",
        "trait": (
            "The unhurried authority. Lets facts land with their own weight. Short "
            "declarative sentences. Pauses after key facts to let them register. "
            "Trusts proximity to reveal the pattern — places two facts next to each "
            "other without editorializing."
        ),
        "tts_preamble": (
            "Low, steady, unhurried. BBC World Service gravitas. Deliberate pauses "
            "after key statements. Calm authority — never raises voice. Precision "
            "over speed."
        ),
        "opinion_tts_preamble": (
            "Scene: A veteran foreign correspondent delivering a dispatch from the "
            "editorial desk. Speaker One is unhurried — the authority of someone who "
            "has been in the room where it happened. Short declarative sentences that "
            "land like dispatches. Pauses after key facts — not for drama, but because "
            "the fact deserves the silence. Places two observations side by side and "
            "lets the listener connect them. Low register, steady pace. Never raises "
            "voice. The close is two facts next to each other, then silence. The "
            "listener draws the conclusion."
        ),
        "opinion_lean": "center",
    },
    "pragmatist": {
        "id": "Gacrux",
        "name": "The Pragmatist",
        "gender": "female",
        "lean": "center-right",
        "google_label": "mature",
        "trait": (
            "Institutional memory and fiscal instinct. Skeptical of grand narratives. "
            "Always asks 'at what cost?' and 'has this been tried before?' Crisp and "
            "efficient. Shorter sentences. Dry delivery — lets understatement do "
            "the work."
        ),
        "tts_preamble": (
            "Mature, crisp, composed. Slightly faster pace — efficient delivery. "
            "Dry wit when appropriate. Emphasis on numbers and costs. No wasted words."
        ),
        "opinion_tts_preamble": (
            "Scene: A fiscal hawk at the editorial desk, making the case with numbers "
            "and institutional memory. Speaker One is crisp, efficient — every word "
            "earns its place. Slightly faster pace than conversational, the cadence of "
            "someone who respects the listener's time. Dry understatement does the heavy "
            "lifting — delivers hard truths in a matter-of-fact register. Pauses before "
            "cost figures to let them land. Skeptical inflection on grand promises. "
            "The close is short and declarative — the pragmatist doesn't need to "
            "persuade, just lay out what the numbers say."
        ),
        "opinion_lean": "right",
    },
    "investigator": {
        "id": "Orus",
        "name": "The Investigator",
        "gender": "male",
        "lean": "left",
        "google_label": "firm",
        "trait": (
            "Follows the money, the mechanism, the paper trail. Prosecutorial "
            "instinct — lays out evidence in sequence so the conclusion is "
            "inescapable. Builds momentum: starts measured, accelerates through "
            "a chain of evidence, then slows for the key detail."
        ),
        "tts_preamble": (
            "Firm, commanding, builds intensity. Starts measured, accelerates through "
            "evidence chains. Slows deliberately for key revelations. Conviction in "
            "every sentence."
        ),
        "opinion_tts_preamble": (
            "Scene: A veteran investigative journalist delivering a closing editorial "
            "at the anchor desk. This is not a reading — it is a closing argument. "
            "Speaker One builds the case like a prosecutor: measured opening, then "
            "accelerating through each piece of evidence with growing urgency. Voice "
            "rises slightly when stacking facts. Gets quieter — almost conspiratorial "
            "— when landing the key detail. Pauses before the damning number. "
            "Pace shifts constantly: slow setup, fast evidence chain, sudden stillness "
            "for the turn. Conviction in every word. This person has done the homework "
            "and is certain of the conclusion."
        ),
        "opinion_lean": "left",
    },
    "realist": {
        "id": "Achernar",
        "name": "The Realist",
        "gender": "female",
        "lean": "right",
        "google_label": "soft",
        "trait": (
            "Challenges consensus with data. 'What does the evidence actually show?' "
            "Fiscally rigorous, skeptical of interventionism. Calm, almost "
            "conversational — delivers hard truths in a soft register. The contrast "
            "makes them land harder."
        ),
        "tts_preamble": (
            "Soft-spoken but precise. Calm, almost intimate delivery. Contrast "
            "between gentle tone and sharp content. Slight pauses before delivering "
            "counter-evidence. Thoughtful, never strident."
        ),
        "opinion_tts_preamble": (
            "Scene: A columnist leaning back in their chair, talking directly to you "
            "across the desk. Speaker One is conversational and unhurried — the tone "
            "of someone explaining the obvious to a friend. Soft-spoken but every word "
            "is chosen. Slight skeptical inflection on received wisdom — eyebrow-raise "
            "energy. Pauses before counter-evidence like setting down a card. Never "
            "raises voice; the calm is the weapon. Occasional wry half-smile audible "
            "in the delivery. Pace stays even until the close, where it slows to let "
            "the final line land with its own weight. Intimate, not performative."
        ),
        "opinion_lean": "right",
    },
    "editor": {
        "id": "Sadaltager",
        "name": "The Editor",
        "gender": "male",
        "lean": "center",
        "google_label": "knowledgeable",
        "trait": (
            "The senior voice. Synthesizes, contextualizes, places today's news in "
            "the arc of the week or the decade. Identifies the through-line across "
            "stories. Comfortable with silence. The voice that provides perspective "
            "— not prediction, but framing that helps the listener think."
        ),
        "tts_preamble": (
            "Knowledgeable, warm authority. Senior editorial voice. Comfortable pace "
            "with weight behind each sentence. Slight warmth — the voice of someone "
            "who has seen this before. Measured gravitas."
        ),
        "opinion_tts_preamble": (
            "Scene: The editor-in-chief at the editorial desk, delivering the paper's "
            "position. Speaker One speaks with measured authority — the weight of the "
            "institution behind every sentence. Comfortable, unhurried pace that "
            "suddenly sharpens into direct, clipped sentences when cutting through "
            "noise. Knows when to let a fact sit in silence. Occasional dry edge — "
            "not sarcasm, but the precision of someone who chose that word deliberately. "
            "Builds from context to conclusion with the patience of a teacher, then "
            "delivers the verdict with the brevity of a judge. Warmth underneath, "
            "steel when it matters."
        ),
        "opinion_lean": "center",
    },
}

# ---------------------------------------------------------------------------
# 3 fixed pairs — each pair covers one edition per run.
# ---------------------------------------------------------------------------
PAIRS = [
    ("correspondent", "structuralist"),   # Alpha: authority + systems
    ("investigator", "realist"),          # Bravo: evidence + counter-data
    ("editor", "pragmatist"),             # Charlie: perspective + fiscal rigor
]

# Edition order for desk assignment rotation.
_EDITIONS = ["world", "us", "india"]

# Opinion voices — fixed timbre per edition for brand recognition.
# The editorial *persona* changes with the lean lens (see get_opinion_host).
OPINION_VOICES: dict[str, str] = {
    "world": "Sulafat",       # female, warm
    "us": "Schedar",          # male, even
    "india": "Despina",       # female, smooth
    "uk": "Rasalgethi",       # male, informative
    "canada": "Vindemiatrix", # female, gentle
}

# Lean → host mapping for opinion persona.
_OPINION_HOST_BY_LEAN = {
    "left": "investigator",
    "center": "editor",
    "right": "realist",
}

# Alternate opinion hosts (fallback if primary is already on news desk —
# not currently used since opinion is a monologue by a separate voice,
# but available for future scheduling constraints).
_OPINION_HOST_ALT = {
    "left": "structuralist",
    "center": "correspondent",
    "right": "pragmatist",
}


def _get_rotation_index() -> int:
    """Get the current rotation index based on UTC time.

    4 runs per day × 3 pair-edition permutations = 12-run cycle (3 days).
    Uses UTC hour buckets: 0-5=run0, 6-11=run1, 12-17=run2, 18-23=run3.
    """
    now = datetime.now(timezone.utc)
    day_of_year = now.timetuple().tm_yday
    run_of_day = now.hour // 6  # 0, 1, 2, or 3
    total_runs = (day_of_year * 4) + run_of_day
    return total_runs


def _get_desk_assignment(edition: str) -> tuple[str, str]:
    """Return (host_a_key, host_b_key) for the given edition this run.

    Each run assigns one of the 3 pairs to each of the 3 editions.
    The pair-to-edition mapping rotates so every pair covers every
    edition over 3 runs (18 hours at 4x/day).

    Within each pair, who leads (Host A) alternates by run index.
    """
    idx = _get_rotation_index()
    edition_index = _EDITIONS.index(edition) if edition in _EDITIONS else 0

    # Rotate which pair covers which edition
    pair_index = (idx + edition_index) % len(PAIRS)
    host_1_key, host_2_key = PAIRS[pair_index]

    # Alternate lead within the pair
    if idx % 2 == 0:
        return host_1_key, host_2_key
    else:
        return host_2_key, host_1_key


def get_opinion_host(lean: str) -> dict:
    """Return the host profile for today's opinion persona.

    The opinion *persona* determines how the argument is built.
    The opinion *voice timbre* is fixed per edition (see OPINION_VOICES).
    """
    host_key = _OPINION_HOST_BY_LEAN.get(lean, "editor")
    return {**HOSTS[host_key], "key": host_key}


def get_voices_for_today(edition: str) -> dict:
    """Return voice config for the current broadcast.

    Returns host_a, host_b (news pair) and opinion voice for the edition.
    Each host dict includes: id (Gemini voice ID), name, trait, tts_preamble.
    """
    host_a_key, host_b_key = _get_desk_assignment(edition)
    host_a = HOSTS[host_a_key]
    host_b = HOSTS[host_b_key]

    opinion_voice_id = OPINION_VOICES.get(edition, OPINION_VOICES["world"])

    return {
        "host_a": {**host_a, "key": host_a_key},
        "host_b": {**host_b, "key": host_b_key},
        "opinion": {"id": opinion_voice_id},
    }


def get_voice_for_today(edition: str) -> dict:
    """Return a single voice for backward compatibility."""
    return get_voices_for_today(edition)["host_a"]
