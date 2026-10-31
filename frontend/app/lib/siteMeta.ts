/* ---------------------------------------------------------------------------
   siteMeta — per-route metadata helper (static export, build-time only).

   Produces a Next.js Metadata object with a DISTINCT title + description and
   an absolute canonical URL for each route. openGraph/twitter images, card
   type, icons, and manifest are inherited from the root layout and merged, so
   only per-route title/description/url are set here.

   Canonical URLs are absolute against the production origin and carry the
   trailing slash (next.config trailingSlash:true) so they match the emitted
   static paths exactly.
   --------------------------------------------------------------------------- */

import type { Metadata } from "next";
import { BASE_PATH } from "./utils";

/** Production origin. Canonicals are absolute against this host. */
export const SITE_URL = "https://news.voidvision.org";

/** Site-wide brand share card. Our own artwork (og-image.png) — no publisher
 *  content, zero copyright exposure. Resolved to an absolute URL by the root
 *  layout's `metadataBase`. Rendered from the one card composer by
 *  `brand/ci/render_og.mjs`; it is never hand-edited. Routes that have a card
 *  of their own (History, Weekly, the latest edition's stories) omit it so the
 *  opengraph-image file convention wins; every other route emits this. */
export const OG_IMAGE_URL = `${BASE_PATH}/og-image.png`;
export const OG_IMAGE = {
  url: OG_IMAGE_URL,
  width: 1200,
  height: 630,
  alt: "Void News. See through the void.",
  type: "image/png",
} as const;

/** One title grammar for the whole site. A section landing or a top-level
 *  page is "Page | Void News"; a leaf inside a section is
 *  "Page | Section | Void News". The front page alone carries the tagline. */
export function sectionTitle(page: string, section?: string): string {
  return section ? `${page} | ${section} | Void News` : `${page} | Void News`;
}

export function pageMetadata(opts: {
  title: string;
  description: string;
  /** Route path WITH leading and trailing slash, e.g. "/sources/". Home = "/". */
  path: string;
}): Metadata {
  const url = `${SITE_URL}${opts.path}`;
  return {
    title: opts.title,
    description: opts.description,
    alternates: { canonical: url },
    openGraph: {
      title: opts.title,
      description: opts.description,
      url,
      type: "website",
      siteName: "Void News",
      // Re-declared per route: Next does NOT inherit openGraph.images from the
      // root layout once a route sets its own openGraph object.
      images: [OG_IMAGE],
    },
    twitter: {
      card: "summary_large_image",
      title: opts.title,
      description: opts.description,
      images: [OG_IMAGE_URL],
    },
  };
}
