"use client";

import Link from "next/link";
import type { Section } from "../lib/types";
import { Globe, Flag } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";

export type ViewMode = "facts" | "opinion";

interface NavBarProps {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead
   Desktop: LogoFull (36px) + full dateline, section tabs, theme toggle
   Mobile:  LogoFull (22px) + edition/date, bottom nav for sections
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

export default function NavBar({ activeSection, onSectionChange, viewMode, onViewModeChange }: NavBarProps) {
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

            {/* Dateline — newspaper date + edition */}
            <span className="nav-dateline">
              {/* Desktop: full edition + date */}
              <span className="nav-dateline__full">
                {getEditionLabel()} &middot; {formatDateFull()}
              </span>
              {/* Mobile: edition + compact date */}
              <span className="nav-dateline__medium">
                {getEditionLabel()} &middot; {formatDateCompact()}
              </span>
            </span>
          </div>

          <div className="nav-tabs">
            {(["world", "us"] as Section[]).map((section) => (
              <button
                key={section}
                onClick={() => onSectionChange(section)}
                aria-current={activeSection === section ? "page" : undefined}
                className={`nav-tab${activeSection === section ? " nav-tab--active" : ""}`}
              >
                <span className="nav-tab__inner">
                  {section === "world" ? (
                    <Globe size={14} weight="light" aria-hidden="true" />
                  ) : (
                    <Flag size={14} weight="light" aria-hidden="true" />
                  )}
                  {section === "world" ? "World" : "US"}
                </span>
              </button>
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

      {/* Mobile bottom nav */}
      <nav className="nav-bottom" aria-label="Section navigation">
        {(["world", "us"] as Section[]).map((section) => (
          <button
            key={`mobile-${section}`}
            onClick={() => onSectionChange(section)}
            aria-pressed={activeSection === section}
            className={`nav-bottom-tab${activeSection === section ? " nav-bottom-tab--active" : ""}`}
          >
            <span className="nav-tab__inner">
              {section === "world" ? (
                <Globe size={18} weight="light" aria-hidden="true" />
              ) : (
                <Flag size={18} weight="light" aria-hidden="true" />
              )}
              {section === "world" ? "World" : "US"}
            </span>
          </button>
        ))}
      </nav>
    </>
  );
}
