import type { Edition, Story } from "../lib/types";

/* ---------------------------------------------------------------------------
   E-Paper Utilities — Modern Broadsheet Layout Engine
   3-tier system, story distribution, dateline maps.
   --------------------------------------------------------------------------- */

// --- Article Tiers (simplified: 3 tiers) ---

export type ArticleTier = "lead" | "standard" | "brief";

export function assignTier(index: number, _story: Story): ArticleTier {
  if (index === 0) return "lead";
  if (index <= 20) return "standard";
  return "brief";
}

// --- Dateline Maps ---

export const US_DATELINES: Record<string, string> = {
  Politics: "WASHINGTON",
  Economy: "NEW YORK",
  Conflict: "WASHINGTON",
  Tech: "SAN FRANCISCO",
  Health: "WASHINGTON",
  Environment: "WASHINGTON",
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
        ? "WASHINGTON"
        : "LONDON";

  return map[story.category] || fallback;
}

// --- Story Distribution ---

export interface FrontPageLayout {
  leadStory: Story | null;
  topStories: Story[];   // Stories 2-5 (2-column grid)
  remaining: Story[];    // All remaining (4-column flow)
}

export function distributeStories(stories: Story[]): FrontPageLayout {
  const sorted = [...stories].sort((a, b) => b.headlineRank - a.headlineRank);

  return {
    leadStory: sorted[0] || null,
    topStories: sorted.slice(1, 5),
    remaining: sorted.slice(5),
  };
}

// --- Section names per edition ---

export function getSectionConfig(edition: Edition): {
  primary: string;
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

// --- Text truncation for e-paper layout ---

export function truncateSummary(text: string, tier: ArticleTier): string {
  if (!text) return "";
  const limits: Record<ArticleTier, number> = {
    lead: 600,
    standard: 300,
    brief: 150,
  };
  const limit = limits[tier] || 300;
  if (text.length <= limit) return text;
  return text.slice(0, limit).replace(/\s+\S*$/, "") + "...";
}

// --- Category normalization ---

export function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics",
    economy: "Economy",
    science: "Science",
    health: "Health",
    culture: "Culture",
    conflict: "Politics",
    tech: "Science",
    technology: "Science",
    environment: "Health",
    sports: "Culture",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
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
