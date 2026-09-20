import { getWeeklyIssueByWeek, getWeeklyIssues } from "../../lib/weeklyIssues";
import { issueCard, size, contentType } from "../ogCard";

export const dynamic = "force-static";
export const dynamicParams = false;
export { size, contentType };
export const alt = "Weekly, one issue, from Void News";

export function generateStaticParams() {
  return getWeeklyIssues().map((i) => ({ week: i.week_start }));
}

export default async function Image({ params }: { params: Promise<{ week: string }> }) {
  const { week } = await params;
  const issue = getWeeklyIssueByWeek(week);
  // generateStaticParams only emits real weeks, so this is a type guard rather
  // than a reachable branch.
  return issueCard(issue ?? getWeeklyIssues()[0]);
}
