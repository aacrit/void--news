"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import type { SourceAccuracy } from "../lib/types";
import CredibilityArc from "./CredibilityArc";

/* ---------------------------------------------------------------------------
   SpectrumChart — Political lean spectrum visualization
   Bar on top, all sources plotted below in 7 lean zones.
   Logos overlap and fan out on zone hover.
   Collapsed to ~4 rows; single expand button reveals all.
   Each zone scrollable when expanded.

   Mobile (< 768px) source browser: the letter grid alone reads as decorative,
   so on small screens readers also get (a) a name search box, (b) a Spectrum /
   List view toggle where List renders full-width readable rows grouped by lean,
   and (c) tapping any spectrum letter opens a bottom sheet naming that source.
   Desktop behaviour is untouched (hover tooltip + fan-out).
   --------------------------------------------------------------------------- */

export interface SpectrumSource {
  name: string;
  slug: string;
  url: string;
  tier: "us_major" | "international" | "independent";
  country: string;
  political_lean_baseline: string | null;
  credibility_notes: string | null;
  claim_accuracy?: SourceAccuracy | null;
}

type LeanCategory =
  | "far-left"
  | "left"
  | "center-left"
  | "center"
  | "center-right"
  | "right"
  | "far-right";

export function normalizeLean(raw: string | null): LeanCategory {
  if (!raw) return "center";
  const s = raw.toLowerCase().trim().replace(/\s+/g, "-");
  const valid: LeanCategory[] = [
    "far-left", "left", "center-left", "center",
    "center-right", "right", "far-right",
  ];
  return valid.includes(s as LeanCategory) ? (s as LeanCategory) : "center";
}

const LEAN_ZONES: { key: LeanCategory; label: string; shortLabel: string }[] = [
  { key: "far-left", label: "Far Left", shortLabel: "Far L" },
  { key: "left", label: "Left", shortLabel: "Left" },
  { key: "center-left", label: "Center Left", shortLabel: "Ctr L" },
  { key: "center", label: "Center", shortLabel: "Ctr" },
  { key: "center-right", label: "Center Right", shortLabel: "Ctr R" },
  { key: "right", label: "Right", shortLabel: "Right" },
  { key: "far-right", label: "Far Right", shortLabel: "Far R" },
];

const LEAN_LABELS: Record<LeanCategory, string> = {
  "far-left": "Far Left",
  "left": "Left",
  "center-left": "Center Left",
  "center": "Center",
  "center-right": "Center Right",
  "right": "Right",
  "far-right": "Far Right",
};

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

function getFaviconUrl(_sourceUrl: string): string {
  // Privacy: never call an external favicon service. Fetching a third-party
  // favicon would leak the reader's IP and which publisher they are viewing to
  // that host. The self-contained letter monogram fallback renders instead.
  return "";
}

/* ---------------------------------------------------------------------------
   SourceLogo — favicon circle with overlap + fan-out on zone hover
   Desktop: hover/focus shows the fixed tooltip.
   Mobile: click (onSelect) opens the naming bottom sheet.
   --------------------------------------------------------------------------- */
function SourceLogo({
  source,
  onTooltip,
  onSelect,
}: {
  source: SpectrumSource;
  onTooltip: (source: SpectrumSource | null, el: HTMLElement | null) => void;
  onSelect: (source: SpectrumSource) => void;
}) {
  const favicon = source.url ? getFaviconUrl(source.url) : "";

  return (
    <button
      className="spectrum-logo"
      aria-label={`${source.name}, ${tierLabel(source.tier)}, ${normalizeLean(source.political_lean_baseline).replace(/-/g, " ")}`}
      onPointerEnter={(e) => onTooltip(source, e.currentTarget)}
      onPointerLeave={() => onTooltip(null, null)}
      onFocus={(e) => onTooltip(source, e.currentTarget)}
      onBlur={() => onTooltip(null, null)}
      onClick={() => onSelect(source)}
    >
      {favicon ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={favicon}
            alt=""
            width={20}
            height={20}
            className="spectrum-logo__img"
            loading="lazy"
            onError={(e) => {
              const t = e.currentTarget;
              t.style.display = "none";
              const fb = t.nextElementSibling as HTMLElement | null;
              if (fb) fb.style.display = "flex";
            }}
          />
          <span className="spectrum-logo__fallback" style={{ display: "none" }}>
            {source.name.charAt(0)}
          </span>
        </>
      ) : (
        <span className="spectrum-logo__fallback">{source.name.charAt(0)}</span>
      )}
    </button>
  );
}

