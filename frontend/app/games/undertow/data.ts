/* ==========================================================================
   UNDERTOW — Daily Cultural Subtext Puzzle Data
   Static mock data for MVP. Pipeline will generate JSON later.
   ========================================================================== */

export type ArtifactCategory =
  | "advertising"
  | "speech"
  | "wellness"
  | "corporate"
  | "literary"
  | "lyric"
  | "linkedin"
  | "manifesto";

export interface Artifact {
  id: string;
  text: string; // The artifact text — NO names, NO dates
  category: ArtifactCategory;
  axis_position: number; // -2 to +2 (negative = left pole, positive = right pole)
  highlighted_words: string[]; // specific words to highlight during reveal
  reveal: string; // 2-3 sentences, witty + precise
}

export interface Axis {
  label: string; // e.g. "CULT <-> YOGA CLASS"
  left_pole: string; // e.g. "CULT"
  right_pole: string; // e.g. "YOGA CLASS"
  description: string; // one sharp question that makes you laugh and think
}

export interface DailyChallenge {
  id: number;
  date: string;
  axis: Axis;
  artifacts: Artifact[];
  correct_order: string[]; // ids: leftmost -> rightmost
  tomorrow_axis?: string; // teaser for next day
}

/** Category label colors — muted, atmospheric */
export const CATEGORY_COLORS: Record<ArtifactCategory, string> = {
  advertising: "#b5a08a",
  speech: "#8a9bb5",
  wellness: "#a08ab5",
  corporate: "#8ab5a0",
  literary: "#b5b08a",
  lyric: "#b58a8a",
  linkedin: "#8aabb5",
  manifesto: "#b58aaa",
};

/** Background images per axis — Unsplash License (free commercial use) */
export const AXIS_IMAGES: Record<string, { url: string; credit: string }> = {
  CULT: {
    url: "https://images.unsplash.com/photo-XS49QQVKh_8?w=1920&q=80&auto=format&fit=crop",
    credit: "Ilia Bronskiy",
  },
  BOSS: {
    url: "https://images.unsplash.com/photo-AHlWf9ICfIc?w=1920&q=80&auto=format&fit=crop",
    credit: "Willian Justen de Vasconcellos",
  },
  "2AM": {
    url: "https://images.unsplash.com/photo-Xq1VNBrpJzI?w=1920&q=80&auto=format&fit=crop",
    credit: "Baris Cobanoglu",
  },
  DAD: {
    url: "https://images.unsplash.com/photo-7q-hhI27pUU?w=1920&q=80&auto=format&fit=crop",
    credit: "Hasan Almasi",
  },
  DEFAULT: {
    url: "https://images.unsplash.com/photo-f01ZbhYCBuQ?w=1920&q=80&auto=format&fit=crop",
    credit: "Alexander X.",
  },
};

/** Resolve the background image for a given axis */
export function getAxisImage(leftPole: string): { url: string; credit: string } {
  const key = Object.keys(AXIS_IMAGES).find((k) => leftPole.includes(k));
  return key ? AXIS_IMAGES[key] : AXIS_IMAGES["DEFAULT"];
}

export const DAILY_UNDERTOW: DailyChallenge = {
  id: 1,
  date: "2026-04-10",
  axis: {
    label: "SOUNDS LIKE A CULT \u2194 SOUNDS LIKE A YOGA CLASS",
    left_pole: "CULT",
    right_pole: "YOGA CLASS",
    description:
      "Is this asking you to surrender yourself \u2014 or just your Saturday morning?",
  },
  artifacts: [
    {
      id: "a",
      text: "Leave everything behind. Your old life was a preparation. The community is waiting. You are ready now.",
      category: "manifesto",
      axis_position: -2,
      highlighted_words: [
        "Leave everything behind",
        "old life",
        "community is waiting",
      ],
      reveal:
        'Four sentences. Four imperatives. The self that arrived is described as a problem to be solved. "Ready now" closes the door on the question of whether you agreed to any of this.',
    },
    {
      id: "b",
      text: "This is not just a workout. This is a movement. Clip in. Find your tribe. Leave it all on the bike.",
      category: "advertising",
      axis_position: -0.9,
      highlighted_words: ["movement", "tribe", "Leave it all"],
      reveal:
        "The copy borrows the grammar of conversion. \"Movement\" and \"tribe\" do not belong to fitness \u2014 they belong to belonging. The bike is incidental. The subscription is not mentioned.",
    },
    {
      id: "c",
      text: "Honor your body. Release what no longer serves you. This hour belongs to you.",
      category: "wellness",
      axis_position: 1.1,
      highlighted_words: [
        "Honor",
        "Release",
        "no longer serves you",
        "belongs to you",
      ],
      reveal:
        '"No longer serves you" treats your own feelings as employees you can terminate. The grammar is gentle. The implication \u2014 that your current self needs to be managed \u2014 is not.',
    },
    {
      id: "d",
      text: "Set an intention. Breathe into it. The mat is a mirror. You already have everything you need.",
      category: "wellness",
      axis_position: 1.9,
      highlighted_words: [
        "intention",
        "mirror",
        "already have everything",
      ],
      reveal:
        "The claim that you already have everything you need is the most radical sentence here \u2014 it is the one selling the least. The mat as mirror is a metaphor so soft it almost disappears. This one means it.",
    },
  ],
  correct_order: ["a", "b", "c", "d"],
};
