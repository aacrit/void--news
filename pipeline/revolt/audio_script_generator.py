"""
void --revolt audio script generator.

Builds a two-voice "narrated anatomy" script DETERMINISTICALLY from the curated
revolution fields. No LLM: $0, and neutral by construction (it only re-voices
analyst-authored text, never invents claims or predictions). Works for both
concluded and active revolutions (active reads the curated analytical_outlook,
never a forecast).

Output format: alternating `A:` (the narrator) / `B:` (the analyst) turns, the
same line format pipeline.revolt.generate_audio consumes. Em dashes are allowed
in audio scripts (TTS breath marks) but the curated source text has none, so the
narration reads clean either way.

Cache: data/revolt/scripts/<slug>.txt (reuse for voice-only re-runs).
"""

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _PROJECT_ROOT / "data" / "revolt" / "scripts"

# Predictive-certainty + advocacy + slop terms that must never reach narration.
REVOLT_PROHIBITED_TERMS = frozenset({
    "will fall", "will collapse", "is doomed", "inevitable", "days are numbered",
    "must resist", "must rise", "rise up", "the people will prevail", "freedom fighters",
    "delve", "it should be noted", "changed the course of history", "the legacy of",
    "let's explore", "in this video", "buckle up",
})

OUTCOME_SENTENCE = {
    "independence": "It won its independence.",
    "consolidated-democracy": "It ended in a democracy.",
    "consolidated-autocracy": "It ended in a new autocracy.",
    "restored-old-regime": "The old regime came back.",
    "failed-suppressed": "It was crushed.",
    "civil-war": "It collapsed into civil war.",
    "ongoing-unresolved": "It is still unresolved.",
    "intra-regime-purge": "It was an internal purge, not an overthrow.",
    "secession-partition": "It ended in partition.",
}


def check_prohibited(text: str) -> list[str]:
    low = text.lower()
    return [t for t in REVOLT_PROHIBITED_TERMS if t in low]


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    parts = text.replace("\n", " ").split(". ")
    return (parts[0].strip().rstrip(".") + ".") if parts else ""


def build_script(e: dict) -> str:
    title = e.get("title", "")
    subtitle = e.get("subtitle", "")
    summary = e.get("summary", "")
    grievances = e.get("grievances", []) or []
    phases = [p for p in (e.get("phases", []) or []) if p.get("reached")]
    outcome = e.get("outcome")
    death = e.get("death_toll")
    ate = e.get("ate_its_children")
    mil = e.get("military_defection")
    resistance = e.get("resistance_type")
    outlook = e.get("analytical_outlook")
    significance = e.get("significance", "")
    status = e.get("status")

    turns: list[tuple[str, str]] = []

    # 1. The hook.
    turns.append(("A", f"{title}. {subtitle}." if subtitle else f"{title}."))
    turns.append(("B", _first_sentence(summary)))

    # 2. Preconditions.
    if grievances:
        turns.append(("A", "It did not come from nowhere. " + grievances[0].get("evidence", "")))
        if len(grievances) > 1:
            turns.append(("B", grievances[1].get("evidence", "")))

    # 3. The spark.
    spark = next((p for p in phases if p.get("phase") == "the-spark"), None)
    if spark and spark.get("summary"):
        turns.append(("A", "Then the spark. " + spark["summary"]))

    # 4. The turn.
    radical = next((p for p in phases if p.get("phase") in ("radical-phase", "terror-virtue")), None)
    if radical and radical.get("summary"):
        turns.append(("B", radical["summary"]))

    # 5. Did the guns turn.
    if mil == "full":
        turns.append(("A", "The security forces broke. In the study of revolutions that is the single strongest sign of which way it falls."))
    elif mil == "partial":
        turns.append(("A", "The security forces partly broke, and never fully held."))
    elif mil == "none" and resistance:
        turns.append(("A", "The security forces held with the regime, which is usually decisive."))

    # 6. The reckoning.
    reck = []
    if outcome:
        reck.append(OUTCOME_SENTENCE.get(outcome, ""))
    if ate:
        reck.append("The revolution turned on its own founders.")
    if death:
        reck.append(death)
    reck = [r for r in reck if r]
    if reck:
        turns.append(("B", " ".join(reck)))

    # 7. The read.
    if status in ("active", "consolidating", "dormant", "watchlist") and outlook:
        turns.append(("A", outlook))
    elif significance:
        turns.append(("A", _first_sentence(significance)))

    # 8. The exit.
    turns.append(("B", "That is the anatomy. Where it broke from the pattern is the whole story."))

    return "\n".join(f"{s}: {t.strip()}" for s, t in turns if t and t.strip())


def _save_cached_script(slug: str, script: str) -> None:
    _SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    (_SCRIPTS_DIR / f"{slug}.txt").write_text(script, encoding="utf-8")


def _load_cached_script(slug: str) -> str | None:
    p = _SCRIPTS_DIR / f"{slug}.txt"
    return p.read_text(encoding="utf-8") if p.exists() else None


def generate_revolt_audio_script(event_data: dict, reuse_cached: bool = False) -> str | None:
    slug = event_data.get("slug", "")
    if reuse_cached:
        cached = _load_cached_script(slug)
        if cached:
            return cached
    script = build_script(event_data)
    turns = [ln for ln in script.splitlines() if ln.strip()]
    if len(turns) < 5:
        print(f"  [warn][revolt-audio:{slug}] script too short ({len(turns)} turns)")
        return None
    bad = check_prohibited(script)
    if bad:
        print(f"  [warn][revolt-audio:{slug}] prohibited terms: {bad[:5]}")
    _save_cached_script(slug, script)
    return script


if __name__ == "__main__":
    import argparse
    import yaml

    EVENTS_DIR = _PROJECT_ROOT / "data" / "revolt" / "events"
    parser = argparse.ArgumentParser(description="Build revolt narration scripts")
    parser.add_argument("--event", type=str)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--print", action="store_true", help="print the script instead of caching")
    args = parser.parse_args()

    paths = [EVENTS_DIR / f"{args.event}.yaml"] if args.event else sorted(EVENTS_DIR.glob("*.yaml"))
    for path in paths:
        if not path.exists():
            print(f"  [error] not found: {path}")
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        script = build_script(data) if args.print else generate_revolt_audio_script(data)
        print(f"\n=== {data.get('slug')} ({len((script or '').splitlines())} turns) ===")
        if args.print:
            print(script)