/* ---------------------------------------------------------------------------
   SpectrumChart — main component
   --------------------------------------------------------------------------- */
interface SpectrumChartProps {
  sources: SpectrumSource[];
}

export default function SpectrumChart({ sources }: SpectrumChartProps) {
  const [expanded, setExpanded] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    source: SpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  /* Mobile source-browser state */
  const [query, setQuery] = useState("");
  const [mobileView, setMobileView] = useState<"spectrum" | "list">("spectrum");
  const [sheetSource, setSheetSource] = useState<SpectrumSource | null>(null);

  /* A name search should land the reader somewhere readable: force list view
     while a query is active so results show as full names, not letters. */
  const effectiveView: "spectrum" | "list" =
    query.trim() !== "" ? "list" : mobileView;

  /* Group all sources by lean zone, sorted alphabetically, filtered by query */
  const zones = useMemo(() => {
    const q = query.trim().toLowerCase();
    const map = new Map<LeanCategory, SpectrumSource[]>();
    for (const zone of LEAN_ZONES) map.set(zone.key, []);
    for (const s of sources) {
      if (q && !s.name.toLowerCase().includes(q)) continue;
      const lean = normalizeLean(s.political_lean_baseline);
      map.get(lean)!.push(s);
    }
    for (const [, srcs] of map)
      srcs.sort((a, b) => a.name.localeCompare(b.name));
    return map;
  }, [sources, query]);

  const matchCount = useMemo(() => {
    let n = 0;
    for (const [, srcs] of zones) n += srcs.length;
    return n;
  }, [zones]);

  /* Detect if the body overflows the viewport — show expand only when needed */
  useEffect(() => {
    const el = bodyRef.current;
    if (!el || expanded) return;
    const check = () => {
      const rect = el.getBoundingClientRect();
      const viewH = window.innerHeight;
      // Overflows if the bottom of the body extends beyond the viewport
      // with some padding for the expand button itself (~48px)
      setOverflows(rect.bottom > viewH - 48);
    };
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    window.addEventListener("resize", check);
    return () => { ro.disconnect(); window.removeEventListener("resize", check); };
  }, [sources, expanded]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setTooltip(null);
        setSheetSource(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleTooltip = useCallback(
    (source: SpectrumSource | null, el: HTMLElement | null) => {
      if (!source || !el) {
        setTooltip(null);
        return;
      }
      const rect = el.getBoundingClientRect();
      setTooltip({
        source,
        x: rect.left + rect.width / 2,
        y: rect.top,
      });
    },
    []
  );

  const handleSelect = useCallback((source: SpectrumSource) => {
    setSheetSource(source);
  }, []);

  const sheetLean = sheetSource
    ? normalizeLean(sheetSource.political_lean_baseline)
    : "center";

  return (
    <>
      {/* ---- Mobile source browser controls (hidden >= 768px via CSS) ---- */}
      <div className="spectrum-controls">
        <label className="spectrum-search" aria-label="Search sources by name">
          <svg
            className="spectrum-search__icon"
            width="16"
            height="16"
            viewBox="0 0 20 20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="9" cy="9" r="6" />
            <line x1="14" y1="14" x2="17" y2="17" />
          </svg>
          <input
            type="search"
            className="spectrum-search__input"
            placeholder="Search sources by name"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
          />
          {query && (
            <button
              type="button"
              className="spectrum-search__clear"
              aria-label="Clear search"
              onClick={() => setQuery("")}
            >
              &times;
            </button>
          )}
        </label>

        <div
          className="spectrum-viewtoggle"
          role="group"
          aria-label="Choose how to browse sources"
        >
          <button
            type="button"
            className={`spectrum-viewtoggle__btn${effectiveView === "spectrum" ? " spectrum-viewtoggle__btn--active" : ""}`}
            aria-pressed={effectiveView === "spectrum"}
            onClick={() => { setQuery(""); setMobileView("spectrum"); }}
          >
            Spectrum
          </button>
          <button
            type="button"
            className={`spectrum-viewtoggle__btn${effectiveView === "list" ? " spectrum-viewtoggle__btn--active" : ""}`}
            aria-pressed={effectiveView === "list"}
            onClick={() => setMobileView("list")}
          >
            List
          </button>
        </div>
      </div>

      <div
        className={`spectrum-chart${effectiveView === "list" ? " spectrum-chart--list" : ""}`}
      >
        {/* ---- Spectrum Bar ---- */}
        <div
          className="spectrum-bar"
          role="img"
          aria-label="Political lean spectrum, far left through far right"
        >
          {LEAN_ZONES.map((zone) => (
            <div
              key={zone.key}
              className="spectrum-bar__zone"
              data-lean={zone.key}
            >
              <span className="spectrum-bar__label">{zone.label}</span>
              <span className="spectrum-bar__label--short">
                {zone.shortLabel}
              </span>
            </div>
          ))}
        </div>

        {/* ---- Spectrum view: all sources below as letter logos ---- */}
        <div
          ref={bodyRef}
          className={`spectrum-body${expanded ? " spectrum-body--expanded" : ""}${
            overflows && !expanded ? " spectrum-body--collapsed" : ""
          }`}
        >
          {/* Mobile-only hint so the letter grid never reads as decorative */}
          <p className="spectrum-taphint" aria-hidden="true">
            Tap any source to see its name
          </p>
          <div className="spectrum-body__grid">
            {LEAN_ZONES.map((zone) => {
              const srcs = zones.get(zone.key) || [];
              return (
                <div
                  key={zone.key}
                  className={`spectrum-zone${expanded ? " spectrum-zone--scrollable" : ""}`}
                  data-lean={zone.key}
                >
                  <div className="spectrum-zone__logos">
                    {srcs.map((s) => (
                      <SourceLogo
                        key={s.slug}
                        source={s}
                        onTooltip={handleTooltip}
                        onSelect={handleSelect}
                      />
                    ))}
                  </div>
                  {srcs.length > 0 && (
                    <span className="spectrum-zone__count">{srcs.length}</span>
                  )}
                </div>
              );
            })}
          </div>
          {overflows && !expanded && (
            <div className="spectrum-body__fade" aria-hidden="true" />
          )}
        </div>

        {/* ---- Single expand/collapse — only shown when content overflows viewport ---- */}
        {(overflows || expanded) && (
          <button
            className="spectrum-expand-btn"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {expanded ? "Show fewer" : `Show all ${sources.length}`}
          </button>
        )}

        {/* ---- List view (mobile): readable full-width rows grouped by lean ---- */}
        <div className="spectrum-list" aria-label="All sources grouped by political lean">
          {query && (
            <p className="spectrum-list__result" role="status" aria-live="polite">
              {matchCount === 0
                ? `No sources match "${query}"`
                : `${matchCount} source${matchCount === 1 ? "" : "s"} match "${query}"`}
            </p>
          )}
          {LEAN_ZONES.map((zone) => {
            const srcs = zones.get(zone.key) || [];
            if (srcs.length === 0) return null;
            return (
              <section
                key={zone.key}
                className="spectrum-list__group"
                data-lean={zone.key}
              >
                <h3 className="spectrum-list__group-head">
                  <span
                    className="spectrum-list__group-dot"
                    data-lean={zone.key}
                    aria-hidden="true"
                  />
                  {zone.label}
                  <span className="spectrum-list__group-count">{srcs.length}</span>
                </h3>
                <ul className="spectrum-list__rows">
                  {srcs.map((s) => (
                    <li key={s.slug}>
                      <a
                        href={s.url || undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="spectrum-list__row"
                      >
                        <span
                          className="spectrum-list__mono"
                          data-lean={normalizeLean(s.political_lean_baseline)}
                          aria-hidden="true"
                        >
                          {s.name.charAt(0)}
                        </span>
                        <span className="spectrum-list__body">
                          <span className="spectrum-list__name">{s.name}</span>
                          <span className="spectrum-list__meta">
                            {tierLabel(s.tier)}
                            {s.country ? ` · ${s.country}` : ""}
                          </span>
                        </span>
                        <span className="spectrum-list__go" aria-hidden="true">
                          &#8599;
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>

        {/* ---- Tooltip (desktop hover; hidden on mobile via CSS) ---- */}
        {tooltip && (
          <div
            className="spectrum-tooltip"
            style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
            role="tooltip"
          >
            <p className="spectrum-tooltip__name">{tooltip.source.name}</p>
            <p className="spectrum-tooltip__lean">
              <span
                className="spectrum-tooltip__lean-dot"
                data-lean={normalizeLean(tooltip.source.political_lean_baseline)}
                aria-hidden="true"
              />
              {normalizeLean(tooltip.source.political_lean_baseline)
                .replace(/-/g, " ")
                .replace(/\b\w/g, (c) => c.toUpperCase())}
            </p>
            <p className="spectrum-tooltip__tier">
              {tierLabel(tooltip.source.tier)}
            </p>
            {tooltip.source.country && (
              <p className="spectrum-tooltip__country">
                {tooltip.source.country}
              </p>
            )}
            {tooltip.source.credibility_notes && (
              <p className="spectrum-tooltip__notes">
                {tooltip.source.credibility_notes}
              </p>
            )}
            {tooltip.source.claim_accuracy && (
              <CredibilityArc accuracy={tooltip.source.claim_accuracy} />
            )}
          </div>
        )}
      </div>

      {/* ---- Mobile bottom sheet: names a tapped spectrum source ---- */}
      {sheetSource && (
        <div
          className="spectrum-sheet-backdrop"
          onClick={() => setSheetSource(null)}
        >
          <div
            className="spectrum-sheet"
            role="dialog"
            aria-modal="true"
            aria-label={`${sheetSource.name} source detail`}
            onClick={(e) => e.stopPropagation()}
          >
            <span className="spectrum-sheet__handle" aria-hidden="true" />
            <div className="spectrum-sheet__head">
              <span
                className="spectrum-sheet__mono"
                data-lean={sheetLean}
                aria-hidden="true"
              >
                {sheetSource.name.charAt(0)}
              </span>
              <p className="spectrum-sheet__name">{sheetSource.name}</p>
            </div>
            <p className="spectrum-sheet__lean">
              <span
                className="spectrum-sheet__lean-dot"
                data-lean={sheetLean}
                aria-hidden="true"
              />
              {LEAN_LABELS[sheetLean]}
            </p>
            <p className="spectrum-sheet__tier">
              {tierLabel(sheetSource.tier)}
              {sheetSource.country ? ` · ${sheetSource.country}` : ""}
            </p>
            {sheetSource.credibility_notes && (
              <p className="spectrum-sheet__notes">
                {sheetSource.credibility_notes}
              </p>
            )}
            {sheetSource.claim_accuracy && (
              <CredibilityArc accuracy={sheetSource.claim_accuracy} />
            )}
            <div className="spectrum-sheet__actions">
              {sheetSource.url && (
                <a
                  href={sheetSource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="spectrum-sheet__link"
                >
                  Visit source &#8599;
                </a>
              )}
              <button
                type="button"
                className="spectrum-sheet__close"
                onClick={() => setSheetSource(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
