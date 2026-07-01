"use client";

import { useState, useEffect } from "react";
import type { SigilData } from "../lib/types";
import { hapticLight, hapticMicro } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";

/* ===========================================================================
   SixLenses — ink-stamp 6-axis bias scores.

   Renders the 6-axis bias breakdown (Political Lean, Sensationalism, Opinion,
   Factual Rigor, Framing, Agreement) as an ink-stamp grid from a SigilData
   object. Ported verbatim out of DeepDive.tsx so it survives that modal's
   eventual deletion. Uses the .dd-lenses* / .dd-lens__* / .dd-bias-toggle*
   classes from the globally-imported components.css (unchanged).
   =========================================================================== */

const SIX_AXES: { id: string; name: string; key: keyof SigilData }[] = [
  { id: "lean",           name: "Political Lean",  key: "politicalLean" },
  { id: "sensationalism", name: "Sensationalism",   key: "sensationalism" },
  { id: "opinion",        name: "Opinion",           key: "opinionFact" },
  { id: "rigor",          name: "Factual Rigor",     key: "factualRigor" },
  { id: "framing",        name: "Framing",           key: "framing" },
  { id: "tracking",       name: "Agreement",         key: "agreement" },
];

export default function SixLenses({ sigilData, visible }: { sigilData: SigilData; visible: boolean }) {
  const [activeAxis, setActiveAxis] = useState<string | null>(null);
  const [isMobileLens, setIsMobileLens] = useState(false);
  // Phase 2 redesign: All lenses hidden by default on mobile behind single button
  const [showAllLenses, setShowAllLenses] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobileLens(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobileLens(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  /* Priority order per memory rule: lean is hero, rigor second, opinion third */
  const PRIMARY_IDS = new Set(["lean", "rigor", "opinion"]);
  const primaryAxes = SIX_AXES.filter(a => PRIMARY_IDS.has(a.id));
  const secondaryAxes = SIX_AXES.filter(a => !PRIMARY_IDS.has(a.id));

  const renderAxis = (axis: typeof SIX_AXES[0], i: number) => {
    const score = sigilData[axis.key] as number;
    const dotCount = Math.max(1, Math.round((score / 100) * 5));
    const isActive = activeAxis === axis.id;
    return (
      <button
        key={axis.id}
        className={`dd-lens${isActive ? " dd-lens--active" : ""}${visible ? " dd-lens--visible" : ""}`}
        style={{ "--lens-delay": `${450 + i * 50}ms` } as React.CSSProperties}
        onClick={() => { hapticMicro(); setActiveAxis(isActive ? null : axis.id); }}
        aria-expanded={isActive}
        aria-label={`${axis.name}: ${score} out of 100`}
      >
        <span className="dd-lens__score">{score}</span>
        <span className="dd-lens__dots" aria-hidden="true">
          {Array.from({ length: 5 }, (_, di) => (
            <span key={di} className={`dd-lens__pip${di < dotCount ? " dd-lens__pip--filled" : ""}`} />
          ))}
        </span>
        <span className="dd-lens__name">{axis.name}</span>
      </button>
    );
  };

  return (
    <div className="dd-lenses">
      {isMobileLens ? (
        <>
          {/* Phase 2 redesign: All lenses hidden behind single "Bias Analysis" button */}
          <button
            className={`dd-bias-toggle text-meta${showAllLenses ? " dd-bias-toggle--open" : ""}`}
            onClick={() => { hapticLight(); setShowAllLenses(!showAllLenses); }}
            aria-expanded={showAllLenses}
            aria-controls="dd-lenses-collapsible"
          >
            <span className="dd-bias-toggle__label">
              {showAllLenses ? "Hide analysis" : "Bias Analysis"}
            </span>
            <span className="dd-bias-toggle__caret" aria-hidden="true">
              {showAllLenses ? "▾" : "▸"}
            </span>
          </button>

          <div
            id="dd-lenses-collapsible"
            className={`dd-lenses__collapsible${showAllLenses ? " dd-lenses__collapsible--open" : ""}`}
            aria-hidden={!showAllLenses}
          >
            <h3 className="dd-section-label text-meta dd-lenses__collapsible-label">Six Lenses</h3>
            <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
              {SIX_AXES.map((axis, i) => renderAxis(axis, i))}
            </div>
          </div>
        </>
      ) : (
        <>
          <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Six Lenses</h3>
          <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
            {SIX_AXES.map((axis, i) => renderAxis(axis, i))}
          </div>
        </>
      )}
      <a href={`${BASE_PATH}/sources/#methodology`} className="dd-lenses__link text-meta">
        How we score
      </a>
    </div>
  );
}
