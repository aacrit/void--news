"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

/* ==========================================================================
   GamesHub — void --games Landing Page
   Featured game card + active games + coming-soon ghost cards.
   ========================================================================== */

/** Active game entries */
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
];

/** Ghost/coming-soon game entries */
const COMING_SOON = [
  {
    name: "THE WIRE",
    tagline: "Headline or hallucination? Spot the AI-generated story.",
  },
];

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
      {/* Film grain */}
      <div className="games-hub__grain" aria-hidden="true" />

      {/* Navigation */}
      <nav className="games-hub__nav" aria-label="Navigation">
        <Link href="/" className="games-hub__back">
          <span aria-hidden="true">&larr;</span>
          {" "}void --news
        </Link>
      </nav>

      {/* Masthead */}
      <header className="games-hub__masthead">
        <h1 className="games-hub__title">void --games</h1>
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
            className={`games-hub__card games-hub__card--featured${i === 0 ? " games-hub__card--hero" : ""}`}
          >
            <div className="games-hub__card-badge">{game.badge}</div>
            <div className="games-hub__card-content">
              <h2 className="games-hub__card-name">{game.name}</h2>
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
                <h3 className="games-hub__card-name">{game.name}</h3>
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
