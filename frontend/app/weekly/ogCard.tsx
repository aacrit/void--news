/* ---------------------------------------------------------------------------
   The per-issue share card.

   Every issue used to share the site-wide OG image, and rev 71 improved that
   to the issue's COVER PHOTOGRAPH. Both are worse than they look: the site
   card says nothing about which issue is being shared, and the cover photo is
   a hotlinked Wikimedia URL that a third-party scraper may 404 or rate-limit,
   carrying no headline even when it loads.

   The composition itself now lives in `app/lib/ogCard.tsx`, shared with
   History. What stays here is the only part that is about a weekly ISSUE:
   which line is the headline, and how the issue names itself.
   --------------------------------------------------------------------------- */

import type { WeeklyDigestData } from "./types";
import { formatArchiveRange, issueLabel } from "./format";
import { sectionCard, size, contentType, ACCENT_WEEKLY } from "../lib/ogCard";

export { size, contentType };

const TAGLINE = "Every source, every story, scored for bias.";

export function issueCard(issue: WeeklyDigestData) {
  const week = formatArchiveRange(issue.week_start, issue.week_end);
  return sectionCard({
    wordmark: "VOID WEEKLY",
    kicker: `${issueLabel(issue.issue_number)}  ·  ${week}`,
    headline: issue.cover_headline || issue.cover_text?.[0]?.headline || "",
    tagline: TAGLINE,
    accent: ACCENT_WEEKLY,
  });
}
