/* ---------------------------------------------------------------------------
   serverBrief — build-time daily-brief fetch (static export).

   The Brief (TL;DR + Opinion) is editorial TEXT, not audio. Before this it was
   fetched client-side in AudioProvider, so the served HTML shipped "Loading
   today's brief…" above the fold. This reads the latest daily brief ONCE at
   `next build` (inside the async root layout) so the prerendered HTML carries
   the real headline + text, matching how the feed is prerendered.

   Module-level memoized promise: the root layout is rendered per route during
   static export, but the brief is fetched exactly once per build process and
   shared across all of them (no per-page query fan-out).

   Never throws: an unavailable brief resolves to null and the UI degrades to
   the existing client fetch. The front-page feed remains the sole fail-loud
   build guard.
   --------------------------------------------------------------------------- */

import { readFileSync } from "fs";
import { join } from "path";
import type { DailyBriefData } from "./types";

let _briefPromise: Promise<DailyBriefData | null> | null = null;

export function getInitialBrief(): Promise<DailyBriefData | null> {
  if (_briefPromise) return _briefPromise;
  _briefPromise = (async () => {
    // Static export (2026-08-30 Cloudflare migration): the brief is emitted as
    // public/data/brief.json by the pipeline (was a build-time Supabase read).
    // Read it directly from disk at build. Unavailable -> null (UI degrades to
    // the client fetch of the same file); never throws.
    try {
      const raw = readFileSync(
        join(process.cwd(), "public", "data", "brief.json"),
        "utf-8",
      );
      const brief = JSON.parse(raw);
      return (brief ?? null) as DailyBriefData | null;
    } catch (e) {
      console.warn(`[serverBrief] daily brief unavailable at build time: ${e}`);
      return null;
    }
  })();
  return _briefPromise;
}
