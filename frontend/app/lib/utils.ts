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
 * Morning/Evening shorthand from the reader's LOCAL time.
 * Only rendered client-side (after mount) so the local clock is the reader's.
 */
export function getEditionTimeOfDay(): "Morning" | "Evening" {
  return new Date().getHours() < 12 ? "Morning" : "Evening";
}

/**
 * Compact dateline timestamp for the masthead: the edition's BUILD time
 * (the pipeline's completed_at), rendered in the reader's LOCAL zone and
 * ROUNDED TO THE NEAREST HOUR, with a short zone label (e.g. "13:00 CDT").
 * Rounding to the hour signals a once-a-day edition rather than a live clock.
 * Pass the pipeline completed_at ISO string; with no (or an invalid) argument
 * it falls back to the current hour. Client-only (local zone), so callers
 * render it after mount.
 */
export function getEditionTimestamp(builtAtISO?: string | null): string {
  const src = builtAtISO ? new Date(builtAtISO) : new Date();
  if (isNaN(src.getTime())) return "";
  // Round to the nearest hour in local time. >= 30 min rounds up; setHours
  // overflow rolls the date correctly (23:45 -> next day 00:00).
  const d = new Date(src);
  d.setMinutes(0, 0, 0);
  if (src.getMinutes() >= 30) d.setHours(d.getHours() + 1);
  const h = String(d.getHours()).padStart(2, "0");
  // Local timezone short label ("CDT", "GMT+2", ...); degrade to bare time.
  let tz = "";
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZoneName: "short",
    }).formatToParts(d);
    tz = parts.find((p) => p.type === "timeZoneName")?.value ?? "";
  } catch {
    /* Intl unavailable — show time without a zone label. */
  }
  return tz ? `${h}:00 ${tz}` : `${h}:00`;
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
