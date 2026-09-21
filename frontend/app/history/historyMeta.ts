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

/* The three browse routes. They were built, prerendered and served with no
   `metadata` export at all, so /history/threads, /history/era/<era> and
   /history/region/<region> each shipped the ROOT layout's title ("Void News.
   See through the void.") and the site-wide card: sixteen served pages that
   said nothing about themselves in a search result or a shared link. Each
   description is assembled from the catalogue the page itself renders, so
   none of them can assert something the page does not show. */

export function eraMetadata(opts: {
  label: string;
  dateRange: string;
  description: string;
  era: string;
}): Metadata {
  return yieldToCardFile(
    pageMetadata({
      title: `${opts.label} | History`,
      description: `${opts.dateRange}. ${opts.description}. Each event told from every side that claimed it.`,
      path: `/history/era/${opts.era}/`,
    })
  );
}

export function regionMetadata(opts: { label: string; region: string }): Metadata {
  return yieldToCardFile(
    pageMetadata({
      title: `${opts.label} | History`,
      description: `Events from ${opts.label}, each told from every side that claimed it. Primary sources, named perspectives, and what each account leaves out.`,
      path: `/history/region/${opts.region}/`,
    })
  );
}

export function threadsMetadata(threadCount: number): Metadata {
  return yieldToCardFile(
    pageMetadata({
      title: "Threads | History",
      description: `${threadCount} threads through the archive, each one following a single argument across centuries.`,
      path: "/history/threads/",
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
