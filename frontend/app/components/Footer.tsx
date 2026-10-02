"use client";

import ChromeLink from "./ChromeLink";
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

        {/* Desktop discoverability: the top nav only toggles Feed/Sources and
            the mobile side panel carries the rest, so the footer links the
            remaining pages for desktop readers. */}
        <nav className="footer-links" aria-label="Site pages">
          <ChromeLink href="/onair" className="footer-link">On Air</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/history" className="footer-link">History</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/weekly" className="footer-link">Weekly</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/paper" className="footer-link">Paper</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/audio" className="footer-link">Audio</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/about" className="footer-link">About</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/sources" className="footer-link">Sources</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/ship" className="footer-link">Feedback</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/press" className="footer-link">Press</ChromeLink>
          <span className="footer-link__sep" aria-hidden="true">&middot;</span>
          <ChromeLink href="/privacy" className="footer-link">Privacy</ChromeLink>
        </nav>

        <p className="footer-built">&copy; 2026 Void News. All rights reserved.</p>
        <p className="footer-kbd-hint" aria-label="Press question mark for keyboard shortcuts">
          <kbd className="footer-kbd-hint__key">?</kbd> shortcuts
        </p>
      </div>
    </footer>
  );
}
