"use client";

import { useMemo, useState } from "react";
import type { StorySource } from "../lib/types";
import { getLeanColor, leanLabel, leanToBucket } from "../lib/biasColors";
import { sourceLogoUrl } from "../lib/sourceLogos";

/* ---------------------------------------------------------------------------
   SourceLedger — the full source roster, as one elegant spectrum-ordered index.

   Replaces the old three-column truncating scroll boxes (dd-src-cols). This is
   the readable companion to the DeepDiveSpectrum portal above it: the spectrum
   answers "where does coverage sit" by placing lean-colored monograms at each
   outlet's exact point on the axis; the ledger answers "who, exactly" as a
   full-width, never-truncated list that walks DOWN the same spectrum (Left band,
   then Center, then Right). Each row carries the SAME lean-tinted monogram tile
   as the spectrum pins, so scanning the ledger reads the same blue to green to
   red progression as the graph.

   No nested scroll, no ellipsis: the list flows with the page. On mobile it
   collapses behind an "All N sources" disclosure (a compact lean-distribution
   teaser bar sits on the toggle); on desktop it renders open.

   Shared by the mobile DeepDive, the desktop InlineDeepDive, and the standalone
   /story archive page so the source vocabulary lives in exactly one place.
   Styles: `.dd-ledger*` in deep-dive-page.css.
   --------------------------------------------------------------------------- */

// Human-readable outlet tier. Never fabricates a tier; unknown -> Independent.
function tierLabel(tier: string | undefined): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

// Compact tier badge for the row meta. Same never-fabricate floor.
function tierAbbr(tier: string | undefined): string {
  if (tier === "us_major") return "US";
  if (tier === "international") return "Intl";
  return "Ind";
}

// The three spectrum bands, top (Left) to bottom (Right), so the ledger reads
// down the same axis the graph reads across. `anchor` feeds getLeanColor so each
// band's hairline rule matches the gradient (blue -> green -> red).
const LEAN_BANDS: { key: "left" | "center" | "right"; label: string; anchor: number }[] = [
  { key: "left", label: "Left", anchor: 28 },
  { key: "center", label: "Center", anchor: 50 },
  { key: "right", label: "Right", anchor: 72 },
];

/* Monogram tile: the self-hosted outlet favicon when we have one (first-party,
   see sourceLogoUrl), the lean-colored letter otherwise. Same tile language as
   the spectrum pins above, so the ledger reads the same blue to green to red. */
function LedgerMono({ name, bucket }: { name: string; bucket: string }) {
  const [failed, setFailed] = useState(false);
  const url = sourceLogoUrl(name);
  return (
    <span className="dd-ledger__mono" data-lean={bucket} aria-hidden="true">
      {url && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt=""
          width={18}
          height={18}
          loading="lazy"
          className="dd-ledger__logo"
          onError={() => setFailed(true)}
        />
      ) : (
        name.charAt(0).toUpperCase()
      )}
    </span>
  );
}

interface SourceLedgerProps {
  sources: StorySource[];
  /** Desktop passes true (rendered open); mobile omits it (collapsed behind
      an "All N sources" disclosure). */
  defaultOpen?: boolean;
}

