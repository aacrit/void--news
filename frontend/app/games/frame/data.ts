/* ==========================================================================
   THE FRAME — Daily Challenge Data
   Static mock data for MVP. Pipeline will generate JSON later.
   ========================================================================== */

export interface BiasTrigger {
  word: string;
  direction: "left" | "right";
}

export interface FrameHeadline {
  id: string;
  text: string;
  lean_score: number;
  lean_label: "FAR LEFT" | "LEFT" | "CENTER-LEFT" | "CENTER" | "CENTER-RIGHT" | "RIGHT" | "FAR RIGHT";
  outlet: string;
  bias_triggers: BiasTrigger[];
}

export interface FrameChallenge {
  id: number;
  date: string;
  /** Deliberately vague event context — no current event knowledge needed */
  topic: string;
  headlines: FrameHeadline[];
  /** Correct left-to-right ordering by headline id */
  correct_order: string[];
}

export const DAILY_FRAME: FrameChallenge = {
  id: 1,
  date: "2026-04-10",
  topic: "A nation\u2019s central bank raised interest rates to combat inflation.",
  headlines: [
    {
      id: "a",
      text: "Working Families Face Mortgage Crisis as Central Bank Hikes Rates Again",
      lean_score: -2.8,
      lean_label: "LEFT",
      outlet: "The Guardian",
      bias_triggers: [
        { word: "Working Families", direction: "left" },
        { word: "Crisis", direction: "left" },
        { word: "Hikes", direction: "left" },
      ],
    },
    {
      id: "b",
      text: "Bank Battles Inflation With Rate Increase; Borrowers to Feel Pressure",
      lean_score: -0.9,
      lean_label: "CENTER-LEFT",
      outlet: "BBC News",
      bias_triggers: [
        { word: "Battles", direction: "left" },
        { word: "Feel Pressure", direction: "left" },
      ],
    },
    {
      id: "c",
      text: "Central Bank Raises Rates 0.5 Points in Inflation Fight",
      lean_score: 0.2,
      lean_label: "CENTER",
      outlet: "Reuters",
      bias_triggers: [],
    },
    {
      id: "d",
      text: "Bold Rate Rise Signals Central Bank\u2019s Commitment to Price Stability",
      lean_score: 2.4,
      lean_label: "RIGHT",
      outlet: "The Wall Street Journal",
      bias_triggers: [
        { word: "Bold", direction: "right" },
        { word: "Commitment", direction: "right" },
        { word: "Price Stability", direction: "right" },
      ],
    },
  ],
  // Correct order left to right: a (LEFT -2.8), b (CENTER-LEFT -0.9), c (CENTER 0.2), d (RIGHT 2.4)
  correct_order: ["a", "b", "c", "d"],
};

/** Lean label to short abbreviation for the spectrum bar */
export const LEAN_ABBREVIATIONS: Record<string, string> = {
  "FAR LEFT": "FL",
  "LEFT": "L",
  "CENTER-LEFT": "CL",
  "CENTER": "C",
  "CENTER-RIGHT": "CR",
  "RIGHT": "R",
  "FAR RIGHT": "FR",
};

/** Map lean label to CSS custom property name */
export function leanToColor(label: string): string {
  const map: Record<string, string> = {
    "FAR LEFT": "var(--bias-far-left)",
    "LEFT": "var(--bias-left)",
    "CENTER-LEFT": "var(--bias-center-left)",
    "CENTER": "var(--bias-center)",
    "CENTER-RIGHT": "var(--bias-center-right)",
    "RIGHT": "var(--bias-right)",
    "FAR RIGHT": "var(--bias-far-right)",
  };
  return map[label] ?? "var(--fg-tertiary)";
}
