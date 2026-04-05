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
    slug: "partition-of-india-1947",
    title: "The Partition of India",
    perspectiveCount: 4,
  },
  {
    keywords: ["hiroshima", "nagasaki", "atomic bomb", "nuclear weapon"],
    slug: "hiroshima-1945",
    title: "Hiroshima & Nagasaki",
    perspectiveCount: 3,
  },
  {
    keywords: ["rwandan genocide", "rwanda genocide", "tutsi", "hutu"],
    slug: "rwandan-genocide-1994",
    title: "The Rwandan Genocide",
    perspectiveCount: 3,
  },
  {
    keywords: ["armenian genocide", "armenian massacre"],
    slug: "armenian-genocide-1915",
    title: "The Armenian Genocide",
    perspectiveCount: 0, // redacted — coming soon
  },
  {
    keywords: ["trail of tears", "native american removal", "cherokee removal"],
    slug: "trail-of-tears-1838",
    title: "The Trail of Tears",
    perspectiveCount: 0,
  },
  {
    keywords: ["slave trade", "transatlantic slave", "slavery abolition"],
    slug: "transatlantic-slave-trade",
    title: "The Transatlantic Slave Trade",
    perspectiveCount: 0,
  },
  {
    keywords: ["tiananmen", "tiananmen square"],
    slug: "tiananmen-square-1989",
    title: "Tiananmen Square",
    perspectiveCount: 0,
  },
  {
    keywords: ["holodomor", "ukraine famine 1932"],
    slug: "holodomor-1932",
    title: "The Holodomor",
    perspectiveCount: 0,
  },
  {
    keywords: ["khmer rouge", "cambodian genocide", "pol pot"],
    slug: "cambodian-genocide-1975",
    title: "The Cambodian Genocide",
    perspectiveCount: 0,
  },
  {
    keywords: ["congo free state", "leopold congo", "rubber terror"],
    slug: "congo-free-state",
    title: "The Congo Free State",
    perspectiveCount: 0,
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
