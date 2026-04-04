"use client";

import { useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { hapticMicro } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";

/* ---------------------------------------------------------------------------
   MobileTabBar — Persistent bottom tab bar (mobile only, <768px).
   4 tabs: Feed, Sources, Weekly, More.
   "More" toggles MobileSidePanel (callback from parent).
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileTabBarProps {
  onMoreTap: () => void;
  moreOpen: boolean;
}

/* ── SVG Icons — 20x20, currentColor ── */

function FeedIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="14" height="14" rx="2" />
      <line x1="3" y1="8" x2="17" y2="8" />
      <line x1="8" y1="8" x2="8" y2="17" />
    </svg>
  );
}

function SourcesIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <circle cx="4" cy="10" r="2" opacity="0.6" />
      <circle cx="8" cy="10" r="2" opacity="0.8" />
      <circle cx="12" cy="10" r="2" />
      <circle cx="16" cy="10" r="2" opacity="0.8" />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="3" y1="5" x2="17" y2="5" />
      <line x1="3" y1="10" x2="17" y2="10" />
      <line x1="3" y1="15" x2="17" y2="15" />
    </svg>
  );
}

const TABS = [
  { key: "feed", label: "feed", Icon: FeedIcon, href: "/" },
  { key: "sources", label: "sources", Icon: SourcesIcon, href: "/sources" },
  { key: "more", label: "more", Icon: MoreIcon, href: null },
] as const;

export default function MobileTabBar({ onMoreTap, moreOpen }: MobileTabBarProps) {
  const pathname = usePathname();

  const isActive = useCallback(
    (key: string): boolean => {
      // Strip basePath prefix for comparison
      const p = pathname.replace(BASE_PATH, "") || "/";
      switch (key) {
        case "feed":
          return p === "/" || p === "" || /^\/(world|us|europe|south-asia)\/?$/.test(p);
        case "sources":
          return p.startsWith("/sources");
        case "more":
          return moreOpen;
        default:
          return false;
      }
    },
    [pathname, moreOpen]
  );

  return (
    <nav className="mtb" aria-label="Mobile navigation">
      {TABS.map(({ key, label, Icon, href }) => {
        const active = isActive(key);
        if (href) {
          return (
            <Link
              key={key}
              href={href}
              className={`mtb__tab${active ? " mtb__tab--active" : ""}`}
              aria-current={active ? "page" : undefined}
              onClick={() => hapticMicro()}
            >
              <Icon />
              <span className="mtb__label">{label}</span>
            </Link>
          );
        }
        return (
          <button
            key={key}
            type="button"
            className={`mtb__tab${active ? " mtb__tab--active" : ""}`}
            aria-expanded={moreOpen}
            aria-label="More options"
            onClick={() => {
              hapticMicro();
              onMoreTap();
            }}
          >
            <Icon />
            <span className="mtb__label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
