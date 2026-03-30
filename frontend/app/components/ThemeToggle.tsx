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

export default function ThemeToggle() {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const [mode, setMode] = useState<"light" | "dark">(getThemeFromStorage);

  const toggle = () => {
    hapticMedium();
    const next = mode === "light" ? "dark" : "light";
    setMode(next);
    document.documentElement.setAttribute("data-mode", next);
    localStorage.setItem("void-news-theme", next);

    // Golden hour pulse — cinematic color grade flash on theme switch.
    // Targets .page-main (not .page-container) because the color grade filter
    // lives on .page-main. Applying filter to .page-container would create a
    // containing block that breaks position:fixed children (AudioPlayer, DeepDive).
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const main = document.querySelector('.page-main');
    if (!prefersReducedMotion && main) {
      main.classList.add('cin-golden-hour');
      setTimeout(() => main.classList.remove('cin-golden-hour'), 700);
    }
  };

  if (!mounted) {
    return <button aria-label="Toggle theme" className="theme-toggle theme-toggle--placeholder" />;
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
