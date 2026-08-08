"use client";

import { useRef, useState, useEffect } from "react";
import { Lightning } from "@phosphor-icons/react";

/* ===========================================================================
   ConsensusBadge — void --verify
   Compact claim consensus indicator shown on story cards next to the Sigil.
   Displays corroborated/total ratio in data voice (IBM Plex Mono).
   Disputed claims marked with a lightning icon in warm amber.

   [V11] Lightning emoji replaced with Phosphor Lightning icon.
   [C-P1] data-entered attribute drives viewport entrance animation.
   [C-P3] Lightning icon uses lightningFlare animation class.
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
    if (!el) return;

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
  }, []);

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
          <span className="consensus-badge__mark consensus-badge__lightning-icon" aria-hidden="true">
            <Lightning size={12} weight="bold" />
          </span>
          <span className="consensus-badge__count">{disputed}</span>
        </span>
      )}
    </span>
  );
}
