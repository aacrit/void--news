/* ---------------------------------------------------------------------------
   The composed share card, shared by every section that has one.

   Extracted from `app/weekly/ogCard.tsx` when History needed the same thing.
   Copying those 148 lines would have produced two cards that drift: the font
   subsetting, the satori `display: flex` requirement and the headline clip are
   all easy to get subtly wrong a second time, and a card is the one surface
   nobody looks at until it is already wrong somewhere else.

   WHY A COMPOSED CARD AT ALL. A section that sets no card of its own inherits
   the site-wide one, which says nothing about what is being shared: every
   History event and the History landing all shared "Void News. See through the
   void." The alternative, hotlinking the page's own photograph, is worse than
   it looks: it is a second cross-origin fetch a scraper can 404 or rate-limit,
   and it carries no headline, so a reader sees a picture with no idea what it
   is about.

   This composes from the page's own text, so it always renders and always says
   what it is. `next/og` DOES run under `output: export` given
   `dynamic = "force-static"` on the route, which is why no rasteriser
   dependency is added.

   NOTE for anyone editing the JSX: satori requires an explicit `display` on
   every element with more than one child, and silently mis-lays-out without
   it. Keep the `display: "flex"` on each wrapper even where it looks
   redundant.
   --------------------------------------------------------------------------- */

import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export const PAPER = "#f4f1e8";
export const INK = "#14120f";
export const MUTED = "#6b655c";

/** Section accents, from `--palette-*` in tokens.css. */
export const ACCENT_WEEKLY = "#B91C1C";
export const ACCENT_HISTORY = "#5C4033";

/* The bias spectrum, left to right, the same ramp the Sigil uses. It is the
   one mark that is unmistakably Void, and it means the same thing in both
   sections: every side, placed rather than averaged. */
const SPECTRUM = ["#2f5d8a", "#5b87ad", "#8fae8a", "#3f8a63", "#c98b7a", "#b5502f", "#8a2318"];

/**
 * Playfair, fetched at build.
 *
 * Safe as a build-time network call because `app/layout.tsx` already imports
 * from `next/font/google`, so a build without network access is already
 * impossible. Still wrapped: a font that fails to load costs the card its
 * display face, not the deploy.
 */
async function displayFont(text: string): Promise<ArrayBuffer | null> {
  try {
    const api =
      "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&text=" +
      encodeURIComponent(text);
    const css = await fetch(api, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; VoidNews/1.0)" },
    }).then((r) => r.text());
    const url = css.match(/src:\s*url\(([^)]+)\)/)?.[1];
    if (!url) return null;
    return await fetch(url).then((r) => r.arrayBuffer());
  } catch {
    return null;
  }
}

/** Long headlines are clipped rather than shrunk: a card is a poster. */
export function clipHeadline(text: string, max = 92): string {
  const t = (text || "").trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  const sp = cut.lastIndexOf(" ");
  return (sp > 0 ? cut.slice(0, sp) : cut).replace(/[,;:]$/, "") + "…";
}

export interface SectionCard {
  /** Letter-spaced mark, e.g. "VOID WEEKLY". */
  wordmark: string;
  /** The line under it, set in the section accent. */
  kicker: string;
  /** The poster line. */
  headline: string;
  /** One sentence along the bottom, under the spectrum. */
  tagline: string;
  accent: string;
}

export async function sectionCard(card: SectionCard): Promise<ImageResponse> {
  const headline = clipHeadline(card.headline);
  const kicker = card.kicker.toUpperCase();

  // EVERY glyph the card sets, or satori falls back mid-sentence: the subset
  // is built from the requested text, so a tagline whose letters the headline
  // happens not to contain would render in a different face.
  const font = await displayFont(
    headline + kicker + card.wordmark + card.tagline + "0123456789"
  );
  const fonts = font
    ? [{ name: "Playfair", data: font, weight: 700 as const, style: "normal" as const }]
    : undefined;

  return new ImageResponse(
    (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          background: PAPER,
          padding: "64px 72px",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div
            style={{
              display: "flex",
              fontSize: 28,
              letterSpacing: 10,
              color: INK,
              fontWeight: 700,
            }}
          >
            {card.wordmark}
          </div>
          <div style={{ display: "flex", fontSize: 22, letterSpacing: 2, color: card.accent }}>
            {kicker}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            fontSize: headline.length > 58 ? 62 : 76,
            lineHeight: 1.12,
            color: INK,
            fontFamily: fonts ? "Playfair" : undefined,
            fontWeight: 700,
            maxWidth: 1000,
          }}
        >
          {headline}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", height: 8, width: "100%" }}>
            {SPECTRUM.map((c, i) => (
              <div key={i} style={{ display: "flex", flex: 1, background: c }} />
            ))}
          </div>
          <div style={{ display: "flex", fontSize: 22, color: MUTED, letterSpacing: 1 }}>
            {card.tagline}
          </div>
        </div>
      </div>
    ),
    { ...size, fonts }
  );
}
