"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — Scaled-down Sources-page spectrum for Deep Dive panel.
   7-zone gradient bar on top, source logos below in matching grid columns.
   Logos overlap and fan out on zone hover. Each is a link to the article.
   --------------------------------------------------------------------------- */

export interface DeepDiveSpectrumSource {
  name: string;
  articleUrl: string;
  sourceUrl: string;
  tier: string;
  politicalLean: number;
}

type LeanCategory =
  | "far-left"
  | "left"
  | "center-left"
  | "center"
  | "center-right"
  | "right"
  | "far-right";

const LEAN_ZONES: { key: LeanCategory; label: string; shortLabel: string }[] = [
  { key: "far-left", label: "Far Left", shortLabel: "Far L" },
  { key: "left", label: "Left", shortLabel: "Left" },
  { key: "center-left", label: "Center Left", shortLabel: "Ctr L" },
  { key: "center", label: "Center", shortLabel: "Ctr" },
  { key: "center-right", label: "Center Right", shortLabel: "Ctr R" },
  { key: "right", label: "Right", shortLabel: "Right" },
  { key: "far-right", label: "Far Right", shortLabel: "Far R" },
];

function leanToBucket(lean: number): LeanCategory {
  if (lean <= 14) return "far-left";
  if (lean <= 28) return "left";
  if (lean <= 42) return "center-left";
  if (lean <= 57) return "center";
  if (lean <= 71) return "center-right";
  if (lean <= 85) return "right";
  return "far-right";
}

function leanLabel(lean: number): string {
  if (lean <= 20) return "Far Left";
  if (lean <= 35) return "Left";
  if (lean <= 45) return "Center-Left";
  if (lean <= 55) return "Center";
  if (lean <= 65) return "Center-Right";
  if (lean <= 80) return "Right";
  return "Far Right";
}

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

function getFaviconUrl(sourceUrl: string): string {
  if (!sourceUrl) return "";
  try {
    const domain = new URL(
      sourceUrl.startsWith("http") ? sourceUrl : `https://${sourceUrl}`
    ).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

/* ---------------------------------------------------------------------------
   SourceLogo — favicon link with overlap + fan-out
   --------------------------------------------------------------------------- */
function SourceLogo({
  source,
  onTooltip,
}: {
  source: DeepDiveSpectrumSource;
  onTooltip: (source: DeepDiveSpectrumSource | null, el: HTMLElement | null) => void;
}) {
  const favicon = getFaviconUrl(source.sourceUrl);

  return (
    <a
      className="dd-spectrum__logo"
      href={source.articleUrl}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${source.name}: ${leanLabel(source.politicalLean)} — click to read article`}
      onPointerEnter={(e) => onTooltip(source, e.currentTarget)}
      onPointerLeave={() => onTooltip(null, null)}
      onFocus={(e) => onTooltip(source, e.currentTarget)}
      onBlur={() => onTooltip(null, null)}
    >
      {favicon ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={favicon}
            alt=""
            width={14}
            height={14}
            className="dd-spectrum__logo-img"
            loading="lazy"
            onError={(e) => {
              const t = e.currentTarget;
              t.style.display = "none";
              const fb = t.nextElementSibling as HTMLElement | null;
              if (fb) fb.style.display = "flex";
            }}
          />
          <span className="dd-spectrum__fallback" style={{ display: "none" }}>
            {source.name.charAt(0)}
          </span>
        </>
      ) : (
        <span className="dd-spectrum__fallback">{source.name.charAt(0)}</span>
      )}
    </a>
  );
}

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — main component
   --------------------------------------------------------------------------- */
interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
}

export default function DeepDiveSpectrum({ sources }: DeepDiveSpectrumProps) {
  const [tooltip, setTooltip] = useState<{
    source: DeepDiveSpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  /* Group sources into 7 lean buckets */
  const zones = useMemo(() => {
    const map = new Map<LeanCategory, DeepDiveSpectrumSource[]>();
    for (const zone of LEAN_ZONES) map.set(zone.key, []);
    for (const s of sources) {
      const bucket = leanToBucket(s.politicalLean);
      map.get(bucket)!.push(s);
    }
    return map;
  }, [sources]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTooltip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleTooltip = useCallback(
    (source: DeepDiveSpectrumSource | null, el: HTMLElement | null) => {
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

  return (
    <div className="dd-spectrum" role="img" aria-label="Article political lean spectrum">
      {/* ---- Gradient Bar ---- */}
      <div className="dd-spectrum__bar" aria-hidden="true">
        {LEAN_ZONES.map((zone) => (
          <div key={zone.key} className="dd-spectrum__bar-zone" data-lean={zone.key}>
            <span className="dd-spectrum__zone-label">{zone.label}</span>
          </div>
        ))}
      </div>

      {/* ---- Logos below bar ---- */}
      <div className="dd-spectrum__body">
        {LEAN_ZONES.map((zone) => {
          const srcs = zones.get(zone.key) || [];
          return (
            <div key={zone.key} className="dd-spectrum__zone" data-lean={zone.key}>
              <div className="dd-spectrum__zone-logos">
                {srcs.map((s) => (
                  <SourceLogo
                    key={s.name}
                    source={s}
                    onTooltip={handleTooltip}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* ---- Tooltip ---- */}
      {tooltip && (
        <div
          className="dd-spectrum__tooltip"
          style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
          role="tooltip"
        >
          <p className="dd-spectrum__tooltip-name">{tooltip.source.name}</p>
          <p className="dd-spectrum__tooltip-lean">
            <span
              className="dd-spectrum__tooltip-dot"
              data-lean={leanToBucket(tooltip.source.politicalLean)}
              aria-hidden="true"
            />
            {leanLabel(tooltip.source.politicalLean)}
            <span className="dd-spectrum__tooltip-score">
              {tooltip.source.politicalLean}
            </span>
          </p>
          <p className="dd-spectrum__tooltip-tier">
            {tierLabel(tooltip.source.tier)}
          </p>
          <p className="dd-spectrum__tooltip-hint">Click to read article</p>
        </div>
      )}
    </div>
  );
}
