/* ===========================================================================
   void --history — Thematic Threads
   Static thread definitions mapping events into multi-century narratives.
   Used by The Ledger (/history/threads) and The Long View (timeline overlay).
   =========================================================================== */

export interface ThematicThread {
  id: string;
  label: string;
  /** CSS custom property suffix for perspective color */
  colorVar: string;
  /** Event slugs in chronological order */
  eventSlugs: string[];
}

/**
 * Five thematic threads derived from the connection graph.
 * Hardcoded membership is correct for launch — the data supports
 * dynamic derivation, but static arrays are more reliable.
 */
export const THREADS: ThematicThread[] = [
  {
    id: "colonialism",
    label: "COLONIALISM",
    colorVar: "var(--hist-persp-a)",
    eventSlugs: [
      "fall-of-tenochtitlan",
      "transatlantic-slave-trade",
      "scramble-for-africa",
      "congo-free-state",
      "opium-wars",
      "partition-of-india",
      "rwandan-genocide",
    ],
  },
  {
    id: "revolution",
    label: "REVOLUTION",
    colorVar: "var(--hist-persp-b)",
    eventSlugs: [
      "french-revolution",
      "haitian-revolution",
      "bolivarian-revolutions",
      "russian-revolution",
      "indian-independence-movement",
      "fall-of-berlin-wall",
    ],
  },
  {
    id: "war-empire",
    label: "WAR & EMPIRE",
    colorVar: "var(--hist-persp-c)",
    eventSlugs: [
      "peloponnesian-war",
      "alexanders-conquests",
      "ashoka-maurya-empire",
      "mongol-empire",
      "mongol-conquest-baghdad",
      "the-crusades",
      "opium-wars",
      "hiroshima-nagasaki",
      "cuban-missile-crisis",
    ],
  },
  {
    id: "genocide-memory",
    label: "GENOCIDE & MEMORY",
    colorVar: "var(--hist-persp-d)",
    eventSlugs: [
      "armenian-genocide",
      "holodomor",
      "the-holocaust",
      "cambodian-genocide",
      "rwandan-genocide",
    ],
  },
  {
    id: "trade-technology",
    label: "TRADE & TECHNOLOGY",
    colorVar: "var(--hist-persp-e)",
    eventSlugs: [
      "silk-road",
      "gutenberg-printing-press",
      "opium-wars",
      "meiji-restoration",
    ],
  },
];

/**
 * Build a lookup: event slug -> list of thread IDs it belongs to.
 */
export function buildThreadMembership(): Map<string, ThematicThread[]> {
  const map = new Map<string, ThematicThread[]>();
  for (const thread of THREADS) {
    for (const slug of thread.eventSlugs) {
      const existing = map.get(slug) ?? [];
      existing.push(thread);
      map.set(slug, existing);
    }
  }
  return map;
}
