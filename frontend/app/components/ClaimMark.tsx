"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import type { DisputedClaim } from "../lib/types";

/* ===========================================================================
   ClaimMark — void --verify
   Inline contradiction highlight for Deep Dive summary text.

   Wraps disputed text in a <span> with wavy underline. On hover/tap, a
   popover reveals both versions with source attribution.

   Cinematic: dormant = haze filter + muted wavy underline.
   Focused = sharp focus, amber background gradient, rack-focus popover.
   =========================================================================== */

interface ClaimMarkProps {
  text: string;
  disputed: DisputedClaim;
}

export default function ClaimMark({ text, disputed }: ClaimMarkProps) {
  const [focused, setFocused] = useState(false);
  const markRef = useRef<HTMLSpanElement>(null);
  const popoverId = useId();

  // Close on outside click
  useEffect(() => {
    if (!focused) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (!markRef.current?.contains(target)) {
        setFocused(false);
      }
    };
    document.addEventListener("click", handler, true);
    return () => document.removeEventListener("click", handler, true);
  }, [focused]);

  // Close on Escape
  useEffect(() => {
    if (!focused) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFocused(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [focused]);

  const handleToggle = useCallback(() => {
    setFocused((prev) => !prev);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleToggle();
      }
    },
    [handleToggle],
  );

  return (
    <span
      ref={markRef}
      className={`claim-mark${focused ? " claim-mark--focused" : ""}`}
      style={{ position: "relative" }}
    >
      <span
        role="button"
        tabIndex={0}
        aria-label={`Disputed claim: sources disagree about ${disputed.topic}`}
        aria-describedby={focused ? popoverId : undefined}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
      >
        {text}
      </span>

      {focused && (
        <div
          id={popoverId}
          className="claim-mark__popover"
          role="status"
          aria-live="polite"
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
          }}
        >
          <span className="claim-mark__label">Sources disagree</span>

          <div className="claim-mark__version">
            <p className="claim-mark__text">{disputed.version_a}</p>
            <span className="claim-mark__sources">
              {disputed.version_a_sources.join(", ")}
            </span>
          </div>

          <span className="claim-mark__vs" aria-hidden="true">
            vs
          </span>

          <div className="claim-mark__version">
            <p className="claim-mark__text">{disputed.version_b}</p>
            <span className="claim-mark__sources">
              {disputed.version_b_sources.join(", ")}
            </span>
          </div>
        </div>
      )}
    </span>
  );
}
