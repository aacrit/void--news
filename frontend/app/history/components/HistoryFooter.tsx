"use client";

import Link from "next/link";

/* ===========================================================================
   HistoryFooter — Minimal footer for void --history
   =========================================================================== */

export default function HistoryFooter() {
  return (
    <footer className="hist-footer" role="contentinfo">
      <div className="hist-footer__brand">void --history</div>
      <Link href="/" className="hist-footer__link">
        &larr; Back to void --news
      </Link>
    </footer>
  );
}
