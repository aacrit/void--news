import { getLatestWeeklyIssue } from "../lib/weeklyIssues";
import { issueCard, size, contentType } from "./ogCard";

// Required under `output: export`: without it the image is treated as a
// dynamic route handler and the build refuses to collect it.
export const dynamic = "force-static";
export { size, contentType };
export const alt = "Void Weekly, the current issue";

export default function Image() {
  return issueCard(getLatestWeeklyIssue());
}
