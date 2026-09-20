/* Per-issue metadata, shared by /weekly and /weekly/[week].
   Server-only: imported by the two page modules' generateMetadata. */

import type { Metadata } from "next";
import { OG_IMAGE, OG_IMAGE_URL, SITE_URL, pageMetadata } from "../lib/siteMeta";
import type { WeeklyDigestData } from "./types";
import { clip, essayParagraphs, formatWeekRange, weeklyDisplayNo } from "./format";

/**
 * Build the share card for one issue.
 *
 * /weekly used to carry the site-wide metadata only, so every issue ever
 * published shared one title, one description and one OG card. An issue is a
 * distinct publication with its own cover story; it deserves its own.
 *
 * The cover art is the OG image when the issue has one. It is always from a
 * freely licensed source (Wikimedia Commons, or Unsplash/Pexels when a key is
 * configured) — a publisher's og:image is never used, because it is usually a
 * wire photograph and grants nothing to whoever scrapes it.
 */
export function issueMetadata(issue: WeeklyDigestData, path: string): Metadata {
  const no = weeklyDisplayNo(issue.issue_number);
  const range = formatWeekRange(issue.week_start, issue.week_end);
  const headline = issue.cover_headline || issue.cover_text?.[0]?.headline || "";
  const lede = essayParagraphs(issue.cover_text?.[0]?.text || "")[0] || "";

  const title = headline
    ? `Issue #${no}: ${headline} — Void Weekly`
    : `Issue #${no} — Void Weekly`;
  const description = lede
    ? clip(lede, 160)
    : `Void Weekly, issue #${no}, covering ${range}.`;

  const base = pageMetadata({ title, description, path });
  const cover = issue.cover_image_url;
  if (!cover) return base;

  const image = { url: cover, alt: headline || `Void Weekly issue ${no}` };
  return {
    ...base,
    openGraph: { ...base.openGraph, images: [image, OG_IMAGE] },
    twitter: { ...base.twitter, images: [cover, OG_IMAGE_URL] },
  };
}

export { SITE_URL };
