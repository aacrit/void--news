'use client';

export interface ScrubNode {
  key: string;
  label: string;
  color: string;
}

interface RevoltScrubberProps {
  nodes: ScrubNode[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

const posFor = (i: number, n: number) => (n <= 1 ? 50 : (i / (n - 1)) * 100);

/* The reel's timeline echo: one diamond node per frame, colored by phase. */
export default function RevoltScrubber({ nodes, activeIndex, onSelect }: RevoltScrubberProps) {
  if (nodes.length === 0) return null;
  const active = nodes[Math.min(activeIndex, nodes.length - 1)];

  return (
    <nav className="rev-scrubber" aria-label="Jump between phases">
      <div className="rev-scrubber__readout" aria-live="polite">{active.label}</div>
      <div className="rev-scrubber__track">
        <span className="rev-scrubber__rail" aria-hidden="true" />
        {nodes.map((n, i) => (
          <button
            key={n.key}
            type="button"
            className={`rev-scrubber__node${i === activeIndex ? ' rev-scrubber__node--active' : ''}`}
            style={{ left: `${posFor(i, nodes.length)}%`, ['--node-color' as string]: n.color }}
            aria-label={`Go to ${n.label}`}
            aria-current={i === activeIndex ? 'true' : undefined}
            onClick={() => onSelect(i)}
          />
        ))}
      </div>
    </nav>
  );
}
