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

      {/* Lead story skeleton */}
      <div className="skeleton-lead">
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
          <div className="shimmer-line" style={{ width: 80, height: 14 }} />
          <div className="shimmer-line" style={{ width: 50, height: 12 }} />
        </div>
        {/* Headline lines */}
        <div className="shimmer-line" style={{ width: "75%", height: 40, marginBottom: "var(--space-2)" }} />
        <div className="shimmer-line" style={{ width: "55%", height: 40, marginBottom: "var(--space-3)" }} />
        {/* Summary lines */}
        <div className="shimmer-line" style={{ width: "90%", height: 16, marginBottom: "var(--space-2)" }} />
        <div className="shimmer-line" style={{ width: "70%", height: 16, marginBottom: "var(--space-4)" }} />
        {/* Meta items */}
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-5)" }}>
          <div className="shimmer-line" style={{ width: 90, height: 16 }} />
          <div className="shimmer-line" style={{ width: 30, height: 24 }} />
        </div>
      </div>

      {/* Medium story skeletons */}
      <div className="skeleton-grid">
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ padding: "var(--space-3) 0" }}>
            {/* Meta items */}
            <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-2)" }}>
              <div className="shimmer-line" style={{ width: 60, height: 12 }} />
              <div className="shimmer-line" style={{ width: 40, height: 12 }} />
            </div>
            {/* Headline lines */}
            <div className="shimmer-line" style={{ width: "90%", height: 22, marginBottom: "var(--space-2)" }} />
            <div className="shimmer-line" style={{ width: "65%", height: 22, marginBottom: "var(--space-2)" }} />
            {/* Summary lines */}
            <div className="shimmer-line" style={{ width: "95%", height: 14, marginBottom: "var(--space-1)" }} />
            <div className="shimmer-line" style={{ width: "80%", height: 14, marginBottom: "var(--space-3)" }} />
            {/* Meta items */}
            <div style={{ display: "flex", gap: "var(--space-3)" }}>
              <div className="shimmer-line" style={{ width: 70, height: 14 }} />
              <div className="shimmer-line" style={{ width: 24, height: 20 }} />
            </div>
          </div>
        ))}
      </div>

      <span className="sr-only">Loading stories, please wait...</span>
    </div>
  );
}
