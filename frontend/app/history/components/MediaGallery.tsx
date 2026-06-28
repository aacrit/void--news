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
}

export default function MediaGallery({ media }: MediaGalleryProps) {
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  if (media.length === 0) return null;

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
              onClick={() => setLightboxIndex(i)}
              aria-label={`${isVideo ? "Play" : "View"}: ${item.caption}`}
            >
              <span className="hist-gallery__frame">
                <img
                  src={item.url}
                  alt={item.caption}
                  className="hist-gallery__image"
                  loading="lazy"
                  onError={(e) => {
                    /* Graceful fallback for missing images */
                    const target = e.currentTarget;
                    target.style.display = "none";
                    const parent = target.parentElement;
                    if (parent) {
                      const fallback = document.createElement("div");
                      fallback.style.cssText =
                        "width:100%;aspect-ratio:3/2;background:var(--hist-paper-deep);display:flex;align-items:center;justify-content:center;border-radius:2px;";
                      fallback.innerHTML = `<span style="font-family:var(--font-data);font-size:var(--text-xs);color:var(--hist-ink-muted);">[${item.type}]</span>`;
                      parent.insertBefore(fallback, target);
                    }
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
