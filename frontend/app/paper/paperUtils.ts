import type { Edition, Story } from "../lib/types";

/* ---------------------------------------------------------------------------
   E-Paper Utilities — 1970s NYT Broadsheet Layout Engine
   Tier assignment, headline deck generation, story distribution, filler generation.
   --------------------------------------------------------------------------- */

// --- Article Tiers ---

export type ArticleTier = "banner" | "major" | "standard" | "brief" | "bulletin" | "filler";

export function assignTier(index: number, story: Story): ArticleTier {
  // Promote stories with high source coverage
  const boost = story.source.count >= 5 ? -2 : story.source.count === 1 ? 2 : 0;
  const adjusted = index + boost;

  if (adjusted <= 0) return "banner";
  if (adjusted <= 2) return "major";
  if (adjusted <= 7) return "standard";
  if (adjusted <= 14) return "brief";
  if (adjusted <= 24) return "bulletin";
  return "filler";
}

// --- Multi-Deck Headlines ---

export function generateDecks(summary: string, tier: ArticleTier): string[] {
  if (tier === "bulletin" || tier === "filler" || tier === "brief") return [];

  const sentences = summary
    .split(/(?<=[.!?])\s+/)
    .filter((s) => s.trim().length > 15);

  const deckCount = tier === "banner" ? 3 : tier === "major" ? 2 : 1;
  return sentences.slice(0, deckCount).map((s) => s.trim().replace(/\.$/, ""));
}

// --- Dateline Maps ---

export const US_DATELINES: Record<string, string> = {
  Politics: "WASHINGTON, D.C.",
  Economy: "NEW YORK",
  Conflict: "WASHINGTON, D.C.",
  Tech: "SAN FRANCISCO",
  Health: "WASHINGTON, D.C.",
  Environment: "WASHINGTON, D.C.",
  Science: "BOSTON",
  Culture: "NEW YORK",
  Sports: "NEW YORK",
};

export const WORLD_DATELINES: Record<string, string> = {
  Politics: "LONDON",
  Economy: "LONDON",
  Conflict: "BEIRUT",
  Tech: "TOKYO",
  Health: "GENEVA",
  Environment: "NAIROBI",
  Science: "GENEVA",
  Culture: "PARIS",
  Sports: "LAUSANNE",
};

export const INDIA_DATELINES: Record<string, string> = {
  Politics: "NEW DELHI",
  Economy: "MUMBAI",
  Conflict: "NEW DELHI",
  Tech: "BENGALURU",
  Health: "NEW DELHI",
  Environment: "NEW DELHI",
  Science: "NEW DELHI",
  Culture: "MUMBAI",
  Sports: "MUMBAI",
};

export function getDateline(story: Story, edition: Edition): string {
  const map =
    edition === "india"
      ? INDIA_DATELINES
      : edition === "us"
        ? US_DATELINES
        : WORLD_DATELINES;

  const fallback =
    edition === "india"
      ? "NEW DELHI"
      : edition === "us"
        ? "WASHINGTON, D.C."
        : "LONDON";

  return map[story.category] || fallback;
}

// --- Filler Items ---

export interface FillerItem {
  type: "wire-bulletin" | "coverage-note" | "editorial-note" | "jump-line";
  text: string;
  heading?: string;
}

function firstSentence(text: string): string {
  const match = text.match(/^(.+?[.!?])\s/);
  return match ? match[1] : text.slice(0, 120) + "\u2026";
}

