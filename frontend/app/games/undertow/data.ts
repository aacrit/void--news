/* ==========================================================================
   UNDERTOW — Daily Cultural Subtext Puzzle Data
   Static mock data for MVP. Pipeline will generate JSON later.
   ========================================================================== */

export type ArtifactCategory =
  | "advertising"
  | "speech"
  | "corporate"
  | "literary"
  | "lyric"
  | "logline";

export interface Artifact {
  id: string;
  text: string; // The artifact text — NO names, NO dates
  category: ArtifactCategory;
  axis_position: number; // -2 to +2 (negative = left pole, positive = right pole)
  highlighted_words: string[]; // specific words to highlight during reveal
  reveal: string; // 2-3 sentences of Orwellian commentary
}

export interface Axis {
  label: string;
  left_pole: string;
  right_pole: string;
  description: string;
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
  speech: "#8a9bb5", // muted blue
  advertising: "#b5a08a", // muted amber
  literary: "#a08ab5", // muted violet
  corporate: "#8ab5a0", // muted teal
  lyric: "#b58a8a", // muted rose
  logline: "#9bb58a", // muted sage
};

/** Background images per axis — Unsplash License (free commercial use) */
export const AXIS_IMAGES: Record<
  string,
  { url: string; credit: string }
> = {
  default: {
    url: "https://images.unsplash.com/photo-f01ZbhYCBuQ?w=1920&q=80&auto=format&fit=crop",
    credit: "Alexander X.",
  },
  "CONTROL": {
    url: "https://images.unsplash.com/photo-XS49QQVKh_8?w=1920&q=80&auto=format&fit=crop",
    credit: "Ilia Bronskiy",
  },
  "COLLECTIVE": {
    url: "https://images.unsplash.com/photo-AHlWf9ICfIc?w=1920&q=80&auto=format&fit=crop",
    credit: "Willian Justen de Vasconcellos",
  },
  "OPTIMISM": {
    url: "https://images.unsplash.com/photo-Xq1VNBrpJzI?w=1920&q=80&auto=format&fit=crop",
    credit: "Baris Cobanoglu",
  },
  "TRADITION": {
    url: "https://images.unsplash.com/photo-7q-hhI27pUU?w=1920&q=80&auto=format&fit=crop",
    credit: "Hasan Almasi",
  },
};

/** Resolve the background image for a given axis */
export function getAxisImage(axis: Axis): { url: string; credit: string } {
  // Try matching left pole first, then right pole
  return (
    AXIS_IMAGES[axis.left_pole] ??
    AXIS_IMAGES[axis.right_pole] ??
    AXIS_IMAGES["default"]
  );
}

export const DAILY_UNDERTOW: DailyChallenge = {
  id: 1,
  date: "2026-04-10",
  axis: {
    label: "CONTROL \u2194 FREEDOM",
    left_pole: "CONTROL",
    right_pole: "FREEDOM",
    description:
      "Where does this text locate the source of order \u2014 in structure, or in the self?",
  },
  artifacts: [
    {
      id: "a",
      text: "The harvest belongs to all. Our fields, our future, our strength \u2014 together.",
      category: "speech",
      axis_position: -2,
      highlighted_words: ["belongs to all", "Our", "together"],
      reveal:
        "No singular pronoun appears. The grammar does the work before the argument does. \u2018Our\u2019 repeated three times confirms what \u2018together\u2019 makes explicit: the individual is grammatically absent before they are politically so.",
    },
    {
      id: "b",
      text: "We exist to connect every person on earth and give everyone the power to share anything with anyone.",
      category: "corporate",
      axis_position: -0.8,
      highlighted_words: ["connect every person", "give", "everyone"],
      reveal:
        "The promise is universal freedom. The mechanism is a single platform owned by one company. The text does not register this tension. \u2018Give\u2019 places the company in the role of benefactor. The infrastructure is not mentioned.",
    },
    {
      id: "c",
      text: "Here\u2019s to the crazy ones. The misfits. The rebels. The troublemakers. The round pegs in the square holes.",
      category: "advertising",
      axis_position: 1.2,
      highlighted_words: ["crazy ones", "misfits", "rebels", "troublemakers"],
      reveal:
        "The copy positions nonconformity as a purchasable feature. The rebels referenced were not selling anything. This text borrows their dissent to sell yours. The grammar is implicit second person: you are the rebel. The company is not.",
    },
    {
      id: "d",
      text: "One must imagine Sisyphus happy.",
      category: "literary",
      axis_position: 2,
      highlighted_words: ["imagine", "happy"],
      reveal:
        "Freedom here is not political but ontological \u2014 the capacity to assign meaning to a condition no external authority can improve. The sentence contains no imperative for collective action. It locates rebellion entirely within the individual\u2019s relationship to their own fate.",
    },
  ],
  correct_order: ["a", "b", "c", "d"],
  tomorrow_axis: "OPTIMISM \u2194 ABSURDISM",
};
