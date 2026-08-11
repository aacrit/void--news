import type { Metadata } from "next";
import HomeContent from "./components/HomeContent";
import { fetchInitialFeed } from "./lib/serverFeed";
import { pageMetadata, SITE_URL } from "./lib/siteMeta";

/* ---------------------------------------------------------------------------
   Front page — PRERENDERED at build time (static export).

   This is an async Server Component. At `next build` it fetches the same
   top-50 feed the client renders and passes it to the client HomeContent as
   `initialStories`, so the served index.html ships the real feed (SEO +
   instant first paint) instead of an empty shell that fills in via useEffect.

   Deterministic first paint (React #418 guard): the feed and all masthead
   date/time strings are computed ONCE here at build and passed down as
   preformatted values. HomeContent does NOT refetch the feed on mount, so the
   client's first paint is byte-identical to this server render.
   --------------------------------------------------------------------------- */

export const metadata: Metadata = pageMetadata({
  title: "Void News. See through the void.",
  description:
    "An experimental newsroom: free per-article bias analysis across 1,016 sources. Six axes. No paywall. No feed tuned to you. Just the news, dissected.",
  path: "/",
});

export default async function Home() {
  const feed = await fetchInitialFeed();

  // schema.org ItemList of the day's top stories. Each item points at the
  // story's canonical prerendered Deep Dive page (/story/<permalink>/) so
  // crawlers follow the list straight into a real, indexable page. Falls back
  // to the in-app ?story deep link only if a card has no archive permalink yet.
  const displayable = feed.stories.filter(
    (s) => (s.sigilData?.sourceCount ?? s.source?.count ?? 0) >= 3,
  );
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "Void News: Today's Top Stories",
    itemListOrder: "https://schema.org/ItemListOrderDescending",
    numberOfItems: Math.min(displayable.length, 30),
    itemListElement: displayable.slice(0, 30).map((s, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: s.title,
      url: s.permalink
        ? `${SITE_URL}${s.permalink}`
        : `${SITE_URL}/?story=${encodeURIComponent(s.id)}`,
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        // Static JSON serialized at build time. `<` is escaped to avoid any
        // chance of premature </script> parsing from story titles.
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, "\\u003c"),
        }}
      />
      <HomeContent
        initialStories={feed.stories}
        initialBuiltAt={feed.builtAt}
        editionDateline={feed.editionDateline}
      />
    </>
  );
}
