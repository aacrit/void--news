"use client";

import { useState, useEffect } from "react";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";

/* ---------------------------------------------------------------------------
   LoadingSkeleton — Placeholder shimmer while Supabase data loads
   Shows animated void circle (loading state) with wordmark beneath.
   --------------------------------------------------------------------------- */

export default function LoadingSkeleton() {
  const [visible, setVisible] = useState(false);
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < 768 : false
  );

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 300);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const mql = window.matchMedia("(max-width: 767px)");
    setIsMobile(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  if (!visible) return null;

  return (
    <div role="status" aria-label="Loading stories" className="anim-fade-in">
      <div className="loading-indicator">
        <LogoIcon animation="loading" size={40} />
        <LogoWordmark height={14} />
      </div>

      {isMobile ? (
        /* ── Mobile skeleton — matches MobileFeed layout ── */
        <div className="skeleton-mobile">
          {/* Hero card placeholder */}
          <div className="skeleton-mobile__hero">
            <div className="shimmer-line" style={{ width: 60, height: 10, marginBottom: 8 }} />
            <div className="shimmer-line" style={{ width: "90%", height: 22, marginBottom: 6 }} />
            <div className="shimmer-line" style={{ width: "70%", height: 22, marginBottom: 10 }} />
            <div className="shimmer-line" style={{ width: "100%", height: 14, marginBottom: 4 }} />
            <div className="shimmer-line" style={{ width: "85%", height: 14, marginBottom: 4 }} />
            <div className="shimmer-line" style={{ width: "60%", height: 14 }} />
          </div>

          {/* Brief pill placeholder */}
          <div className="skeleton-mobile__pill">
            <div className="shimmer-line" style={{ width: "100%", height: 44, borderRadius: 8 }} />
          </div>

          {/* 5 compact card placeholders */}
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton-mobile__card">
              <div className="skeleton-mobile__card-text">
                <div className="shimmer-line" style={{ width: 50, height: 8, marginBottom: 6 }} />
                <div className="shimmer-line" style={{ width: "90%", height: 14, marginBottom: 4 }} />
                <div className="shimmer-line" style={{ width: "60%", height: 14 }} />
              </div>
              <div className="shimmer-line" style={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0 }} />
            </div>
          ))}
        </div>
      ) : (
        /* ── Desktop skeleton — three-zone broadsheet ── */
        <>
          {/* Zone 0: SkyboxBanner placeholder — 2-column compact bar + OnAir strip */}
          <div className="skeleton-skybox">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-4)" }}>
              <div>
                <div className="shimmer-line" style={{ width: 90, height: 10, marginBottom: 6 }} />
                <div className="shimmer-line" style={{ width: "80%", height: 14, marginBottom: 6 }} />
                <div className="shimmer-line" style={{ width: "60%", height: 10 }} />
              </div>
              <div>
                <div className="shimmer-line" style={{ width: 100, height: 10, marginBottom: 6 }} />
                <div className="shimmer-line" style={{ width: "70%", height: 14, marginBottom: 6 }} />
                <div className="shimmer-line" style={{ width: "50%", height: 10 }} />
              </div>
            </div>
            <div style={{ marginTop: 8, borderTop: "1px dotted var(--border-subtle)", paddingTop: 8 }}>
              <div className="shimmer-line" style={{ width: 140, height: 12 }} />
            </div>
          </div>

          {/* Zone 1: Asymmetric lead section — 2fr | 1fr columns */}
          <div className="skeleton-lead-v2">
            {/* Primary column (larger) */}
            <div className="skeleton-lead-v2__primary">
              <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
                <div className="shimmer-line" style={{ width: 80, height: 14 }} />
                <div className="shimmer-line" style={{ width: 50, height: 12 }} />
              </div>
              <div className="shimmer-line" style={{ width: "85%", height: 36, marginBottom: "var(--space-2)" }} />
              <div className="shimmer-line" style={{ width: "60%", height: 36, marginBottom: "var(--space-3)" }} />
              <div className="shimmer-line" style={{ width: "95%", height: 16, marginBottom: "var(--space-2)" }} />
              <div className="shimmer-line" style={{ width: "80%", height: 16, marginBottom: "var(--space-2)" }} />
              <div className="shimmer-line" style={{ width: "70%", height: 16 }} />
            </div>
            {/* Secondary column (smaller) */}
            <div className="skeleton-lead-v2__secondary">
              <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
                <div className="shimmer-line" style={{ width: 60, height: 12 }} />
                <div className="shimmer-line" style={{ width: 40, height: 12 }} />
              </div>
              <div className="shimmer-line" style={{ width: "90%", height: 28, marginBottom: "var(--space-2)" }} />
              <div className="shimmer-line" style={{ width: "70%", height: 28, marginBottom: "var(--space-3)" }} />
              <div className="shimmer-line" style={{ width: "95%", height: 14, marginBottom: "var(--space-2)" }} />
              <div className="shimmer-line" style={{ width: "65%", height: 14 }} />
            </div>
          </div>

          {/* Zone 2: Digest rows — single-line headline placeholders */}
          <div className="skeleton-digest">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="skeleton-digest__row">
                <div className="shimmer-line" style={{ width: 60, height: 12 }} />
                <div className="shimmer-line" style={{ flex: 1, height: 16 }} />
                <div className="shimmer-line" style={{ width: 24, height: 24, borderRadius: "50%" }} />
              </div>
            ))}
          </div>

          {/* Zone 3: Wire grid — 4-column compact cards */}
          <div className="skeleton-wire">
            {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
              <div key={i} className="skeleton-wire__card">
                <div className="shimmer-line" style={{ width: "50%", height: 10, marginBottom: "var(--space-2)" }} />
                <div className="shimmer-line" style={{ width: "90%", height: 14, marginBottom: "var(--space-1)" }} />
                <div className="shimmer-line" style={{ width: "70%", height: 14 }} />
              </div>
            ))}
          </div>
        </>
      )}

      <span className="sr-only">Loading stories, please wait...</span>
    </div>
  );
}
