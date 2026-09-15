"use client";

import { useState } from "react";
import type { MediaItem } from "../types";
import Lightbox from "./Lightbox";

/* ===========================================================================
   MediaGallery — Horizontal scroll of media items with archival grade filter.
   Click opens Lightbox. Attribution bar below each image.
   =========================================================================== */

interface MediaGalleryProps {
  media: MediaItem[];
  /** When provided, a thumbnail click delegates to the caller (e.g. to open a
      shared Lightbox) instead of the gallery's own internal Lightbox. */
  onSelect?: (index: number) => void;
}

export default function MediaGallery({ media, onSelect }: MediaGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  if (media.length === 0) return null;

  const openAt = (i: number) => {
    if (onSelect) onSelect(i);
    else setLightboxIndex(i);
  };

  return (
    <>
      <div className="hist-gallery" role="list" aria-label="Archival media">
        {media.map((item, i) => {
          const isVideo = item.type === "video";
          return (
            <button
              key={item.id}
              className="hist-gallery__item"
              role="listitem"
              onClick={() => openAt(i)}
              aria-label={`${isVideo ? "Play" : "View"}: ${item.caption}`}
            >
              <span className="hist-gallery__frame">
                <img
                  src={item.url}
                  alt={item.caption}
                  className="hist-gallery__image"
                  loading="lazy"
                  onError={(e) => {
                    /* Skip broken thumbnails entirely — hide the whole item so
                       the gallery never shows a broken frame. */
                    const el = e.currentTarget.closest(".hist-gallery__item") as HTMLElement | null;
                    if (el) el.style.display = "none";
                  }}
                />
                {isVideo && (
                  <span className="hist-gallery__play" aria-hidden="true">
                    <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
                      <circle cx="24" cy="24" r="23" stroke="currentColor" strokeWidth="1.5" opacity="0.85" />
                      <path d="M19 16l14 8-14 8V16z" fill="currentColor" opacity="0.95" />
                    </svg>
                  </span>
                )}
              </span>
              <p className="hist-gallery__caption">{item.caption}</p>
              <p className="hist-gallery__attribution">
                {isVideo ? "Filmed by: " : ""}
                {item.attribution}
                {item.year && ` (${item.year})`}
              </p>
            </button>
          );
        })}
      </div>

      {lightboxIndex !== null && (
        <Lightbox
          media={media}
          currentIndex={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onNavigate={setLightboxIndex}
        />
      )}
    </>
  );
}
