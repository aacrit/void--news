"""
Audio script generator for void --history companion audio.

Generates two-host dialogue scripts from YAML event data.
The product is DIVERGENCE between perspectives — placed next to each
other so the listener hears the contradiction and draws their own conclusion.

Cardinal rules (enforced in system instruction):
  Show Not Tell: Never assert significance. Juxtapose concrete facts.
  Arrive Late, Leave Early: Open with the hook. Close on unresolved fact.

Script structure (Five Movements):
  1. THE HOOK        — arrive-late one-liner + complicating fact
  2. FIRST PASS      — victor vs. vanquished, direct quote
  3. SECOND PASS     — bystander/academic leads, omissions surface
  4. THE NUMBER      — contested statistic, both figures presented
  5. THE EXIT        — unresolved fact from unexpected perspective

Host pair: Sadaltager (Chronicler) + Achernar (Witness)
Generation: one Gemini call per event, ~600-800 word output target.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.prohibited_terms import PROHIBITED_TERMS as _SHARED_PROHIBITED, check_prohibited_terms as _shared_check
    _USE_SHARED_PROHIBITED = True
except ImportError:
    _USE_SHARED_PROHIBITED = False
    _SHARED_PROHIBITED = frozenset()
    def _shared_check(text, context=""): return []

# ---------------------------------------------------------------------------
# History-specific prohibited terms (extends shared list)
# ---------------------------------------------------------------------------

HISTORY_PROHIBITED_TERMS = frozenset({
    # --- Moral authority / omniscience ---
    "the truth is", "the truth was",
    "what really happened", "what actually happened",
    "history will judge", "history has judged",
    "history teaches us", "history shows us",
    "the lesson of", "the lesson here", "the lessons of",
    "we can learn", "we should learn",
    "on the right side of history", "on the wrong side of history",

    # --- False objectivity ---
    "in reality", "in truth",
    "the real reason", "the real story",
    "the true cost", "the true impact",
    "what is clear is", "what is certain is",
    "one thing is clear", "one thing is certain",
    "beyond doubt", "beyond question",

    # --- Teleological language ---
    "changed the course of history",
    "altered the trajectory",
    "shaped the modern world",
    "the world would never be the same",
    "a turning point in human history",
    "defining moment",
    "turned the tide",

    # --- Generic historical framing ---
    "in the annals of",
    "throughout history",
    "since time immemorial",
    "a story of", "this is the story of",
    "one of the most", "one of history's",
    "perhaps the greatest", "among the worst",

    # --- Podcast/explainer scaffolding ---
    "let's explore", "let us explore",
    "let's examine", "let us examine",
    "let's consider", "let us consider",
    "let's take a look", "let us take a look",
    "as we'll see", "as we will see",
    "but first", "before we get to",
    "to understand this", "to put this in context",
    "fast forward to", "flash forward",

    # --- Significance assertion (history-specific) ---
    "the legacy of",
    "the lasting impact", "the profound impact",
    "the far-reaching consequences",
    "reverberations",
    "echoes to this day",
    "still felt today",
    "continues to shape",
    "the shadow of",
})


def _all_prohibited() -> frozenset:
    return _SHARED_PROHIBITED | HISTORY_PROHIBITED_TERMS


def check_history_prohibited(text: str, slug: str = "") -> list[str]:
    """Check for prohibited terms in generated history audio script."""
    lower = text.lower()
    found = [term for term in _all_prohibited() if term in lower]
    if found and slug:
        print(f"  [warn][history-audio:{slug}] prohibited terms: {found}")
    return found


# ---------------------------------------------------------------------------
# Gemini system instruction
# ---------------------------------------------------------------------------

_HISTORY_SYSTEM_INSTRUCTION = """\
You are writing a two-host dialogue script for void --history, an archival \
audio companion to a multi-perspective historical events platform. Your \
product is the DIVERGENCE between historical perspectives — the places \
where accounts contradict each other in numbers, causation, or emphasis.

You are NOT a lecturer. You are NOT a summarizer. You present concrete \
facts from multiple perspectives so the listener hears the contradiction \
and draws their own conclusion.

History is not what happened. History is who told the story.

