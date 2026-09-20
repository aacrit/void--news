/* ---------------------------------------------------------------------------
   The per-issue share card.

   Every issue used to share the site-wide OG image, and rev 71 improved that
   to the issue's COVER PHOTOGRAPH. Both are worse than they look:

   - The site card says nothing about which issue is being shared.
   - The cover photo is a hotlinked Wikimedia URL. It is correctly licensed and
     it renders on the page, but a third-party scraper fetching it
     cross-origin is a second request that can 404, 429 or time out, and when
     it does the share falls back to nothing. Worse, the photo carries no
     headline: a reader sees an Arctic satellite image with no idea what the
     issue argues.

   This composes the card from the issue's own text, so it always renders and
   always says what the issue is. It is emitted as a real PNG at build time
   (`next/og` runs under `output: export` given `dynamic = "force-static"`),
   which is why no rasteriser dependency is added.

   The cover photo is kept as the SECOND image, so a platform that prefers a
   photograph still finds one.
   --------------------------------------------------------------------------- */

import { ImageResponse } from "next/og";
import type { WeeklyDigestData } from "./types";
import { formatArchiveRange, issueLabel } from "./format";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const PAPER = "#f4f1e8";
const INK = "#14120f";
const ACCENT = "#a8321e";
const MUTED = "#6b655c";

/* The bias spectrum, which is the one mark that is unmistakably Void. Left to
   right, the same ramp the Sigil uses. */
const TAGLINE = "Every source, every story, scored for bias.";

const SPECTRUM = ["#2f5d8a", "#5b87ad", "#8fae8a", "#3f8a63", "#c98b7a", "#b5502f", "#8a2318"];

/**
 * Playfair, fetched at build.
 *
 * Safe as a build-time network call because `app/layout.tsx` already imports
 * from `next/font/google`, so a build without network access is already
 * impossible. It is still wrapped: a font that fails to load costs the card
 * its display face, not the deploy.
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
function clipHeadline(text: string, max = 92): string {
  const t = (text || "").trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  return cut.slice(0, cut.lastIndexOf(" ")).replace(/[,;:]$/, "") + "…";
}

export async function issueCard(issue: WeeklyDigestData): Promise<ImageResponse> {
  const headline = clipHeadline(issue.cover_headline || issue.cover_text?.[0]?.headline || "");
  const week = formatArchiveRange(issue.week_start, issue.week_end);
  const kicker = `${issueLabel(issue.issue_number)}  ·  ${week}`;

  // EVERY glyph the card sets, or satori falls back mid-sentence: the subset
  // is built from the requested text, so a tagline whose letters the headline
  // happens not to contain would render in a different face.
  const font = await displayFont(
    headline + kicker + "VOID WEEKLY" + TAGLINE + "0123456789"
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
            VOID WEEKLY
          </div>
          <div style={{ display: "flex", fontSize: 22, letterSpacing: 2, color: ACCENT }}>
            {kicker.toUpperCase()}
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
          {/* The spectrum: coverage from left to right, measured. */}
          <div style={{ display: "flex", height: 8, width: "100%" }}>
            {SPECTRUM.map((c, i) => (
              <div key={i} style={{ display: "flex", flex: 1, background: c }} />
            ))}
          </div>
          <div style={{ display: "flex", fontSize: 22, color: MUTED, letterSpacing: 1 }}>
            {TAGLINE}
          </div>
        </div>
      </div>
    ),
    { ...size, fonts }
  );
}
