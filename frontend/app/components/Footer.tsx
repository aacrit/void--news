"use client";

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

function formatLastUpdated(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffHrs = Math.floor(diffMs / 3600000);
  const diffMins = Math.floor(diffMs / 60000);

  const time = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  if (diffMins < 60) {
    return `Last updated ${diffMins}m ago`;
  }
  if (diffHrs < 24) {
    return `Last updated ${diffHrs}h ago`;
  }
  const date = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `Last updated ${date}, ${time}`;
}

export default function Footer({ lastUpdated }: FooterProps) {
  const updatedText = lastUpdated
    ? formatLastUpdated(lastUpdated)
    : "Updated twice daily";

  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="si-hoverable" style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <LogoIcon size={22} animation="idle" />
          <LogoWordmark height={16} />
        </div>
        <p className="footer-tagline">Free, transparent news bias analysis</p>
        <p className="footer-stats">200 curated sources &middot; {updatedText}</p>
        <p className="footer-built">&copy; 2026 void --news. All rights reserved.</p>
      </div>
    </footer>
  );
}
