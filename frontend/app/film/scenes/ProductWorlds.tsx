"use client";

import {
  VOID_CIRCLE, BEAM_CURVE, SRC_DOTS, WAVE_HEIGHTS,
} from "../constants";
import { PRODUCT_FAMILY } from "../data";

/* ==========================================================================
   ProductWorlds — Scene V: "The Worlds"
   6 product page previews in native design language.
   Prologue: 2-column grid. Manifesto: 3-column with clickable links.
   ========================================================================== */

interface Props {
  mode: "prologue" | "manifesto";
  active: boolean;
}

/* ── Mini preview components (CSS-rendered, no images) ── */

function FeedPreview() {
  return (
    <div className="film-preview film-preview--feed">
      <div className="film-preview__cols">
        <div className="film-preview__col film-preview__col--lead">
          <div className="film-preview__headline-bar" />
          <div className="film-preview__text-lines"><div /><div /><div /></div>
          <svg viewBox="0 0 32 32" className="film-preview__sigil" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <path d={VOID_CIRCLE} stroke="currentColor" strokeWidth="2.5" opacity={0.5} />
            <path d={BEAM_CURVE} stroke="currentColor" strokeWidth="2.5" opacity={0.7} />
          </svg>
        </div>
        <div className="film-preview__col film-preview__col--side">
          <div className="film-preview__card-mini" />
          <div className="film-preview__card-mini" />
          <div className="film-preview__card-mini" />
        </div>
      </div>
    </div>
  );
}

function WeeklyPreview() {
  return (
    <div className="film-preview film-preview--weekly">
      <div className="film-preview__masthead" />
      <div className="film-preview__cover-hl" />
      <div className="film-preview__cover-sub" />
      <div className="film-preview__mag-cols"><div /><div /><div /></div>
    </div>
  );
}

function PaperPreview() {
  return (
    <div className="film-preview film-preview--paper">
      <div className="film-preview__broadsheet-hdr" />
      <div className="film-preview__broadsheet-rule" />
      <div className="film-preview__broadsheet-hl" />
      <div className="film-preview__broadsheet-cols"><div /><div /><div /><div /></div>
    </div>
  );
}

function SourcesPreview() {
  return (
    <div className="film-preview film-preview--sources">
      <div className="film-preview__spectrum-bar" />
      <div className="film-preview__dots">
        {SRC_DOTS.map((d, i) => (
          <div key={i} className="film-preview__src-dot" style={d} />
        ))}
      </div>
    </div>
  );
}

function OnairPreview() {
  return (
    <div className="film-preview film-preview--onair">
      <div className="film-preview__waveform">
        {WAVE_HEIGHTS.map((h, i) => (
          <div key={i} className="film-preview__wave-bar" style={{ height: h }} />
        ))}
      </div>
      <div className="film-preview__hosts"><span>A</span><span>B</span></div>
    </div>
  );
}

function ShipPreview() {
  return (
    <div className="film-preview film-preview--ship">
      <div className="film-preview__kanban">
        <div className="film-preview__kanban-col">
          <div className="film-preview__kanban-card" /><div className="film-preview__kanban-card" />
        </div>
        <div className="film-preview__kanban-col">
          <div className="film-preview__kanban-card" />
        </div>
        <div className="film-preview__kanban-col">
          <div className="film-preview__kanban-card" /><div className="film-preview__kanban-card" /><div className="film-preview__kanban-card" />
        </div>
      </div>
    </div>
  );
}

const PREVIEW_MAP: Record<string, React.FC> = {
  feed: FeedPreview, weekly: WeeklyPreview, paper: PaperPreview,
  sources: SourcesPreview, onair: OnairPreview, ship: ShipPreview,
};

export default function ProductWorlds({ mode, active }: Props) {
  return (
    <div className={`film-worlds film-worlds--${mode}`} aria-hidden="true">
      <div className="film-worlds__grid">
        {PRODUCT_FAMILY.map((w, i) => {
          const Preview = PREVIEW_MAP[w.palette];
          const inner = (
            <>
              <div className="film-worlds__preview">{Preview && <Preview />}</div>
              <div className="film-worlds__text">
                <span className="film-worlds__cli">{w.cli}</span>
                <span className="film-worlds__name">{w.name}</span>
                <span className="film-worlds__desc">{w.desc}</span>
              </div>
            </>
          );

          const className = `film-world film-world--${w.palette}${active ? " film-world--in" : ""}`;
          const style = { transitionDelay: `${300 + i * 180}ms` };

          // Manifesto: clickable links. Prologue: static cards.
          return mode === "manifesto" ? (
            <a key={w.cli} href={`/void--news${w.href}`} className={className} style={style}>
              {inner}
            </a>
          ) : (
            <div key={w.cli} className={className} style={style}>
              {inner}
            </div>
          );
        })}
      </div>
    </div>
  );
}
