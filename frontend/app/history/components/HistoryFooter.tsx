"use client";

import Link from "next/link";
import LogoFull from "../../components/LogoFull";

/* ===========================================================================
   HistoryFooter — Minimal footer for void --history
   Logo brand mark + section label + back link.
   =========================================================================== */

export default function HistoryFooter() {
  return (
    <footer className="hist-footer" role="contentinfo">
      <div className="hist-footer__brand">
        <span className="hist-footer__logo" aria-hidden="true">
          <LogoFull height={20} />
        </span>
        <span className="hist-footer__section">history</span>
      </div>
      <Link href="/" className="hist-footer__link">
        &larr; Back to void --news
      </Link>
    </footer>
  );
}
