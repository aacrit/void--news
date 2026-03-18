"use client";

import { useState, useEffect } from "react";
import { Sun, Moon } from "@phosphor-icons/react";

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
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: mode === "light" ? 1 : 0,
          transform: mode === "light" ? "rotate(0deg)" : "rotate(-90deg)",
          transition: `opacity var(--dur-morph) var(--ease-out), transform var(--dur-morph) var(--ease-out)`,
        }}
      >
        <Sun size={18} weight="light" />
      </span>

      {/* Moon icon (dark mode) */}
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: mode === "dark" ? 1 : 0,
          transform: mode === "dark" ? "rotate(0deg)" : "rotate(90deg)",
          transition: `opacity var(--dur-morph) var(--ease-out), transform var(--dur-morph) var(--ease-out)`,
        }}
      >
        <Moon size={18} weight="light" />
      </span>
    </button>
  );
}
