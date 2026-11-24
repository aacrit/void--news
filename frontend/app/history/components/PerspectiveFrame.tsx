"use client";

import type { Perspective, MediaItem } from "../types";

/* ===========================================================================
   PerspectiveFrame — one voice, one screen (the reel's essence frame).
   Shows only the sharpest argument, one primary-source quote, and what this
   side leaves out. Depth lives behind "Read the full account".
   =========================================================================== */

interface PerspectiveFrameProps {
  perspective: Perspective;
  index: number;
  total: number;
  background: MediaItem | null;
  active: boolean;
  onReadFull: () => void;
}

export default function PerspectiveFrame({
  perspective,
  index,
  total,
  background,
  active,
  onReadFull,
}: PerspectiveFrameProps) {
  const lead = perspective.keyNarratives[0];
  const quote = perspective.primarySources[0];
  const omissions = perspective.omissions.slice(0, 2);
  const color = `var(--hist-persp-${perspective.color})`;

  return (
    <section
      className={`hist-reel__frame hist-frame${active ? " hist-frame--active" : ""}`}
      style={{ ["--persp-color" as string]: color }}
      aria-roledescription="testimony"
      aria-label={`${perspective.viewpointName}, account ${index + 1} of ${total}`}
    >
      {background && (
        <div className="hist-frame__bg" aria-hidden="true">
          <img src={background.url} alt="" loading="lazy" onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = "none"; }} />
        </div>
      )}
      <div className="hist-frame__scrim" aria-hidden="true" />

      <div className="hist-frame__content">
        <span className="hist-frame__index">{String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}</span>
        <span className="hist-frame__eyebrow">
          {perspective.viewpointType}
          {perspective.geographicAnchor ? ` · ${perspective.geographicAnchor}` : ""}
        </span>
        <h2 className="hist-frame__name">{perspective.viewpointName}</h2>

        {lead && <p className="hist-frame__lead">{lead}</p>}

        {quote && (
          <blockquote className="hist-frame__quote">
            <p className="hist-frame__quote-text">&ldquo;{quote.text}&rdquo;</p>
            <cite className="hist-frame__quote-cite">
              {quote.author}
              {quote.work ? `, ${quote.work}` : ""}
            </cite>
          </blockquote>
        )}

        {omissions.length > 0 && (
          <div className="hist-frame__omits">
            <span className="hist-frame__omits-label">What this side leaves out</span>
            <ul className="hist-frame__omits-list">
              {omissions.map((o, i) => (
                <li key={i}>{o}</li>
              ))}
            </ul>
          </div>
        )}

        <button type="button" className="hist-frame__read" onClick={onReadFull}>
          Read the full account
          <span className="hist-frame__read-arrow" aria-hidden="true">→</span>
        </button>
      </div>
    </section>
  );
}
