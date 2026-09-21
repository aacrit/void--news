/* ---------------------------------------------------------------------------
   The Void News share card. ONE composer, every card.

   WHY ONE. Before this file was rewritten there were three looks for one
   brand: History and Weekly shared a paper card that set a letter-spaced
   "VOID HISTORY" / "VOID WEEKLY" and no Sigil, the site-wide og-image.png was
   a dark card with a footed Sigil and "AN EXPERIMENTAL NEWSROOM", and every
   story page inherited that dark card. A reader who saw two of them in the
   same timeline had no way to tell they came from the same newsroom, and one
   of the three named products that do not exist.

   THE GRAMMAR, in the order the eye reads it:

     [brass Sigil]  VOID NEWS          <- the lockup, identical on every card
     ─────────────────────────────     <- the rule
     ▌ History                         <- the section nameplate, in its accent
     The Cyrus Cylinder                <- the card's own content
     539 BCE  ·  Middle East
     ▓▓▓▓▓▓▓ (the lean spectrum)
     tagline                    news.voidvision.org

   "VOID NEWS" is the only word that gets a lockup. History, Weekly, Deep Dive,
   On Air and The Argument are SECTIONS of Void News (CLAUDE.md, Brand), so
   each gets a nameplate in its own accent and never a wordmark of its own.

   The Sigil is the coverage ring with the level balance beam, the same footed
   geometry as `components/ScaleIcon.tsx`, `SigilWordmark.tsx` and
   `public/favicon.svg`, drawn in brass (--sigil-brass, light mode).

   NOTE for anyone editing the JSX: satori requires an explicit `display` on
   every element with more than one child, and silently mis-lays-out without
   it. Keep the `display: "flex"` on each wrapper even where it looks
   redundant.

   `next/og` DOES run under `output: export` given `dynamic = "force-static"`
   on the route, which is why no rasteriser dependency is added.
   --------------------------------------------------------------------------- */

import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/* ── Palette, from tokens.css light mode ("Morning Edition") ─────────────── */

export const PAPER = "#F0EBDD"; // --bg-primary
export const INK = "#1A1A1A"; // --fg-primary
export const INK_SECONDARY = "#4A4540"; // --fg-secondary
export const MUTED = "#52504A"; // --fg-muted
export const RULE = "#C8C0B5"; // --border-strong
export const BRASS = "#946B15"; // --sigil-brass

/** Section accents, from `--palette-*` in tokens.css. A nameplate is set at
 *  34px bold, so the terracotta (3.3:1) clears AA for large text; it is never
 *  used here for anything smaller. */
export const ACCENT_NEWS = "#B26F52"; // --palette-news
export const ACCENT_WEEKLY = "#B91C1C"; // --palette-weekly
export const ACCENT_HISTORY = "#5C4033"; // --palette-history

/** The 7-point lean spectrum, light mode, left to right (tokens.css). It is
 *  the one mark that is unmistakably Void, and it means the same thing in
 *  every section: every side, placed rather than averaged. */
const SPECTRUM = [
  "#0E2E70", "#1B5298", "#2E78B4", "#2B784A", "#C4503E", "#9C2C22", "#6E1610",
];

export const DOMAIN = "news.voidvision.org";

/* ── The site-wide card ──────────────────────────────────────────────────────
   Rendered to `public/og-image.png` by `brand/ci/render_og.mjs`, and used as
   the fallback wherever a page has no card of its own. It carries NO count:
   "1,016 sources" on the old card was a number that goes stale the day a
   source is added, and a share card is the one surface nobody re-reads.    ── */

export const SITE_TITLE = "See through the void.";
export const SITE_TAGLINE = "Six axes of bias. No paywall. No feed tuned to you.";

/* ── The Sigil, as an image satori can place ─────────────────────────────── */

/**
 * Satori renders `<img>` reliably and nested `<svg>` elements only partially,
 * so the mark ships as a data URI. Geometry is lifted verbatim from
 * SigilWordmark: ring r41, beam out to the ticks, post and base hanging below
 * like a descender. The viewBox is 124 tall so the foot never clips.
 */
