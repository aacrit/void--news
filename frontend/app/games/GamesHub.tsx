"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

/* ==========================================================================
   GamesHub — void --games Landing Page
   Featured game card + active games + coming-soon ghost cards.
   UNDERTOW is the featured hero game. THE FRAME is second.

   Brand identity: inline SVG wordmark with staged entrance animation.
   Signal diamond (amber) pulses once on load. Sigils on each card.
   ========================================================================== */

/* --------------------------------------------------------------------------
   Game Sigil Components — inline SVG marks (24x24)
   Minimal typographic marks, not icons. IBM Plex Mono aesthetic.
   -------------------------------------------------------------------------- */

function SigilUndertow({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--undertow${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      {/* Surface wave */}
      <path
        d="M4,14 C8,9 12,9 16,14 C20,19 24,19 28,14"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      {/* Undertow current */}
      <path
        d="M6,22 C10,19 14,19 18,22 C22,25 26,25 28,22"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.4"
      />
    </svg>
  );
}

function SigilWire({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--wire${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      {/* Flat line with signal pulse */}
      <polyline
        points="3,16 10,16 13,16 15,8 17,24 19,12 21,16 22,16 29,16"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SigilRun({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--run${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      {/* Forward dash — the signal */}
      <line
        x1="6"
        y1="16"
        x2="20"
        y2="16"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      {/* Arrow tip */}
      <polyline
        points="17,11 22,16 17,21"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Trail fade */}
      <line
        x1="3"
        y1="16"
        x2="8"
        y2="16"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.3"
      />
    </svg>
  );
}

function SigilFrame({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--frame${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      {/* Frame brackets — seeing through the frame */}
      <polyline
        points="8,6 4,6 4,26 8,26"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        points="24,6 28,6 28,26 24,26"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Center crosshair — the analytical eye */}
      <line x1="14" y1="16" x2="18" y2="16" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5" />
      <line x1="16" y1="14" x2="16" y2="18" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}

/** Map game name to its sigil component */
function GameSigil({ game }: { game: string }) {
  switch (game) {
    case "UNDERTOW": return <SigilUndertow />;
    case "THE FRAME": return <SigilFrame />;
    case "VOID RUN": return <SigilRun />;
    case "THE WIRE": return <SigilWire />;
    default: return null;
  }
}

/* --------------------------------------------------------------------------
   Games Wordmark — inline SVG with animation classes
   -------------------------------------------------------------------------- */

function GamesWordmark() {
  return (
    <div className="games-hub__wordmark-wrap" role="img" aria-label="void --games">
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 340 44"
        fill="currentColor"
        aria-hidden="true"
      >
        {/* "void" — fades in first */}
        <g className="games-wordmark__void" transform="translate(0,4)">
          {/* "v" */}
          <polygon points="0,4 5.5,4 14,28 22.5,4 28,4 16.5,36 11.5,36" />
          {/* "o" — hollow void */}
          <path
            d="M48 3.5 C61 3 62 10 61.5 20 C61 30 58 37 48 36.5 C38 37 35 30 34.5 20 C34 10 35 3 48 3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
          />
          {/* "i" */}
          <rect x="69" y="2" width="5" height="5" rx="0.8" />
          <rect x="69.5" y="11" width="4" height="25" rx="0.5" />
          {/* "d" */}
          <path d="M82,20C82,10.5 87,3 94,3C97,3 100,4.5 102,7.5L102,0L107,0L107,36L102,36L102,32.5C100,35.5 97,37 94,37C87,37 82,29.5 82,20ZM88,20C88,27.5 90.8,32 95,32C98,32 100.5,29.5 102,26L102,14C100.5,10.5 98,8 95,8C90.8,8 88,12.5 88,20Z" />
        </g>

        {/* Signal diamond — amber frequency marker */}
        <rect
          className="games-wordmark__signal"
          x="120"
          y="15"
          width="8"
          height="8"
          rx="1"
          fill="var(--cin-amber, #c9a84c)"
          transform="rotate(45 124 19)"
        />

        {/* "--" dashes — amber accent */}
        <g className="games-wordmark__dashes" transform="translate(0,4)">
          <rect x="140" y="17.5" width="10" height="3" rx="0.5" fill="var(--cin-amber, #c9a84c)" />
          <rect x="153" y="17.5" width="10" height="3" rx="0.5" fill="var(--cin-amber, #c9a84c)" />
        </g>

        {/* "games" — slides in from right */}
        <g className="games-wordmark__flag" transform="translate(0,4)" opacity="0.85">
          {/* "g" */}
          <path d="M176,23.5C176,17.5 179,11.5 184.5,11.5C187.5,11.5 189.5,13 191,15L191,12L194.2,12L194.2,33C194.2,38 191,42 185.5,42C181.5,42 178.5,40 177,37.5L179.2,35.8C180.5,38 182.5,39.5 185.5,39.5C189,39.5 191,37 191,33.5L191,31.5C189.5,34 187.5,35.5 184.5,35.5C179,35.5 176,29.5 176,23.5ZM179.5,23.5C179.5,28.5 181.5,33 185,33C188,33 190,30.5 191,28L191,19C190,16.5 188,14 185,14C181.5,14 179.5,18.5 179.5,23.5Z" />
          {/* "a" */}
          <path d="M204,28.5C204,25 206,23 209,22L213,20.5C215.5,19.5 216.5,18 216.5,16.2C216.5,14 214.5,12 211.5,12C209,12 207,13.5 206,15.5L203.5,14C205,11.5 208,9.5 211.5,9.5C216.5,9.5 220,12.5 220,16.5C220,19.5 218,21.5 215,22.5L210.5,24.2C208,25.2 207,26.8 207,28.8L220,28.8L220,31.5L204,31.5L204,28.5Z" />
          {/* "m" */}
          <path d="M228,12L231.2,12L231.2,16C233,13 235,11 238,11C241,11 242.5,12.5 243.5,15C245.5,12.5 247.5,11 250.5,11C254,11 256,13 256,17L256,36L252.8,36L252.8,18C252.8,15 251.5,13.5 249.5,13.5C247.5,13.5 245.5,15 244.5,17.5L244.5,36L241.3,36L241.3,18C241.3,15 240,13.5 238,13.5C236,13.5 234,15 233,17.5L233,36L228,36Z" />
          {/* "e" */}
          <path d="M266,23.5C266,17.5 269.5,11 276,11C282.5,11 285.5,17 285.5,23L285.5,24.5L269.5,24.5C269.8,29 272.5,33 276.5,33C279.5,33 281.5,31 282.8,29L285,30.5C283,33.5 280,36 276,36C270,36 266,30 266,23.5ZM269.5,22L282,22C281.5,17.5 279.5,14 276,14C272.5,14 270.2,17.5 269.5,22Z" />
          {/* "s" */}
          <path d="M294,28C294,24.5 296,22.5 299,21.5L303.5,20C306,19 307,17.8 307,16C307,13.8 305,12 302,12C299,12 297,13.5 296,15.5L293.5,14C295,11.5 298,9.5 302,9.5C307,9.5 310.5,12.5 310.5,16.5C310.5,19.5 308.5,21.5 305.5,22.5L301,24C298.5,25 297.5,26.5 297.5,28.5C297.5,31 299.5,33 302.5,33C305,33 307,31.5 308,29.5L310.2,31C308.5,34 305.5,36 302,36C297.5,36 294,32.5 294,28Z" />
        </g>
      </svg>
    </div>
  );
}

/* --------------------------------------------------------------------------
   Game Data
   -------------------------------------------------------------------------- */

/** Active game entries — UNDERTOW first (hero) */
const ACTIVE_GAMES = [
  {
    name: "UNDERTOW",
    href: "/games/undertow",
    tagline: "every text has a tide",
    description:
      "Four cultural artifacts. One axis. Order them from pole to pole.",
    badge: "DAILY",
  },
  {
    name: "THE FRAME",
    href: "/games/frame",
    tagline: "see through the frame",
    description:
      "Four outlets. One story. Rank the headlines from left to right.",
    badge: "DAILY",
  },
  {
    name: "VOID RUN",
    href: "/games/run",
    tagline: "run until the signal breaks",
    description:
      "An endless runner through corridors of language. You are the signal. The obstacles are noise.",
    badge: "ENDLESS",
  },
];

/** Ghost/coming-soon game entries */
const COMING_SOON = [
  {
    name: "THE WIRE",
    tagline: "Headline or hallucination? Spot the AI-generated story.",
  },
];

/* --------------------------------------------------------------------------
   GamesHub Component
   -------------------------------------------------------------------------- */

export default function GamesHub() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  const today = mounted
    ? new Date().toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : "\u00A0";

  return (
    <div className="games-hub">
      {/* VFX Layer 1: Film grain */}
      <div className="games-hub__grain" aria-hidden="true" />

      {/* VFX Layer 2: Cinematic vignette — draws eye to center */}
      <div className="games-hub__vignette" aria-hidden="true" />

      {/* VFX Layer 3: Ambient glow — broadcast frequency warmth */}
      <div className="games-hub__ambient-glow" aria-hidden="true" />

      {/* Navigation */}
      <nav className="games-hub__nav" aria-label="Navigation">
        <Link href="/" className="games-hub__back">
          <span aria-hidden="true">&larr;</span>
          {" "}void --news
        </Link>
      </nav>

      {/* Masthead — animated wordmark replaces plain h1 */}
      <header className="games-hub__masthead">
        <h1>
          <GamesWordmark />
        </h1>
        <p className="games-hub__subtitle">
          every text has a tide
        </p>

        {/* Organic ink divider */}
        <svg
          className="games-hub__divider"
          viewBox="0 0 600 4"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path d="M0,2 C50,0.5 100,3.5 150,2 C200,0.5 250,3 300,2 C350,1 400,3.5 450,2 C500,0.5 550,3 600,2" />
        </svg>
      </header>

      {/* Active games */}
      <section className="games-hub__featured" aria-label="Active games">
        {ACTIVE_GAMES.map((game, i) => (
          <Link
            key={game.name}
            href={game.href}
            className={`games-hub__card games-hub__card--featured${i === 0 ? " games-hub__card--hero" : ""}${game.name === "UNDERTOW" ? " games-hub__card--undertow" : ""}`}
          >
            <div className="games-hub__card-badge">{game.badge}</div>
            <div className="games-hub__card-content">
              <div className="games-hub__card-header">
                <GameSigil game={game.name} />
                <h2 className="games-hub__card-name">{game.name}</h2>
              </div>
              <p className="games-hub__card-tagline">{game.description}</p>
              <div className="games-hub__card-meta">
                <span className="games-hub__card-date" suppressHydrationWarning>
                  {today}
                </span>
                <span className="games-hub__card-id">#1</span>
              </div>
            </div>
            <div className="games-hub__card-cta" aria-hidden="true">
              PLAY &rarr;
            </div>
          </Link>
        ))}
      </section>

      {/* Coming soon */}
      <section className="games-hub__upcoming" aria-label="Coming soon">
        <h2 className="games-hub__section-label">COMING SOON</h2>
        <div className="games-hub__ghost-grid">
          {COMING_SOON.map((game) => (
            <div
              key={game.name}
              className="games-hub__card games-hub__card--ghost"
              aria-disabled="true"
            >
              <div className="games-hub__card-content">
                <div className="games-hub__card-header">
                  <GameSigil game={game.name} />
                  <h3 className="games-hub__card-name">{game.name}</h3>
                </div>
                <p className="games-hub__card-tagline">{game.tagline}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="games-hub__footer">
        <p className="games-hub__footer-text">
          Media literacy, gamified. From{" "}
          <Link href="/" className="games-hub__footer-link">void --news</Link>.
        </p>
      </footer>
    </div>
  );
}
