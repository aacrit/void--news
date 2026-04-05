"use client";

import { useRef, useState, useEffect } from "react";

/* ===========================================================================
   ConsensusBadge — void --verify
   Compact claim consensus indicator shown on story cards next to the Sigil.
   Displays corroborated/total ratio in data voice (IBM Plex Mono).
   Disputed claims marked with a lightning mark in warm amber.

   Dormant: muted amber, haze filter. Hover: full opacity, sharp focus.
   Lightning mark pulses once on first viewport entry (IntersectionObserver).
   =========================================================================== */

interface ConsensusBadgeProps {
  ratio?: number;
  disputed?: number;
  total?: number;
  corroborated?: number;
}

export default function ConsensusBadge({
  ratio,
  disputed,
  total,
  corroborated,
}: ConsensusBadgeProps) {
  const badgeRef = useRef<HTMLSpanElement>(null);
  const [hasEntered, setHasEntered] = useState(false);

  // One-shot IntersectionObserver for lightning pulse on first viewport entry
  useEffect(() => {
    const el = badgeRef.current;
    if (!el || !disputed || disputed <= 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setHasEntered(true);
            observer.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "50px" },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [disputed]);

  // Hidden when no data or insufficient claims
  if (!total || total < 3 || corroborated == null) return null;

  const hasDisputed = disputed != null && disputed > 0;

  return (
    <span
      ref={badgeRef}
      className="consensus-badge"
      data-entered={hasEntered ? "true" : undefined}
      aria-label={`${corroborated} of ${total} claims corroborated${hasDisputed ? `, ${disputed} disputed` : ""}`}
    >
      <span className="consensus-badge__ratio">
        {corroborated}/{total}
      </span>
      {hasDisputed && (
        <span
          className={`consensus-badge__disputed${hasEntered ? " consensus-badge__disputed--entered" : ""}`}
          aria-label={`${disputed} disputed claim${disputed !== 1 ? "s" : ""}`}
        >
          <span className="consensus-badge__mark" aria-hidden="true">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 1.5L3.5 9H8L7 14.5L12.5 7H8L9 1.5Z" />
            </svg>
          </span>
          <span className="consensus-badge__count">{disputed}</span>
        </span>
      )}
    </span>
  );
}