function sigilDataUri(color: string): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 124" width="100" height="124">` +
    `<g fill="none" stroke="${color}" stroke-linecap="round" stroke-linejoin="round">` +
    `<circle cx="50" cy="50" r="41" stroke-width="8"/>` +
    `<line x1="4" y1="50" x2="96" y2="50" stroke-width="6"/>` +
    `<line x1="4" y1="42" x2="4" y2="58" stroke-width="5"/>` +
    `<line x1="96" y1="42" x2="96" y2="58" stroke-width="5"/>` +
    `<line x1="50" y1="91" x2="50" y2="112" stroke-width="6"/>` +
    `<path d="M35 118 C43 113 57 113 65 118" stroke-width="6"/>` +
    `</g></svg>`;
  return `data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`;
}

/** The paper grain, the same feTurbulence as `--paper-texture` in tokens.css
 *  at the same 0.08 opacity, tiled over the card. */
const GRAIN =
  "data:image/svg+xml;base64," +
  Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300">` +
      `<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" stitchTiles="stitch"/></filter>` +
      `<rect width="100%" height="100%" filter="url(#n)" opacity="0.08"/>` +
      `</svg>`,
  ).toString("base64");

/* ── Fonts ───────────────────────────────────────────────────────────────── */

interface LoadedFont {
  name: string;
  data: ArrayBuffer;
  weight: 400 | 600 | 700;
  style: "normal";
}

let _fonts: Promise<LoadedFont[]> | null = null;

/**
 * Playfair (editorial) and Inter (structural), fetched ONCE per build process
 * and shared by every card. Whole faces, not `text=` subsets: a subset built
 * from one card's glyphs renders the next card's missing letters in a fallback
 * face, and the subset request is a network round trip per card, which a
 * per-story card cannot afford.
 *
 * Safe as a build-time network call because `app/layout.tsx` already imports
 * from `next/font/google`, so a build without network access is already
 * impossible. Still wrapped: a font that fails to load costs the cards their
 * faces, not the deploy.
 *
 * The User-Agent matters. Google serves woff2 to a modern browser string, and
 * satori cannot read woff2; this one gets plain TTF back.
 */
function loadFonts(): Promise<LoadedFont[]> {
  if (_fonts) return _fonts;
  _fonts = (async () => {
    try {
      const css = await fetch(
        "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600",
        { headers: { "User-Agent": "Mozilla/5.0 (compatible; VoidNews/1.0)" } },
      ).then((r) => r.text());

      const faces: { name: string; weight: 400 | 600 | 700; url: string }[] = [];
      for (const block of css.split("@font-face").slice(1)) {
        const family = block.match(/font-family:\s*'([^']+)'/)?.[1];
        const weight = Number(block.match(/font-weight:\s*(\d+)/)?.[1] ?? 400);
        const url = block.match(/src:\s*url\(([^)]+)\)/)?.[1];
        if (!family || !url) continue;
        faces.push({
          name: family.startsWith("Playfair") ? "Playfair" : "Inter",
          weight: weight as 400 | 600 | 700,
          url,
        });
      }

      return await Promise.all(
        faces.map(async (f) => ({
          name: f.name,
          weight: f.weight,
          style: "normal" as const,
          data: await fetch(f.url).then((r) => r.arrayBuffer()),
        })),
      );
    } catch {
      return [];
    }
  })();
  return _fonts;
}

/* ── Text ────────────────────────────────────────────────────────────────── */

/** Long headlines are clipped rather than shrunk: a card is a poster. */
export function clipHeadline(text: string, max = 92): string {
  const t = (text || "").trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max);
  const sp = cut.lastIndexOf(" ");
  return (sp > 0 ? cut.slice(0, sp) : cut).replace(/[,;:]$/, "") + "…";
}

/** The dash ban reaches the cards too: an em or en dash in a headline the
 *  pipeline wrote becomes a comma, which is what the rule says to do when a
 *  sentence cannot be split. */
function deDash(text: string): string {
  return (text || "").replace(/\s*[—–]\s*/g, ", ").replace(/\s+,/g, ",");
}

/* ── The composer ────────────────────────────────────────────────────────── */

