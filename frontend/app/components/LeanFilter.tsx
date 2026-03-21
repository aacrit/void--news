"use client";

import { useState, useRef, useCallback, useEffect, useId } from "react";

/* ---------------------------------------------------------------------------
   Lean Filter — Universal political lean range filter
   Pill: colored dots + "Lean" label, matches filter-chip sizing.
   Panel: just the spectrum slider with embedded zone labels. No chrome.
   --------------------------------------------------------------------------- */

export interface LeanRange {
  min: number;
  max: number;
}

interface LeanFilterProps {
  value: LeanRange | null;
  onChange: (range: LeanRange | null) => void;
}

const ZONES = [
  { label: "Far Left",     short: "FL",  min: 0,   max: 20,  colorVar: "var(--bias-far-left)"     },
  { label: "Left",         short: "L",   min: 20,  max: 35,  colorVar: "var(--bias-left)"          },
  { label: "Center-Left",  short: "CL",  min: 35,  max: 46,  colorVar: "var(--bias-center-left)"  },
  { label: "Center",       short: "C",   min: 46,  max: 54,  colorVar: "var(--bias-center)"        },
  { label: "Center-Right", short: "CR",  min: 54,  max: 65,  colorVar: "var(--bias-center-right)" },
  { label: "Right",        short: "R",   min: 65,  max: 80,  colorVar: "var(--bias-right)"         },
  { label: "Far Right",    short: "FR",  min: 80,  max: 100, colorVar: "var(--bias-far-right)"     },
] as const;

function getLeanLabel(value: number): string {
  for (let i = 0; i < ZONES.length; i++) {
    const z = ZONES[i];
    if (i < ZONES.length - 1) {
      if (value >= z.min && value < z.max) return z.label;
    } else {
      if (value >= z.min && value <= z.max) return z.label;
    }
  }
  return value < 50 ? "Left" : "Right";
}

function getLeanColor(value: number): string {
  if (value < 20)  return "var(--bias-far-left)";
  if (value < 35)  return "var(--bias-left)";
  if (value < 46)  return "var(--bias-center-left)";
  if (value < 54)  return "var(--bias-center)";
  if (value < 65)  return "var(--bias-center-right)";
  if (value < 80)  return "var(--bias-right)";
  return "var(--bias-far-right)";
}

const DEFAULT_RANGE: LeanRange = { min: 35, max: 65 };

