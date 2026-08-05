/* ---------------------------------------------------------------------------
   summaryHygiene — belt-and-suspenders guard against raw scraped excerpts.

   The pipeline's step-8d.6 summary floor guarantees every displayed top-50
   cluster gets a clean, on-topic summary (LLM or deterministic rule-based).
   This is the last line of defence: if a summary still slips through looking
   like a raw scraped excerpt (CMS artifacts, a photo/byline credit, a trailing
   "- outlet.com" suffix, or run-together words from a bad extraction), we drop
   it so the card falls back to its neutral "N sources reporting" pending line
   instead of rendering the garbage.
   --------------------------------------------------------------------------- */

// Obvious CMS / newsroom-scaffolding + syndication artifacts that never belong
// in an editorial summary. Kept conservative to avoid false positives on real
// prose.
const RAW_EXCERPT_PATTERNS: RegExp[] = [
  /\bWhy it matters:/i,
  /\bthe big picture:/i,
  /\bgo deeper:/i,
  /\bread more:/i,
  /\bkeep reading:/i,
  /\bsign up for/i,
  /\bsubscribe to/i,
  /\badvertisement\b/i,
  /\bphoto(?:graph)?:\s/i,
  /\bimage caption\b/i,
  /\bgetty images\b/i,
  // Photo/byline credit like "(John Smith/AFP)" or "(AP Photo/...)".
  /\([^)]*\/\s*(?:AFP|AP|Reuters|Getty|EPA|Bloomberg|Anadolu|Xinhua|AAP)\b/i,
  // Trailing outlet-domain suffix like " - reuters.com" / " — bbc.co.uk".
  /[\s\-–—]+[a-z0-9-]+\.(?:com|org|net|gov|co\.[a-z]{2})\s*$/i,
];

/** True when a non-empty summary looks like a raw scraped excerpt, not prose. */
export function isRawExcerpt(summary: string): boolean {
  const s = (summary ?? "").trim();
  if (!s) return false;

  for (const re of RAW_EXCERPT_PATTERNS) {
    if (re.test(s)) return true;
  }

  // Run-together words from a broken extraction ("reportingThe minister said").
  // Require several lowercase→uppercase transitions to avoid flagging the rare
  // legitimate camel token (iPhone, eBay, McDonald's).
  const camelBoundaries = (s.match(/[a-z][A-Z]/g) || []).length;
  if (camelBoundaries >= 3) return true;

  // A single absurdly long token is almost always concatenated words / a URL
  // slug that survived extraction.
  if (/\S{40,}/.test(s)) return true;

  return false;
}

/**
 * Return a display-safe summary. Empty or raw-excerpt input yields "" so the
 * card renders its neutral "N sources reporting" pending line (a clean,
 * headline-independent fallback) rather than the raw text. Clean prose passes
 * through untouched.
 */
export function cleanFeedSummary(summary: string, _title?: string): string {
  const s = (summary ?? "").trim();
  if (!s) return "";
  if (isRawExcerpt(s)) return "";
  return summary;
}
