"use client";

/* ===========================================================================
   ReelScrubber — the timeline echo.
   A drawn ink track with one color node per frame, a progress fill that
   tracks scroll position, and a rolling readout naming the current voice.
   Click a node to jump; the reel also responds to scroll / drag / arrows.
   =========================================================================== */

export interface ScrubNode {
  key: string;
  label: string;
  sublabel: string;
  /** CSS color value, e.g. "var(--hist-persp-a)" */
  color: string;
}

interface ReelScrubberProps {
  nodes: ScrubNode[];
  activeIndex: number;
  /** Continuous scroll progress across the reel, 0..1 */
  fraction: number;
  onSelect: (index: number) => void;
}

/* The track is already inset from the viewport by the scrubber's padding, so
   nodes run the full 0..100% and edge glows have room to breathe. */
const posFor = (i: number, n: number) => (n <= 1 ? 50 : (i / (n - 1)) * 100);

export default function ReelScrubber({ nodes, activeIndex, fraction, onSelect }: ReelScrubberProps) {
  if (nodes.length === 0) return null;
  const active = nodes[Math.min(activeIndex, nodes.length - 1)];
  const fillWidth = Math.max(0, Math.min(1, fraction)) * 100;

  return (
    <nav className="hist-scrubber" aria-label="Jump between accounts">
      <div className="hist-scrubber__readout" aria-live="polite">
        <span className="hist-scrubber__readout-label">{active.label}</span>
        {active.sublabel && (
          <span className="hist-scrubber__readout-sub">{active.sublabel}</span>
        )}
      </div>

      <div className="hist-scrubber__track">
        <span className="hist-scrubber__rail" aria-hidden="true" />
        <span
          className="hist-scrubber__fill"
          style={{ width: `${fillWidth}%` }}
          aria-hidden="true"
        />
        {nodes.map((n, i) => (
          <button
            key={n.key}
            type="button"
            className={`hist-scrubber__node${i === activeIndex ? " hist-scrubber__node--active" : ""}`}
            style={{
              left: `${posFor(i, nodes.length)}%`,
              ["--node-color" as string]: n.color,
            }}
            aria-label={`Go to ${n.label}`}
            aria-current={i === activeIndex ? "true" : undefined}
            onClick={() => onSelect(i)}
          />
        ))}
      </div>
    </nav>
  );
}
