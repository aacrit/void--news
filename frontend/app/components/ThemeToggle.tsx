"use client";

import { useState, useSyncExternalStore } from "react";
import { Sun, Moon } from "@phosphor-icons/react";
import { hapticMedium } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   ThemeToggle — Sun/Moon icon toggle
   --------------------------------------------------------------------------- */

function getThemeFromStorage(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem("void-news-theme") as "light" | "dark" | null;
  if (stored) return stored;
  // Match the inline script's logic: respect system preference on first visit.
  // The inline script in layout.tsx sets data-mode before React hydrates, so
  // reading the DOM attribute is the fastest path. matchMedia is the fallback
  // if the DOM attribute hasn't been set yet (SSR / edge case).
  const domMode = document.documentElement.getAttribute("data-mode");
  if (domMode === "light" || domMode === "dark") return domMode;
  if (window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
  return "dark";
}

const subscribe = () => () => {};

/* The masthead's paper as a custom property: read the moment data-mode flips,
   before the background-color transition has moved. */
function mastheadPaper(): string {
  const nav = document.querySelector<HTMLElement>(".nav-header");
  const v = nav ? getComputedStyle(nav).getPropertyValue("--nav-paper").trim() : "";
  return v || getComputedStyle(document.documentElement).getPropertyValue("--bg-primary").trim();
}

/* Any CSS colour to #RRGGBB, through the engine's own parser. */
function resolveHex(value: string): string | null {
  if (!value) return null;
  const probe = document.createElement("span");
  probe.style.color = value;
  document.body.appendChild(probe);
  const rgb = getComputedStyle(probe).color;
  probe.remove();
  const m = rgb.match(/\d+(\.\d+)?/g);
  if (!m || m.length < 3) return null;
  return "#" + m.slice(0, 3).map((n) => Math.round(Number(n)).toString(16).padStart(2, "0")).join("").toUpperCase();
}

export default function ThemeToggle() {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const [mode, setMode] = useState<"light" | "dark">(getThemeFromStorage);

  const toggle = () => {
    hapticMedium();
    const next = mode === "light" ? "dark" : "light";
    setMode(next);
    document.documentElement.setAttribute("data-mode", next);
    localStorage.setItem("void-news-theme", next);

    // The status bar follows the masthead. The bar is painted with --nav-paper
    // (components.css), which the section skins override, so History reads
    // its archival paper here and Weekly its magazine stock, not a site literal.
    const themeColor = resolveHex(mastheadPaper()) ?? (next === "light" ? "#F0EBDD" : "#1C1A17");
    document.querySelectorAll('meta[name="theme-color"]').forEach((m) => m.setAttribute("content", themeColor));

    // Golden hour pulse — cinematic color grade flash on theme switch.
    // Targets .page-main (not .page-container) because the color grade filter
    // lives on .page-main. Applying filter to .page-container would create a
    // containing block that breaks position:fixed children (AudioPlayer, DeepDive).
    // Golden hour pulse on both page-main AND nav-header — the dissolve
    // warms the entire visible frame, not just the content area. Scene 8
    // spec: "paper is slower than ink, both are slower than light."
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!prefersReducedMotion) {
      const targets = document.querySelectorAll('.page-main, .nav-header');
      targets.forEach(el => el.classList.add('cin-golden-hour'));
      setTimeout(() => targets.forEach(el => el.classList.remove('cin-golden-hour')), 700);
    }
  };

  if (!mounted) {
    return (
      <button aria-label="Toggle theme" className="theme-toggle theme-toggle--placeholder">
        <span aria-hidden="true" className="theme-toggle__icon">
          <Sun size={18} weight="light" />
        </span>
      </button>
    );
  }

  return (
    <button
      onClick={toggle}
      aria-label={`Switch to ${mode === "light" ? "dark" : "light"} mode`}
      title={`Switch to ${mode === "light" ? "dark" : "light"} mode`}
      className="theme-toggle"
    >
      <span
        aria-hidden="true"
        className={`theme-toggle__icon${mode !== "light" ? " theme-toggle__icon--hidden theme-toggle__icon--sun-hidden" : ""}`}
      >
        <Sun size={18} weight="light" />
      </span>
      <span
        aria-hidden="true"
        className={`theme-toggle__icon${mode !== "dark" ? " theme-toggle__icon--hidden theme-toggle__icon--moon-hidden" : ""}`}
      >
        <Moon size={18} weight="light" />
      </span>
    </button>
  );
}
