export interface BiasScores {
  /** 0 = far left, 50 = center, 100 = far right */
  politicalLean: number;
  /** 0 = measured, 100 = inflammatory */
  sensationalism: number;
  /** 0 = hard reporting, 50 = analysis, 100 = opinion */
  opinionFact: number;
  /** 0 = unsourced, 100 = well-sourced */
  factualRigor: number;
  /** 0 = neutral framing, 100 = heavy framing */
  framing: number;
}

export interface Source {
  name: string;
  count: number;
}

export interface StorySource {
  name: string;
  url: string;
  tier: "us_major" | "international" | "independent";
  biasScores: BiasScores;
}

export interface DeepDiveData {
  consensus: string[];
  divergence: string[];
  sources: StorySource[];
}

export interface Story {
  id: string;
  title: string;
  summary: string;
  source: Source;
  category: Category;
  publishedAt: string;
  biasScores: BiasScores;
  section: "world" | "us";
  importance: number;
  deepDive?: DeepDiveData;
}

export type Category =
  | "Politics"
  | "Economy"
  | "Tech"
  | "Health"
  | "Environment"
  | "Conflict"
  | "Science"
  | "Society"
  | "Energy"
  | "Diplomacy";

export type Section = "world" | "us";
