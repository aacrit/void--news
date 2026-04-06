"use client";

import { useMemo } from "react";
import type { HistoryRegion, HistoricalEvent } from "../types";

/* ===========================================================================
   CartographerStrip — Compact SVG atlas strip for the timeline top zone
   Replaces era pills when [globe] toggle is active. Shows simplified
   continental outlines with event pins. Region click → ghost-filter.
   Focused event pin pulses. Organic ink aesthetic.
   =========================================================================== */

/* Region paths from MapView — simplified continental outlines */
const REGION_PATHS: Record<string, { d: string; cx: number; cy: number }> = {
  africa: {
    d: "M240,130 C238,135 235,140 232,150 C228,165 225,180 226,195 C228,210 232,218 238,222 C242,225 248,224 252,218 C256,210 258,198 258,185 C258,170 255,155 250,142 C247,136 244,132 240,130Z",
    cx: 242, cy: 175,
  },
  europe: {
    d: "M225,90 C228,92 234,96 238,100 C242,104 248,106 252,103 C256,100 258,95 256,90 C254,85 250,82 245,80 C240,78 235,80 230,84 C227,86 225,88 225,90Z",
    cx: 242, cy: 92,
  },
  americas: {
    d: "M100,60 C105,65 108,75 108,88 C108,100 105,115 102,130 C100,140 98,152 100,165 C102,180 108,195 112,210 C114,220 112,228 108,232 C105,235 100,234 98,228 C95,220 92,208 88,195 C85,180 82,165 82,150 C82,135 84,120 88,108 C90,98 94,88 96,78 C97,70 98,64 100,60Z",
    cx: 100, cy: 145,
  },
  "east-asia": {
    d: "M340,100 C345,102 350,108 354,115 C356,120 358,128 356,135 C354,140 350,142 345,140 C340,138 336,132 334,125 C332,118 332,110 335,104 C336,102 338,100 340,100Z",
    cx: 345, cy: 120,
  },
  "south-asia": {
    d: "M305,135 C308,138 312,145 314,155 C316,165 314,172 310,175 C306,178 302,176 300,170 C298,164 298,155 300,148 C302,142 304,138 305,135Z",
    cx: 307, cy: 155,
  },
  "southeast-asia": {
    d: "M340,155 C344,158 348,162 350,168 C352,175 350,182 346,185 C342,188 338,186 335,180 C332,174 332,166 335,160 C336,157 338,155 340,155Z",
    cx: 342, cy: 170,
  },
  "middle-east": {
    d: "M272,115 C276,118 280,125 282,132 C284,138 282,144 278,146 C274,148 270,145 268,140 C265,134 265,126 268,120 C270,117 271,115 272,115Z",
    cx: 275, cy: 130,
  },
  oceania: {
    d: "M360,205 C365,208 370,215 372,222 C374,228 372,234 368,236 C364,238 360,235 358,228 C356,222 356,214 358,208 C359,206 359,205 360,205Z",
    cx: 365, cy: 220,
  },
  "central-asia": {
    d: "M295,95 C300,98 305,104 308,110 C310,115 308,120 304,122 C300,124 296,122 294,117 C292,112 292,105 294,100 C295,97 295,96 295,95Z",
    cx: 300, cy: 108,
  },
};

const REGION_LABELS: Record<string, string> = {
  africa: "Africa",
  europe: "Europe",
  americas: "Americas",
  "east-asia": "East Asia",
  "south-asia": "South Asia",
  "southeast-asia": "SE Asia",
  "middle-east": "Middle East",
  oceania: "Oceania",
  "central-asia": "C. Asia",
};

function getEventPosition(event: HistoricalEvent): { x: number; y: number } | null {
  const region = event.regions[0];
  if (!region || region === "global") return null;
  const regionData = REGION_PATHS[region];
  if (!regionData) return null;
  const hash = event.slug.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return {
    x: regionData.cx + ((hash % 12) - 6),
    y: regionData.cy + ((hash % 8) - 4),
  };
}

interface CartographerStripProps {
  events: HistoricalEvent[];
  focusedIndex: number;
  activeRegion: HistoryRegion | null;
  currentEra: string;
  onRegionClick: (region: HistoryRegion) => void;
  onEventClick: (event: HistoricalEvent) => void;
}

