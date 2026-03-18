"use client";

import type { Section } from "../lib/types";
import { Globe, Flag } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import ScaleIcon from "./ScaleIcon";

interface NavBarProps {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
}

/** Full combination mark — Weighing Scale icon + "void --news" wordmark */
function LogoFull({ height = 28 }: { height?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 320 40"
      fill="currentColor"
      role="img"
      aria-hidden="true"
      style={{ height, width: "auto", display: "block", flexShrink: 0 }}
    >
      {/* Weighing Scale Icon — scaled to ~24px high, uses shared si- classes */}
      <g transform="translate(0,8) scale(0.75)" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {/* Fulcrum triangle */}
        <path d="M16,4 L13,9 L19,9 Z"/>
        {/* Animated beam group */}
        <g className="si-beam--idle">
          {/* Beam */}
          <line x1="4" y1="9" x2="28" y2="9"/>
          {/* Left suspension + pan */}
          <path d="M7,9 L5,18 L11,18 L9,9"/>
          {/* Right suspension + pan */}
          <path d="M23,9 L21,18 L27,18 L25,9"/>
        </g>
        {/* Center post */}
        <line x1="16" y1="9" x2="16" y2="27"/>
        {/* Base */}
        <line x1="12" y1="27" x2="20" y2="27"/>
      </g>

      {/* Wordmark */}
      <g transform="translate(36,2)">
        {/* "void" — serif letterforms, bold, condensed */}
        <polygon points="0,4 5.5,4 14,28 22.5,4 28,4 16.5,36 11.5,36" />
        <path d="M34,20C34,10.5 39.5,3 48,3C56.5,3 62,10.5 62,20C62,29.5 56.5,37 48,37C39.5,37 34,29.5 34,20ZM40,20C40,27.5 43,32 48,32C53,32 56,27.5 56,20C56,12.5 53,8 48,8C43,8 40,12.5 40,20Z" />
        <rect x="69" y="2" width="5" height="5" rx="0.8" />
        <rect x="69.5" y="11" width="4" height="25" rx="0.5" />
        <path d="M82,20C82,10.5 87,3 94,3C97,3 100,4.5 102,7.5L102,0L107,0L107,36L102,36L102,32.5C100,35.5 97,37 94,37C87,37 82,29.5 82,20ZM88,20C88,27.5 90.8,32 95,32C98,32 100.5,29.5 102,26L102,14C100.5,10.5 98,8 95,8C90.8,8 88,12.5 88,20Z" />

        {/* "--news" — monospace letterforms, regular weight */}
        <rect x="122" y="17.5" width="10" height="3" rx="0.5" />
        <rect x="134" y="17.5" width="10" height="3" rx="0.5" />
        <path d="M156,12L159.2,12L159.2,16C161,13 163.5,11 167,11C170,11 172,12.5 173.2,14.8C174,16.5 174,18.5 174,21L174,36L170.8,36L170.8,21.5C170.8,18.5 170.5,17 169.5,15.8C168.5,14.6 167,14 165,14C162.5,14 160.8,15.5 159.8,17.5C159.2,18.8 159.2,20 159.2,21.5L159.2,36L156,36Z" />
        <path d="M182,23.5C182,17.5 185.5,11 192,11C198.5,11 201.5,17 201.5,23L201.5,24.5L185.5,24.5C185.8,29 188.5,33 192.5,33C195.5,33 197.5,31 198.8,29L201,30.5C199,33.5 196,36 192,36C186,36 182,30 182,23.5ZM185.5,22L198,22C197.5,17.5 195.5,14 192,14C188.5,14 186.2,17.5 185.5,22Z" />
        <path d="M208,12L211.5,12L217,30L222.5,12L225.5,12L231,30L236.5,12L240,12L232.5,36L229,36L223.5,18L218,36L214.5,36Z" />
        <path d="M247,28C247,24.5 249,22.5 252,21.5L256.5,20C259,19 260,17.8 260,16C260,13.8 258,12 255,12C252,12 250,13.5 249,15.5L246.5,14C248,11.5 251,9.5 255,9.5C260,9.5 263.5,12.5 263.5,16.5C263.5,19.5 261.5,21.5 258.5,22.5L254,24C251.5,25 250.5,26.5 250.5,28.5C250.5,31 252.5,33 255.5,33C258,33 260,31.5 261,29.5L263.2,31C261.5,34 258.5,36 255,36C250.5,36 247,32.5 247,28Z" />
      </g>
    </svg>
  );
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead
   Desktop: top bar with full logo (icon + wordmark), section tabs, theme toggle
   Mobile: minimal top bar with icon only, bottom nav with section tabs
   Thin bottom border (newspaper rule)
   --------------------------------------------------------------------------- */

export default function NavBar({ activeSection, onSectionChange }: NavBarProps) {
  return (
    <>
      {/* Desktop / Mobile Top Nav */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: "var(--z-nav)",
          backgroundColor: "var(--bg-primary)",
          borderBottom: "var(--rule-thin)",
          transition: "background-color var(--dur-morph) var(--ease-out)",
        }}
      >
        <nav
          style={{
            maxWidth: "1280px",
            margin: "0 auto",
            padding: "var(--space-3) var(--space-7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
          aria-label="Main navigation"
        >
          {/* Masthead — inline SVG logo (currentColor for theme support) */}
          <a
            href="/"
            aria-label="void --news — home"
            style={{
              display: "flex",
              alignItems: "center",
              textDecoration: "none",
              color: "var(--fg-primary)",
            }}
          >
            {/* Desktop: full combination mark (icon + wordmark) */}
            <span className="nav-logo-desktop" style={{ display: "block" }}>
              <LogoFull height={28} />
            </span>
            {/* Mobile: icon only (weighing scale mark) */}
            <span className="nav-logo-mobile" style={{ display: "none" }}>
              <ScaleIcon animation="idle" size={24} />
            </span>
          </a>

          {/* Section tabs — desktop */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 0,
            }}
            className="nav-tabs-desktop"
          >
            {(["world", "us"] as Section[]).map((section) => (
              <button
                key={section}
                onClick={() => onSectionChange(section)}
                aria-current={activeSection === section ? "page" : undefined}
                aria-pressed={activeSection === section}
                style={{
                  fontFamily: "var(--font-structural)",
                  fontSize: "var(--text-sm)",
                  fontWeight: activeSection === section ? 600 : 400,
                  letterSpacing: "0.02em",
                  textTransform: "uppercase",
                  color:
                    activeSection === section
                      ? "var(--fg-primary)"
                      : "var(--fg-tertiary)",
                  padding: "var(--space-2) var(--space-4)",
                  borderBottom:
                    activeSection === section
                      ? "2px solid var(--fg-primary)"
                      : "2px solid transparent",
                  transition:
                    "color var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
                  minHeight: 44,
                  minWidth: 44,
                }}
              >
                <span style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
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

          {/* Theme toggle */}
          <ThemeToggle />
        </nav>
      </header>

      {/* Mobile bottom nav */}
      <nav
        className="nav-bottom-mobile"
        aria-label="Section navigation"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: "var(--z-nav)",
          backgroundColor: "var(--bg-primary)",
          borderTop: "var(--rule-thin)",
          display: "none", /* shown via media query in page styles */
          padding: "var(--space-2) var(--space-5)",
          justifyContent: "center",
          gap: "var(--space-5)",
          transition: "background-color var(--dur-morph) var(--ease-out)",
        }}
      >
        {(["world", "us"] as Section[]).map((section) => (
          <button
            key={`mobile-${section}`}
            onClick={() => onSectionChange(section)}
            aria-pressed={activeSection === section}
            style={{
              fontFamily: "var(--font-structural)",
              fontSize: "var(--text-sm)",
              fontWeight: activeSection === section ? 600 : 400,
              letterSpacing: "0.02em",
              textTransform: "uppercase",
              color:
                activeSection === section
                  ? "var(--fg-primary)"
                  : "var(--fg-tertiary)",
              padding: "var(--space-3) var(--space-5)",
              borderTop:
                activeSection === section
                  ? "2px solid var(--fg-primary)"
                  : "2px solid transparent",
              minHeight: 44,
              minWidth: 44,
              transition:
                "color var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
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
