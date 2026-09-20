"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Station } from "../hearing";

/* ===========================================================================
   SpineRail — where you are in the record.

   The timeline the page carries, redirected: it plots the READER's position
   along one spine, not five accounts against each other. Open and Close are
   ink ticks, scenes are numbered ticks, the five accounts are five dots in
   their own colours, and the turn is a brass diamond, because the turn is not
   one more account.

   Every station is an <a href="#…">, rendered on the server. With JavaScript
   off the rail is a working contents list, inline under the hero on a phone
   and sticky in the left track on a desktop, and that is the mechanism. The
   fill, the current marker, the segmented strip and the readout are the
   enhancement: they appear only once this mounts and sets data-enhanced.

   Progress comes from an IntersectionObserver on the sections. There is no
   scroll listener: a scroll handler that measures on every frame is what the
   reel did, and it is why the reel fought the medium.
   =========================================================================== */

interface SpineRailProps {
  stations: Station[];
  /** Id of the hero section. The mobile strip stays out of the way until the
   *  hero has left: 56px of topbar plus a strip plus a readout is a lot of
   *  chrome to put over a cold open. */
  heroId: string;
}

export default function SpineRail({ stations, heroId }: SpineRailProps) {
  const [enhanced, setEnhanced] = useState(false);
  const [current, setCurrent] = useState(0);
  const [pastHero, setPastHero] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [weights, setWeights] = useState<number[]>([]);
  const visible = useRef<Set<string>>(new Set());

  /* ── Which station the reader is in ──
     A thin band across the middle of the viewport. Whatever is in that band is
     where they are; when nothing is (mid-rest, mid-image) the last answer
     stands rather than flickering to none. */
  useEffect(() => {
    if (stations.length === 0) return;
    const ids = stations.map((s) => s.id);
    const nodes = ids
      .map((id) => document.getElementById(id))
      .filter((n): n is HTMLElement => !!n);
    if (nodes.length === 0) return;

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) visible.current.add(e.target.id);
          else visible.current.delete(e.target.id);
        }
        let best = -1;
        ids.forEach((id, i) => {
          if (visible.current.has(id)) best = Math.max(best, i);
        });
        if (best >= 0) setCurrent(best);
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 },
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, [stations]);

  /* ── The hero, for the mobile strip's entrance ── */
  useEffect(() => {
    const hero = document.getElementById(heroId);
    if (!hero) {
      /* No hero to wait for: the strip has nothing to stay clear of. Deferred
         a frame so this is not a synchronous setState inside an effect. */
      const id = requestAnimationFrame(() => setPastHero(true));
      return () => cancelAnimationFrame(id);
    }
    const io = new IntersectionObserver(
      ([e]) => setPastHero(!e.isIntersecting),
      { threshold: 0 },
    );
    io.observe(hero);
    return () => io.disconnect();
  }, [heroId]);

  /* ── Segment proportions ──
     The mobile strip is the page in miniature, so each segment is as wide as
     its section is tall. Measured once and on resize, never on scroll. */
  const measure = useCallback(() => {
    const tops = stations.map((s) => {
      const el = document.getElementById(s.id);
      return el ? el.getBoundingClientRect().top + window.scrollY : null;
    });
    const docEnd = document.body.scrollHeight;
    const out = tops.map((t, i) => {
      if (t === null) return 1;
      const next = tops.slice(i + 1).find((v) => v !== null) ?? docEnd;
      return Math.max(1, next - t);
    });
    setWeights(out);
  }, [stations]);

  useEffect(() => {
    /* One frame after mount: the rail turns itself on and takes its first
       measurement together, after layout has settled and outside the effect
       body, so neither is a synchronous setState during render. */
    let frame = requestAnimationFrame(() => {
      setEnhanced(true);
      measure();
    });
    const onResize = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
    };
  }, [measure]);

  /* ── The station sheet ── */
  useEffect(() => {
    if (!sheetOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSheetOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [sheetOpen]);

  if (stations.length === 0) return null;

  const total = weights.reduce((a, b) => a + b, 0) || stations.length;
  const fill =
    stations.length > 1 ? `${(current / (stations.length - 1)) * 100}%` : "0%";

  return (
    <nav
      className="hist-rail"
      aria-label="Where you are in the record"
      data-enhanced={enhanced ? "true" : undefined}
      data-past-hero={pastHero ? "true" : undefined}
      data-sheet={sheetOpen ? "open" : undefined}
    >
      {enhanced && (
        <div className="hist-rail__strip" aria-hidden="true">
          {stations.map((s, i) => (
            <span
              key={s.id}
              className="hist-rail__seg"
              data-glyph={s.glyph}
              data-passed={i <= current ? "true" : undefined}
              style={{
                flexGrow: (weights[i] ?? 1) / total,
                ...(s.color ? ({ "--hist-seg-color": s.color } as React.CSSProperties) : {}),
              }}
            />
          ))}
        </div>
      )}

      {enhanced && (
        <button
          type="button"
          className="hist-rail__readout"
          aria-expanded={sheetOpen}
          onClick={() => setSheetOpen((v) => !v)}
        >
          <span className="hist-rail__readout-pos">
            {current + 1}/{stations.length}
          </span>
          <span className="hist-rail__readout-label">{stations[current]?.label}</span>
          <span className="hist-rail__readout-chevron" aria-hidden="true" />
        </button>
      )}

      <span className="hist-rail__track" aria-hidden="true">
        <span
          className="hist-rail__fill"
          style={enhanced ? { height: fill } : undefined}
        />
      </span>

      <ol className="hist-rail__list">
        {stations.map((s, i) => (
          <li key={s.id} className="hist-rail__item">
            <a
              href={`#${s.id}`}
              className="hist-rail__station"
              data-glyph={s.glyph}
              aria-current={enhanced && i === current ? "true" : undefined}
              onClick={() => setSheetOpen(false)}
              style={s.color ? ({ "--hist-station-color": s.color } as React.CSSProperties) : undefined}
            >
              <span className="hist-rail__glyph" aria-hidden="true">
                {s.glyph === "scene" && (
                  <span className="hist-rail__num">{String(s.number).padStart(2, "0")}</span>
                )}
              </span>
              <span className="hist-rail__label">{s.label}</span>
            </a>
          </li>
        ))}
      </ol>

      {sheetOpen && (
        <button
          type="button"
          className="hist-rail__scrim"
          aria-label="Close the contents"
          onClick={() => setSheetOpen(false)}
        />
      )}
    </nav>
  );
}
