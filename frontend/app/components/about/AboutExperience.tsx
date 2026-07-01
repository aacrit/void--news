"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import LogoIcon from "../LogoIcon";
import { PRODUCT_FAMILY, FIRST_PRINCIPLES } from "../../film/data";
import BeatVoid from "./beats/BeatVoid";
import BeatSigil from "./beats/BeatSigil";
import BeatEngine from "./beats/BeatEngine";
import BeatVerdict from "./beats/BeatVerdict";

/* ===========================================================================
   AboutExperience — ONE interactive experience, two presentations.

   presentation="page"     → the /about route (normal scroll document + footer)
   presentation="overlay"  → first-visit dialog (portal, focus trap, scroll-snap)

   The four beats are identical in both; only the chrome differs. Replaces the
   old manifesto-vs-prologue fork and the auto-advance carousel.
   =========================================================================== */

interface Props {
  presentation: "page" | "overlay";
  onClose?: () => void;
  onComplete?: () => void;
}

function Beats({ presentation, onComplete }: { presentation: "page" | "overlay"; onComplete?: () => void }) {
  return (
    <>
      <BeatVoid />
      <BeatSigil />
      <BeatEngine />
      <BeatVerdict presentation={presentation} onComplete={onComplete} />
    </>
  );
}

export default function AboutExperience({ presentation, onClose, onComplete }: Props) {
  if (presentation === "overlay") {
    return <Overlay onClose={onClose} onComplete={onComplete} />;
  }
  return <PageExperience />;
}

/* ── Page presentation — the /about route ────────────────────────────────── */

function PageExperience() {
  return (
    <div className="about-x about-x--page">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News Feed
      </Link>

      <header className="about-x__hero">
        <div className="about-x__hero-mark"><LogoIcon size={108} animation="idle" /></div>
        <h1 className="about-x__tagline">See through the void.</h1>
        <p className="about-x__sub">News, measured. Scroll to see how it works.</p>
        <span className="about-x__scroll" aria-hidden="true" />
      </header>

      <Beats presentation="page" />

      {/* Page-only footer: product family + principles (not in the overlay). */}
      <footer className="about-x__footer">
        <h2 className="about-x__footer-h">The void suite</h2>
        <ul className="about-x__worlds">
          {PRODUCT_FAMILY.map((p) => (
            <li key={p.cli}>
              <Link href={p.href} className="about-x__world">
                <span className="about-x__world-cli">{p.cli}</span>
                <span className="about-x__world-name">{p.name}</span>
                <span className="about-x__world-desc">{p.desc}</span>
              </Link>
            </li>
          ))}
        </ul>
        <ul className="about-x__principles">
          {FIRST_PRINCIPLES.map((t) => <li key={t}>{t}</li>)}
        </ul>
      </footer>
    </div>
  );
}

/* ── Overlay presentation — first-visit dialog ───────────────────────────── */

function Overlay({ onClose, onComplete }: { onClose?: () => void; onComplete?: () => void }) {
  const [exiting, setExiting] = useState(false);
  const [progress, setProgress] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const prevFocus = useRef<HTMLElement | null>(null);

  // Body scroll lock (effects run client-only; no mount gate needed).
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  const dismiss = useCallback((cb?: () => void) => {
    if (exiting) return;
    setExiting(true);
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTimeout(() => { prevFocus.current?.focus(); cb?.(); }, reduced ? 0 : 360);
  }, [exiting]);

  const handleSkip = useCallback(() => dismiss(onClose), [dismiss, onClose]);
  const handleComplete = useCallback(() => dismiss(onComplete), [dismiss, onComplete]);

  const nudge = useCallback((dir: 1 | -1) => {
    const s = scrollerRef.current;
    if (!s) return;
    s.scrollBy({ top: dir * s.clientHeight, behavior: "smooth" });
  }, []);

  // Focus trap + keyboard
  useEffect(() => {
    prevFocus.current = document.activeElement as HTMLElement;
    const t = setTimeout(() => dialogRef.current?.querySelector<HTMLElement>("button, a[href]")?.focus(), 100);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { handleSkip(); return; }
      if (e.key === "ArrowDown") { e.preventDefault(); nudge(1); }
      if (e.key === "ArrowUp") { e.preventDefault(); nudge(-1); }
      if (e.key === "Tab" && dialogRef.current) {
        const f = dialogRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input, [tabindex]:not([tabindex="-1"])');
        if (!f.length) return;
        const first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { clearTimeout(t); document.removeEventListener("keydown", onKey); };
  }, [handleSkip, nudge]);

  const onScroll = useCallback(() => {
    const s = scrollerRef.current;
    if (!s) return;
    const max = s.scrollHeight - s.clientHeight;
    setProgress(max > 0 ? Math.min(1, s.scrollTop / max) : 0);
  }, []);

  if (typeof document === "undefined") return null;

  return createPortal(
    <div className={`onb${exiting ? " onb--exiting" : ""}`}>
      <div className="onb__backdrop" aria-hidden="true" onClick={handleSkip} />
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-label="How void news works" className="onb__stage">
        <div className="onb__progress" aria-hidden="true"><div className="onb__progress-fill" style={{ width: `${progress * 100}%` }} /></div>
        <button className="onb__skip" onClick={handleSkip} aria-label="Skip tour">Skip</button>

        <div className="onb__scroller" ref={scrollerRef} onScroll={onScroll}>
          <Beats presentation="overlay" onComplete={handleComplete} />
        </div>

        <button className="onb__next" onClick={() => nudge(1)} aria-label="Next section">Next &darr;</button>
      </div>
    </div>,
    document.body,
  );
}