export function generateFillers(
  overflowStories: Story[],
  totalCount: number,
  edition: Edition,
): FillerItem[] {
  const fillers: FillerItem[] = [];

  // Wire bulletins from low-rank stories
  for (const story of overflowStories.slice(0, 8)) {
    const dateline = getDateline(story, edition);
    fillers.push({
      type: "wire-bulletin",
      heading: "BULLETIN",
      text: `${dateline} \u2014 ${firstSentence(story.summary)}`,
    });
  }

  // Coverage note
  fillers.push({
    type: "coverage-note",
    heading: "COVERAGE NOTES",
    text: `This edition compiled from ${totalCount} dispatches across 200 curated news organisations. All assessments computed algorithmically.`,
  });

  // Editorial note
  fillers.push({
    type: "editorial-note",
    heading: "THE EDITORS NOTE",
    text: `Divergent perspectives have been observed across multiple wire services on several matters reported in this edition. Readers are encouraged to consult the Digital Edition for detailed source analysis.`,
  });

  return fillers;
}

// --- Story Distribution ---

export interface FrontPageLayout {
  zoneA: Story[]; // Left 3 columns
  zoneB: Story[]; // Center 2 columns (lead)
  zoneC: Story[]; // Right 3 columns
  fillers: FillerItem[];
  sectionStories: Story[]; // Remaining for section flow
}

export function distributeStories(
  stories: Story[],
  edition: Edition,
): FrontPageLayout {
  const sorted = [...stories].sort((a, b) => b.headlineRank - a.headlineRank);

  const zoneB: Story[] = [];
  const zoneA: Story[] = [];
  const zoneC: Story[] = [];

  const FRONT_PAGE_CAP = 20;

  // #1 -> Zone B (banner lead, center)
  if (sorted.length > 0) zoneB.push(sorted[0]);
  // #2 -> Zone C (major, upper-right -- traditional lead position)
  if (sorted.length > 1) zoneC.push(sorted[1]);
  // #3 -> Zone A (major, upper-left)
  if (sorted.length > 2) zoneA.push(sorted[2]);
  // #4 -> Zone B (below lead)
  if (sorted.length > 3) zoneB.push(sorted[3]);

  // #5+ -> Alternate between zones A and C
  for (let i = 4; i < Math.min(sorted.length, FRONT_PAGE_CAP); i++) {
    if (zoneA.length <= zoneC.length) {
      zoneA.push(sorted[i]);
    } else {
      zoneC.push(sorted[i]);
    }
  }

  // Overflow stories become section flow + fillers
  const sectionStories = sorted.slice(FRONT_PAGE_CAP, 60);
  const overflowForFillers = sorted.slice(60);

  const fillers = generateFillers(overflowForFillers, stories.length, edition);

  return { zoneA, zoneB, zoneC, fillers, sectionStories };
}

// --- Section names per edition ---

export function getSectionConfig(edition: Edition): {
  primary: string;
  secondary?: string;
} {
  switch (edition) {
    case "us":
      return { primary: "THE NATION" };
    case "india":
      return { primary: "NATIONAL" };
    default:
      return { primary: "WORLD NEWS" };
  }
}

// --- Category normalization (from current page.tsx) ---

export function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics",
    conflict: "Conflict",
    economy: "Economy",
    science: "Science",
    health: "Health",
    environment: "Environment",
    culture: "Culture",
    tech: "Science",
    technology: "Science",
    sports: "Culture",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
}

// --- Body text — never truncated in epaper view ---

export function truncateSummary(summary: string, _tier: ArticleTier): string {
  return summary;
}

// --- Subhead generation (every ~3 sentences for banner/major) ---

export function generateSubheads(
  summary: string,
  tier: ArticleTier,
  category: string,
): string[] {
  if (tier !== "banner" && tier !== "major") return [];

  const sentences = summary.split(/(?<=[.!?])\s+/).filter((s) => s.length > 10);
  if (sentences.length < 6) return [];

  // Insert a subhead every ~4 sentences
  const subheads: string[] = [];
  const interval = 4;
  for (let i = interval; i < sentences.length; i += interval) {
    // Use category-derived subhead text
    subheads.push(category.toUpperCase());
  }
  return subheads;
}

// --- Edition display names ---

export function editionSubtitle(edition: Edition): string | null {
  switch (edition) {
    case "us":
      return "United States Edition";
    case "india":
      return "India Edition";
    default:
      return null;
  }
}
