"use client";

import { useState, useMemo, useRef, useEffect, useLayoutEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  LEAN_BASELINES,
  leanToBucket,
  leanLabel,
  leanShapeLabel,
  type LeanCategory,
  type WingCounts,
} from "../lib/biasColors";
import { sourceLogoUrl } from "../lib/sourceLogos";
import {
  packBench,
  benchRows,
  BENCH_FAVICON_MIN,
  BENCH_GAP,
  type BenchPack,
} from "../lib/bench";

/* ---------------------------------------------------------------------------
   Bench — who is sitting where, left to right.

   Replaces the KDE wave (2026-09-21). The wave was a smoothed density over a
   distribution that is not continuous: 74% of measured articles sit EXACTLY on
   one of the seven outlet baselines and 87% within two points of one, so the
   curve drew hills between spikes that nothing stands on, and a reader could
   not count anything off it. It also needed a mean plumb line to say which way
   the story went, and a mean returns the empty middle of a bimodal roster.

   The Bench is the same seven rungs the card's register uses, at full size:
   one column per rung, one mark per source, the column's height IS the count.
   Nothing is smoothed, nothing is interpolated, and every mark is a source you
   can name by pointing at it.

   The marks are circles because a circle has no direction of its own: a square
   in a row of squares reads as a bar segment, and the bar is the column, not
   the source.
   --------------------------------------------------------------------------- */

export interface BenchSource {
  name: string;
  articleUrl: string;
  tier: string;
  politicalLean: number;
  /** The article's own headline, where the surface has one. */
  headline?: string;
}

const BUCKET_TOKEN: Record<LeanCategory, string> = {
  "far-left": "--bias-far-left",
  left: "--bias-left",
  "center-left": "--bias-center-left",
  center: "--bias-center",
  "center-right": "--bias-center-right",
  right: "--bias-right",
  "far-right": "--bias-far-right",
};

const BUCKET_ORDER = LEAN_BASELINES.map(([name]) => name);

const BUCKET_NAME: Record<LeanCategory, string> = {
  "far-left": "far left",
  left: "left",
  "center-left": "centre left",
  center: "centre",
  "center-right": "centre right",
  right: "right",
  "far-right": "far right",
};

const TIER_RANK: Record<string, number> = {
  us_major: 0,
  international: 1,
  independent: 2,
};

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

/* The stack's height budget, and the taller one the toggle re-packs against.
   Both are the height of the MARKS only: the rule, counts and anchors sit
   under them. */
const BOX_H = 176;
const BOX_H_NARROW = 132;
const BOX_H_EXPANDED = 440;
const COL_GAP = 8;
const COL_GAP_NARROW = 4;

/* ── The card that names a mark ─────────────────────────────────────────── */

interface CardData {
  source: BenchSource;
  x: number;
  y: number;
}

function BenchCard({ data }: { data: CardData }) {
  const ref = useRef<HTMLDivElement>(null);
  /* The card is centred on its mark and sits above it, which puts it off the
     left edge for a mark in the far-left column on a phone and off the top for
     a mark near the masthead. Measure once it is up and nudge it back inside,
     rather than guessing from a max-width that changes with the breakpoint. */
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.left = `${data.x}px`;
    el.style.top = `${data.y}px`;
    el.removeAttribute("data-below");
    const r = el.getBoundingClientRect();
    const M = 6;
    let dx = 0;
    if (r.left < M) dx = M - r.left;
    else if (r.right > window.innerWidth - M) dx = window.innerWidth - M - r.right;
    if (dx) el.style.left = `${data.x + dx}px`;
    if (r.top < M) el.setAttribute("data-below", "true");
  }, [data.x, data.y, data.source.name]);

  if (typeof document === "undefined") return null;
  const s = data.source;
  return createPortal(
    <div
      ref={ref}
      className="bench__card"
      style={{ left: `${data.x}px`, top: `${data.y}px` }}
      role="tooltip"
    >
      <p className="bench__card-name">{s.name}</p>
      <p className="bench__card-lean">
        <span
          className="bench__card-dot"
          style={{ background: `var(${BUCKET_TOKEN[leanToBucket(s.politicalLean)]})` }}
          aria-hidden="true"
        />
        {leanLabel(s.politicalLean)}
        <span className="bench__card-score">{Math.round(s.politicalLean)}</span>
      </p>
      <p className="bench__card-tier">{tierLabel(s.tier)}</p>
      {s.headline && <p className="bench__card-headline">{s.headline}</p>}
      <p className="bench__card-hint">
        <a
          href={s.articleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="bench__card-link"
          onClick={(e) => e.stopPropagation()}
        >
          &#x2197; Open article
        </a>
      </p>
    </div>,
    document.body,
  );
}

