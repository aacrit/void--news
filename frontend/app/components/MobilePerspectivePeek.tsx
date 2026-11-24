"use client";

import type { Story } from "../lib/types";
import Sigil from "./Sigil";

interface MobilePerspectivePeekProps {
  story: Story;
  onClose: () => void;
  onOpenDeepDive: () => void;
}

export default function MobilePerspectivePeek({
  story,
  onClose,
  onOpenDeepDive,
}: MobilePerspectivePeekProps) {
  const deepDive = story.deepDive;
  const sources = deepDive?.sources || [];
  const hasSources = sources.length > 0;
  const topSources = hasSources
    ? [...sources]
        .sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0))
        .slice(0, 3)
    : [];

  return (
    <div className="mpp" onClick={(e) => e.stopPropagation()}>
      {/* Header */}
      <div className="mpp__header">
        <h3 className="mpp__title">Source perspectives</h3>
        <button
          type="button"
          className="mpp__close"
          onClick={onClose}
          aria-label="Close perspectives"
        >
          ✕
        </button>
      </div>

      {/* Sources grid */}
      {hasSources ? (
        <div className="mpp__sources">
          {topSources.map((source) => (
            <a
              key={source.name}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mpp__source-card"
            >
              <div className="mpp__source-sigil">
                {/* Use story Sigil — sources don't have individual sigilData */}
                <Sigil data={story.sigilData} size="sm" instant />
              </div>
              <h4 className="mpp__source-headline">{source.articleTitle || story.title}</h4>
              <p className="mpp__source-outlet">{source.name}</p>
            </a>
          ))}
        </div>
      ) : (
        <div className="mpp__empty">
          <p className="mpp__empty-text">Deep dive data loading...</p>
        </div>
      )}

      {/* Consensus/Divergence summary */}
      {deepDive && (deepDive.divergence.length > 0 || deepDive.consensus.length > 0) && (
        <div className="mpp__divergence">
          {deepDive.divergence.length > deepDive.consensus.length ? (
            <span className="mpp__divergence-label mpp__divergence-label--split">
              Divergent coverage
            </span>
          ) : deepDive.divergence.length > 0 ? (
            <span className="mpp__divergence-label mpp__divergence-label--mixed">
              Mixed perspectives
            </span>
          ) : (
            <span className="mpp__divergence-label mpp__divergence-label--consensus">
              Source consensus
            </span>
          )}
        </div>
      )}

      {/* CTA */}
      <button
        type="button"
        className="mpp__cta"
        onClick={(e) => {
          e.preventDefault();
          onOpenDeepDive();
        }}
      >
        Open deep dive
      </button>
    </div>
  );
}
