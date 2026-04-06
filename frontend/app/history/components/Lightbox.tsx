"use client";

import { useEffect, useCallback, useRef } from "react";
import type { MediaItem } from "../types";

/* ===========================================================================
   Lightbox — Full-screen media viewer
   Dark backdrop, centered image, caption + attribution, prev/next arrows,
   close button, keyboard navigation. Focus-trapped modal with return focus.
   =========================================================================== */

interface LightboxProps {
  media: MediaItem[];
  currentIndex: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

export default function Lightbox({
  media,
  currentIndex,
  onClose,
  onNavigate,
}: LightboxProps) {
  const backdropRef = useRef<HTMLDivElement>(null);
  /* Store the element that had focus before the lightbox opened */
  const triggerRef = useRef<HTMLElement | null>(null);
  const current = media[currentIndex];
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < media.length - 1;

  /* Focus trap: Tab wraps within the lightbox */
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          onClose();
          break;
        case "ArrowLeft":
          if (hasPrev) onNavigate(currentIndex - 1);
          break;
        case "ArrowRight":
          if (hasNext) onNavigate(currentIndex + 1);
          break;
        case "Tab": {
          const container = backdropRef.current;
          if (!container) break;
          const focusable = container.querySelectorAll<HTMLElement>(
            'button, [href], [tabindex]:not([tabindex="-1"])'
          );
          if (focusable.length === 0) break;
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
          break;
        }
      }
    },
    [onClose, onNavigate, currentIndex, hasPrev, hasNext]
  );

  useEffect(() => {
    /* Capture the trigger element on mount */
    triggerRef.current = document.activeElement as HTMLElement | null;

    document.addEventListener("keydown", handleKeyDown);
    /* Prevent background scroll */
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    /* Auto-focus the dialog container */
    backdropRef.current?.focus();

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = prev;
      /* Return focus to the element that opened the lightbox */
      triggerRef.current?.focus();
    };
  }, [handleKeyDown]);

  /* Preload adjacent images for snappy navigation (H12) */
  useEffect(() => {
    if (currentIndex > 0 && media[currentIndex - 1]?.url) {
      const img = new Image();
      img.src = media[currentIndex - 1].url;
    }
    if (currentIndex < media.length - 1 && media[currentIndex + 1]?.url) {
      const img = new Image();
      img.src = media[currentIndex + 1].url;
    }
  }, [currentIndex, media]);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === backdropRef.current) {
      onClose();
    }
  };

  if (!current) return null;

  return (
    <div
      className="hist-lightbox"
      ref={backdropRef}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label={`Viewing: ${current.caption}`}
      tabIndex={-1}
    >
      {/* Close button */}
      <button
        className="hist-lightbox__close"
        onClick={onClose}
        aria-label="Close lightbox"
      >
        &times;
      </button>

      {/* Prev */}
      {hasPrev && (
        <button
          className="hist-lightbox__nav hist-lightbox__nav--prev"
          onClick={() => onNavigate(currentIndex - 1)}
          aria-label="Previous image"
        >
          &larr;
        </button>
      )}

      {/* Image */}
      <img
        src={current.url}
        alt={current.caption}
        className="hist-lightbox__image"
        onError={(e) => {
          e.currentTarget.alt = `[Image unavailable: ${current.caption}]`;
          e.currentTarget.style.maxWidth = "400px";
          e.currentTarget.style.background = "var(--hist-bg-card)";
          e.currentTarget.style.padding = "2rem";
          e.currentTarget.style.textAlign = "center";
          e.currentTarget.style.color = "var(--hist-ink-muted)";
          e.currentTarget.style.fontFamily = "var(--font-data)";
          e.currentTarget.style.fontSize = "var(--text-sm)";
        }}
      />

      {/* Next */}
      {hasNext && (
        <button
          className="hist-lightbox__nav hist-lightbox__nav--next"
          onClick={() => onNavigate(currentIndex + 1)}
          aria-label="Next image"
        >
          &rarr;
        </button>
      )}

      {/* Caption */}
      <div className="hist-lightbox__caption">
        <p className="hist-lightbox__caption-text">{current.caption}</p>
        <p className="hist-lightbox__caption-attr">
          {current.attribution}
          {current.year && ` (${current.year})`}
        </p>
      </div>
    </div>
  );
}
