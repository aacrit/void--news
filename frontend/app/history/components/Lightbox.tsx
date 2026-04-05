"use client";

import { useEffect, useCallback, useRef } from "react";
import type { MediaItem } from "../types";

/* ===========================================================================
   Lightbox — Full-screen media viewer
   Dark backdrop, centered image, caption + attribution, prev/next arrows,
   close button, keyboard navigation.
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
  const current = media[currentIndex];
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < media.length - 1;

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
      }
    },
    [onClose, onNavigate, currentIndex, hasPrev, hasNext]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    /* Prevent background scroll */
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = prev;
    };
  }, [handleKeyDown]);

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
