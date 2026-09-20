/* ---------------------------------------------------------------------------
   History metadata, and the reason it did not exist.

   `app/history/page.tsx` was a Client Component. A client component cannot
   export `metadata` or `generateMetadata` at all, so the landing silently
   inherited the root layout: every share of /history/ showed the title "Void
   News. See through the void." and the site-wide card, and so did all 78 event
   pages' images. The event pages at least had titles, because
   `[slug]/page.tsx` is a server component.

   The fix is the pattern `/sources` and `/about` already use: a thin server
   page that owns the metadata and renders the client tree beneath it.

   `imagesFromFile` exists for the same reason `weekly/issueMeta.ts` deletes
   them: Next uses an `opengraph-image.tsx` file ONLY when the route does not
   declare `openGraph.images` itself, and `pageMetadata` declares the site-wide
   card for every route. Leaving that in place is exactly how a section ends up
   sharing a card that says nothing about it.
   --------------------------------------------------------------------------- */

import type { Metadata } from "next";
import { pageMetadata, SITE_URL } from "../lib/siteMeta";

/** `pageMetadata`, with the site-wide card removed so the file convention wins. */
export function yieldToCardFile(base: Metadata): Metadata {
  const og = { ...base.openGraph } as Record<string, unknown>;
  delete og.images;
  const tw = { ...base.twitter } as Record<string, unknown>;
  delete tw.images;
  return { ...base, openGraph: og, twitter: tw } as Metadata;
}

export const HISTORY_TAGLINE = "One event. Every side. Decide for yourself.";

export function landingMetadata(eventCount: number): Metadata {
  const n = eventCount || 78;
  return yieldToCardFile(
    pageMetadata({
      title: "History | Void News",
      // Says what the section IS and what makes it different, because this is
      // the line a reader sees in a search result and in a shared link.
      description:
        `${n} events, each told from every side that claimed it. ` +
        `Primary sources, named perspectives, and what each account leaves out.`,
      path: "/history/",
    })
  );
}

export function eventMetadata(opts: {
  title: string;
  description: string;
  slug: string;
}): Metadata {
  return yieldToCardFile(
    pageMetadata({
      title: `${opts.title} | History`,
      description: opts.description,
      path: `/history/${opts.slug}/`,
    })
  );
}

export { SITE_URL };
