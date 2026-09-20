"use client";

import ThemeToggle from "../../components/ThemeToggle";
import SectionNameplate from "../../components/SectionNameplate";

/* ===========================================================================
   HistoryTopbar — sticky masthead for History.

   History is a SECTION of Void News, not a product beside it, so this bar
   carries one nameplate rather than two marks: VOID NEWS in its own lockup,
   a hairline, then "History" in archival umber italic (see SectionNameplate).

   Until rev 75 it ran three zones: a small "← VOID NEWS" back mark on the
   left and a large VOID HISTORY lockup dead centre, which said the reader had
   left Void News for a sibling brand and needed a way back to it. They had
   not. The lockup IS the way home now, exactly as it is in the news masthead,
   and the arrow, the duplicate wordmark and the two CSS-toggled size copies go
   with it.
   =========================================================================== */

export default function HistoryTopbar() {
  return (
    <header className="hist-topbar hist-cold-open--topbar" role="banner">
      <SectionNameplate
        section="History"
        href="/history"
        height={22}
        accent="var(--palette-history)"
        className="hist-topbar__nameplate"
      />

      <div className="hist-topbar__actions">
        <ThemeToggle />
      </div>
    </header>
  );
}
