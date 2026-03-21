"use client";

import { useState, useRef, useCallback, useEffect, useId } from "react";

/* ---------------------------------------------------------------------------
   Lean Filter — Universal political lean range filter
   Collapsed: a small pill hinting at the filter.
   Expanded: a dual-handle range slider over the spectrum gradient.
   --------------------------------------------------------------------------- */

export interface LeanRange {
  min: number;
  max: number;
}

interface LeanFilterProps {
  value: LeanRange | null;
  onChange: (range: LeanRange | null) => void;
}

/* Zone definitions — calibrated against cluster-level avg_political_lean.
 * Tighter center (46-54) reflects that baseline blending + factual-rigor
 * weighting compress most cluster averages toward 50. Wider flanks ensure
 * NPR-heavy clusters land in Center-Left, Fox-heavy in Center-Right, etc. */
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
  /* Walk zones in order — first match wins (non-terminal use < max to avoid
   * double-counting at shared boundaries; terminal zone uses <=) */
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

/* Default range when filter is first activated — Center-Left to Center-Right */
const DEFAULT_RANGE: LeanRange = { min: 35, max: 65 };

export default function LeanFilter({ value, onChange }: LeanFilterProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localRange, setLocalRange] = useState<LeanRange>(value ?? DEFAULT_RANGE);
  const [dragging, setDragging] = useState<"min" | "max" | null>(null);

  const trackRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const minThumbRef = useRef<HTMLButtonElement>(null);
  const maxThumbRef = useRef<HTMLButtonElement>(null);

  const isActive = value !== null;
  const pillId = useId();
  const panelId = useId();

  /* Sync local range when external value changes (e.g. on clear) */
  useEffect(() => {
    if (value !== null) {
      setLocalRange(value);
    }
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

  /* Close on Escape */
  useEffect(() => {
    if (!isExpanded) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setIsExpanded(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isExpanded]);

  /* ---- Drag handling ---- */
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
          const newMin = Math.min(v, prev.max - 5);
          return { ...prev, min: Math.max(0, newMin) };
        } else {
          const newMax = Math.max(v, prev.min + 5);
          return { ...prev, max: Math.min(100, newMax) };
        }
      });
    },
    [dragging, getValueFromPosition],
  );

  const handlePointerUp = useCallback(() => {
    if (!dragging) return;
    setDragging(null);
    /* Commit to parent on release */
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

  /* ---- Keyboard for thumbs ---- */
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

  /* ---- Track click (jump to nearest thumb) ---- */
  const handleTrackClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const v = getValueFromPosition(e.clientX);
      const distMin = Math.abs(v - localRange.min);
      const distMax = Math.abs(v - localRange.max);
      if (distMin <= distMax) {
        const newMin = Math.max(0, Math.min(v, localRange.max - 5));
        const next = { ...localRange, min: newMin };
        setLocalRange(next);
        onChange(next);
      } else {
        const newMax = Math.min(100, Math.max(v, localRange.min + 5));
        const next = { ...localRange, max: newMax };
        setLocalRange(next);
        onChange(next);
      }
    },
    [getValueFromPosition, localRange, onChange],
  );

  /* ---- Toggle pill ---- */
  const handlePillClick = useCallback(() => {
    if (isActive && !isExpanded) {
      /* Already active — clicking the pill opens the editor */
      setIsExpanded(true);
      return;
    }
    setIsExpanded((prev) => !prev);
    if (!isExpanded && !isActive) {
      /* Expanding for the first time — activate with default range */
      setLocalRange(DEFAULT_RANGE);
      onChange(DEFAULT_RANGE);
    }
  }, [isActive, isExpanded, onChange]);

  /* ---- Clear ---- */
  const handleClear = useCallback(
    (e: React.MouseEvent | React.KeyboardEvent) => {
      e.stopPropagation();
      if ("key" in e && e.key !== "Enter" && e.key !== " ") return;
      setLocalRange(DEFAULT_RANGE);
      onChange(null);
      setIsExpanded(false);
    },
    [onChange],
  );

  /* ---- Derived display values ---- */
  const minColor = getLeanColor(localRange.min);
  const maxColor = getLeanColor(localRange.max);
  const minLabel = getLeanLabel(localRange.min);
  const maxLabel = getLeanLabel(localRange.max);

  /* Left/width for the selection highlight strip */
  const selLeft = `${localRange.min}%`;
  const selWidth = `${localRange.max - localRange.min}%`;

  /* Determine if all stories are included (filter is effectively off) */
  const isFullRange = localRange.min <= 0 && localRange.max >= 100;

  /* Active zone detection — which zone exactly matches the current range? */
  const activeZone = ZONES.find(
    (z) => z.min === localRange.min && z.max === localRange.max,
  ) ?? null;

  return (
    <div
      className={`lean-filter${isActive ? " lean-filter--active" : ""}${isExpanded ? " lean-filter--expanded" : ""}${dragging ? " lean-filter--dragging" : ""}`}
      ref={containerRef}
    >
      {/* ---- Collapsed pill ---- */}
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
        {/* Spectrum indicator — 3 colored dots (blue / gray / red) */}
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

        {/* Active indicator */}
        {isActive && !isFullRange && (
          <span className="lean-filter__active-dot" aria-hidden="true" />
        )}

        {/* Caret */}
        <span
          className={`lean-filter__caret${isExpanded ? " lean-filter__caret--open" : ""}`}
          aria-hidden="true"
        >
          <svg width="10" height="6" viewBox="0 0 10 6" fill="none">
            <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      {/* ---- Expanded panel (grid-template-rows animation) ---- */}
      <div
        id={panelId}
        className="lean-filter__panel"
        aria-hidden={!isExpanded}
        role="group"
        aria-label="Political lean range selector"
      >
        {/* Overflow wrapper for the grid-rows collapse trick */}
        <div className="lean-filter__panel-overflow">
          <div className="lean-filter__panel-inner">
            {/* Panel header */}
            <div className="lean-filter__panel-header">
              <span className="lean-filter__panel-title">Political Lean</span>
              {isActive && !isFullRange && (
                <button
                  className="lean-filter__clear"
                  onClick={handleClear}
                  onKeyDown={handleClear}
                  aria-label="Clear lean filter"
                  tabIndex={isExpanded ? 0 : -1}
                >
                  Clear
                </button>
              )}
            </div>

            {/* Range labels */}
            <div className="lean-filter__range-labels" aria-live="polite" aria-atomic="true">
              <span
                className="lean-filter__range-label lean-filter__range-label--min"
                style={{ color: minColor }}
              >
                {minLabel}
              </span>
              <span className="lean-filter__range-sep">to</span>
              <span
                className="lean-filter__range-label lean-filter__range-label--max"
                style={{ color: maxColor }}
              >
                {maxLabel}
              </span>
            </div>

            {/* Slider track */}
            <div className="lean-filter__track-area">
              {/* Gradient track */}
              <div
                ref={trackRef}
                className="lean-filter__track"
                onClick={handleTrackClick}
                aria-hidden="true"
              >
                {/* Selected range highlight */}
                <div
                  className="lean-filter__selection"
                  style={{ left: selLeft, width: selWidth }}
                  aria-hidden="true"
                />

                {/* Min thumb */}
                <button
                  ref={minThumbRef}
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

                {/* Max thumb */}
                <button
                  ref={maxThumbRef}
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

              {/* Zone tick marks */}
              <div className="lean-filter__ticks" aria-hidden="true">
                {ZONES.map((zone) => (
                  <span
                    key={zone.label}
                    className="lean-filter__tick"
                    style={{ left: `${zone.min}%` }}
                  />
                ))}
              </div>
            </div>

            {/* Zone labels row */}
            <div className="lean-filter__zone-labels" aria-hidden="true">
              {ZONES.map((zone) => {
                const isZoneActive = activeZone?.label === zone.label;
                return (
                  <button
                    key={zone.label}
                    className={`lean-filter__zone-btn${isZoneActive ? " lean-filter__zone-btn--active" : ""}`}
                    tabIndex={isExpanded ? 0 : -1}
                    aria-label={`Set range to ${zone.label} only`}
                    aria-pressed={isZoneActive}
                    style={{ "--zone-color": zone.colorVar } as React.CSSProperties}
                    onClick={() => {
                      const next = { min: zone.min, max: zone.max };
                      setLocalRange(next);
                      onChange(next);
                    }}
                  >
                    {zone.short}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
