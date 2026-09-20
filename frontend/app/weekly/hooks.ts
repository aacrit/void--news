"use client";

/* void --weekly — client behaviour. */

import { useEffect, useRef, useState } from "react";

/**
 * Reveal a section once, the first time it enters the viewport.
 *
 * Unobserves on the first hit: a magazine page is read downward, and a section
 * that has been seen does not need re-animating on the way back up. Returns
 * visible immediately under prefers-reduced-motion, so nothing is ever hidden
 * behind an animation that will not play.
 */
export function useScrollReveal(
  threshold = 0.15
): [React.RefObject<HTMLElement | null>, boolean] {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (
      typeof window === "undefined" ||
      !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold, rootMargin: "0px 0px -8% 0px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold]);

  return [ref, visible];
}

/**
 * Track whether an image actually loaded.
 *
 * `onError` alone is NOT enough for an image the server already rendered. The
 * browser requests it while parsing the HTML, so a 404 or a 429 is over before
 * hydration attaches the handler and the callback never fires. Blocking
 * upload.wikimedia.org reproduced it exactly: `complete: true`,
 * `naturalWidth: 0`, and the cover still in its image variant — near-white
 * furniture over a scrim with nothing behind it, under a credit line for a
 * photograph that was not on the page.
 *
 * These are hotlinked Wikimedia Commons URLs. They 404 and they 429 in the
 * wild, so this is a live case, not a theoretical one.
 *
 * Returns a ref to put on the <img>, plus `loaded` and `failed`. A caller must
 * treat `failed` as "there is no picture here" — no scrim, no credit, no
 * caption, and the typographic variant of whatever it was decorating.
 */
export function useImageStatus(src?: string | null) {
  const ref = useRef<HTMLImageElement | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setLoaded(false);
    setFailed(false);
    if (!src) return;
    const img = ref.current;
    if (!img) return;
    // The decision the browser already made, before React was listening.
    if (img.complete) {
      if (img.naturalWidth === 0) setFailed(true);
      else setLoaded(true);
    }
  }, [src]);

  return {
    ref,
    loaded,
    failed,
    onLoad: () => setLoaded(true),
    onError: () => setFailed(true),
  };
}
