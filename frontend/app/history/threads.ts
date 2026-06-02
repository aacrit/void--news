/* ===========================================================================
   void --history — Thematic Threads
   Static thread definitions mapping events into multi-century narratives.
   Used by The Ledger (/history/threads) and The Long View (timeline overlay).
   =========================================================================== */

export interface ThematicThread {
  id: string;
  label: string;
  /** Subtitle shown in thread-grouped view */
  subtitle: string;
  /** CSS custom property suffix for perspective color */
  colorVar: string;
  /** Event slugs in chronological order */
  eventSlugs: string[];
}

/**
 * Six thematic threads derived from the connection graph.
 * Updated for the full 58-event archive (2026-04-10).
 */
export const THREADS: ThematicThread[] = [
  {
    id: "cold-war",
    label: "THE COLD WAR",
    subtitle: "Capitalism vs. Communism — the 200-year ideological contest that never formally ended",
    colorVar: "var(--hist-persp-a)",
    eventSlugs: [
      "industrial-revolution",     // capitalism born, 1760
      "russian-revolution",        // communism's seizure of state power, 1917
      "korean-war",                // first direct US-China military confrontation, 1950
      "cuban-missile-crisis",      // the nuclear flashpoint, 1962
      "vietnam-war",               // capitalism's second proxy war, 1955-1975
      "chinese-cultural-revolution", // high communism, 1966
      "tiananmen-square",          // communism's internal reckoning, 1989
      "fall-of-berlin-wall",       // communism falls, 1989
      "bandung-conference",        // the third path — neither, 1955
      "iranian-revolution",        // the fourth path — theocracy, 1979
    ],
  },
  {
    id: "colonialism",
    label: "COLONIALISM",
    subtitle: "The extraction project — from the first ships to the last borders",
    colorVar: "var(--hist-persp-b)",
    eventSlugs: [
      "columbian-exchange",        // the biological conquest, 1492
      "fall-of-tenochtitlan",      // Mesoamerica falls, 1521
      "inca-conquest-peru",        // Andes falls, 1532
      "transatlantic-slave-trade", // the labor system, 1500-1888
      "kingdom-of-kongo",          // Afonso I's letter to Portugal, 1526
      "opium-wars",                // gunboat economics, 1839
      "scramble-for-africa",       // Berlin, 1884
      "congo-free-state",          // Leopold's severed hands, 1885-1908
      "partition-of-india",        // a lawyer draws the border, 1947
      "rwandan-genocide",          // post-colonial state failure, 1994
      "congo-wars",                // neo-colonial extraction, 1996-2003
      "bandung-conference",        // the anti-colonial response, 1955
    ],
  },
  {
    id: "revolution",
    label: "REVOLUTION",
    subtitle: "When the governed stopped consenting — and what came next",
    colorVar: "var(--hist-persp-c)",
    eventSlugs: [
      "french-revolution",         // liberty, equality, guillotine, 1789
      "haitian-revolution",        // the only successful slave revolt, 1791
      "bolivarian-revolutions",    // Latin America shakes off Spain, 1810
      "russian-revolution",        // October 1917
      "womens-suffrage",           // the longest revolution, 1848-1971
      "indian-independence-movement", // salt to independence, 1930-1947
      "iranian-revolution",        // 1979 — mullahs and women both marched
      "fall-of-berlin-wall",       // November 9, 1989
      "arab-spring",               // fruit vendor to three fallen presidents, 2010
    ],
  },
  {
    id: "war-empire",
    label: "WAR & EMPIRE",
    subtitle: "How power is seized, held, and lost — from Athens to Hiroshima",
    colorVar: "var(--hist-persp-d)",
    eventSlugs: [
      "peloponnesian-war",         // Athens vs Sparta, 431 BCE
      "alexanders-conquests",      // 323 BCE
      "ashoka-maurya-empire",      // conquest to conscience, 268 BCE
      "mongol-empire",             // the largest land empire ever
      "mongol-conquest-baghdad",   // 1258 — a civilization ended
      "the-crusades",              // 1095-1291
      "ottoman-empire",            // 623 years, 1299-1922
      "hiroshima-nagasaki",        // 8.5 seconds, 66,000 dead
      "korean-war",                // the forgotten war, 1950-1953
      "vietnam-war",               // 1955-1975
    ],
  },
  {
    id: "genocide-memory",
    label: "GENOCIDE & MEMORY",
    subtitle: "The systematic killing of peoples — and who decides what is remembered",
    colorVar: "var(--hist-persp-e)",
    eventSlugs: [
      "armenian-genocide",         // the word 'genocide' came from here, 1915
      "holodomor",                 // man-made famine, 1932-1933
      "the-holocaust",             // 6 million, 1941-1945
      "cambodian-genocide",        // 1975-1979 — and the UN backed Pol Pot after
      "rwandan-genocide",          // 800,000 in 100 days, 1994
      "congo-wars",                // 5.4 million dead, 1996-2003 — unnamed
    ],
  },
  {
    id: "trade-technology",
    label: "TRADE & TECHNOLOGY",
    subtitle: "The networks that connected — and the power they transferred",
    colorVar: "var(--hist-persp-f)",
    eventSlugs: [
      "silk-road",                 // merchants, monks, and microbes
      "gutenberg-printing-press",  // copied from a Buddhist idea, 1440
      "columbian-exchange",        // the original biological trade network
      "industrial-revolution",     // steam, coal, and the factory, 1760-1840
      "opium-wars",                // gunboat trade policy, 1839
      "meiji-restoration",         // industrial catch-up, 1868
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
