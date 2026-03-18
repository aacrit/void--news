"use client";

import { useState, useEffect } from "react";
import LogoIcon from "./LogoIcon";

/* ---------------------------------------------------------------------------
   LoadingSkeleton — Placeholder shimmer while Supabase data loads
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
        <LogoIcon animation="loading" size={32} />
      </div>

      {/* Lead story skeleton */}
      <div className="skeleton-lead">
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
          <div className="skeleton" style={{ width: 80, height: 14 }} />
          <div className="skeleton" style={{ width: 50, height: 12 }} />
        </div>
        <div className="skeleton" style={{ width: "75%", height: 40, marginBottom: "var(--space-2)" }} />
        <div className="skeleton" style={{ width: "55%", height: 40, marginBottom: "var(--space-3)" }} />
        <div className="skeleton" style={{ width: "90%", height: 16, marginBottom: "var(--space-2)" }} />
        <div className="skeleton" style={{ width: "70%", height: 16, marginBottom: "var(--space-4)" }} />
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-5)" }}>
          <div className="skeleton" style={{ width: 90, height: 16 }} />
          <div className="skeleton" style={{ width: 30, height: 24 }} />
        </div>
      </div>

      {/* Medium story skeletons */}
      <div className="skeleton-grid">
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ padding: "var(--space-3) 0" }}>
            <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-2)" }}>
              <div className="skeleton" style={{ width: 60, height: 12 }} />
              <div className="skeleton" style={{ width: 40, height: 12 }} />
            </div>
            <div className="skeleton" style={{ width: "90%", height: 22, marginBottom: "var(--space-2)" }} />
            <div className="skeleton" style={{ width: "65%", height: 22, marginBottom: "var(--space-2)" }} />
            <div className="skeleton" style={{ width: "95%", height: 14, marginBottom: "var(--space-1)" }} />
            <div className="skeleton" style={{ width: "80%", height: 14, marginBottom: "var(--space-3)" }} />
            <div style={{ display: "flex", gap: "var(--space-3)" }}>
              <div className="skeleton" style={{ width: 70, height: 14 }} />
              <div className="skeleton" style={{ width: 24, height: 20 }} />
            </div>
          </div>
        ))}
      </div>

      <span className="sr-only">Loading stories, please wait...</span>
    </div>
  );
}
