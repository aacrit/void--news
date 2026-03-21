"use client";

import Link from "next/link";
import type { Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import { Globe, Flag } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import { getEditionTimeOfDay, getEditionTimestamp } from "../lib/utils";

interface NavBarProps {
  activeEdition: Edition;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead
   Desktop: LogoFull (36px) + full dateline, edition tabs, theme toggle
   Mobile:  LogoFull (22px) + edition/date, bottom nav for editions
   --------------------------------------------------------------------------- */

function formatDateFull(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function getEditionHref(slug: Edition): string {
  if (slug === "world") return "/";
  return `/${slug}`;
}

/* Ashoka Chakra — circle + 12 spokes, stroke only. Cleanly readable at 14–18px. */
function IndiaIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="2" strokeWidth="1" />
      {Array.from({ length: 12 }, (_, i) => {
        const angle = (i * 30 * Math.PI) / 180;
        const x1 = 12 + 2.4 * Math.cos(angle);
        const y1 = 12 + 2.4 * Math.sin(angle);
        const x2 = 12 + 9 * Math.cos(angle);
        const y2 = 12 + 9 * Math.sin(angle);
        return (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth="1" />
        );
      })}
    </svg>
  );
}

function EditionIcon({ slug, size }: { slug: Edition; size: number }) {
  if (slug === "world") return <Globe size={size} weight="light" aria-hidden="true" />;
  if (slug === "us") return <Flag size={size} weight="light" aria-hidden="true" />;
  if (slug === "india") return <IndiaIcon size={size} />;
  return null;
}

export default function NavBar({ activeEdition }: NavBarProps) {
  const activeEditionMeta = EDITIONS.find((e) => e.slug === activeEdition) ?? EDITIONS[0];

  return (
    <>
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          <div className="nav-left">
            <Link href="/" aria-label="void --news — home" className="nav-logo si-hoverable">
              {/* Desktop: full combination mark at 36px */}
              <span className="nav-logo-desktop">
                <LogoFull height={36} />
              </span>
              {/* Mobile: same full logo at 22px — brand stays visible */}
              <span className="nav-logo-mobile">
                <LogoFull height={22} />
              </span>
            </Link>

            {/* Dateline — edition name + time of day + date.
                Uses nav-dateline-row__text class (visible) instead of
                legacy nav-dateline (display:none). */}
            <span className="nav-dateline-row__text" style={{ display: "none" }}>
              {/* Desktop: rendered in the dateline row below instead */}
            </span>
          </div>

          <div className="nav-tabs" role="tablist" aria-label="Edition selector">
            {EDITIONS.map((edition) => (
              <Link
                key={edition.slug}
                href={getEditionHref(edition.slug)}
                role="tab"
                aria-selected={activeEdition === edition.slug}
                aria-current={activeEdition === edition.slug ? "page" : undefined}
                className={`nav-tab${activeEdition === edition.slug ? " nav-tab--active" : ""}`}
              >
                <span className="nav-tab__inner">
                  <EditionIcon slug={edition.slug} size={14} />
                  {edition.label}
                </span>
              </Link>
            ))}

            {/* Section divider */}
            <span className="nav-tabs__divider" aria-hidden="true" />
          </div>

          <div className="nav-right">
            <PageToggle activePage="feed" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

      {/* Dateline row — thin data strip below masthead (desktop only, hidden on mobile via CSS) */}
      <div className="nav-dateline-row">
        <div className="nav-dateline-row__inner">
          {/* Edition badge */}
          <span className="nav-dateline-row__badge">
            {activeEditionMeta.label}
          </span>
          {/* Time-of-day badge */}
          <span className="nav-dateline-row__badge">
            {getEditionTimeOfDay(activeEdition)}
          </span>
          {/* "Edition" label */}
          <span className="nav-dateline-row__text">
            Edition
          </span>
          {/* Separator + full date + regional timestamp */}
          <span className="nav-dateline-row__text nav-dateline-row__date">
            &middot; {formatDateFull()}
            <span className="nav-dateline-row__timestamp">
              &middot; {getEditionTimestamp(activeEdition)}
            </span>
          </span>
        </div>
      </div>

      {/* Mobile bottom nav — all 3 editions */}
      <nav className="nav-bottom" aria-label="Edition navigation">
        {EDITIONS.map((edition) => (
          <Link
            key={`mobile-${edition.slug}`}
            href={getEditionHref(edition.slug)}
            aria-current={activeEdition === edition.slug ? "page" : undefined}
            className={`nav-bottom-tab${activeEdition === edition.slug ? " nav-bottom-tab--active" : ""}`}
          >
            <span className="nav-tab__inner">
              <EditionIcon slug={edition.slug} size={18} />
              {edition.label}
            </span>
          </Link>
        ))}
      </nav>
    </>
  );
}
