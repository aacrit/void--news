/* ---------------------------------------------------------------------------
   /weekly/archive/ — every issue, in one place.

   /weekly is THE CURRENT ISSUE, which is the right thing for it to be: a
   magazine's front door is this week's cover, not a filing cabinet. But that
   left the back catalogue reachable only by scrolling to the foot of an issue,
   with no stable URL of its own to link, share, or point a podcast feed at.

   Prerendered like the issues themselves, from the same memoized read.
   --------------------------------------------------------------------------- */

import type { Metadata } from "next";
import { getWeeklyIssues } from "../../lib/weeklyIssues";
import { pageMetadata } from "../../lib/siteMeta";
import IssueIndex from "./IssueIndex";

export const dynamic = "force-static";

export function generateMetadata(): Metadata {
  const n = getWeeklyIssues().length;
  return pageMetadata({
    title: "Every issue · Weekly · Void News",
    description:
      n > 0
        ? `All ${n} issues of Weekly, the Sunday magazine from Void News. ` +
          "Every issue is free, with no advertising and no paywall."
        : "Weekly, the Sunday magazine from Void News.",
    path: "/weekly/archive/",
  });
}

export default function WeeklyArchivePage() {
  return <IssueIndex issues={getWeeklyIssues()} />;
}
