"use client";

import Link from "next/link";
import ThemeToggle from "../../components/ThemeToggle";
import SigilWordmark from "../../components/SigilWordmark";

/* ===========================================================================
   HistoryTopbar — Sticky three-zone navigation for void --history
   Mirrors void --weekly's topbar so the product family reads consistently.

   LEFT   : a small "back to parent" mark — a left arrow + the VOID NEWS
            wordmark (currentColor letters, brass Sigil-O), linking to `/`,
            the main news app. The exit / return affordance.
   CENTER : the large VOID HISTORY product logo (umber accent) — the hero of
            this page — linking to /history (the product home).
   RIGHT  : the theme toggle (and any future actions).

   So VOID NEWS (back, small) < VOID HISTORY (center, large).
   =========================================================================== */

export default function HistoryTopbar() {
  return (
    <header className="hist-topbar hist-cold-open--topbar" role="banner">
      <div className="hist-topbar__left">
        <Link href="/" className="hist-topbar__back" aria-label="Back to Void News">
          <span className="hist-topbar__arrow" aria-hidden="true">&larr;</span>
          <span className="hist-topbar__back-word">
            <SigilWordmark product="NEWS" height={14} />
          </span>
        </Link>
      </div>

      <Link
        href="/history"
        className="hist-topbar__brand"
        aria-label="Void History home"
      >
        {/* Two size variants, toggled by CSS so the centered hero never
            overflows a narrow phone. Both are aria-hidden; the Link names it. */}
        <span className="hist-topbar__brand-lg">
          <SigilWordmark product="HISTORY" height={26} accent="var(--palette-history)" />
        </span>
        <span className="hist-topbar__brand-sm">
          <SigilWordmark product="HISTORY" height={21} accent="var(--palette-history)" />
        </span>
      </Link>

      <div className="hist-topbar__actions">
        <ThemeToggle />
      </div>
    </header>
  );
}
