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