export interface VoidCard {
  /** "History", "Weekly", "Deep Dive", "On Air", "The Argument". Omitted on
   *  the site-wide card, which is the brand itself and not a section. */
  section?: string;
  /** The section accent. Ignored without a section. */
  accent?: string;
  /** The poster line: an event title, a cover headline, a story headline. */
  title: string;
  /** Dates, issue and week, source count and lean. Joined with a middot;
   *  empty entries are dropped, so a caller can pass a maybe-value. */
  meta?: (string | null | undefined | false)[];
  /** One line along the bottom, under the spectrum. */
  tagline?: string;
}

export async function voidCard(card: VoidCard): Promise<ImageResponse> {
  const title = deDash(clipHeadline(card.title));
  const meta = (card.meta ?? []).filter(Boolean).map((m) => deDash(String(m)));
  const accent = card.accent ?? ACCENT_NEWS;
  const fonts = await loadFonts();

  // A card is a poster: the headline is clipped, never shrunk to fit, but the
  // three sizes keep a 92-character clip from overflowing the measure.
  const titleSize = title.length > 72 ? 54 : title.length > 46 ? 64 : 76;

  return new ImageResponse(
    (
      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: "100%",
          background: PAPER,
          padding: "52px 72px 48px",
        }}
      >
        {/* Paper grain, tiled. Behind everything, felt rather than seen. */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: 1200,
            height: 630,
            display: "flex",
            backgroundImage: `url("${GRAIN}")`,
            backgroundRepeat: "repeat",
            backgroundSize: "300px 300px",
          }}
        />

        {/* ── The lockup: brass Sigil, then VOID NEWS. Never a section. ── */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={sigilDataUri(BRASS)} width={57} height={71} alt="" />
            <div
              style={{
                display: "flex",
                marginLeft: 22,
                fontFamily: "Playfair",
                fontWeight: 700,
                fontSize: 46,
                letterSpacing: 3,
                color: INK,
              }}
            >
              VOID NEWS
            </div>
          </div>
          <div
            style={{
              display: "flex",
              height: 2,
              width: "100%",
              marginTop: 24,
              background: RULE,
            }}
          />
        </div>

        {/* ── The section nameplate, then this card's own content. ── */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            justifyContent: "center",
          }}
        >
          {card.section ? (
            <div style={{ display: "flex", alignItems: "center", marginBottom: 22 }}>
              <div style={{ display: "flex", width: 44, height: 5, background: accent }} />
              <div
                style={{
                  display: "flex",
                  marginLeft: 16,
                  fontFamily: "Playfair",
                  fontWeight: 700,
                  fontSize: 34,
                  color: accent,
                }}
              >
                {card.section}
              </div>
            </div>
          ) : null}

          <div
            style={{
              display: "flex",
              fontFamily: "Playfair",
              fontWeight: 700,
              fontSize: titleSize,
              lineHeight: 1.12,
              letterSpacing: -0.5,
              color: INK,
              maxWidth: 1000,
            }}
          >
            {title}
          </div>

          {meta.length ? (
            <div
              style={{
                display: "flex",
                marginTop: 24,
                fontFamily: "Inter",
                fontWeight: 600,
                fontSize: 23,
                letterSpacing: 1,
                color: INK_SECONDARY,
              }}
            >
              {meta.join("  ·  ")}
            </div>
          ) : null}
        </div>

        {/* ── The spectrum, the tagline and the address. ── */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", height: 8, width: "100%" }}>
            {SPECTRUM.map((c, i) => (
              <div key={i} style={{ display: "flex", flex: 1, background: c }} />
            ))}
          </div>
          <div
            style={{
              display: "flex",
              marginTop: 18,
              alignItems: "center",
              justifyContent: "space-between",
              fontFamily: "Inter",
              fontSize: 21,
              color: MUTED,
            }}
          >
            <div style={{ display: "flex" }}>{deDash(card.tagline ?? "")}</div>
            <div style={{ display: "flex", fontWeight: 600, letterSpacing: 0.5 }}>
              {DOMAIN}
            </div>
          </div>
        </div>
      </div>
    ),
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
