"use client";

import { useState, useRef, useEffect, useCallback } from "react";
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
  const popoverRef = useRef<HTMLDivElement>(null);

  // Position the popover above the mark
  const [popoverPos, setPopoverPos] = useState<{
    left: number;
    bottom: number;
  } | null>(null);

  const updatePosition = useCallback(() => {
    if (!markRef.current) return;
    const rect = markRef.current.getBoundingClientRect();
    setPopoverPos({
      left: rect.left + rect.width / 2,
      bottom: window.innerHeight - rect.top + 8,
    });
  }, []);

  // Close on outside click
  useEffect(() => {
    if (!focused) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        !markRef.current?.contains(target) &&
        !popoverRef.current?.contains(target)
      ) {
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
    setFocused((prev) => {
      if (!prev) updatePosition();
      return !prev;
    });
  }, [updatePosition]);

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
    <>
      <span
        ref={markRef}
        className={`claim-mark${focused ? " claim-mark--focused" : ""}`}
        role="button"
        tabIndex={0}
        aria-label={`Disputed claim: sources disagree about ${disputed.topic}`}
        aria-expanded={focused}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
      >
        {text}
      </span>

      {focused && popoverPos && (
        <div
          ref={popoverRef}
          className="claim-mark__popover"
          role="tooltip"
          style={{
            position: "fixed",
            left: `${popoverPos.left}px`,
            bottom: `${popoverPos.bottom}px`,
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
    </>
  );
}
