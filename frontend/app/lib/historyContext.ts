/* ===========================================================================
   History Context — keyword-based cross-link between void --news and void --history
   Checks if a story cluster's title/summary references a historical event.
   Returns the matched event's slug + title for deep-linking.
   =========================================================================== */

import { BASE_PATH } from "./utils";

interface HistoryMatch {
  slug: string;
  title: string;
  perspectiveCount: number;
  href: string;
}

/**
 * Keyword → history event mapping.
 * Keys are lowercase phrases; matched against lowercased title + summary.
 * Multi-word keys require the full phrase to appear (not individual words).
 */
const HISTORY_CONTEXT_MAP: {
  keywords: string[];
  slug: string;
  title: string;
  perspectiveCount: number;
}[] = [
  {
    keywords: ["partition of india", "kashmir conflict", "india-pakistan", "india pakistan border"],
    slug: "partition-of-india",
    title: "The Partition of India",
    perspectiveCount: 4,
  },
  {
    keywords: ["hiroshima", "nagasaki", "atomic bomb", "nuclear weapon"],
    slug: "hiroshima-nagasaki",
    title: "Hiroshima & Nagasaki",
    perspectiveCount: 4,
  },
  {
    keywords: ["rwandan genocide", "rwanda genocide", "tutsi", "hutu"],
    slug: "rwandan-genocide",
    title: "The Rwandan Genocide",
    perspectiveCount: 4,
  },
  {
    keywords: ["israel", "palestine", "nakba", "zionist"],
    slug: "creation-of-israel-nakba",
    title: "The Creation of Israel & the Nakba",
    perspectiveCount: 4,
  },
  {
    keywords: ["berlin wall", "german reunification", "east germany"],
    slug: "fall-of-berlin-wall",
    title: "The Fall of the Berlin Wall",
    perspectiveCount: 4,
  },
  {
    keywords: ["french revolution", "bastille", "robespierre"],
    slug: "french-revolution",
    title: "The French Revolution",
    perspectiveCount: 4,
  },
  {
    keywords: ["opium war", "china trade", "lin zexu"],
    slug: "opium-wars",
    title: "The Opium Wars",
    perspectiveCount: 4,
  },
  {
    keywords: ["scramble for africa", "berlin conference", "colonial africa"],
    slug: "scramble-for-africa",
    title: "The Scramble for Africa",
    perspectiveCount: 4,
  },
  {
    keywords: ["trail of tears", "native american removal", "cherokee removal"],
    slug: "trail-of-tears",
    title: "The Trail of Tears",
    perspectiveCount: 4,
  },
  {
    keywords: ["slave trade", "transatlantic slave", "slavery abolition"],
    slug: "transatlantic-slave-trade",
    title: "The Transatlantic Slave Trade",
    perspectiveCount: 4,
  },
];

/**
 * Given a story's title and summary, find the first matching historical event.
 * Returns null if no keyword matches.
 */
export function findHistoryContext(
  title: string,
  summary: string
): HistoryMatch | null {
  const haystack = `${title} ${summary}`.toLowerCase();

  for (const entry of HISTORY_CONTEXT_MAP) {
    for (const keyword of entry.keywords) {
      if (haystack.includes(keyword)) {
        return {
          slug: entry.slug,
          title: entry.title,
          perspectiveCount: entry.perspectiveCount,
          href: `${BASE_PATH}/history/${entry.slug}`,
        };
      }
    }
  }

  return null;
}
