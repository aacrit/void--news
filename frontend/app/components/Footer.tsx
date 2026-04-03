"use client";

import Link from "next/link";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";
import { useBrandVersion } from "../lib/brandVersion";

/* ---------------------------------------------------------------------------
   Footer — Newspaper-style footer
   Uses LogoIcon (idle animation) + LogoWordmark for branding.
   Shows "951 sources" with last pipeline run time.
   --------------------------------------------------------------------------- */

interface FooterProps {
  lastUpdated?: string | null;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function Footer({ lastUpdated }: FooterProps) {
  const { version, setVersion } = useBrandVersion();

  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="si-hoverable" style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <LogoIcon size={22} animation="idle" />
          <LogoWordmark height={16} />
        </div>
        <p className="footer-tagline">951 sources. Six axes. Zero mystery.</p>

        {/* Product family */}
        <div className="footer-products">
          <span className="footer-products__item" title="The Daily Brief">void --tl;dr</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <span className="footer-products__item" title="Audio Broadcast">void --onair</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <span className="footer-products__item" title="The Board">void --opinion</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/sources" className="footer-products__item" title="Source Spectrum">void --sources</Link>
        </div>

        <p className="footer-built">&copy; 2026 void --news. All rights reserved.</p>

        {/* Brand version toggle */}
        <div className="footer-brand-toggle" role="radiogroup" aria-label="Brand mark version">
          <span className="footer-brand-toggle__label">Mark:</span>
          <button
            className={`footer-brand-toggle__btn${version === "v1" ? " footer-brand-toggle__btn--active" : ""}`}
            onClick={() => setVersion("v1")}
            role="radio"
            aria-checked={version === "v1"}
            aria-label="Scale beam mark"
          >
            V1
          </button>
          <button
            className={`footer-brand-toggle__btn${version === "v2" ? " footer-brand-toggle__btn--active" : ""}`}
            onClick={() => setVersion("v2")}
            role="radio"
            aria-checked={version === "v2"}
            aria-label="Void lens mark"
          >
            V2
          </button>
        </div>

        <p className="footer-kbd-hint" aria-label="Press question mark for keyboard shortcuts">
          <kbd className="footer-kbd-hint__key">?</kbd> shortcuts
        </p>
      </div>
    </footer>
  );
}
