"use client";

import Link from "next/link";
import ThemeToggle from "../../components/ThemeToggle";

/* ===========================================================================
   HistoryTopbar — Sticky navigation for void --history
   Pattern: same as weekly's .wk-topbar — back arrow + brand + theme toggle.
   =========================================================================== */

export default function HistoryTopbar() {
  return (
    <header className="hist-topbar hist-cold-open--topbar" role="banner">
      <Link href="/" className="hist-topbar__back" aria-label="Back to void --news">
        <span className="hist-topbar__arrow" aria-hidden="true">&larr;</span>
        <span className="hist-topbar__title">void --history</span>
        <span className="hist-topbar__subtitle">The Archive</span>
      </Link>
      <div className="hist-topbar__actions">
        <ThemeToggle />
      </div>
    </header>
  );
}
