"use client";

import Link from "next/link";
import type { Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import { Globe, Flag } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";

export type ViewMode = "facts" | "opinion";

interface NavBarProps {
  activeEdition: Edition;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead
   Desktop: LogoFull (36px) + full dateline, edition tabs, theme toggle
   Mobile:  LogoFull (22px) + edition/date, bottom nav for editions
   --------------------------------------------------------------------------- */

function getEditionLabel(): string {
  const hour = new Date().getHours();
  return hour < 12 ? "Morning Edition" : "Evening Edition";
}

function formatDateFull(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function getEditionHref(slug: Edition): string {
  if (slug === "world") return "/";
  return `/${slug}`;
}

function EditionIcon({ slug, size }: { slug: Edition; size: number }) {
  if (slug === "world") return <Globe size={size} weight="light" aria-hidden="true" />;
  if (slug === "us") return <Flag size={size} weight="light" aria-hidden="true" />;
  return null;
}

export default function NavBar({ activeEdition, viewMode, onViewModeChange }: NavBarProps) {
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

            {/* Dateline — edition name + time of day + date */}
            <span className="nav-dateline">
              {/* Desktop: full edition + date */}
              <span className="nav-dateline__full">
                {activeEditionMeta.label} Edition &middot; {getEditionLabel()} &middot; {formatDateFull()}
              </span>
              {/* Mobile: edition + compact date */}
              <span className="nav-dateline__medium">
                {activeEditionMeta.label} Edition &middot; {formatDateCompact()}
              </span>
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

            {/* Facts / Opinion toggle */}
            <div
              className="view-mode-toggle"
              role="group"
              aria-label="Content type filter"
            >
              <button
                className={`view-mode-toggle__btn${viewMode === "facts" ? " view-mode-toggle__btn--active" : ""}`}
                onClick={() => onViewModeChange("facts")}
                aria-pressed={viewMode === "facts"}
              >
                Facts
              </button>
              <button
                className={`view-mode-toggle__btn${viewMode === "opinion" ? " view-mode-toggle__btn--active" : ""}`}
                onClick={() => onViewModeChange("opinion")}
                aria-pressed={viewMode === "opinion"}
              >
                Opinion
              </button>
            </div>
          </div>

          <div className="nav-right">
            <PageToggle activePage="feed" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

      {/* Mobile bottom nav — all 5 editions */}
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
