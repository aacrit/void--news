"use client";

import { useState, useSyncExternalStore } from "react";
import { Sun, Moon } from "@phosphor-icons/react";

/* ---------------------------------------------------------------------------
   ThemeToggle — Sun/Moon icon toggle
   --------------------------------------------------------------------------- */

function getThemeFromStorage(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  const stored = localStorage.getItem("void-news-theme") as "light" | "dark" | null;
  if (stored) return stored;
  return "dark";
}

const subscribe = () => () => {};

export default function ThemeToggle() {
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);
  const [mode, setMode] = useState<"light" | "dark">(getThemeFromStorage);

  const toggle = () => {
    const next = mode === "light" ? "dark" : "light";
    setMode(next);
    document.documentElement.setAttribute("data-mode", next);
    localStorage.setItem("void-news-theme", next);
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
