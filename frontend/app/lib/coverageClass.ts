import type { Story } from "./types";

export interface CoverageVerdict {
  label: string;
  tone: "single" | "consensus" | "split" | "skewed" | "divergent" | "neutral";
}

export function classifyCoverage(story: Story): CoverageVerdict | null {
  const count = story.source.count ?? 0;
  if (count < 1) return null;

  const spread = story.sigilData?.biasSpread?.leanSpread ?? 0;
  const range = story.sigilData?.biasSpread?.leanRange ?? 0;
  const flag = story.sigilData?.divergenceFlag ?? null;
  const avgLean = story.sigilData?.politicalLean ?? 50;

  const noun = count === 1 ? "source" : "sources";
  const head = `${count} ${noun}`;

  if (count === 1) {
    return { label: `${head} · single report`, tone: "single" };
  }

  if (flag === "divergent" || range >= 50) {
    return { label: `${head} · left-right split`, tone: "split" };
  }

  if (flag === "consensus" || (spread <= 8 && range <= 20)) {
    return { label: `${head} · in agreement`, tone: "consensus" };
  }

  if (spread >= 18) {
    return { label: `${head} · mixed views`, tone: "divergent" };
  }

  if (avgLean <= 35) {
    return { label: `${head} · left-leaning coverage`, tone: "skewed" };
  }
  if (avgLean >= 65) {
    return { label: `${head} · right-leaning coverage`, tone: "skewed" };
  }

  return { label: `${head} · center-weighted`, tone: "neutral" };
}
