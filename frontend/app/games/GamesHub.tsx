"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

/* ==========================================================================
   GamesHub — void --games Landing Page
   Featured game card + coming-soon ghost cards.
   ========================================================================== */

/** Ghost/coming-soon game entries */
const COMING_SOON = [
  {
    name: "THE WIRE",
    tagline: "Headline or hallucination? Spot the AI-generated story.",
  },
  {
    name: "THE SOURCE",
    tagline: "Match the quote to the outlet. Harder than it sounds.",
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
          everyone reads the story. almost nobody reads the frame.
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

      {/* Featured game */}
      <section className="games-hub__featured" aria-label="Featured game">
        <Link href="/games/frame" className="games-hub__card games-hub__card--featured">
          <div className="games-hub__card-badge">DAILY</div>
          <div className="games-hub__card-content">
            <h2 className="games-hub__card-name">THE FRAME</h2>
            <p className="games-hub__card-tagline">
              Four outlets. One story. Rank the headlines from left to right.
            </p>
            <div className="games-hub__card-meta">
              <span className="games-hub__card-date" suppressHydrationWarning>{today}</span>
              <span className="games-hub__card-id">#1</span>
            </div>
          </div>
          <div className="games-hub__card-cta" aria-hidden="true">
            PLAY &rarr;
          </div>
        </Link>
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
