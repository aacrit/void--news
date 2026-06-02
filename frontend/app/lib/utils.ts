/**
 * Base path for the deployed site — must match next.config.ts basePath.
 *
 * Defaults to /void--news (GitHub Pages project-repo path). Cloudflare
 * Pages and custom-domain deployments set NEXT_PUBLIC_BASE_PATH="" in the
 * build env, which Next.js inlines at compile time so the browser bundle
 * sees the empty string at runtime.
 */
export const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "/void--news";

/**
 * 2026-06-02 single-feed — Morning/Evening shorthand from UTC.
 * Edition-specific timezone branches removed.
 */
export function getEditionTimeOfDay(): "Morning" | "Evening" {
  return new Date().getUTCHours() < 12 ? "Morning" : "Evening";
}

/**
 * Compact UTC dateline timestamp ("14:05 UTC"). Single-feed mode.
 */
export function getEditionTimestamp(): string {
  const now = new Date();
  const h = String(now.getUTCHours()).padStart(2, "0");
  const m = String(now.getUTCMinutes()).padStart(2, "0");
  return `${h}:${m} UTC`;
}

/**
 * Relative time formatting — "5m ago", "2h ago", "1d ago"
 */
export function timeAgo(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

/**
 * Derive "Why This Story" ranking explanation from available story data.
 * Returns the top 2-3 signals that drove this story's ranking.
 */
export function whyThisStory(opts: {
  sourceCount: number;
  coverageVelocity: number;
  divergenceScore: number;
  leanSpread?: number;
  headlineRank: number;
}): string[] {
  const reasons: { text: string; weight: number }[] = [];

  if (opts.sourceCount >= 8) {
    reasons.push({ text: `${opts.sourceCount} sources`, weight: 90 });
  } else if (opts.sourceCount >= 5) {
    reasons.push({ text: `${opts.sourceCount} sources`, weight: 70 });
  } else if (opts.sourceCount >= 3) {
    reasons.push({ text: `${opts.sourceCount} sources`, weight: 40 });
  }

  if (opts.coverageVelocity >= 5) {
    reasons.push({ text: "Rapidly developing", weight: 85 });
  } else if (opts.coverageVelocity >= 3) {
    reasons.push({ text: "Gaining coverage", weight: 55 });
  }

  if (opts.divergenceScore >= 60) {
    reasons.push({ text: "High source disagreement", weight: 75 });
  } else if (opts.divergenceScore >= 30) {
    reasons.push({ text: "Sources differ on framing", weight: 45 });
  }

  if (opts.leanSpread != null && opts.leanSpread >= 20) {
    reasons.push({ text: "Cross-spectrum coverage", weight: 65 });
  }

  // Sort by weight descending, take top 3
  reasons.sort((a, b) => b.weight - a.weight);
  return reasons.slice(0, 3).map((r) => r.text);
}
