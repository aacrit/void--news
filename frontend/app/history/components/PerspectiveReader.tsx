"use client";

import { useEffect, useCallback, useRef } from "react";
import type { Perspective } from "../types";
import PrimarySourceBlock from "./PrimarySourceBlock";
import OmissionsPanel from "./OmissionsPanel";

/* ===========================================================================
   PerspectiveReader — Full-account reading overlay.
   Opens from a reel frame's "Read the full account". Holds the long
   narrative + primary sources + emphasized/omitted/disputed in a clean,
   left-aligned reading column whose typography matches the main site.
   Focus-trapped modal with Escape + body-scroll lock (mirrors Lightbox).
   =========================================================================== */

interface PerspectiveReaderProps {
  perspective: Perspective;
  onClose: () => void;
}

export default function PerspectiveReader({ perspective, onClose }: PerspectiveReaderProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const root = rootRef.current;
        if (!root) return;
        const focusable = root.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
    [onClose]
  );

  useEffect(() => {
    triggerRef.current = document.activeElement as HTMLElement | null;
    document.addEventListener("keydown", handleKeyDown);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    rootRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = prevOverflow;
      triggerRef.current?.focus();
    };
  }, [handleKeyDown]);

  const onBackdrop = (e: React.MouseEvent) => {
    if (e.target === rootRef.current) onClose();
  };

  const paragraphs = perspective.narrative.split("\n").filter(Boolean);

  return (
    <div
      ref={rootRef}
      className="hist-reader"
      role="dialog"
      aria-modal="true"
      aria-label={`${perspective.viewpointName} — full account`}
      tabIndex={-1}
      onClick={onBackdrop}
    >
      <article className="hist-reader__sheet">
        <button
          type="button"
          className="hist-reader__close"
          onClick={onClose}
          aria-label="Close account"
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M18 6L6 18" />
            <path d="M6 6l12 12" />
          </svg>
        </button>

        <header className="hist-reader__head">
          <span
            className="hist-reader__eyebrow"
            style={{ color: `var(--hist-persp-${perspective.color})` }}
          >
            {perspective.viewpointType}
            {perspective.geographicAnchor ? ` · ${perspective.geographicAnchor}` : ""}
          </span>
          <h2 className="hist-reader__name">{perspective.viewpointName}</h2>
        </header>

        <div className="hist-reader__body">
          {paragraphs.map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>

        {perspective.primarySources.length > 0 && (
          <section className="hist-reader__sources" aria-label="Primary sources">
            <h3 className="hist-reader__subhead">Primary sources</h3>
            {perspective.primarySources.map((source, i) => (
              <PrimarySourceBlock key={i} source={source} />
            ))}
          </section>
        )}

        <OmissionsPanel
          keyNarratives={perspective.keyNarratives}
          omissions={perspective.omissions}
          disputed={perspective.disputed}
          color={perspective.color}
        />
      </article>
    </div>
  );
}
