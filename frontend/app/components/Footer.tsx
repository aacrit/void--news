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
        <p className="footer-tagline">Free, transparent news bias analysis</p>
        <p className="footer-built">&copy; 2026 void --news. All rights reserved. &middot; <Link href="/void--news/paper" style={{ color: "inherit", textDecoration: "underline", textUnderlineOffset: "3px" }}>Read the Broadsheet Edition</Link></p>
      </div>
    </footer>
  );
}
