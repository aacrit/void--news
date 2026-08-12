"use client";

import type { SigilData } from "../lib/types";
import {
  getLeanColor,
  leanLabel,
  leanLabelState,
  NO_CLEAR_LEAN_LABEL,
  CONTESTED_LABEL,
} from "../lib/biasColors";
import LeanCoverageBar from "./LeanCoverageBar";

interface BiasSnapshotProps {
  data: SigilData;
  sourceCount: number;
  /** Layout variant.
   *   - "inline": 28px tall horizontal strip — sits below the headline
   *     (mobile + Deep Dive header). Lean dot · rigor pip · opinion pill · "N sources".
   *   - "rail": vertical compact column for the desktop Deep Dive right rail.
   *     Three primary axes stacked, each with a small bar + label. */
  variant?: "inline" | "rail";
  /** Suppress the embedded LeanCoverageBar. Set true where a fuller coverage
   *  view (e.g. the Deep Dive's DeepDiveSpectrum) already plots the L->R
   *  distribution, so the small segmented bar would be a redundant restatement.
   *  Defaults false — StoryCard and the mobile feed keep the bar (their only
   *  coverage signal). */
  hideCoverageBar?: boolean;
}

/* ---------------------------------------------------------------------------
   BiasSnapshot — Compact bias signal for above-the-fold placement
   Surfaces the three primary axes (lean, coverage/rigor, opinion) without
   the full SixLenses real estate. Full breakdown sits behind a disclosure.
   --------------------------------------------------------------------------- */

export default function BiasSnapshot({ data, sourceCount, variant = "inline", hideCoverageBar = false }: BiasSnapshotProps) {
  // False-center band suppression: inside [48,52] the confident "Center" label
  // overstates the signal. "Contested" when both wings are present, else "No
  // clear lean"; the dot goes neutral (or contested red). Outside the band the
  // existing directional label + color stand. (BiasSnapshot shows the label
  // text, not a numeric lean, so there is no separate score to withhold.)
  const leanState = leanLabelState(data.politicalLean, data.biasSpread, sourceCount);
  const leanColor = leanState === "contested"
    ? "var(--sense-high)"
    : leanState === "no-clear-lean"
      ? "var(--fg-tertiary)"
      : getLeanColor(data.politicalLean);
  const lean = leanState === "no-clear-lean"
    ? NO_CLEAR_LEAN_LABEL
    : leanState === "contested"
      ? CONTESTED_LABEL
      : leanLabel(data.politicalLean);
  const opinion = data.opinionLabel;
  // "Reporting" is the default classification for most stories, so the pill is
  // redundant noise there. Show the Type pill ONLY for the meaningful values
  // (Analysis / Opinion / Editorial).
  const showOpinion = opinion !== "Reporting";
  const rigor = Math.round(data.factualRigor);

  if (variant === "rail") {
    return (
      <aside className="bias-snapshot bias-snapshot--rail" aria-label="Bias snapshot">
        <div className="bias-snapshot__row">
          <span className="bias-snapshot__label">Lean</span>
          <span className="bias-snapshot__dot" style={{ background: leanColor }} aria-hidden="true" />
          <span className="bias-snapshot__value">{lean}</span>
        </div>
        <div className="bias-snapshot__row">
          <span className="bias-snapshot__label">Rigor</span>
          <span className="bias-snapshot__bar" aria-hidden="true">
            <span className="bias-snapshot__bar-fill" style={{ width: `${rigor}%` }} />
          </span>
          <span className="bias-snapshot__value">{rigor}</span>
        </div>
        {showOpinion && (
          <div className="bias-snapshot__row">
            <span className="bias-snapshot__label">Type</span>
            <span className="bias-snapshot__pill">{opinion}</span>
          </div>
        )}
        <div className="bias-snapshot__row bias-snapshot__row--sources">
          <span className="bias-snapshot__label">Sources</span>
          <span className="bias-snapshot__value bias-snapshot__value--strong">{sourceCount}</span>
        </div>
        {!hideCoverageBar && <LeanCoverageBar spread={data.biasSpread} />}
      </aside>
    );
  }

  // inline variant — horizontal strip, fits under the Deep Dive headline
  return (
    <div className="bias-snapshot bias-snapshot--inline" aria-label="Bias snapshot">
      <span className="bias-snapshot__chip">
        <span className="bias-snapshot__dot" style={{ background: leanColor }} aria-hidden="true" />
        <span className="bias-snapshot__value">{lean}</span>
      </span>
      <span className="bias-snapshot__sep" aria-hidden="true">·</span>
      <span className="bias-snapshot__chip">
        <span className="bias-snapshot__bar bias-snapshot__bar--inline" aria-hidden="true">
          <span className="bias-snapshot__bar-fill" style={{ width: `${rigor}%` }} />
        </span>
        <span className="bias-snapshot__value">Rigor {rigor}</span>
      </span>
      {showOpinion && (
        <>
          <span className="bias-snapshot__sep" aria-hidden="true">·</span>
          <span className="bias-snapshot__pill">{opinion}</span>
        </>
      )}
      <span className="bias-snapshot__sep" aria-hidden="true">·</span>
      <span className="bias-snapshot__sources">{sourceCount} {sourceCount === 1 ? "source" : "sources"}</span>
      {!hideCoverageBar && <LeanCoverageBar spread={data.biasSpread} compact />}
    </div>
  );
}
