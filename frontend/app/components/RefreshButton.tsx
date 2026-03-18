"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Clock, Warning } from "@phosphor-icons/react";
import LogoIcon from "./LogoIcon";

/* ---------------------------------------------------------------------------
   RefreshButton — Subtle "Last updated" with refresh action
   --------------------------------------------------------------------------- */

interface RefreshButtonProps {
  externalLastUpdated?: string | null;
}

export default function RefreshButton({ externalLastUpdated }: RefreshButtonProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [localLastUpdated, setLocalLastUpdated] = useState("6:00 AM CT");

  const refreshButtonRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  const displayTime = externalLastUpdated
    ? new Date(externalLastUpdated).toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      })
    : localLastUpdated;

  const closeDialog = useCallback(() => {
    setShowConfirm(false);
  }, []);

  const handleRefresh = useCallback(() => {
    setShowConfirm(false);
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
      const now = new Date();
      const hours = now.getHours();
      const minutes = now.getMinutes().toString().padStart(2, "0");
      const ampm = hours >= 12 ? "PM" : "AM";
      const h = hours % 12 || 12;
      setLocalLastUpdated(`${h}:${minutes} ${ampm} CT`);
    }, 1200);
  }, []);

  useEffect(() => {
    if (showConfirm) {
      const t = setTimeout(() => cancelButtonRef.current?.focus(), 0);
      return () => clearTimeout(t);
    } else {
      refreshButtonRef.current?.focus();
    }
  }, [showConfirm]);

  useEffect(() => {
    if (!showConfirm) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeDialog();
        return;
      }

      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [showConfirm, closeDialog]);

  return (
    <div style={{ position: "relative", display: "inline-flex", alignItems: "center" }}>
      <button
        ref={refreshButtonRef}
        onClick={() => setShowConfirm(true)}
        disabled={refreshing}
        aria-label={`Last updated ${displayTime}. Click to refresh.`}
        className={`refresh-btn${refreshing ? " refresh-btn--loading" : ""}`}
      >
        <LogoIcon animation={refreshing ? "loading" : "none"} size={14} />
        <Clock size={12} weight="light" aria-hidden="true" />
        <span>{refreshing ? "Refreshing..." : `Last updated: ${displayTime}`}</span>
      </button>

      {showConfirm && (
        <>
          <div
            onClick={closeDialog}
            className="deep-dive-backdrop anim-fade-in"
          />
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="Confirm refresh"
            className="refresh-dialog anim-fade-in-up"
          >
            <h3
              className="section-heading"
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-2)",
                borderBottom: "none",
                paddingBottom: 0,
              }}
            >
              <Warning size={20} weight="light" aria-hidden="true" />
              Refresh data?
            </h3>
            <p style={{
              fontFamily: "var(--font-structural)",
              fontSize: "var(--text-sm)",
              color: "var(--fg-secondary)",
              marginBottom: "var(--space-5)",
              lineHeight: 1.5,
            }}>
              This will re-fetch the latest stories from all sources.
            </p>
            <div className="refresh-dialog__actions">
              <button ref={cancelButtonRef} onClick={closeDialog} className="btn-secondary">
                Cancel
              </button>
              <button onClick={handleRefresh} className="btn-primary">
                Refresh
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