export default function SourceLedger({ sources, defaultOpen = false }: SourceLedgerProps) {
  const [open, setOpen] = useState(defaultOpen);

  /* Bucket every source into Left / Center / Right and sort each band outward
     from center. Collapses the 7-way leanToBucket the same way the spectrum
     thirds do. */
  const bucketed = useMemo(() => {
    const groups: { left: StorySource[]; center: StorySource[]; right: StorySource[] } = {
      left: [],
      center: [],
      right: [],
    };
    for (const src of sources) {
      const lean = src.biasScores?.politicalLean ?? 50;
      const bucket = leanToBucket(lean);
      if (bucket === "center") groups.center.push(src);
      else if (bucket === "far-left" || bucket === "left" || bucket === "center-left") groups.left.push(src);
      else groups.right.push(src);
    }
    const byLean = (a: StorySource, b: StorySource) =>
      (a.biasScores?.politicalLean ?? 50) - (b.biasScores?.politicalLean ?? 50);
    groups.left.sort(byLean);
    groups.center.sort(byLean);
    groups.right.sort(byLean);
    return groups;
  }, [sources]);

  if (sources.length === 0) return null;

  const counts = {
    left: bucketed.left.length,
    center: bucketed.center.length,
    right: bucketed.right.length,
  };
  const total = sources.length;

  // Compact lean-distribution teaser on the collapsed toggle: three segments
  // sized by count, so a reader sees the L/C/R balance before expanding.
  const teaser = (
    <span className="dd-ledger__teaser" aria-hidden="true">
      {(["left", "center", "right"] as const).map((k) =>
        counts[k] > 0 ? (
          <span
            key={k}
            className="dd-ledger__teaser-seg"
            style={{
              flexGrow: counts[k],
              backgroundColor: getLeanColor(k === "left" ? 28 : k === "center" ? 50 : 72),
            }}
          />
        ) : null,
      )}
    </span>
  );

  const body = (
    <div className="dd-ledger__bands">
      {LEAN_BANDS.map((band) => {
        const bandSources = bucketed[band.key];
        if (bandSources.length === 0) return null;
        return (
          <section className="dd-ledger__band" key={band.key} aria-label={`${band.label} sources`}>
            <div
              className="dd-ledger__band-head"
              style={{ "--band-lean": getLeanColor(band.anchor) } as React.CSSProperties}
            >
              <span className="dd-ledger__band-name text-meta">{band.label}</span>
              <span className="dd-ledger__band-count text-data" aria-hidden="true">{bandSources.length}</span>
              <span className="dd-ledger__band-rule" aria-hidden="true" />
            </div>
            <ul className="dd-ledger__list" role="list">
              {bandSources.map((src, i) => {
                const lean = src.biasScores?.politicalLean ?? 50;
                const bucket = leanToBucket(lean);
                const label = `${src.name}. ${leanLabel(lean)}. ${tierLabel(src.tier)}.`;
                const inner = (
                  <>
                    <LedgerMono name={src.name} bucket={bucket} />
                    <span className="dd-ledger__name">{src.name}</span>
                    <span className="dd-ledger__meta">
                      <span className="dd-ledger__tier text-data" aria-hidden="true">{tierAbbr(src.tier)}</span>
                      <span
                        className="dd-ledger__lean text-data"
                        style={{ color: getLeanColor(lean) }}
                        aria-hidden="true"
                      >
                        {lean}
                      </span>
                    </span>
                  </>
                );
                return (
                  <li key={`${src.name}-${i}`} className="dd-ledger__row">
                    {src.url && src.url !== "#" ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="dd-ledger__link"
                        aria-label={label}
                      >
                        {inner}
                      </a>
                    ) : (
                      <span className="dd-ledger__link dd-ledger__link--static" aria-label={label}>
                        {inner}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );

  return (
    <div className={`dd-ledger${open ? " dd-ledger--open" : ""}`}>
      {defaultOpen ? (
        <>
          <h3 className="dd-section-label text-meta dd-ledger__label">
            Sources <span className="text-data dd-ledger__count">({total})</span>
          </h3>
          {body}
        </>
      ) : (
        <>
          <button
            type="button"
            className="dd-ledger__toggle"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="dd-ledger-body"
          >
            <span className="dd-ledger__toggle-label text-meta">
              {open ? "Hide sources" : `All ${total} sources`}
            </span>
            {!open && teaser}
            <span className="dd-ledger__toggle-caret" aria-hidden="true">{open ? "▾" : "▸"}</span>
          </button>
          <div id="dd-ledger-body" hidden={!open}>
            {body}
          </div>
        </>
      )}
    </div>
  );
}
