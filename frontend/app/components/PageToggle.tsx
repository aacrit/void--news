"use client";

import Link from "next/link";
import { Newspaper, ListBullets } from "@phosphor-icons/react";

/* ---------------------------------------------------------------------------
   PageToggle — Persistent pill that toggles between News Feed and Sources.
   Sits next to the theme toggle in the nav bar. Shows the *other* page
   as the label so users know where they'll go.
   --------------------------------------------------------------------------- */

interface PageToggleProps {
  /** Which page is currently active */
  activePage: "feed" | "sources";
}

export default function PageToggle({ activePage }: PageToggleProps) {
  const isFeed = activePage === "feed";
  const href = isFeed ? "/sources" : "/";
  const label = isFeed ? "Sources" : "News Feed";
  const brandLabel = isFeed ? "void --sources" : "void --news";
  const Icon = isFeed ? ListBullets : Newspaper;

  return (
    <Link href={href} className="page-toggle" aria-label={`Go to ${label}`} title={brandLabel}>
      <Icon size={14} weight="regular" aria-hidden="true" />
      <span className="page-toggle__label">{label}</span>
    </Link>
  );
}
