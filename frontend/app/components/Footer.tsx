"use client";

import Link from "next/link";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";
import { AUDIO_ENABLED } from "../lib/audioGate";

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

        {/* Product family — the live product set only (no Paper / Games /
            Revolt). Names match the nav + mobile side panel. void --onair gated
            by AUDIO_ENABLED. */}
        <div className="footer-products">
          <span className="footer-products__item" title="The Daily Brief">The Brief</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          {AUDIO_ENABLED && (
            <>
              <Link href="/onair" className="footer-products__item" title="The audio broadcast">On Air</Link>
              <span className="footer-products__sep" aria-hidden="true">&middot;</span>
            </>
          )}
          <span className="footer-products__item" title="The Opinion board">Opinion</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/weekly" className="footer-products__item" title="The week in review">Weekly</Link>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/history" className="footer-products__item" title="The archive of consequence">History</Link>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/sources" className="footer-products__item" title="1,016 curated sources">Sources</Link>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/ship" className="footer-products__item" title="Request it, vote, watch it ship">Ship</Link>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/about" className="footer-products__item" title="About Void News">About</Link>
        </div>

        <p className="footer-built">&copy; 2026 Void News. All rights reserved.</p>
        <p className="footer-kbd-hint" aria-label="Press question mark for keyboard shortcuts">
          <kbd className="footer-kbd-hint__key">?</kbd> shortcuts
        </p>
      </div>
    </footer>
  );
}
