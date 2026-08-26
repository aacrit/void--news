"use client";

import Link from "next/link";
import LogoWordmark from "./LogoWordmark";

/* ---------------------------------------------------------------------------
   Footer — Newspaper-style footer
   Uses LogoWordmark for branding (the Sigil-O IS the "O" in VOID NEWS, so the
   wordmark already carries the mark; a separate LogoIcon would render the ring
   twice, which read as a doubled footer wordmark).
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
          <LogoWordmark height={16} />
        </div>
        <p className="footer-tagline">See through the void.</p>

        {/* Desktop discoverability: the top nav only toggles Feed/Sources and
            the mobile side panel carries the rest, so the footer links the
            remaining pages for desktop readers. */}
        <nav className="footer-links" aria-label="Site pages">
          <Link href="/onair" className="footer-link">On Air</Link>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <Link href="/about" className="footer-link">About</Link>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <Link href="/sources" className="footer-link">Sources</Link>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <Link href="/ship" className="footer-link">Feedback</Link>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <Link href="/press" className="footer-link">Press</Link>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <Link href="/privacy" className="footer-link">Privacy</Link>
        </nav>

        <p className="footer-built">&copy; 2026 Void News. All rights reserved.</p>
        <p className="footer-kbd-hint" aria-label="Press question mark for keyboard shortcuts">
          <kbd className="footer-kbd-hint__key">?</kbd> shortcuts
        </p>
      </div>
    </footer>
  );
}
