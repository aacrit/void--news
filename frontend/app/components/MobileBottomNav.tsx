"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Category, LeanChip } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import LogoIcon from "./LogoIcon";
import { hapticMicro, hapticLight, hapticConfirm } from "../lib/haptics";

interface MobileBottomNavProps {
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
  activeCategory: "All" | Category;
  onCategoryChange: (cat: "All" | Category) => void;
  dailyBriefState?: DailyBriefState;
}

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

type OpenPanel = null | "lean" | "topic";

/* ---------------------------------------------------------------------------
   MobileBottomNav — 2 filter buttons + OnAir progress (mobile only).

   [Perspective ▾]  [Topic ▾]
   ▶ ━━━━━━━━━━━ onair progress ━━━━━━━━━━━

   Editions moved to top NavBar tabs. Bottom nav is filters only.
   OnAir mini-progress taps to expand FloatingPlayer.
   Hidden on desktop via CSS (display: none above 768px).
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
  dailyBriefState,
}: MobileBottomNavProps) {
  const [openPanel, setOpenPanel] = useState<OpenPanel>(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const leanPanelRef = useRef<HTMLDivElement>(null);
  const topicPanelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mql.matches);
    const onChange = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (openPanel) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [openPanel]);

  const toggle = useCallback((panel: OpenPanel) => {
    hapticLight();
    setOpenPanel((prev) => prev === panel ? null : panel);
  }, []);

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

  useEffect(() => {
    if (openPanel) {
      triggerRef.current = document.activeElement as HTMLButtonElement | null;
      const panelMap: Record<string, React.RefObject<HTMLDivElement | null>> = {
        lean: leanPanelRef,
        topic: topicPanelRef,
      };
      const panelEl = panelMap[openPanel]?.current;
      if (panelEl) {
        requestAnimationFrame(() => {
          const firstInteractive = panelEl.querySelector<HTMLElement>("button, a, input");
          firstInteractive?.focus();
        });
      }
    } else {
      if (triggerRef.current && typeof triggerRef.current.focus === "function") {
        triggerRef.current.focus();
        triggerRef.current = null;
      }
    }
  }, [openPanel]);

  useEffect(() => {
    if (!openPanel) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); setOpenPanel(null); }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [openPanel]);

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

  const leanLabel = activeLean === "All" ? "All" : activeLean;
  const topicLabel = activeCategory === "All" ? "All Topics" : activeCategory;

  // OnAir state (optional — pages without daily brief pass no state)
  const brief = dailyBriefState?.brief;
  const isPlaying = dailyBriefState?.isPlaying ?? false;
  const currentTime = dailyBriefState?.currentTime ?? 0;
  const duration = dailyBriefState?.duration ?? 0;
  const handlePlayPause = dailyBriefState?.handlePlayPause;
  const setPlayerVisible = dailyBriefState?.setPlayerVisible;
  const hasAudio = !!brief?.audio_url;
  const displayDuration = brief?.audio_duration_seconds || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  const handleOnairTap = () => {
    hapticConfirm();
    setPlayerVisible?.(true);
    if (!isPlaying) handlePlayPause?.();
  };

  const panelTransition = (isOpen: boolean) =>
    prefersReducedMotion
      ? "none"
      : isOpen
        ? "transform 250ms var(--spring-snappy), opacity 200ms var(--ease-out)"
        : "transform 180ms var(--ease-out), opacity 120ms var(--ease-out)";

  return (
    <nav className="mob-nav anim-cold-open-nav" aria-label="Mobile navigation" ref={navRef}>
      {/* Backdrop */}
      <div
        className="mob-nav__backdrop"
        style={{
          opacity: openPanel ? 1 : 0,
          pointerEvents: openPanel ? "auto" : "none",
          transition: prefersReducedMotion ? "none" : openPanel ? "opacity 150ms var(--ease-out)" : "opacity 120ms var(--ease-out)",
        }}
        onClick={() => setOpenPanel(null)}
        aria-hidden="true"
      />

      {/* Perspective panel */}
      <div
        ref={leanPanelRef}
        className="mob-nav__panel"
        role="menu"
        aria-label="Perspective"
        style={{
          transform: openPanel === "lean" ? "translateY(0)" : "translateY(100%)",
          opacity: openPanel === "lean" ? 1 : 0,
          transition: panelTransition(openPanel === "lean"),
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
          transition: panelTransition(openPanel === "topic"),
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

      {/* OnAir mini-progress — persistent strip above buttons */}
      {hasAudio && (
        <button
          className={`mob-nav__onair${isPlaying ? " mob-nav__onair--playing" : ""}`}
          onClick={handleOnairTap}
          type="button"
          aria-label={isPlaying ? "Now playing — tap to expand" : "Play broadcast"}
        >
          <LogoIcon size={12} animation={isPlaying ? "analyzing" : "idle"} />
          <span className="mob-nav__onair-label">
            {isPlaying ? "void --onair" : "Listen"}
          </span>
          <div className="mob-nav__onair-bar" aria-hidden="true">
            <div className="mob-nav__onair-fill" style={{ width: `${progress}%` }} />
          </div>
        </button>
      )}

      {/* Navigation bar — 2 filter buttons */}
      <div className="mob-nav__bar">
        <button
          className={`mob-nav__cta mob-nav__cta--lean${openPanel === "lean" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("lean")}
          aria-expanded={openPanel === "lean"}
          type="button"
        >
          <span className="mob-nav__cta-icon" aria-hidden="true">
            <svg width="20" height="14" viewBox="0 0 20 14" fill="none">
              <circle cx="3" cy="7" r="2.5" fill="var(--bias-left)" />
              <circle cx="10" cy="7" r="2.5" fill="var(--bias-center)" />
              <circle cx="17" cy="7" r="2.5" fill="var(--bias-right)" />
            </svg>
          </span>
          <span className="mob-nav__cta-label">{leanLabel}</span>
        </button>

        <button
          className={`mob-nav__cta mob-nav__cta--topic${openPanel === "topic" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("topic")}
          aria-expanded={openPanel === "topic"}
          type="button"
        >
          <span className="mob-nav__cta-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="currentColor">
              <rect x="1" y="4" width="5" height="5" rx="1" opacity="0.8" />
              <rect x="7" y="4" width="5" height="5" rx="1" opacity="0.6" />
              <rect x="13" y="4" width="4" height="5" rx="1" opacity="0.4" />
              <rect x="1" y="10" width="5" height="4" rx="1" opacity="0.6" />
              <rect x="7" y="10" width="5" height="4" rx="1" opacity="0.4" />
            </svg>
          </span>
          <span className="mob-nav__cta-label">{topicLabel}</span>
        </button>
      </div>
    </nav>
  );
}