GROUNDING RULE: Every fact, figure, name, quote, and claim MUST come from \
the provided event data. Do not supplement with outside knowledge. If the \
data does not contain it, you do not say it.

TENSE: Past tense throughout. These events already happened. Never use \
present tense to create false immediacy ("Truman faces a choice" — wrong; \
"Truman faced a choice" — correct). Exception: direct quotes preserve their \
original tense. Present tense is permitted for enduring states ("Kashmir \
remains disputed") and statements about sources ("The British perspective \
emphasizes...").

ATTRIBUTION: Every contested factual claim belongs to a perspective. Never \
state a disputed fact as neutral truth. "The American account held that \
the bombing shortened the war" — not "The bombing shortened the war." \
"The Voyages Database recorded 12.5 million embarked" — not "12.5 million \
were taken." When perspectives disagree on a number, present both figures \
with their attributed sources.

INTERLEAVING: Never present one perspective as a full block, then another. \
Weave them. A fact from Perspective 1 should be followed within 2-4 lines \
by a complicating fact from Perspective 2. The listener should never hear \
more than 4 consecutive lines from one viewpoint.

SHOW, DON'T TELL: Never assert that perspectives differ — demonstrate it by \
placing two facts next to each other. The juxtaposition IS the point. Never \
write "perspectives differ" or "this is contested" or "historians disagree." \
Just present the two facts. Place them in sequence. Let the listener see \
the gap.

ARRIVE LATE, LEAVE EARLY: The first line is the hook — drop the listener \
into a specific moment (use the provided HOOK verbatim or near-verbatim). \
The last line is an unresolved fact — not a summary, not a lesson, not a \
moral. The listener completes the thought. No closing tag line.

DIRECT QUOTES: Use 1-3 direct quotes from the provided source data. \
Attribute each precisely: speaker name and context. Quotes anchor the \
script in primary sources.

CONCRETENESS: Names, dates, numbers, places. Every sentence should contain \
at least one specific noun. Abstract sentences without specifics are cut.

HOST ROLES: Neither host "owns" a perspective. Both present facts from \
multiple viewpoints. One host introduces a claim; the other complicates \
it with a fact from a different angle. Disagreement is expressed through \
additional facts — never through "I disagree" or "that's contested."

FORMAT: A:/B: speaker tags only. One turn per line. Maximum 35 words per \
turn. No stage directions, no parentheticals, no [MARKER] labels. Rhythm \
of the words creates the pacing. No closing "That was void history." line.

PROHIBITED OUTPUT — script containing ANY of these is rejected: \
significant, significantly, notable, notably, important, importantly, \
pivotal, transformative, watershed, landmark (as adjective), historic (as \
emphasis), it should be noted, interestingly, crucially, remarkably, \
unprecedented, comprehensive, nuanced, complex, multifaceted, robust, \
delve, navigate, underscores, highlights the, illustrates the, \
demonstrates the, signals a, reflects a, marks a shift, the truth is, \
the reality is, what really happened, history will judge, history teaches \
us, we can learn from, the lesson of, the legacy of, on the right side of \
history, changed the course of, shaped the modern, defining moment, turned \
the tide, the world would never be the same, a story of, in the annals of, \
throughout history, let's explore, let's examine, to understand this, \
to put this in context, fast forward, still felt today, echoes to this day.
"""


# ---------------------------------------------------------------------------
# User prompt template
# ---------------------------------------------------------------------------

_HISTORY_PROMPT_TEMPLATE = """\
Generate a two-host audio script for the historical event: {event_title}.