export default function LeanFilter({ value, onChange }: LeanFilterProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localRange, setLocalRange] = useState<LeanRange>(value ?? DEFAULT_RANGE);
  const [dragging, setDragging] = useState<"min" | "max" | null>(null);

  const trackRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const isActive = value !== null;
  const pillId = useId();
  const panelId = useId();

  useEffect(() => {
    if (value !== null) setLocalRange(value);
  }, [value]);

  /* Close on outside click */
  useEffect(() => {
    if (!isExpanded) return;
    function handleOutside(e: MouseEvent | TouchEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsExpanded(false);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    document.addEventListener("touchstart", handleOutside, { passive: true });
    return () => {
      document.removeEventListener("mousedown", handleOutside);
      document.removeEventListener("touchstart", handleOutside);
    };
  }, [isExpanded]);

  useEffect(() => {
    if (!isExpanded) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setIsExpanded(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isExpanded]);

  /* ---- Drag ---- */
  const getValueFromPosition = useCallback((clientX: number): number => {
    if (!trackRef.current) return 50;
    const rect = trackRef.current.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return Math.round(ratio * 100);
  }, []);

  const handlePointerMove = useCallback(
    (e: PointerEvent) => {
      if (!dragging) return;
      const v = getValueFromPosition(e.clientX);
      setLocalRange((prev) => {
        if (dragging === "min") {
          return { ...prev, min: Math.max(0, Math.min(v, prev.max - 5)) };
        } else {
          return { ...prev, max: Math.min(100, Math.max(v, prev.min + 5)) };
        }
      });
    },
    [dragging, getValueFromPosition],
  );

  const handlePointerUp = useCallback(() => {
    if (!dragging) return;
    setDragging(null);
    onChange(localRange);
  }, [dragging, localRange, onChange]);

  useEffect(() => {
    if (!dragging) return;
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [dragging, handlePointerMove, handlePointerUp]);

  /* ---- Keyboard ---- */
  const handleThumbKey = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, thumb: "min" | "max") => {
      let delta = 0;
      if (e.key === "ArrowLeft" || e.key === "ArrowDown") delta = -1;
      if (e.key === "ArrowRight" || e.key === "ArrowUp") delta = 1;
      if (e.key === "Home") delta = thumb === "min" ? -localRange.min : -(localRange.max - (localRange.min + 5));
      if (e.key === "End") delta = thumb === "max" ? 100 - localRange.max : (localRange.max - 5 - localRange.min);
      if (delta === 0) return;
      e.preventDefault();
      setLocalRange((prev) => {
        if (thumb === "min") {
          const n = Math.max(0, Math.min(prev.min + delta, prev.max - 5));
          const next = { ...prev, min: n };
          onChange(next);
          return next;
        } else {
          const n = Math.max(prev.min + 5, Math.min(prev.max + delta, 100));
          const next = { ...prev, max: n };
          onChange(next);
          return next;
        }
      });
    },
    [localRange, onChange],
  );

  /* ---- Track click ---- */
  const handleTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const v = getValueFromPosition(e.clientX);
      const distMin = Math.abs(v - localRange.min);
      const distMax = Math.abs(v - localRange.max);
      if (distMin <= distMax) {
        const next = { ...localRange, min: Math.max(0, Math.min(v, localRange.max - 5)) };
        setLocalRange(next);
        onChange(next);
      } else {
        const next = { ...localRange, max: Math.min(100, Math.max(v, localRange.min + 5)) };
        setLocalRange(next);
        onChange(next);
      }
    },
    [getValueFromPosition, localRange, onChange],
  );

  /* ---- Pill toggle ---- */
  const handlePillClick = useCallback(() => {
    if (isActive && !isExpanded) {
      setIsExpanded(true);
      return;
    }
    setIsExpanded((prev) => !prev);
    if (!isExpanded && !isActive) {
      setLocalRange(DEFAULT_RANGE);
      onChange(DEFAULT_RANGE);
    }
  }, [isActive, isExpanded, onChange]);

  /* ---- Clear ---- */
  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setLocalRange(DEFAULT_RANGE);
      onChange(null);
      setIsExpanded(false);
    },
    [onChange],
  );

  /* ---- Derived values ---- */
  const minColor = getLeanColor(localRange.min);
  const maxColor = getLeanColor(localRange.max);
  const minLabel = getLeanLabel(localRange.min);
  const maxLabel = getLeanLabel(localRange.max);
  const selLeft = `${localRange.min}%`;
  const selWidth = `${localRange.max - localRange.min}%`;
  const isFullRange = localRange.min <= 0 && localRange.max >= 100;

  return (
    <div
      className={`lean-filter${isActive ? " lean-filter--active" : ""}${isExpanded ? " lean-filter--expanded" : ""}${dragging ? " lean-filter--dragging" : ""}`}
      ref={containerRef}
    >
      {/* ---- Pill ---- */}
      <button
        id={pillId}
        className="lean-filter__pill"
        onClick={handlePillClick}
        aria-expanded={isExpanded}
        aria-controls={panelId}
        aria-label={
          isActive
            ? `Political lean filter active: ${minLabel} to ${maxLabel}. Click to adjust.`
            : "Filter stories by political lean"
        }
      >
        <span className="lean-filter__spectrum-dots" aria-hidden="true">
          <span className="lean-filter__dot lean-filter__dot--left" />
          <span className="lean-filter__dot lean-filter__dot--center" />
          <span className="lean-filter__dot lean-filter__dot--right" />
        </span>

        <span className="lean-filter__pill-label">
          {isActive && !isFullRange ? (
            <span className="lean-filter__pill-range">
              {minLabel} — {maxLabel}
            </span>
          ) : (
            "Lean"
          )}
        </span>

        {isActive && !isFullRange && (
          <span className="lean-filter__active-dot" aria-hidden="true" />
        )}

        <span
          className={`lean-filter__caret${isExpanded ? " lean-filter__caret--open" : ""}`}
          aria-hidden="true"
        >
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      {/* ---- Panel — just the slider, nothing else ---- */}
      <div
        id={panelId}
        className="lean-filter__panel"
        aria-hidden={!isExpanded}
        role="group"
        aria-label="Political lean range selector"
      >
        <div className="lean-filter__panel-overflow">
          <div className="lean-filter__panel-inner">
            {/* Track + thumbs */}
            <div className="lean-filter__track-area">
              <div
                ref={trackRef}
                className="lean-filter__track"
                onClick={handleTrackClick}
                aria-hidden="true"
              >
                <div
                  className="lean-filter__selection"
                  style={{ left: selLeft, width: selWidth }}
                  aria-hidden="true"
                />
                <button
                  className={`lean-filter__thumb lean-filter__thumb--min${dragging === "min" ? " lean-filter__thumb--dragging" : ""}`}
                  style={{ left: selLeft, "--thumb-color": minColor } as React.CSSProperties}
                  role="slider"
                  aria-label={`Minimum lean: ${minLabel} (${localRange.min})`}
                  aria-valuemin={0}
                  aria-valuemax={localRange.max - 5}
                  aria-valuenow={localRange.min}
                  aria-valuetext={minLabel}
                  tabIndex={isExpanded ? 0 : -1}
                  onPointerDown={(e) => {
                    e.preventDefault();
                    (e.target as HTMLElement).setPointerCapture(e.pointerId);
                    setDragging("min");
                  }}
                  onKeyDown={(e) => handleThumbKey(e, "min")}
                />
                <button
                  className={`lean-filter__thumb lean-filter__thumb--max${dragging === "max" ? " lean-filter__thumb--dragging" : ""}`}
                  style={{ left: `${localRange.max}%`, "--thumb-color": maxColor } as React.CSSProperties}
                  role="slider"
                  aria-label={`Maximum lean: ${maxLabel} (${localRange.max})`}
                  aria-valuemin={localRange.min + 5}
                  aria-valuemax={100}
                  aria-valuenow={localRange.max}
                  aria-valuetext={maxLabel}
                  tabIndex={isExpanded ? 0 : -1}
                  onPointerDown={(e) => {
                    e.preventDefault();
                    (e.target as HTMLElement).setPointerCapture(e.pointerId);
                    setDragging("max");
                  }}
                  onKeyDown={(e) => handleThumbKey(e, "max")}
                />
              </div>

              {/* Zone labels as ruler marks — positioned at zone midpoints */}
              <div className="lean-filter__ruler" aria-hidden="true">
                {ZONES.map((zone) => (
                  <span
                    key={zone.label}
                    className="lean-filter__ruler-label"
                    style={{ left: `${(zone.min + zone.max) / 2}%` }}
                    onClick={() => {
                      const next = { min: zone.min, max: zone.max };
                      setLocalRange(next);
                      onChange(next);
                    }}
                  >
                    {zone.short}
                  </span>
                ))}
              </div>
            </div>

            {/* Clear — ✕ icon, only when filter is active */}
            {isActive && !isFullRange && (
              <button
                className="lean-filter__reset"
                onClick={handleClear}
                aria-label="Clear lean filter"
                tabIndex={isExpanded ? 0 : -1}
              >
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
