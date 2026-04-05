/* DEFERRED: Not rendered in current version. Preserved for Phase 2. */
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
      <section aria-label="Media gallery">
        <h3 className="hist-section-label">Archival Media</h3>
        <div className="hist-gallery" role="list">
          {media.map((item, i) => (
            <button
              key={item.id}
              className="hist-gallery__item"
              role="listitem"
              onClick={() => setLightboxIndex(i)}
              aria-label={`View: ${item.caption}`}
            >
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
              <p className="hist-gallery__caption">{item.caption}</p>
              <p className="hist-gallery__attribution">
                {item.attribution}
                {item.year && ` (${item.year})`}
              </p>
            </button>
          ))}
        </div>
      </section>

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