HOOK (deliver this as Host A's opening line, verbatim or near-verbatim):
{hook}

EVENT SUMMARY:
{summary}

KEY FIGURES:
{key_figures_block}

STATISTICS:
- Death toll: {death_toll}
- Affected population: {affected_population}
- Duration: {duration}

PERSPECTIVES ({n_perspectives} viewpoints):
{perspectives_block}

DIVERGENCE POINTS — build the dialogue around these contradictions:
{divergence_block}

---

SCRIPT STRUCTURE (Five Movements):

Movement 1 — THE HOOK (2-3 exchanges):
A delivers the hook above, verbatim or near-verbatim.
B enters immediately with a second concrete fact that complicates or \
extends it — pulled from the summary or a different perspective. \
No preamble. No "Today we're looking at."

Movement 2 — FIRST PASS (4-6 exchanges):
Present the strongest factual claim from {perspective_1_name} \
({perspective_1_type}). Include one direct quote from the source data. \
Then B presents a contradicting or complicating fact from \
{perspective_2_name} ({perspective_2_type}).

Movement 3 — SECOND PASS (4-6 exchanges):
B leads with a fact from {perspective_3_name} ({perspective_3_type}). \
A then surfaces something from the OMISSIONS data — what the first \
perspective leaves out. Use the "emphasized" and "omitted" arrays.

Movement 4 — THE NUMBER (3-5 exchanges):
Surface the contested statistic from the DIVERGENCE POINTS above. \
Both hosts present the competing figures with their attributed sources. \
Neither host adjudicates which is correct.{movement_4_extra}

Movement 5 — THE EXIT (1-2 lines):
End on a single unresolved fact — often from the least-expected \
perspective, often from the omissions data. Not a summary. Not a \
lesson. The piece ends after this line. Silence is the punctuation.

DIALOGUE RULES:
- Neither host owns a perspective. Both present facts from multiple viewpoints.
- One host introduces a claim; the other complicates it with a fact from a \
different angle.
- Maximum 35 words per turn. Split longer thoughts across exchanges.
- Start every line with a concrete element: name, number, date, place, document.
- Never start a line with: "That's...", "Which tells you...", "Here's the \
thing...", "What's interesting...", "It's worth noting...", "Essentially..."
- No meta-framing: never say "what's fascinating is," "the key question," \
"the tension here," "what this shows us."

TARGET: {target_words} words ({target_min}-{target_max} word range). \
Approximately {target_exchanges} exchanges total.

Return JSON with a single key: {{"audio_script": "A: ...\\nB: ...\\n..."}}
"""


# ---------------------------------------------------------------------------
# Perspective block builder
# ---------------------------------------------------------------------------

def _build_perspectives_block(perspectives: list[dict]) -> str:
    """Format perspectives array into a structured block for the prompt."""
    lines = []
    for i, p in enumerate(perspectives):
        vtype = p.get("viewpoint_type", "bystander")
        vname = p.get("viewpoint", f"Perspective {i+1}")
        region = p.get("region_origin", "")
        lines.append(f"### [{vtype.upper()}] {vname}" + (f" ({region})" if region else ""))

        key_args = p.get("key_arguments", [])
        if key_args:
            lines.append("Key arguments:")
            for arg in key_args[:4]:
                lines.append(f"  - {arg}")

        emphasized = p.get("emphasized", [])
        if emphasized:
            lines.append("Emphasizes:")
            for e in emphasized[:3]:
                lines.append(f"  - {e}")

        omitted = p.get("omitted", [])
        if omitted:
            lines.append("Omits:")
            for o in omitted[:3]:
                lines.append(f"  - {o}")

        quotes = p.get("notable_quotes", [])
        if quotes:
            lines.append("Direct quotes:")
            for q in quotes[:2]:
                text = q.get("text", "")
                speaker = q.get("speaker", "")
                context = q.get("context", "")
                if text:
                    attr = speaker
                    if context:
                        attr += f", {context}"
                    lines.append(f'  "{text}" — {attr}')

        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Divergence extraction engine
# ---------------------------------------------------------------------------

def _extract_divergence(
    perspectives: list[dict],
    death_toll: str = "",
    affected_population: str = "",
) -> list[dict]:
    """Pre-process perspectives to surface three types of contradiction.

    Returns list of dicts with keys: type, claim_1, perspective_1, claim_2, perspective_2.
    Types: 'numerical', 'causal', 'omission'.

    The divergence block is injected into the prompt as explicit material
    for Gemini to build the dialogue around — without this, Gemini defaults
    to sequential perspective summaries instead of interleaved contradictions.
    """
    divergences = []

    # Type A: Numerical contradiction
    # Scan key_arguments and emphasized for numbers attached to the same concept
    _NUMBER_RE = re.compile(r"\b(\d[\d,\.]*(?:\s*(?:million|billion|thousand|hundred))?\s*(?:people|dead|killed|displaced|casualties|percent|%)?)\b", re.IGNORECASE)

    # Look for perspectives that cite competing death toll figures
    toll_claims = []
    for p in perspectives:
        all_text = " ".join([
            *p.get("key_arguments", []),
            *p.get("emphasized", []),
            p.get("narrative", "")[:500],
        ])
        numbers = _NUMBER_RE.findall(all_text)
        if numbers:
            toll_claims.append({
                "perspective": p.get("viewpoint", "Unknown"),
                "type": p.get("viewpoint_type", "unknown"),
                "text_sample": all_text[:300],
                "numbers": numbers[:3],
            })

    # If we have 2+ perspectives with numbers, surface the first pair
    if len(toll_claims) >= 2:
        c1, c2 = toll_claims[0], toll_claims[1]
        # Only add if the numbers look different
        if c1["numbers"] and c2["numbers"] and c1["numbers"][0] != c2["numbers"][0]:
            divergences.append({
                "type": "numerical",
                "claim_1": f"{c1['perspective']} ({c1['type']}): {c1['numbers'][0]}",
                "claim_2": f"{c2['perspective']} ({c2['type']}): {c2['numbers'][0]}",
            })

    # Add death toll if it looks like a range (indicates dispute)
    if death_toll and ("–" in death_toll or "-" in death_toll or "to" in death_toll.lower()):
        divergences.append({
            "type": "numerical",
            "claim_1": f"Official/early estimates: {death_toll.split('-')[0].split('–')[0].strip()}",
            "claim_2": f"Later scholarship: {death_toll.split('-')[-1].split('–')[-1].strip()}",
        })

    # Type B: Causal contradiction
    # Look for perspectives that cite different causes for the same outcome
    causal_claims = []
    _CAUSAL_WORDS = ["because", "caused by", "due to", "result of", "led to", "driven by", "forced by", "enabled by"]
    for p in perspectives:
        key_args = p.get("key_arguments", [])
        causal_args = [a for a in key_args if any(w in a.lower() for w in _CAUSAL_WORDS)]
        if causal_args:
            causal_claims.append({
                "perspective": p.get("viewpoint", "Unknown"),
                "type": p.get("viewpoint_type", "unknown"),
                "claim": causal_args[0],
            })

    if len(causal_claims) >= 2:
        c1, c2 = causal_claims[0], causal_claims[1]
        divergences.append({
            "type": "causal",
            "claim_1": f"{c1['perspective']} ({c1['type']}): {c1['claim']}",
            "claim_2": f"{c2['perspective']} ({c2['type']}): {c2['claim']}",
        })

    # Type C: Omission asymmetry
    # Perspective A emphasizes X; Perspective B has X in its omissions list
    persp_emphasized = {}
    persp_omitted = {}
    for p in perspectives:
        name = p.get("viewpoint", "")
        persp_emphasized[name] = set(
            item if isinstance(item, str) else str(item)
            for item in p.get("emphasized", [])
        )
        persp_omitted[name] = set(
            item if isinstance(item, str) else str(item)
            for item in p.get("omitted", [])
        )

    for p1_name, p1_emph in persp_emphasized.items():
        for p2_name, p2_omit in persp_omitted.items():
            if p1_name == p2_name:
                continue
            # Find items that P1 emphasizes but P2 explicitly omits
            for item in p1_emph:
                # Fuzzy match: look for substantial word overlap (>3 words in common)
                item_words = set(item.lower().split())
                for omit_item in p2_omit:
                    omit_words = set(omit_item.lower().split())
                    overlap = item_words & omit_words - {"the", "a", "an", "of", "in", "and", "to", "for"}
                    if len(overlap) >= 2:
                        divergences.append({
                            "type": "omission",
                            "claim_1": f"{p1_name} emphasizes: {item}",
                            "claim_2": f"{p2_name} omits: {omit_item}",
                        })
                        break

    # Deduplicate and cap at 4 divergence points
    seen = set()
    unique = []
    for d in divergences:
        key = d["type"] + d["claim_1"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique[:4]


def _format_divergence_block(divergences: list[dict]) -> str:
    """Format extracted divergences into a labeled prompt block."""
    if not divergences:
        return "Surface numerical contradictions and omission asymmetries from the perspectives above."

    lines = []
    for i, d in enumerate(divergences, 1):
        label = {"numerical": "[NUMERICAL CONTRADICTION]", "causal": "[CAUSAL CONTRADICTION]", "omission": "[OMISSION ASYMMETRY]"}.get(d["type"], "[CONTRADICTION]")
        lines.append(f"{i}. {label}")
        lines.append(f"   {d['claim_1']}")
        lines.append(f"   vs. {d['claim_2']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Word count calculator (by date_precision and temporal scope)
# ---------------------------------------------------------------------------

def calculate_word_target(event_data: dict) -> tuple[int, int, int, int]:
    """Return (target_words, min_words, max_words, target_exchanges).

    Calibrated to produce 3-5 minutes at ~150 words/minute TTS pace.
    Longer targets for century-scale events to avoid superficial surveys.
    """
    precision = event_data.get("date_precision", "year")
    duration_str = event_data.get("duration", "") or ""
    n_perspectives = len(event_data.get("perspectives", []))

    # Base target by date precision
    if precision == "day":
        # Single event: Hiroshima (3 days), Partition (day zero)
        target, low, high = 580, 500, 680
    elif precision == "month":
        # Short period: Rwandan Genocide (100 days)
        target, low, high = 650, 560, 760
    elif precision == "year":
        # Year-scale: Holocaust (6 years), French Revolution (decade)
        target, low, high = 720, 620, 840
    elif precision == "decade":
        # Decade-scale: Cold War, Cultural Revolution
        target, low, high = 780, 670, 900
    else:
        # Century-scale: Silk Road, Slave Trade
        target, low, high = 820, 700, 950

    # Adjust for perspective richness
    if n_perspectives >= 5:
        target = min(target + 50, high)
    elif n_perspectives <= 2:
        target = max(target - 80, low)

    # Rough exchange count: ~25 words per exchange average
    exchanges = round(target / 25)

    return target, low, high, exchanges


# ---------------------------------------------------------------------------
# Main prompt builder
# ---------------------------------------------------------------------------

def _get_perspective_by_priority(perspectives: list[dict]) -> tuple[dict, dict, dict, dict | None]:
    """Return (p1, p2, p3, p4) ordered by: victor, vanquished, bystander/academic, revisionist/indigenous."""
    by_type: dict[str, list[dict]] = {}
    for p in perspectives:
        vtype = p.get("viewpoint_type", "bystander")
        by_type.setdefault(vtype, []).append(p)

    ordered = []
    for priority_type in ("victor", "vanquished", "bystander", "academic", "indigenous", "revisionist"):
        if priority_type in by_type:
            ordered.extend(by_type[priority_type])

    # Fallback: any remaining perspectives
    for p in perspectives:
        if p not in ordered:
            ordered.append(p)

    p1 = ordered[0] if len(ordered) > 0 else perspectives[0]
    p2 = ordered[1] if len(ordered) > 1 else perspectives[0]
    p3 = ordered[2] if len(ordered) > 2 else perspectives[1]
    p4 = ordered[3] if len(ordered) > 3 else None
    return p1, p2, p3, p4


def build_history_audio_prompt(event_data: dict, hook: str) -> str:
    """Build the Gemini user prompt for history audio script generation.

    Args:
        event_data: Parsed YAML event dict.
        hook: The arrive-late one-liner from hooks.ts.

    Returns:
        Formatted prompt string ready for Gemini.
    """
    title = event_data.get("title", event_data.get("slug", "Unknown Event"))
    summary = (event_data.get("summary", "") or "").strip()
    death_toll = event_data.get("death_toll", "Not recorded") or "Not recorded"
    affected = event_data.get("affected_population", "Not recorded") or "Not recorded"
    duration = event_data.get("duration", "Not recorded") or "Not recorded"
    perspectives = event_data.get("perspectives", [])

    # Key figures block
    key_figures = event_data.get("key_figures", [])
    key_figures_block = "\n".join(
        f"- {kf.get('name', '')}: {kf.get('role', '')}"
        for kf in key_figures[:7]
    ) or "Not specified"

    # Perspectives block
    perspectives_block = _build_perspectives_block(perspectives)

    # Divergence extraction
    divergences = _extract_divergence(perspectives, death_toll, affected)
    divergence_block = _format_divergence_block(divergences)

    # Perspective ordering for movement assignments
    p1, p2, p3, p4 = _get_perspective_by_priority(perspectives)

    movement_4_extra = ""
    if p4:
        movement_4_extra = (
            f" Also draw on {p4.get('viewpoint', 'the fourth perspective')} "
            f"({p4.get('viewpoint_type', 'unknown')}) for additional context."
        )

    # Word targets
    target, low, high, exchanges = calculate_word_target(event_data)

    return _HISTORY_PROMPT_TEMPLATE.format(
        event_title=title,
        hook=hook,
        summary=summary[:1500] if len(summary) > 1500 else summary,
        key_figures_block=key_figures_block,
        death_toll=death_toll,
        affected_population=affected,
        duration=duration,
        n_perspectives=len(perspectives),
        perspectives_block=perspectives_block,
        divergence_block=divergence_block,
        perspective_1_name=p1.get("viewpoint", "Perspective A"),
        perspective_1_type=p1.get("viewpoint_type", "victor"),
        perspective_2_name=p2.get("viewpoint", "Perspective B"),
        perspective_2_type=p2.get("viewpoint_type", "vanquished"),
        perspective_3_name=p3.get("viewpoint", "Perspective C"),
        perspective_3_type=p3.get("viewpoint_type", "bystander"),
        movement_4_extra=movement_4_extra,
        target_words=target,
        target_min=low,
        target_max=high,
        target_exchanges=exchanges,
    )


# ---------------------------------------------------------------------------
# Script generation (calls Gemini)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "data" / "history" / "scripts"


def _load_cached_script(slug: str) -> str | None:
    path = _SCRIPTS_DIR / f"{slug}.txt"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def _save_cached_script(slug: str, script: str) -> None:
    _SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    (_SCRIPTS_DIR / f"{slug}.txt").write_text(script, encoding="utf-8")


def generate_history_audio_script(
    event_data: dict,
    hook: str,
    slug: str = "",
    reuse_cached: bool = False,
) -> str | None:
    """Generate audio script for a single history event via Gemini.

    Args:
        event_data: Parsed YAML event dict.
        hook: The arrive-late one-liner from hooks.ts.
        slug: Event slug for logging.
        reuse_cached: If True and a cached script exists on disk,
            return it without calling Gemini. Used for TTS-only
            regeneration (voice sweeps).

    Returns:
        The audio_script string (A:/B: format), or None on failure.
    """
    label = slug or event_data.get("slug", "unknown")

    if reuse_cached:
        cached = _load_cached_script(label)
        if cached:
            print(f"  [history-audio:{label}] Reusing cached script (skipping Gemini)")
            return cached
        print(f"  [history-audio:{label}] No cached script — generating fresh")

    try:
        from summarizer.gemini_client import generate_json
    except ImportError:
        try:
            from pipeline.summarizer.gemini_client import generate_json
        except ImportError:
            print(f"  [error][history-audio:{slug}] Cannot import gemini_client")
            return None

    prompt = build_history_audio_prompt(event_data, hook)

    print(f"  [history-audio:{label}] Generating script via Gemini...")
    result = generate_json(
        prompt,
        system_instruction=_HISTORY_SYSTEM_INSTRUCTION,
        count_call=False,
        max_output_tokens=16384,
    )

    if not result or not isinstance(result, dict):
        print(f"  [error][history-audio:{label}] Gemini returned no result")
        return None

    script = result.get("audio_script", "")
    if not script or not isinstance(script, str):
        print(f"  [error][history-audio:{label}] No audio_script in response")
        return None

    # Quality gates
    lines = [l for l in script.splitlines() if l.strip()]
    exchange_count = len(lines)

    if exchange_count < 10:
        print(f"  [warn][history-audio:{label}] Script too short: {exchange_count} exchanges")
        return None

    prohibited = check_history_prohibited(script, label)
    if prohibited:
        print(f"  [warn][history-audio:{label}] Prohibited terms found: {prohibited[:5]}")
        # Don't reject — log and continue. Re-generation wastes quota.

    word_count = len(script.split())
    print(f"  [history-audio:{label}] Script OK: {exchange_count} exchanges, {word_count} words")

    _save_cached_script(label, script)
    return script
