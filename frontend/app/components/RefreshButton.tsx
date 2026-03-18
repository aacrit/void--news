"use client";

import { useState } from "react";

/* ---------------------------------------------------------------------------
   RefreshButton — Subtle "Last updated" with refresh action
   Click triggers confirmation dialog. On confirm, simulates data refresh.
   --------------------------------------------------------------------------- */

export default function RefreshButton() {
  const [showConfirm, setShowConfirm] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState("6:00 AM CT");

  const handleRefresh = () => {
    setShowConfirm(false);
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
      const now = new Date();
      const hours = now.getHours();
      const minutes = now.getMinutes().toString().padStart(2, "0");
      const ampm = hours >= 12 ? "PM" : "AM";
      const h = hours % 12 || 12;
      setLastUpdated(`${h}:${minutes} ${ampm} CT`);
    }, 1200);
  };

  return (
    <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
      <button
        onClick={() => setShowConfirm(true)}
        disabled={refreshing}
        aria-label={`Last updated ${lastUpdated}. Click to refresh.`}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          color: "var(--fg-tertiary)",
          padding: "var(--space-2) var(--space-3)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          cursor: refreshing ? "wait" : "pointer",
          opacity: refreshing ? 0.6 : 1,
          transition:
            "opacity var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
          fontFeatureSettings: '"tnum" 1',
          minHeight: 32,
        }}
        onMouseEnter={(e) => {
          if (!refreshing)
            (e.currentTarget as HTMLElement).style.borderColor =
              "var(--border-strong)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLElement).style.borderColor =
            "var(--border-subtle)";
        }}
      >
        {/* Refresh icon */}
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          style={{
            animation: refreshing ? "spin 1s linear infinite" : "none",
          }}
        >
          <polyline points="23 4 23 10 17 10" />
          <polyline points="1 20 1 14 7 14" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
        <span>
          {refreshing ? "Refreshing..." : `Last updated: ${lastUpdated}`}
        </span>
      </button>

      {/* Confirmation dialog */}
      {showConfirm && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => setShowConfirm(false)}
            style={{
              position: "fixed",
              inset: 0,
              zIndex: "var(--z-overlay)",
              backgroundColor: "rgba(0, 0, 0, 0.15)",
              animation: "fadeIn var(--dur-normal) var(--ease-out)",
            }}
          />
          {/* Dialog */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Confirm refresh"
            style={{
              position: "fixed",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              zIndex: "var(--z-modal)",
              backgroundColor: "var(--bg-card)",
              border: "1px solid var(--border-strong)",
              padding: "var(--space-5) var(--space-6)",
              maxWidth: 340,
              width: "90%",
              animation: "fadeInUp var(--dur-normal) var(--ease-out)",
              boxShadow: "var(--shadow-e3)",
            }}
          >
            <h3
              style={{
                fontFamily: "var(--font-editorial)",
                fontSize: "var(--text-lg)",
                fontWeight: 700,
                marginBottom: "var(--space-3)",
                color: "var(--fg-primary)",
              }}
            >
              Refresh data?
            </h3>
            <p
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-sm)",
                color: "var(--fg-secondary)",
                marginBottom: "var(--space-5)",
                lineHeight: 1.5,
              }}
            >
              This will re-fetch the latest stories from all sources.
            </p>
            <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowConfirm(false)}
                style={{
                  fontFamily: "var(--font-structural)",
                  fontSize: "var(--text-sm)",
                  fontWeight: 500,
                  color: "var(--fg-tertiary)",
                  padding: "var(--space-2) var(--space-4)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  minHeight: 36,
                  minWidth: 44,
                  transition: "border-color var(--dur-fast) var(--ease-out)",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleRefresh}
                style={{
                  fontFamily: "var(--font-structural)",
                  fontSize: "var(--text-sm)",
                  fontWeight: 600,
                  color: "var(--bg-primary)",
                  backgroundColor: "var(--fg-primary)",
                  padding: "var(--space-2) var(--space-4)",
                  borderRadius: "var(--radius-md)",
                  minHeight: 36,
                  minWidth: 44,
                  transition:
                    "opacity var(--dur-fast) var(--ease-out)",
                }}
              >
                Refresh
              </button>
            </div>
          </div>
        </>
      )}

      {/* Spin keyframe injected */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
