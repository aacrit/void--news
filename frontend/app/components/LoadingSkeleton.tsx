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
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 100);
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
        /* ── Desktop skeleton — matches actual layout: SkyboxBanner → hero → feed-grid ── */
        <>
          {/* SkyboxBanner placeholder — 2-column compact bar */}
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
          </div>

          {/* Hero slot — single full-width lead story shimmer */}
          <div style={{ paddingTop: "var(--space-4)", marginBottom: "var(--space-5)", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "var(--space-5)" }}>
            <div className="shimmer-line" style={{ width: 80, height: 10, marginBottom: "var(--space-3)" }} />
            <div className="shimmer-line" style={{ width: "75%", height: 36, marginBottom: "var(--space-2)" }} />
            <div className="shimmer-line" style={{ width: "55%", height: 36, marginBottom: "var(--space-4)" }} />
            <div className="shimmer-line" style={{ width: "95%", height: 14, marginBottom: "var(--space-2)" }} />
            <div className="shimmer-line" style={{ width: "90%", height: 14, marginBottom: "var(--space-2)" }} />
            <div className="shimmer-line" style={{ width: "70%", height: 14 }} />
          </div>

          {/* Feed grid — 3-column story card shimmer (matches feed-grid) */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0 var(--space-5)" }}>
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div key={i} style={{ borderRight: (i % 3) < 2 ? "1px solid var(--border-subtle)" : "none", paddingRight: (i % 3) < 2 ? "var(--space-5)" : 0, paddingBottom: "var(--space-4)", borderBottom: "1px solid var(--border-subtle)", marginBottom: "var(--space-4)" }}>
                <div className="shimmer-line" style={{ width: "85%", height: 18, marginBottom: "var(--space-2)" }} />
                <div className="shimmer-line" style={{ width: "65%", height: 18, marginBottom: "var(--space-3)" }} />
                <div className="shimmer-line" style={{ width: "95%", height: 12, marginBottom: "var(--space-1)" }} />
                <div className="shimmer-line" style={{ width: "80%", height: 12 }} />
              </div>
            ))}
          </div>
        </>
      )}

      <span className="sr-only">Loading stories, please wait...</span>
    </div>
  );
}
