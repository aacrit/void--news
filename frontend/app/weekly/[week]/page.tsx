/* ---------------------------------------------------------------------------
   /weekly/<week_start>/ — one back issue, prerendered.

   The slug is the week (2026-09-14), not the issue number. The week is the
   natural key — weekly_digests is UNIQUE(edition, week_start) — it sorts, it
   is self-documenting, and it survives renumbering: the reader-facing issue
   number subtracts WEEKLY_LAUNCH_ISSUE, so if that constant ever moves, every
   issue-number URL 404s.

   This replaces /weekly/[edition], which is deleted. Next cannot have two
   differently-named dynamic params at the same segment, so that was forced
   rather than chosen — and [edition] only ever emitted a /weekly/world/
   duplicate of /weekly, which its own comment admitted existed to satisfy
   Turbopack.
   --------------------------------------------------------------------------- */

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getPreviousWeeklyIssue,
  getWeeklyArchiveIndex,
  getWeeklyCorrections,
  getWeeklyIssueByWeek,
  getWeeklyIssues,
} from "../../lib/weeklyIssues";
import { issueMetadata } from "../issueMeta";
import WeeklyIssue from "../WeeklyIssue";

// force-static lets an empty archive export zero pages instead of Next treating
// the dynamic segment as missing params under output: export.
export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return getWeeklyIssues().map((i) => ({ week: i.week_start }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ week: string }> }
): Promise<Metadata> {
  const { week } = await params;
  const issue = getWeeklyIssueByWeek(week);
  if (!issue) return {};
  return issueMetadata(issue, `/weekly/${week}/`);
}

export default async function WeeklyArchivedIssuePage(
  { params }: { params: Promise<{ week: string }> }
) {
  const { week } = await params;
  const issue = getWeeklyIssueByWeek(week);
  if (!issue) notFound();
  return (
    <WeeklyIssue
      issue={issue}
      archive={getWeeklyArchiveIndex()}
      previous={getPreviousWeeklyIssue(issue.week_start)}
      corrections={getWeeklyCorrections(issue.week_start)}
    />
  );
}
