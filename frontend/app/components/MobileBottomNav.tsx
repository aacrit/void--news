"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Edition, Category, LeanChip } from "../lib/types";
import { EDITIONS } from "../lib/types";
import EditionIcon from "./EditionIcon";
import { hapticMicro, hapticLight } from "../lib/haptics";

interface MobileBottomNavProps {
  activeEdition: Edition;
  onEditionChange: (edition: Edition) => void;
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
  activeCategory: "All" | Category;
  onCategoryChange: (cat: "All" | Category) => void;
}

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

type OpenPanel = null | "edition" | "lean" | "topic";

/* ---------------------------------------------------------------------------
   MobileBottomNav — 3 expandable CTA buttons at bottom (mobile only).

   [Edition ▾]  [Perspective ▾]  [Topic ▾]

   Each button shows current selection. Tapping expands an upward panel
   with options. Only one panel open at a time.
   Hidden on desktop via CSS (display: none above 768px).
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeEdition,
  onEditionChange,
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
}: MobileBottomNavProps) {
  const [openPanel, setOpenPanel] = useState<OpenPanel>(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const editionPanelRef = useRef<HTMLDivElement>(null);
  const leanPanelRef = useRef<HTMLDivElement>(null);
  const topicPanelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  // Detect reduced-motion preference and keep it in sync
  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mql.matches);
    const onChange = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  const toggle = useCallback((panel: OpenPanel) => {
    hapticLight();
    setOpenPanel((prev) => {
      const next = prev === panel ? null : panel;
      return next;
    });
  }, []);

  const handleEditionTap = (edition: Edition) => {
    hapticMicro();
    onEditionChange(edition);
    // URL sync handled by HomeContent useEffect — single source of truth
    setOpenPanel(null);
  };

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
    setOpenPanel(null);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setOpenPanel(null);
  };

  // Focus management: move focus into panel when opened, return to trigger on close
  useEffect(() => {
    if (openPanel) {
      // Save the element that triggered the panel open
      triggerRef.current = document.activeElement as HTMLButtonElement | null;

      const panelMap: Record<string, React.RefObject<HTMLDivElement | null>> = {
        edition: editionPanelRef,
        lean: leanPanelRef,
        topic: topicPanelRef,
      };
      const panelEl = panelMap[openPanel]?.current;
      if (panelEl) {
        // Delay focus until panel transition starts rendering
        requestAnimationFrame(() => {
          const firstInteractive = panelEl.querySelector<HTMLElement>("button, a, input");
          firstInteractive?.focus();
        });
      }
    } else {
      // Panel closed: return focus to the trigger button
      if (triggerRef.current && typeof triggerRef.current.focus === "function") {
        triggerRef.current.focus();
        triggerRef.current = null;
      }
    }
  }, [openPanel]);

  // Close on Escape key — return focus to trigger button
  useEffect(() => {
    if (!openPanel) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setOpenPanel(null);
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [openPanel]);

  // Close on outside tap
  useEffect(() => {
    if (!openPanel) return;
    const close = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [openPanel]);

  const editionLabel = EDITIONS.find((e) => e.slug === activeEdition)?.label ?? "World";
  const leanLabel = activeLean === "All" ? "All" : activeLean;
  const topicLabel = activeCategory === "All" ? "All Topics" : activeCategory;

  return (
    <nav className="mob-nav anim-cold-open-nav" aria-label="Mobile navigation" ref={navRef}>
      {/* Backdrop — fades in when any panel is open */}
      <div
        className="mob-nav__backdrop"
        style={{
          opacity: openPanel ? 1 : 0,
          pointerEvents: openPanel ? "auto" : "none",
          transition: prefersReducedMotion
            ? "none"
            : openPanel
              ? "opacity 150ms var(--ease-out)"
              : "opacity 120ms var(--ease-out)",
        }}
        onClick={() => setOpenPanel(null)}
        aria-hidden="true"
      />

      {/* Edition panel */}
      <div
        ref={editionPanelRef}
        className="mob-nav__panel"
        role="menu"
        aria-label="Edition"
        style={{
          transform: openPanel === "edition" ? "translateY(0)" : "translateY(100%)",
          opacity: openPanel === "edition" ? 1 : 0,
          transition: prefersReducedMotion
            ? "none"
            : openPanel === "edition"
              ? "transform 250ms var(--spring-snappy), opacity 200ms var(--ease-out)"
              : "transform 180ms var(--ease-out), opacity 120ms var(--ease-out)",
          pointerEvents: openPanel === "edition" ? "auto" : "none",
        }}
      >
        {EDITIONS.map((ed) => (
          <button
            key={ed.slug}
            role="menuitem"
            aria-current={activeEdition === ed.slug ? "page" : undefined}
            className={`mob-nav__opt${activeEdition === ed.slug ? " mob-nav__opt--active" : ""}`}
            onClick={() => handleEditionTap(ed.slug)}
          >
            <EditionIcon slug={ed.slug} size={12} />
            {ed.label}
          </button>
        ))}
      </div>

      {/* Perspective panel */}
      <div
        ref={leanPanelRef}
        className="mob-nav__panel"
        role="menu"
        aria-label="Perspective"
        style={{
          transform: openPanel === "lean" ? "translateY(0)" : "translateY(100%)",
          opacity: openPanel === "lean" ? 1 : 0,
          transition: prefersReducedMotion
            ? "none"
            : openPanel === "lean"
              ? "transform 250ms var(--spring-snappy), opacity 200ms var(--ease-out)"
              : "transform 180ms var(--ease-out), opacity 120ms var(--ease-out)",
          pointerEvents: openPanel === "lean" ? "auto" : "none",
        }}
      >
        {(["All", "Left", "Center", "Right"] as LeanChip[]).map((lean) => (
          <button
            key={lean}
            role="menuitem"
            aria-current={activeLean === lean ? "true" : undefined}
            className={`mob-nav__opt mob-nav__opt--lean-${lean.toLowerCase()}${activeLean === lean ? " mob-nav__opt--active" : ""}`}
            onClick={() => handleLeanTap(lean)}
          >
            {lean === "All" ? "All Perspectives" : lean}
          </button>
        ))}
      </div>

      {/* Topic panel */}
      <div
        ref={topicPanelRef}
        className="mob-nav__panel"
        role="menu"
        aria-label="Topic"
        style={{
          transform: openPanel === "topic" ? "translateY(0)" : "translateY(100%)",
          opacity: openPanel === "topic" ? 1 : 0,
          transition: prefersReducedMotion
            ? "none"
            : openPanel === "topic"
              ? "transform 250ms var(--spring-snappy), opacity 200ms var(--ease-out)"
              : "transform 180ms var(--ease-out), opacity 120ms var(--ease-out)",
          pointerEvents: openPanel === "topic" ? "auto" : "none",
        }}
      >
        {ALL_CATEGORIES.map((cat) => (
          <button
            key={cat}
            role="menuitem"
            aria-current={activeCategory === cat ? "true" : undefined}
            className={`mob-nav__opt${activeCategory === cat ? " mob-nav__opt--active" : ""}`}
            onClick={() => handleTopicTap(cat)}
          >
            {cat === "All" ? "All Topics" : cat}
          </button>
        ))}
      </div>

      {/* Three CTA buttons */}
      <div className="mob-nav__bar">
        <button
          className={`mob-nav__cta mob-nav__cta--edition${openPanel === "edition" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("edition")}
          aria-expanded={openPanel === "edition"}
          type="button"
        >
          <EditionIcon slug={activeEdition} size={10} />
          <span className="mob-nav__cta-label">{editionLabel}</span>
          <span className="mob-nav__cta-caret" aria-hidden="true">&#9652;</span>
        </button>

        <button
          className={`mob-nav__cta mob-nav__cta--lean${openPanel === "lean" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("lean")}
          aria-expanded={openPanel === "lean"}
          type="button"
        >
          <span className="mob-nav__lean-dots" aria-hidden="true">
            <span className="mob-nav__lean-dot mob-nav__lean-dot--left" />
            <span className="mob-nav__lean-dot mob-nav__lean-dot--center" />
            <span className="mob-nav__lean-dot mob-nav__lean-dot--right" />
          </span>
          <span className="mob-nav__cta-label">{leanLabel}</span>
          <span className="mob-nav__cta-caret" aria-hidden="true">&#9652;</span>
        </button>

        <button
          className={`mob-nav__cta mob-nav__cta--topic${openPanel === "topic" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("topic")}
          aria-expanded={openPanel === "topic"}
          type="button"
        >
          <span className="mob-nav__topic-hash" aria-hidden="true">#</span>
          <span className="mob-nav__cta-label">{topicLabel}</span>
          <span className="mob-nav__cta-caret" aria-hidden="true">&#9652;</span>
        </button>
      </div>
    </nav>
  );
}
