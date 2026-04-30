"use client";

import Link from "next/link";

/* ---------------------------------------------------------------------------
   PageToggle — Layer 3 (Background) text link toggling Feed ↔ Sources.
   No pills, no icons. Plain structural text with departure arrow on hover.
   --------------------------------------------------------------------------- */

interface PageToggleProps {
  activePage: "feed" | "sources";
}

export default function PageToggle({ activePage }: PageToggleProps) {
  const isFeed = activePage === "feed";
  const href = isFeed ? "/sources" : "/";
  const label = isFeed ? "Sources" : "News Feed";
  const brandLabel = isFeed ? "void --sources" : "void --news";

  return (
    <Link href={href} className="nav-page" aria-label={`Go to ${label}`} title={brandLabel}>
      {label}
    </Link>
  );
}
