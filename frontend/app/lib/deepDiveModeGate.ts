/**
 * Deep Dive mode gate — single source of truth for how a story expands when
 * a feed card is clicked.
 *
 *   "card"   →  the legacy DeepDive modal slides in over the feed (default).
 *   "inline" →  the Deep Dive content renders in place inside the feed as a
 *               full-width block, pushing later cards down (Cinematic Inline
 *               Deep Dive, stage 1: static).
 *
 * Set the default via the NEXT_PUBLIC_DEEP_DIVE_MODE env var (inlined by
 * Next.js at build time). For quick dev A/B, a `?dd=inline` or `?dd=card`
 * query param overrides the env value on the client.
 *
 * Mirrors the audioGate.ts kill-switch idiom. SSR-safe: the query-param
 * branch only runs when `window` exists, so the first server/client paint
 * always resolves to the env value (default "card") and never mismatches.
 */
export type DeepDiveMode = "card" | "inline";

/** Compile-time default from the deploy env. Falls back to "card". */
export const DEEP_DIVE_MODE_ENV: DeepDiveMode =
  (process.env.NEXT_PUBLIC_DEEP_DIVE_MODE ?? "card") === "inline"
    ? "inline"
    : "card";

/**
 * Resolve the active Deep Dive mode.
 *
 * On the client a `?dd=inline` / `?dd=card` query param wins (dev A/B);
 * otherwise the env default is returned. On the server (or when `window`
 * is absent) this returns the env default, so SSR and the first client
 * paint agree. Read it inside a useEffect to pick up the query override
 * without risking a hydration mismatch.
 */
export function getDeepDiveMode(): DeepDiveMode {
  if (typeof window !== "undefined") {
    try {
      const param = new URLSearchParams(window.location.search).get("dd");
      if (param === "inline") return "inline";
      if (param === "card") return "card";
    } catch {
      /* malformed search string — fall through to env default */
    }
  }
  return DEEP_DIVE_MODE_ENV;
}
