"use client";

import { useState, useEffect } from "react";

/* ---------------------------------------------------------------------------
   LoadingSkeleton — Placeholder rectangles matching story card layout
   Shows shimmer animation while Supabase data is being fetched.
   Only visible for 300ms+ loads (avoids flash for fast connections).
   --------------------------------------------------------------------------- */

export default function LoadingSkeleton() {
  const [visible, setVisible] = useState(false);

  // Only show skeleton after 300ms delay to avoid flash on fast loads
  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 300);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  return (
    <div
      role="status"
      aria-label="Loading stories"
      style={{ animation: "fadeIn var(--dur-normal) var(--ease-out)" }}
    >
      {/* Lead story skeleton */}
      <div
        style={{
          padding: "var(--space-6) 0",
          borderBottom: "var(--rule-strong)",
        }}
      >
        {/* Category + time */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-3)",
            marginBottom: "var(--space-3)",
          }}
        >
          <div className="skeleton" style={{ width: 80, height: 14 }} />
          <div className="skeleton" style={{ width: 50, height: 12 }} />
        </div>
        {/* Headline */}
        <div
          className="skeleton"
          style={{ width: "75%", height: 40, marginBottom: "var(--space-2)" }}
        />
        <div
          className="skeleton"
          style={{ width: "55%", height: 40, marginBottom: "var(--space-3)" }}
        />
        {/* Summary */}
        <div
          className="skeleton"
          style={{ width: "90%", height: 16, marginBottom: "var(--space-2)" }}
        />
        <div
          className="skeleton"
          style={{ width: "70%", height: 16, marginBottom: "var(--space-4)" }}
        />
        {/* Source count + bars */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "var(--space-5)",
          }}
        >
          <div className="skeleton" style={{ width: 90, height: 16 }} />
          <div className="skeleton" style={{ width: 30, height: 24 }} />
        </div>
      </div>

      {/* Medium story skeletons */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: "var(--space-5)",
          borderBottom: "var(--rule-thin)",
          padding: "var(--space-5) 0",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div key={i} style={{ padding: "var(--space-3) 0" }}>
            {/* Category + time */}
            <div
              style={{
                display: "flex",
                gap: "var(--space-3)",
                marginBottom: "var(--space-2)",
              }}
            >
              <div className="skeleton" style={{ width: 60, height: 12 }} />
              <div className="skeleton" style={{ width: 40, height: 12 }} />
            </div>
            {/* Headline */}
            <div
              className="skeleton"
              style={{
                width: "90%",
                height: 22,
                marginBottom: "var(--space-2)",
              }}
            />
            <div
              className="skeleton"
              style={{
                width: "65%",
                height: 22,
                marginBottom: "var(--space-2)",
              }}
            />
            {/* Summary */}
            <div
              className="skeleton"
              style={{
                width: "95%",
                height: 14,
                marginBottom: "var(--space-1)",
              }}
            />
            <div
              className="skeleton"
              style={{
                width: "80%",
                height: 14,
                marginBottom: "var(--space-3)",
              }}
            />
            {/* Source + bars */}
            <div style={{ display: "flex", gap: "var(--space-3)" }}>
              <div className="skeleton" style={{ width: 70, height: 14 }} />
              <div className="skeleton" style={{ width: 24, height: 20 }} />
            </div>
          </div>
        ))}
      </div>

      {/* Screen-reader only loading text */}
      <span
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          whiteSpace: "nowrap",
          borderWidth: 0,
        }}
      >
        Loading stories, please wait...
      </span>
    </div>
  );
}
