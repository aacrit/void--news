/* ---------------------------------------------------------------------------
   The per-issue share card.

   Every issue used to share the site-wide OG image, and rev 71 improved that
   to the issue's COVER PHOTOGRAPH. Both are worse than they look: the site
   card says nothing about which issue is being shared, and the cover photo is
   a hotlinked Wikimedia URL that a third-party scraper may 404 or rate-limit,
   carrying no headline even when it loads.

   The composition itself lives in `app/lib/ogCard.tsx`, the one composer every
   Void card is drawn by. What stays here is the only part that is about a
   weekly ISSUE: which line is the headline, and how the issue names itself.

   Weekly is a SECTION of Void News, so the card carries the VOID NEWS lockup
   and a Weekly nameplate in the section's red. It used to set a letter-spaced
   "VOID WEEKLY" wordmark, which named a publication that does not exist.
   --------------------------------------------------------------------------- */

import type { WeeklyDigestData } from "./types";
import { formatArchiveRange, issueLabel } from "./format";
import { voidCard, size, contentType, ACCENT_WEEKLY } from "../lib/ogCard";

export { size, contentType };

const TAGLINE = "Every source, every story, scored for bias.";

export function issueCard(issue: WeeklyDigestData) {
  return voidCard({
    section: "Weekly",
    accent: ACCENT_WEEKLY,
    title: issue.cover_headline || issue.cover_text?.[0]?.headline || "",
    meta: [
      issueLabel(issue.issue_number),
      formatArchiveRange(issue.week_start, issue.week_end),
    ],
    tagline: TAGLINE,
  });
}
