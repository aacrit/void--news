"use client";

import Link from "next/link";
import type { Section } from "../lib/types";
import { Globe, Flag } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import LogoFull from "./LogoFull";
import LogoIcon from "./LogoIcon";

interface NavBarProps {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead
   Desktop: LogoFull (icon + wordmark, bigger), section tabs, theme toggle
   Mobile: LogoIcon (icon only), bottom nav with section tabs
   --------------------------------------------------------------------------- */

export default function NavBar({ activeSection, onSectionChange }: NavBarProps) {
  return (
    <>
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          <Link href="/" aria-label="void --news — home" className="nav-logo si-hoverable">
            {/* Desktop: full combination mark (icon + wordmark) — bigger */}
            <span className="nav-logo-desktop">
              <LogoFull height={36} />
            </span>
            {/* Mobile: icon only */}
            <span className="nav-logo-mobile">
              <LogoIcon size={28} animation="idle" />
            </span>
          </Link>

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
          </div>

          <ThemeToggle />
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
                <Globe size={14} weight="light" aria-hidden="true" />
              ) : (
                <Flag size={14} weight="light" aria-hidden="true" />
              )}
              {section === "world" ? "World" : "US"}
            </span>
          </button>
        ))}
      </nav>
    </>
  );
}
