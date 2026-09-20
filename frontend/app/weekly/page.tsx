/* ---------------------------------------------------------------------------
   /weekly — the current issue, prerendered.

   This was a six-line client shell that fetched weekly.json in a useEffect, so
   the served HTML carried no issue content at all and every issue shared one OG
   card. It is a server component now, reading the issue at build the way
   app/page.tsx has read the feed since rev 62.
   --------------------------------------------------------------------------- */

import type { Metadata } from "next";
import { getLatestWeeklyIssue, getWeeklyArchiveIndex } from "../lib/weeklyIssues";
import { issueMetadata } from "./issueMeta";
import WeeklyIssue from "./WeeklyIssue";

export const dynamic = "force-static";

export function generateMetadata(): Metadata {
  return issueMetadata(getLatestWeeklyIssue(), "/weekly/");
}

export default function WeeklyPage() {
  return (
    <WeeklyIssue
      issue={getLatestWeeklyIssue()}
      archive={getWeeklyArchiveIndex()}
    />
  );
}
