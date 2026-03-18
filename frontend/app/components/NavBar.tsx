"use client";

import type { Section } from "../lib/types";
import ThemeToggle from "./ThemeToggle";

interface NavBarProps {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead
   Desktop: top bar with "void --news" in Playfair, section tabs, theme toggle
   Mobile: minimal top bar with logo, bottom nav with tabs
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
          {/* Masthead */}
          <div
            style={{
              fontFamily: "var(--font-editorial)",
              fontSize: "var(--text-lg)",
              fontWeight: 700,
              letterSpacing: "-0.01em",
              color: "var(--fg-primary)",
              userSelect: "none",
              lineHeight: 1,
            }}
          >
            void{" "}
            <span
              style={{
                fontFamily: "var(--font-data)",
                fontWeight: 400,
                fontSize: "0.85em",
              }}
            >
              --news
            </span>
          </div>

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
                {section === "world" ? "World" : "US"}
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
            {section === "world" ? "World" : "US"}
          </button>
        ))}
      </nav>
    </>
  );
}
