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

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 300);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div role="status" aria-label="Loading stories" className="anim-fade-in">
      <div className="loading-indicator">
        <LogoIcon animation="loading" size={40} />
        <LogoWordmark height={14} />
      </div>

      {/* Zone 0: SkyboxBanner placeholder — thin bar matching ~40px collapsed height */}
      <div className="skeleton-skybox">
        <div className="shimmer-line" style={{ width: 100, height: 12 }} />
        <div className="shimmer-line" style={{ width: "40%", height: 12 }} />
        <div className="shimmer-line" style={{ width: 60, height: 12 }} />
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

      <span className="sr-only">Loading stories, please wait...</span>
    </div>
  );
}
