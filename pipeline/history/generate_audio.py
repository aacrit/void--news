"""
void --history companion audio — batch generator.

Generates MP3 audio companions for history events.
One MP3 per event: Gemini script generation (1 call) + TTS (1-2 calls).
Idempotent: skips events already in the manifest.

Usage:
  # Pilot run — specific slugs
  python pipeline/history/generate_audio.py --slugs partition-of-india hiroshima-nagasaki

  # Batch by offset/count
  python pipeline/history/generate_audio.py --batch-size 8 --offset 0

  # Force regenerate (ignore manifest)
  python pipeline/history/generate_audio.py --slugs partition-of-india --force

Environment:
  GEMINI_API_KEY  — required
  SUPABASE_URL    — required for upload + DB update
  SUPABASE_KEY    — required for upload + DB update

Output:
  data/history/audio-manifest.json  — slug → {url, duration_seconds, generated_at}
  Supabase history_events.audio_url + audio_duration_seconds updated
  Supabase Storage: audio-briefs/history/{slug}.mp3
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from project root
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

import yaml

from history.audio_script_generator import generate_history_audio_script
from briefing.audio_producer import produce_history_audio

# ---------------------------------------------------------------------------
# HOOKS — arrive-late one-liners for each event (mirrors hooks.ts)
# ---------------------------------------------------------------------------

HOOKS: dict[str, str] = {
    "partition-of-india": "A lawyer who'd never been to India drew the border in five weeks. 15 million crossed it.",
    "hiroshima-nagasaki": "66,000 dead in 8.5 seconds. Seven of eight five-star American generals said it wasn't necessary.",
    "rwandan-genocide": "The UN had a fax warning them. They reduced their force from 2,500 to 270. 800,000 died in 100 days.",
    "scramble-for-africa": "Fourteen nations met in a Berlin conference room in 1884. Not one African was invited. By 1914, Europeans controlled 90% of the continent.",
    "opium-wars": "Britain went to war because China burned 20,000 chests of opium. The peace treaty ceded Hong Kong for 156 years.",
    "french-revolution": "A Parisian laborer spent 88% of his wages on bread. On July 14, the crowd took 30,000 muskets. The Bastille fell by dinner.",
    "creation-of-israel-nakba": "On May 14, 1948, one people declared independence. On May 15, 750,000 of another people became refugees. Same land.",
    "trail-of-tears": "The Supreme Court ruled in their favor. The president ignored the ruling. 60,000 walked. 4,000 never arrived.",
    "fall-of-berlin-wall": "At 6:53 p.m. on November 9, 1989, a spokesman misread a memo on live television. The Wall fell by midnight.",
    "transatlantic-slave-trade": "12.5 million embarked. 10.7 million survived the crossing. The database lists 36,000 individual voyages.",
    "armenian-genocide": "The American ambassador cabled Washington: 'Race extermination.' Raphael Lemkin later coined a word for it — 'genocide.'",
    "holodomor": "Gareth Jones walked through Ukrainian villages counting bodies. Walter Duranty won a Pulitzer for saying there was no famine.",
    "congo-free-state": "Leopold II never visited the Congo. His agents collected severed hands as proof of productivity. The population fell by 10 million.",
    "cambodian-genocide": "Tuol Sleng processed 17,000 prisoners. Seven survived. The guards photographed every face before killing them.",
    "tiananmen-square": "On June 5, 1989, a man with two shopping bags stopped a column of tanks. No one knows his name. China erased the photograph.",
    "peloponnesian-war": "Athens told the island of Melos: submit or die. Melos chose neutrality. Athens killed every man and enslaved the women and children.",
    "mongol-conquest-baghdad": "The Tigris ran black with ink from a million manuscripts. Then Hulagu built the world's finest observatory with the looted books.",
    "haitian-revolution": "Dessalines tore the white from the French tricolor. The flag that remained was the first made by formerly enslaved people who'd defeated a European army.",
    "meiji-restoration": "Japan watched China lose two wars to Britain. In 30 years, a feudal archipelago built railways, a constitution, and a navy that sank the Russian fleet.",
    "treaty-of-waitangi": "The English text said 'sovereignty.' The Maori text said 'governance.' Hone Heke cut down the British flagpole four times to make the point.",
    "bolivarian-revolutions": "Bolívar sailed to Haiti after his defeat. Pétion gave him ships and soldiers in exchange for one promise: free the enslaved. Bolívar partially broke it.",
    "ashoka-maurya-empire": "He carved the body count into rock for everyone to read: 100,000 killed, 150,000 deported. Then, on the same stone, he said he regretted it.",
    "fall-of-rome": "The last emperor was sixteen. The general who deposed him didn't kill him — he gave him a pension and mailed the crown to Constantinople.",
    "mali-empire-mansa-musa": "Mansa Musa carried 18 tons of gold to Mecca. His charity crashed Egypt's gold market for twelve years.",
    "the-crusades": "The Fourth Crusade never reached Jerusalem. It sacked Constantinople — the largest Christian city on earth — instead.",
    "september-11-attacks": "Nineteen men with box cutters turned the world's most powerful military against two countries that didn't attack it.",
    "black-death": "It killed one in three Europeans — and the survivors demanded higher wages.",
    "assassination-of-caesar": "The Senate voted him dictator for life. Forty days later, twenty-three senators voted with knives.",
    "civil-rights-movement": "Four college students sat at a lunch counter in Greensboro. Within two months, sit-ins had spread to 54 cities.",
    "indian-independence-movement": "A lawyer in a loincloth walked to the sea to pick up salt — and broke an empire's monopoly on everything.",
    "fall-of-tenochtitlan": "Cortés had 500 soldiers. Tenochtitlan had 300,000 people. Smallpox decided the math.",
    "alexanders-conquests": "He named 20 cities after himself and one after his horse.",
    "the-holocaust": "IBM sold the machines that sorted people by ancestry. The trains ran on time.",
    "russian-revolution": "The Tsar abdicated on a Wednesday. By Friday, two governments claimed to rule Russia. By October, neither did.",
    "apartheid": "They imprisoned him for 27 years. Then they asked him to run the country.",
    "silk-road": "A Roman woman wore Chinese silk without either empire knowing the other existed.",
    "mongol-empire": "He couldn't read, but he wrote a legal code that governed more people than Rome ever did.",
    "cuban-missile-crisis": "For thirteen days, one Soviet submarine officer was the only thing between humanity and nuclear war.",
    "gutenberg-printing-press": "A bankrupt goldsmith copied a Buddhist idea and accidentally ended the Catholic Church's monopoly on truth.",
    "chinese-cultural-revolution": "Students beat their teachers to death with the textbooks they'd been taught from.",
    "cyrus-cylinder": "He freed the Babylonians, the Jews, and the Egyptians — and put it in writing. 2,500 years before human rights became a legal concept.",
    "fall-of-constantinople": "A 21-year-old sultan hired a cannon maker the emperor couldn't pay. Then someone left a gate unlocked.",
    "mughal-empire": "Twenty followers joined Akbar's new religion. His empire held 25% of world GDP.",
    "angkor-khmer-empire": "LIDAR revealed a city larger than modern Paris, buried under jungle since 1431. No one had noticed the canals.",
    "kingdom-of-kongo": "Afonso I wrote to Portugal in 1526: 'Your people are taking our people.' He was writing to the man selling them.",
    "rise-of-islam": "Within 100 years of the first revelation, Islam stretched from Spain to the borders of China. The Byzantine and Sassanid empires were gone.",
    "inca-conquest-peru": "168 soldiers captured the emperor of 12 million people. The ransom room filled with gold. Then they killed him anyway.",
    "taiping-rebellion": "A failed exam candidate claimed to be Jesus's brother. His kingdom grew to 30 million people and cost more lives than the First World War.",
    "ottoman-empire": "The empire lasted 623 years. The men who carved it up needed six.",
    "industrial-revolution": "In 1750, a Bengali weaver earned more than his English counterpart. By 1830, the looms of Dacca were silent — Britain had made sure of it.",
    "vietnam-war": "The Pentagon Papers showed the government knew by 1967 it couldn't win. The war continued for eight more years. 2.1 million more people died.",
    "womens-suffrage": "New Zealand gave women the vote in 1893. Switzerland waited until 1971. One canton held out until 1990 — a federal court forced it.",
    "arab-spring": "A fruit vendor set himself on fire in a town of 40,000. Within 60 days, three presidents had fallen.",
    "columbian-exchange": "Columbus carried 17 ships on his second voyage. On them were horses, cattle, pigs, and smallpox. Within 50 years, 90% of the people he'd found were dead.",
    "korean-war": "The US dropped more bombs on Korea than it used in the entire Pacific war. The armistice was signed in 1953. No peace treaty has ever followed.",
    "congo-wars": "The deadliest war since 1945 killed 5.4 million people. Most people cannot name the country where it happened.",
    "bandung-conference": "Twenty-nine nations sent delegates to a city in Java. They represented 1.5 billion people — more than half the world — and not one of their countries had been independent 15 years earlier.",
    "iranian-revolution": "Women marched alongside mullahs to overthrow the Shah. Within a year, the mullahs made the veil mandatory.",
}

# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

MANIFEST_PATH = REPO_ROOT / "data" / "history" / "audio-manifest.json"
EVENTS_DIR = REPO_ROOT / "data" / "history" / "events"


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Supabase update
# ---------------------------------------------------------------------------

def _update_supabase(slug: str, audio_url: str, duration_seconds: float) -> bool:
    """Update history_events row with audio_url and audio_duration_seconds."""
    try:
        from utils.supabase_client import supabase
        result = supabase.table("history_events").update({
            "audio_url": audio_url,
            "audio_duration_seconds": duration_seconds,
        }).eq("slug", slug).execute()
        return True
    except Exception as e:
        print(f"  [warn][history-audio:{slug}] Supabase update failed: {e}")
        return False


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def _load_event_yaml(slug: str) -> dict | None:
    """Load and parse a history event YAML file."""
    yaml_path = EVENTS_DIR / f"{slug}.yaml"
    if not yaml_path.exists():
        print(f"  [error] YAML not found: {yaml_path}")
        return None
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"  [error] YAML parse failed for {slug}: {e}")
        return None


def _all_slugs() -> list[str]:
    """Return all event slugs sorted chronologically (by filename, then date_sort)."""
    yaml_files = sorted(EVENTS_DIR.glob("*.yaml"))
    slugs = []
    for p in yaml_files:
        slug = p.stem
        # Quick-parse date_sort for ordering
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            date_sort = data.get("date_sort", 9999)
            slugs.append((date_sort, slug))
        except Exception:
            slugs.append((9999, slug))
    slugs.sort(key=lambda x: x[0])
    return [s for _, s in slugs]


# ---------------------------------------------------------------------------
# Per-event processing
# ---------------------------------------------------------------------------

def process_event(slug: str, force: bool = False) -> bool:
    """Generate and upload audio for a single history event.

    Args:
        slug: Event slug (e.g. 'partition-of-india').
        force: If True, regenerate even if already in manifest.

    Returns:
        True on success, False on failure.
    """
    manifest = _load_manifest()

    if not force and slug in manifest:
        print(f"  [skip] {slug} — already in manifest (use --force to regenerate)")
        return True

    hook = HOOKS.get(slug, "")
    if not hook:
        print(f"  [warn] No hook found for {slug} — using event title as opener")

    event_data = _load_event_yaml(slug)
    if not event_data:
        return False

    # Add slug to event_data if missing
    if "slug" not in event_data:
        event_data["slug"] = slug

    print(f"\n{'='*60}")
    print(f"  Processing: {event_data.get('title', slug)}")
    print(f"  Era: {event_data.get('era', 'unknown')} | Precision: {event_data.get('date_precision', 'year')}")
    print(f"  Perspectives: {len(event_data.get('perspectives', []))}")
    print(f"{'='*60}")

    # Step 1: Generate script
    script = generate_history_audio_script(event_data, hook, slug)
    if not script:
        print(f"  [FAIL] Script generation failed for {slug}")
        return False

    # Step 2: Rate-limit pause before TTS
    print(f"  [history-audio:{slug}] Waiting 15s before TTS call...")
    time.sleep(15)

    # Step 3: Synthesize and upload
    result = produce_history_audio(script, slug)
    if not result:
        print(f"  [FAIL] Audio production failed for {slug}")
        return False

    audio_url = result["audio_url"]
    duration_seconds = result["duration_seconds"]

    # Step 4: Update manifest
    manifest[slug] = {
        "url": audio_url,
        "duration_seconds": duration_seconds,
        "file_size_kb": round(result.get("file_size", 0) / 1024, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_manifest(manifest)

    # Step 5: Update Supabase
    db_ok = _update_supabase(slug, audio_url, duration_seconds)
    status = "DB updated" if db_ok else "DB update FAILED (manifest saved)"

    print(f"  [OK] {slug}: {duration_seconds:.1f}s, {result.get('file_size', 0) // 1024} KB — {status}")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate void --history companion audio")
    parser.add_argument(
        "--slugs", nargs="+", metavar="SLUG",
        help="Specific event slugs to process",
    )
    parser.add_argument(
        "--batch-size", type=int, default=8,
        help="Number of events per batch (default: 8)",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Starting event index in chronological order (default: 0)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate even if already in manifest",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all events and their manifest status, then exit",
    )
    args = parser.parse_args()

    manifest = _load_manifest()
    all_slugs = _all_slugs()

    if args.list:
        print(f"\nvoid --history audio manifest ({len(manifest)} generated / {len(all_slugs)} total)\n")
        for i, slug in enumerate(all_slugs):
            status = "✓" if slug in manifest else "·"
            dur = f"{manifest[slug]['duration_seconds']:.0f}s" if slug in manifest else ""
            print(f"  {status} [{i:2d}] {slug:<45} {dur}")
        return

    # Determine which slugs to process
    if args.slugs:
        target_slugs = args.slugs
    else:
        target_slugs = all_slugs[args.offset : args.offset + args.batch_size]

    print(f"\nvoid --history audio batch: {len(target_slugs)} events")
    if not args.slugs:
        print(f"  Offset: {args.offset}, batch size: {args.batch_size}")
    print(f"  Manifest: {len(manifest)} already generated")
    print()

    success = 0
    failed = 0

    for i, slug in enumerate(target_slugs):
        if i > 0:
            # Rate-limit pause between events (script gen + TTS = ~30s each)
            print(f"\n[pause 20s between events...]")
            time.sleep(20)

        ok = process_event(slug, force=args.force)
        if ok:
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"Batch complete: {success} succeeded, {failed} failed")
    print(f"Manifest: {MANIFEST_PATH}")
    manifest = _load_manifest()
    print(f"Total generated: {len(manifest)} / {len(all_slugs)} events")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
