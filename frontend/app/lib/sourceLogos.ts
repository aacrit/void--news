import manifest from "./sourceLogos.json";
import { BASE_PATH } from "./utils";

/* ---------------------------------------------------------------------------
   sourceLogoUrl — first-party outlet favicon path, or "" when we don't have one.

   Void News self-hosts small outlet favicons under /public/logos (fetched once
   at build time by scripts/fetch_source_favicons.py, committed as static assets)
   so the site never hotlinks a third-party favicon service at read time (which
   would leak the reader's IP and which outlet they are viewing). Showing a mark
   to identify its outlet is nominative use.

   The manifest maps a normalized source name to its icon slug. A miss returns
   "" so the caller falls back to the lean-colored letter monogram.
   --------------------------------------------------------------------------- */

const MAP = manifest as Record<string, string>;

export function sourceLogoUrl(name: string | undefined | null): string {
  if (!name) return "";
  const slug = MAP[name.trim().toLowerCase()];
  return slug ? `${BASE_PATH}/logos/${slug}.png` : "";
}
