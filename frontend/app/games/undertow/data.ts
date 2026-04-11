/* ==========================================================================
   UNDERTOW — Daily Cultural Subtext Puzzle Data
   Static mock data for MVP. Pipeline will generate JSON later.
   ========================================================================== */

export type Direction = "left" | "right" | "neutral";

export interface RevealLine {
  text: string; // 2-3 sentences of Orwellian commentary
}

export interface Artifact {
  id: string;
  text: string; // The artifact text — NO names, NO dates
  category:
    | "advertising"
    | "speech"
    | "corporate"
    | "literary"
    | "lyric"
    | "logline";
  axis_position: number; // -2 to +2 (negative = left pole, positive = right pole)
  reveal: RevealLine;
  highlighted_words: string[]; // specific words to highlight during reveal
}

export interface DailyChallenge {
  id: number;
  date: string;
  axis: {
    label: string; // e.g. "CONTROL <-> FREEDOM"
    left_pole: string; // e.g. "CONTROL"
    right_pole: string; // e.g. "FREEDOM"
    description: string; // one sentence explaining today's axis
  };
  artifacts: Artifact[];
  correct_order: string[]; // ids ordered left pole -> right pole
  tomorrow_axis?: string; // teaser for next day
}

export const DAILY_UNDERTOW: DailyChallenge = {
  id: 1,
  date: "2026-04-10",
  axis: {
    label: "CONTROL \u2194 FREEDOM",
    left_pole: "CONTROL",
    right_pole: "FREEDOM",
    description:
      "Where does this text locate the source of order \u2014 in structure, or in the individual?",
  },
  artifacts: [
    {
      id: "a",
      text: "The harvest belongs to all. Our fields, our future, our strength \u2014 together.",
      category: "speech",
      axis_position: -2,
      reveal: {
        text: "No singular pronoun appears. The grammar does the work before the argument does. \u2018Our\u2019 repeated three times confirms what \u2018together\u2019 makes explicit: the individual is grammatically absent before they are politically so.",
      },
      highlighted_words: ["all", "Our", "our", "our", "together"],
    },
    {
      id: "b",
      text: "We exist to connect every person on earth and give everyone the power to share anything with anyone.",
      category: "corporate",
      axis_position: -0.8,
      reveal: {
        text: "The promise is universal freedom. The mechanism is a single platform owned by one company. The text does not register this tension. \u2018Everyone\u2019 is the subject; the infrastructure is not mentioned.",
      },
      highlighted_words: [
        "connect every person",
        "everyone",
        "anything",
        "anyone",
      ],
    },
    {
      id: "c",
      text: "Here\u2019s to the crazy ones. The misfits. The rebels. The troublemakers. The round pegs in square holes.",
      category: "advertising",
      axis_position: 1.2,
      reveal: {
        text: "The copy positions nonconformity as a purchasable feature. The rebels named in the full version were not selling anything. This text borrows their dissent to sell yours. The grammar is second person: you are the rebel. The company is not.",
      },
      highlighted_words: ["crazy ones", "misfits", "rebels", "troublemakers"],
    },
    {
      id: "d",
      text: "One must imagine Sisyphus happy.",
      category: "literary",
      axis_position: 2,
      reveal: {
        text: "Freedom here is not political but ontological \u2014 the capacity to assign meaning to a condition no external authority can improve. The sentence contains no imperative for collective action, no promise of resolution. It locates rebellion entirely within the individual\u2019s relationship to their own fate.",
      },
      highlighted_words: ["imagine", "happy"],
    },
  ],
  correct_order: ["a", "b", "c", "d"],
  tomorrow_axis: "OPTIMISM \u2194 ABSURDISM",
};
