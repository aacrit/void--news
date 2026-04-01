"use client";

import { useMemo } from "react";
import type { StorySource } from "../lib/types";

/* ---------------------------------------------------------------------------
   FramingContrastStrip — Per-source framing signal summary
   Shows at a glance which sources use charged language and which are clean.
   Renders below the cluster summary in DeepDive Summary tab.
   --------------------------------------------------------------------------- */

interface FramingContrastStripProps {
  sources: StorySource[];
}

interface SourceSignalRow {
  name: string;
  signals: number;
  tier: string;
}

export default function FramingContrastStrip({ sources }: FramingContrastStripProps) {
  const { rows, maxSignals, omissionSummary } = useMemo(() => {
    const computed: SourceSignalRow[] = [];
    const omissionMap = new Map<string, number>();

    for (const src of sources) {
      let signals = 0;

      // Count charged matches
      const charged = src.lensData?.framingRationale?.chargedMatches;
      if (charged) {
        for (const m of charged) signals += m.count;
      }

      // Count entity sentiments with non-neutral polarity
      const sentiments = src.lensData?.leanRationale?.entitySentiments;
      if (sentiments) {
        for (const s of Object.values(sentiments)) {
          if (Math.abs(s) > 0.05) signals++;
        }
      }

      computed.push({ name: src.name, signals, tier: src.tier });

      // Collect omission data
      const missing = src.lensData?.framingRationale?.entitiesMissing;
      if (missing) {
        for (const entity of missing) {
          omissionMap.set(entity, (omissionMap.get(entity) || 0) + 1);
        }
      }
    }

    // Sort: most signals first, then clean sources
    computed.sort((a, b) => b.signals - a.signals);
    const max = computed.length > 0 ? computed[0].signals : 0;

    // Entities omitted by 2+ sources
    const significantOmissions = Array.from(omissionMap.entries())
      .filter(([, count]) => count >= 2)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map(([entity, count]) => ({ entity, count }));

    return { rows: computed, maxSignals: max, omissionSummary: significantOmissions };
  }, [sources]);

  // Don't render if no meaningful data
  if (rows.length === 0) return null;

  const hasSignals = rows.some((r) => r.signals > 0);
  if (!hasSignals && omissionSummary.length === 0) return null;

  return (
    <div className="framing-strip" role="region" aria-label="Framing contrast across sources">
      <h4 className="framing-strip__header">Framing contrast</h4>

      {hasSignals && (
        <div className="framing-strip__rows">
          {rows.map((row) => (
            <div key={row.name} className="framing-strip__row">
              <span className="framing-strip__name">{row.name}</span>
              <div className="framing-strip__bar-track">
                {row.signals > 0 ? (
                  <div
                    className="framing-strip__bar-fill"
                    style={{ width: `${Math.max(8, (row.signals / maxSignals) * 100)}%` }}
                  />
                ) : (
                  <span className="framing-strip__clean">clean</span>
                )}
              </div>
              <span className="framing-strip__count">
                {row.signals > 0 ? row.signals : "0"}
              </span>
            </div>
          ))}
        </div>
      )}

      {omissionSummary.length > 0 && (
        <div className="framing-strip__omission">
          {omissionSummary.map(({ entity, count }) => (
            <span key={entity} className="framing-strip__omission-item">
              <span className="framing-strip__omission-count">{count}/{sources.length}</span>
              {" omit "}
              <span className="framing-strip__omission-entity">{entity}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
