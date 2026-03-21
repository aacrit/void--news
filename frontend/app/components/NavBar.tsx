"use client";

import Link from "next/link";
import type { Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import EditionIcon from "./EditionIcon";
import { getEditionTimeOfDay, getEditionTimestamp } from "../lib/utils";

interface NavBarProps {
  activeEdition: Edition;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead (single compact row)
   Desktop: Logo (32px) | Edition tabs | Dateline (tertiary) | Sources | Theme
   Mobile:  Logo (22px) | Sources + Theme (top bar) | Edition tabs (bottom nav)
   --------------------------------------------------------------------------- */

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getEditionHref(slug: Edition): string {
  if (slug === "world") return "/";
  return `/${slug}`;
}

export default function NavBar({ activeEdition }: NavBarProps) {
  return (
    <>
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          {/* Logo — P1 */}
          <div className="nav-left">
            <Link href="/" aria-label="void --news — home" className="nav-logo si-hoverable">
              {/* Desktop: full combination mark at 32px */}
              <span className="nav-logo-desktop">
                <LogoFull height={32} />
              </span>
              {/* Mobile: same full logo at 22px */}
              <span className="nav-logo-mobile">
                <LogoFull height={22} />
              </span>
            </Link>
          </div>

          {/* Edition tabs — P1 primary navigation */}
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
          </div>

          {/* Dateline — P3 tertiary, desktop only, fills remaining flex space */}
          <span className="nav-dateline-inline" aria-hidden="true">
            {getEditionTimeOfDay(activeEdition)} Edition
            <span className="nav-dateline-inline__sep">&middot;</span>
            {formatDateCompact()}
            <span className="nav-dateline-inline__sep">&middot;</span>
            <span className="nav-dateline-inline__time">{getEditionTimestamp(activeEdition)}</span>
          </span>

          {/* Utility actions — P2 */}
          <div className="nav-right">
            <PageToggle activePage="feed" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

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
