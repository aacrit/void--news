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
 * Base URL of the void-api Cloudflare Worker (D1-backed ship board / feedback
 * write path). Set NEXT_PUBLIC_API_BASE in the build env to the deployed Worker
 * URL (e.g. https://void-api.<subdomain>.workers.dev or https://api.voidvision.org).
 * When empty, the ship board degrades gracefully to read-empty / write-noop.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

/**
 * Morning/Evening shorthand from the reader's LOCAL time.
 * Only rendered client-side (after mount) so the local clock is the reader's.
 */
export function getEditionTimeOfDay(): "Morning" | "Evening" {
  return new Date().getHours() < 12 ? "Morning" : "Evening";
}

const EDITION_MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/**
 * Compact dateline timestamp for the masthead: the edition's BUILD time
 * (the pipeline's completed_at), rendered in the VIEWER'S LOCAL zone and
 * ROUNDED TO THE NEAREST HOUR, with a short zone label (e.g. "4:00 PM CDT").
 * Rounding to the hour signals a once-a-day edition rather than a live clock;
 * the local zone makes the "as of" time relevant to each reader.
 *
 * HYDRATION: local time depends on the viewer's machine, so this string can
 * NEVER be baked into the prerendered HTML (the build box's zone is not the
 * reader's). Every surface calls this ONLY after mount (a `mounted` gate), so
 * the server HTML and the first client render agree (empty), then the real
 * local time paints in. Do not call it during the initial React render.
 *
 * The raw ISO input is the single source of truth; every surface (front-page
 * masthead, Deep Dive masthead, Menu drawer, /onair, /sources) formats the
 * SAME pipeline completed_at through THIS one helper so they never diverge.
 * With no (or an invalid) argument it falls back to the current hour.
 */
export function getEditionTimestampLocal(builtAtISO?: string | null): string {
  const src = builtAtISO ? new Date(builtAtISO) : new Date();
  if (isNaN(src.getTime())) return "";
  // Round to the nearest hour in the viewer's LOCAL zone. >= 30 min rounds up.
  const d = new Date(src.getTime());
  if (d.getMinutes() >= 30) d.setHours(d.getHours() + 1);
  d.setMinutes(0, 0, 0);
  // e.g. "4:00 PM CDT" (locale + zone come from the viewer's runtime).
  return d.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

/**
 * Compact UTC dateline for the masthead (e.g. "Aug 9, 2026"), matching the
 * prerendered front page (serverFeed.formatDatelineUTC). Deterministic for a
 * given ISO input, so it is safe on both server and client and never shifts
 * with the reader's timezone. Falls back to "now" when the arg is absent.
 */
export function getEditionDatelineUTC(builtAtISO?: string | null): string {
  const d = builtAtISO ? new Date(builtAtISO) : new Date();
  if (isNaN(d.getTime())) return "";
  return `${EDITION_MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
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
