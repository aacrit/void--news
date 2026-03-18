"use client";

import { useState, useEffect } from "react";

/* ---------------------------------------------------------------------------
   ThemeToggle — Sun/Moon icon toggle
   Persists to localStorage, toggles data-mode on <html>.
   Cross-fade transition, no layout shift.
   --------------------------------------------------------------------------- */

export default function ThemeToggle() {
  const [mode, setMode] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("void-news-theme") as
      | "light"
      | "dark"
      | null;
    if (stored) {
      setMode(stored);
      document.documentElement.setAttribute("data-mode", stored);
    } else if (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      setMode("dark");
      document.documentElement.setAttribute("data-mode", "dark");
    } else {
      document.documentElement.setAttribute("data-mode", "light");
    }
  }, []);

  const toggle = () => {
    const next = mode === "light" ? "dark" : "light";
    setMode(next);
    document.documentElement.setAttribute("data-mode", next);
    localStorage.setItem("void-news-theme", next);
  };

  if (!mounted) {
    return (
      <button
        aria-label="Toggle theme"
        style={{
          width: 36,
          height: 36,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: 0,
        }}
      />
    );
  }

  return (
    <button
      onClick={toggle}
      aria-label={`Switch to ${mode === "light" ? "dark" : "light"} mode`}
      title={`Switch to ${mode === "light" ? "dark" : "light"} mode`}
      style={{
        width: 36,
        height: 36,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "var(--radius-md)",
        transition: "background-color var(--dur-fast) var(--ease-out)",
        position: "relative",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.backgroundColor =
          "var(--bg-secondary)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
      }}
    >
      {/* Sun icon (light mode) */}
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{
          position: "absolute",
          opacity: mode === "light" ? 1 : 0,
          transform: mode === "light" ? "rotate(0deg)" : "rotate(-90deg)",
          transition: `opacity var(--dur-morph) var(--ease-out), transform var(--dur-morph) var(--ease-out)`,
        }}
      >
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
      </svg>

      {/* Moon icon (dark mode) */}
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{
          position: "absolute",
          opacity: mode === "dark" ? 1 : 0,
          transform: mode === "dark" ? "rotate(0deg)" : "rotate(90deg)",
          transition: `opacity var(--dur-morph) var(--ease-out), transform var(--dur-morph) var(--ease-out)`,
        }}
      >
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
      </svg>
    </button>
  );
}
