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
   fill, the current marker, the segmented strip, the readout and the step
   carets are the enhancement: they appear only once this mounts and sets
   data-enhanced.

   Progress comes from an IntersectionObserver on the sections. There is no
   scroll listener: a scroll handler that measures on every frame is what the
   reel did, and it is why the reel fought the medium.

   The carets step one station at a time. They are live: their labels name the
   station they go to, and each end of the spine disables its own caret. The
   keyboard reaches the same two moves, j/k anywhere on the page and the arrow
   keys once focus is inside the rail. Plain arrow keys stay the reader's, so
   an 800-word account still scrolls a line at a time.
   =========================================================================== */

interface SpineRailProps {
  stations: Station[];
  /** Id of the hero section. The mobile strip stays out of the way until the
   *  hero has left: 56px of topbar plus a strip plus a readout is a lot of
   *  chrome to put over a cold open. */
  heroId: string;
}

/** Read at the moment of the move, not cached: a reader can flip the setting
 *  mid-page and the next step should already obey it. */
function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** Typing, choosing, or reading inside a disclosure. The keys are theirs. */
function isTypingContext(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    tag === "AUDIO" ||
    tag === "VIDEO"
  ) {
    return true;
  }
  if (target.isContentEditable) return true;
  return target.closest("details") !== null;
}

export default function SpineRail({ stations, heroId }: SpineRailProps) {
  const [enhanced, setEnhanced] = useState(false);
  const [current, setCurrent] = useState(0);
  const [pastHero, setPastHero] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [weights, setWeights] = useState<number[]>([]);
  const visible = useRef<Set<string>>(new Set());
  const navRef = useRef<HTMLElement>(null);
  const listRef = useRef<HTMLOListElement>(null);

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

  /* ── One station, either way ──
     The page glides. setCurrent runs ahead of the observer so a second press
     lands on the next station rather than repeating the first; the observer
     confirms the same answer when the scroll settles. */
  const goTo = useCallback(
    (index: number) => {
      const station = stations[index];
      if (!station) return;
      const el = document.getElementById(station.id);
      if (!el) return;
      el.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
        block: "start",
      });
      setCurrent(index);
      setSheetOpen(false);
    },
    [stations],
  );

  /* ── Keyboard ──
     j and k anywhere the reader is not typing. The arrow keys only once focus
     is inside the rail, where up and down are what a list of controls means by
     them: a plain ArrowDown in the middle of a 900-word account is the
     reader's own scroll, and taking it would be worse than not binding it. */
  useEffect(() => {
    if (!enhanced) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;
      if (isTypingContext(e.target)) return;

      let step = 0;
      if (e.key === "j") step = 1;
      else if (e.key === "k") step = -1;
      else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        const nav = navRef.current;
        const active = document.activeElement;
        if (!nav || !active || !nav.contains(active)) return;
        step = e.key === "ArrowDown" ? 1 : -1;
      } else return;

      const next = current + step;
      if (next < 0 || next >= stations.length) return;
      e.preventDefault();
      goTo(next);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [enhanced, current, stations.length, goTo]);

  /* ── Keep the current station inside a rail that had to scroll ──
     Only when the list actually overflows, and only the list: scrollIntoView
     would take the page with it. */
  useEffect(() => {
    if (!enhanced) return;
    const list = listRef.current;
    if (!list) return;
    if (list.scrollHeight <= list.clientHeight + 1) return;
    const item = list.children[current];
    if (!(item instanceof HTMLElement)) return;

    const pad = 28;
    const top = item.offsetTop;
    const bottom = top + item.offsetHeight;
    const viewTop = list.scrollTop;
    const viewBottom = viewTop + list.clientHeight;

    let next = viewTop;
    if (top - pad < viewTop) next = Math.max(0, top - pad);
    else if (bottom + pad > viewBottom) next = bottom + pad - list.clientHeight;
    if (Math.abs(next - viewTop) < 1) return;

    list.scrollTo({
      top: next,
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
  }, [current, enhanced]);

  if (stations.length === 0) return null;

  const total = weights.reduce((a, b) => a + b, 0) || stations.length;
  const fill =
    stations.length > 1 ? `${(current / (stations.length - 1)) * 100}%` : "0%";

  const prev = stations[current - 1];
  const next = stations[current + 1];

  return (
    <nav
      className="hist-rail"
      aria-label="Where you are in the record"
      ref={navRef}
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

      {enhanced && (
        <button
          type="button"
          className="hist-rail__step hist-rail__step--prev"
          disabled={!prev}
          aria-label={prev ? `Previous: ${prev.label}` : "Previous station"}
          onClick={() => goTo(current - 1)}
        />
      )}

      <span className="hist-rail__track" aria-hidden="true">
        <span
          className="hist-rail__fill"
          style={enhanced ? { height: fill } : undefined}
        />
      </span>

      <ol className="hist-rail__list" ref={listRef}>
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

      {enhanced && (
        <button
          type="button"
          className="hist-rail__step hist-rail__step--next"
          disabled={!next}
          aria-label={next ? `Next: ${next.label}` : "Next station"}
          onClick={() => goTo(current + 1)}
        />
      )}

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
