"use client";

import Link from "next/link";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";

/* ---------------------------------------------------------------------------
   Footer — Newspaper-style footer
   Uses LogoIcon (idle animation) + LogoWordmark for branding.
   Shows "200 curated sources" with last pipeline run time.
   --------------------------------------------------------------------------- */

interface FooterProps {
  lastUpdated?: string | null;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function Footer({ lastUpdated }: FooterProps) {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="si-hoverable" style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <LogoIcon size={22} animation="idle" />
          <LogoWordmark height={16} />
        </div>
        <p className="footer-tagline">370 sources. Six axes. Zero mystery.</p>

        {/* Product family */}
        <div className="footer-products">
          <span className="footer-products__item" title="The Daily Brief">void --tl;dr</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <span className="footer-products__item" title="Audio Broadcast">void --onair</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <span className="footer-products__item" title="The Board">void --opinion</span>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/sources" className="footer-products__item" title="Source Spectrum">void --sources</Link>
          <span className="footer-products__sep" aria-hidden="true">&middot;</span>
          <Link href="/void--news/paper" className="footer-products__item" title="Broadsheet Edition">void --paper</Link>
        </div>

        <p className="footer-built">&copy; 2026 void --news. All rights reserved.</p>
      </div>
    </footer>
  );
}
