"use client";

import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";

/* ---------------------------------------------------------------------------
   Footer — Newspaper-style footer
   Uses LogoIcon (idle animation) + LogoWordmark for branding.
   Shows source count with last pipeline run time.
   --------------------------------------------------------------------------- */

interface FooterProps {
  lastUpdated?: string | null;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function Footer({ lastUpdated }: FooterProps) {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        {/* nowrap belt-and-suspenders: the wordmark must always read "VOID NEWS"
            on ONE line (matching the masthead), never break to V / ID / NEWS. */}
        <div
          className="si-hoverable"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-3)",
            flexWrap: "nowrap",
            whiteSpace: "nowrap",
            maxWidth: "100%",
          }}
        >
          <LogoIcon size={22} animation="idle" />
          <LogoWordmark height={16} />
        </div>
        <p className="footer-tagline">See through the void.</p>

        {/* Product links intentionally omitted — they already live in the top
            nav + mobile side panel. Repeating them here was redundant. */}

        <p className="footer-built">&copy; 2026 Void News. All rights reserved.</p>
        <p className="footer-kbd-hint" aria-label="Press question mark for keyboard shortcuts">
          <kbd className="footer-kbd-hint__key">?</kbd> shortcuts
        </p>
      </div>
    </footer>
  );
}