/* ── One mark ───────────────────────────────────────────────────────────── */

function Mark({ source, size }: { source: BenchSource; size: number }) {
  const [failed, setFailed] = useState(false);
  const url = size >= BENCH_FAVICON_MIN ? sourceLogoUrl(source.name) : "";
  const bucket = leanToBucket(source.politicalLean);
  return (
    <span
      className="bench__disc"
      data-lean={bucket}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {!failed && url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt=""
          width={size - 4}
          height={size - 4}
          onError={() => setFailed(true)}
          className="bench__disc-img"
        />
      ) : size >= BENCH_FAVICON_MIN ? (
        <span className="bench__disc-letter">{source.name.charAt(0).toUpperCase()}</span>
      ) : null}
    </span>
  );
}

/* ── The Bench ──────────────────────────────────────────────────────────── */

export interface BenchProps {
  /** Sources with a MEASURED lean. The caller does the filtering. */
  sources: BenchSource[];
  /** Sources that covered the story but whose lean was never measured. */
  unscoredCount?: number;
  /** Mount already drawn: the parent owns the one opening motion. */
  settled?: boolean;
}

export default function Bench({ sources, unscoredCount = 0, settled = false }: BenchProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [coarse, setCoarse] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [card, setCard] = useState<CardData | null>(null);
  const [pinned, setPinned] = useState<string | null>(null);
  const [drawn, setDrawn] = useState(settled);

  /* Own width, because the mark size is chosen from it. Falls back to a
     desktop-ish default before the first measurement so the server render and
     the first paint are not empty. */
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      if (w > 0) setWidth(w);
    });
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(pointer: coarse)");
    setCoarse(mq.matches);
    const h = (e: MediaQueryListEvent) => setCoarse(e.matches);
    mq.addEventListener("change", h);
    return () => mq.removeEventListener("change", h);
  }, []);

  useEffect(() => {
    if (settled) return;
    const t = setTimeout(() => setDrawn(true), 40);
    return () => clearTimeout(t);
  }, [settled]);

  /* Seven columns of marks, each sorted so the heaviest tier sits at the
     bottom of its stack. */
  const columns = useMemo(() => {
    const by: Record<string, BenchSource[]> = {};
    for (const name of BUCKET_ORDER) by[name] = [];
    for (const s of sources) by[leanToBucket(s.politicalLean)].push(s);
    for (const name of BUCKET_ORDER) {
      by[name].sort(
        (a, b) =>
          (TIER_RANK[a.tier] ?? 3) - (TIER_RANK[b.tier] ?? 3) ||
          a.name.localeCompare(b.name),
      );
    }
    return BUCKET_ORDER.map((name) => ({ bucket: name, items: by[name] }));
  }, [sources]);

  const counts = useMemo(() => columns.map((c) => c.items.length), [columns]);
  const total = counts.reduce((a, b) => a + b, 0);
  const tallest = counts.length ? Math.max(...counts) : 0;

  /* The same L/C/R split the card's register reads, derived from the same
     seven buckets, so the Bench and the card can never print different words
     about one story. */
  const spread: WingCounts = useMemo(
    () => ({
      leanBuckets: counts,
      leanLeftCount: counts[0] + counts[1] + counts[2],
      leanCenterCount: counts[3],
      leanRightCount: counts[4] + counts[5] + counts[6],
      leanMeasuredCount: total,
    }),
    [counts, total],
  );

  const narrow = width > 0 && width < 560;
  const colGap = narrow ? COL_GAP_NARROW : COL_GAP;
  const measured = width > 0 ? width : 640;
  const colWidth = (measured - colGap * 6) / 7;
  const collapsedH = narrow ? BOX_H_NARROW : BOX_H;
  const boxH = expanded ? BOX_H_EXPANDED : collapsedH;

  const pack: BenchPack = useMemo(
    () => packBench({ colWidth, maxHeight: boxH, tallest }),
    [colWidth, boxH, tallest],
  );

  /* The toggle is offered on whether the COLLAPSED box cuts anything, not on
     whether the current one does. Read off `pack` it would vanish the moment
     it worked, leaving the reader inside an expanded Bench with no way back. */
  const collapsed: BenchPack = useMemo(
    () => packBench({ colWidth, maxHeight: collapsedH, tallest }),
    [colWidth, collapsedH, tallest],
  );
  const capped = collapsed.capPerColumn !== Infinity && tallest > collapsed.capPerColumn;

  /* Dismiss a pinned card on an outside press or Escape (coarse pointers). */
  useEffect(() => {
    if (!pinned) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.closest(".bench__mark") || t.closest(".bench__card"))) return;
      setPinned(null);
      setCard(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPinned(null);
        setCard(null);
      }
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [pinned]);

  const show = useCallback((el: HTMLElement, source: BenchSource) => {
    const r = el.getBoundingClientRect();
    setCard({ source, x: r.left + r.width / 2, y: r.top });
  }, []);

  if (total === 0) {
    return (
      <div className="bench bench--empty" role="img" aria-label="No measured sources">
        <p className="bench__empty">
          {unscoredCount > 0
            ? `${unscoredCount} ${unscoredCount === 1 ? "source" : "sources"}, none measured`
            : "No sources"}
        </p>
      </div>
    );
  }

  const focusName = card?.source.name ?? null;

  return (
    <div
      className={[
        "bench",
        drawn ? "bench--drawn" : "",
        focusName ? "bench--focused" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="bench__head">
        <p className="bench__shape">{leanShapeLabel(spread)}</p>
        <p className="bench__count">
          {total} {total === 1 ? "source" : "sources"} placed
          {unscoredCount > 0 && (
            <span className="bench__unscored"> &middot; {unscoredCount} not measured</span>
          )}
        </p>
      </div>

      <div
        ref={wrapRef}
        className="bench__grid"
        style={
          {
            "--bench-gap": `${colGap}px`,
            "--bench-gap-marks": `${BENCH_GAP}px`,
            "--bench-box": `${boxH}px`,
          } as React.CSSProperties
        }
        role="group"
        aria-label="Sources by political lean, far left to far right"
      >
        {columns.map(({ bucket, items }, ci) => {
          const drawnItems =
            pack.capPerColumn === Infinity ? items : items.slice(0, pack.capPerColumn);
          const hidden = items.length - drawnItems.length;
          const rows = benchRows(drawnItems, pack.perRow);
          return (
            <div
              className="bench__col"
              key={bucket}
              style={{ "--bench-delay": `${ci * 40}ms` } as React.CSSProperties}
            >
              <div className="bench__stack">
                {hidden > 0 && (
                  <span className="bench__more" aria-hidden="true">
                    +{hidden}
                  </span>
                )}
                {[...rows].reverse().map((row, ri) => (
                  <div
                    className="bench__row"
                    key={ri}
                    style={{ gap: `${BENCH_GAP}px` }}
                  >
                    {row.map((s) =>
                      coarse ? (
                        <button
                          key={s.name}
                          type="button"
                          className="bench__mark"
                          data-focused={focusName === s.name ? "true" : undefined}
                          aria-label={`${s.name}, ${leanLabel(s.politicalLean)}. Show details.`}
                          aria-expanded={pinned === s.name}
                          onClick={(e) => {
                            if (pinned === s.name) {
                              setPinned(null);
                              setCard(null);
                            } else {
                              setPinned(s.name);
                              show(e.currentTarget, s);
                            }
                          }}
                        >
                          <Mark source={s} size={pack.mark} />
                        </button>
                      ) : (
                        <a
                          key={s.name}
                          href={s.articleUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bench__mark"
                          data-focused={focusName === s.name ? "true" : undefined}
                          aria-label={`${s.name}, ${leanLabel(s.politicalLean)}`}
                          onPointerEnter={(e) => show(e.currentTarget, s)}
                          onPointerLeave={() => setCard(null)}
                          onFocus={(e) => show(e.currentTarget, s)}
                          onBlur={() => setCard(null)}
                        >
                          <Mark source={s} size={pack.mark} />
                        </a>
                      ),
                    )}
                  </div>
                ))}
              </div>
              <span
                className="bench__tally"
                data-zero={items.length === 0 ? "true" : undefined}
                style={{ color: items.length ? `var(${BUCKET_TOKEN[bucket]})` : undefined }}
              >
                {items.length || "0"}
              </span>
              <span className="bench__sr">
                {items.length} {BUCKET_NAME[bucket]}
              </span>
            </div>
          );
        })}
      </div>

      <div className="bench__rule" aria-hidden="true" />
      <div className="bench__anchors" aria-hidden="true">
        <span className="bench__anchor bench__anchor--left">Left</span>
        <span className="bench__anchor bench__anchor--center">Centre</span>
        <span className="bench__anchor bench__anchor--right">Right</span>
      </div>

      {capped && (
        <button
          type="button"
          className="bench__toggle"
          aria-expanded={expanded}
          onClick={() => {
            setPinned(null);
            setCard(null);
            setExpanded((v) => !v);
          }}
        >
          {expanded ? "Show fewer" : `Show all ${total} sources`}
        </button>
      )}

      {card && <BenchCard data={card} />}
    </div>
  );
}
