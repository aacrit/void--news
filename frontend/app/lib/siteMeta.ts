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

/** Production origin. Canonicals are absolute against this host. */
export const SITE_URL = "https://news.voidvision.org";

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
    },
    twitter: {
      title: opts.title,
      description: opts.description,
    },
  };
}