export default function CartographerStrip({
  events,
  focusedIndex,
  activeRegion,
  currentEra,
  onRegionClick,
  onEventClick,
}: CartographerStripProps) {
  /* Compute pin data with focused state */
  const pins = useMemo(() => {
    return events.map((event, i) => {
      const pos = getEventPosition(event);
      if (!pos) return null;
      const isFocused = i === focusedIndex;
      const isActiveEra = event.era === currentEra;
      const isActiveRegion = !activeRegion || event.regions.includes(activeRegion);
      return { event, pos, isFocused, isActiveEra, isActiveRegion, index: i };
    }).filter(Boolean) as {
      event: HistoricalEvent;
      pos: { x: number; y: number };
      isFocused: boolean;
      isActiveEra: boolean;
      isActiveRegion: boolean;
      index: number;
    }[];
  }, [events, focusedIndex, currentEra, activeRegion]);

  /* Region event counts for aria labels */
  const regionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const event of events) {
      const r = event.regions[0];
      if (r) counts[r] = (counts[r] || 0) + 1;
    }
    return counts;
  }, [events]);

  return (
    <div className="hist-carto-strip" role="img" aria-label="World map showing event locations">
      <svg
        className="hist-carto-strip__svg"
        viewBox="0 60 460 180"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Ink-stipple texture */}
        <defs>
          <filter id="hist-carto-stipple">
            <feTurbulence type="fractalNoise" baseFrequency="1.2" numOctaves="2" seed="7" />
            <feColorMatrix type="saturate" values="0" />
            <feComponentTransfer>
              <feFuncA type="discrete" tableValues="0 0.03" />
            </feComponentTransfer>
          </filter>
          <filter id="hist-carto-wobble" x="-2%" y="-2%" width="104%" height="104%">
            <feTurbulence type="turbulence" baseFrequency="0.015" numOctaves="3" seed="42" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.5" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>

        {/* Ocean background */}
        <rect x="0" y="60" width="460" height="180" fill="var(--hist-bg-card)" />
        <rect x="0" y="60" width="460" height="180" filter="url(#hist-carto-stipple)" opacity="0.2" />

        {/* Continental regions */}
        {Object.entries(REGION_PATHS).map(([id, data]) => {
          if (!data.d) return null;
          const isActive = activeRegion === id;
          return (
            <g key={id}>
              {/* Land fill */}
              <path
                d={data.d}
                className={`hist-carto-strip__region${isActive ? " hist-carto-strip__region--active" : ""}`}
                filter="url(#hist-carto-wobble)"
                onClick={() => onRegionClick(id as HistoryRegion)}
                role="button"
                aria-label={`${REGION_LABELS[id] || id}, ${regionCounts[id] || 0} events`}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onRegionClick(id as HistoryRegion);
                  }
                }}
              />
              {/* Feathered border */}
              <path
                d={data.d}
                fill="none"
                stroke="var(--hist-border)"
                strokeWidth="0.6"
                opacity="0.4"
                filter="url(#hist-carto-wobble)"
              />
            </g>
          );
        })}

        {/* Event pins */}
        {pins.map(({ event, pos, isFocused, isActiveEra, isActiveRegion }) => {
          const pinOpacity = !isActiveRegion ? 0.1 : isActiveEra ? 0.9 : 0.25;
          const severityColor =
            event.severity === "catastrophic" ? "#8B0000" :
            event.severity === "critical" ? "#B44C00" :
            "var(--hist-brass)";
          return (
            <circle
              key={event.slug}
              cx={pos.x}
              cy={pos.y}
              r={isFocused ? 5 : 3.5}
              fill={severityColor}
              opacity={pinOpacity}
              className={`hist-carto-strip__pin${isFocused ? " hist-carto-strip__pin--focused" : ""}`}
              onClick={(e) => {
                e.stopPropagation();
                onEventClick(event);
              }}
              style={{ cursor: "pointer" }}
            >
              <title>{event.title} ({event.datePrimary})</title>
            </circle>
          );
        })}
      </svg>

      {/* Active region dismissal pill */}
      {activeRegion && (
        <button
          className="hist-carto-strip__dismiss"
          onClick={() => onRegionClick(activeRegion)}
          type="button"
          aria-label={`Clear ${REGION_LABELS[activeRegion]} filter`}
        >
          {REGION_LABELS[activeRegion]} <span aria-hidden="true">&times;</span>
        </button>
      )}
    </div>
  );
}
