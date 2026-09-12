"use client";

import { useRef, useState, useEffect } from "react";

/* ===========================================================================
   Shared IntersectionObserver — pooled across all card components

   Instead of each StoryCard / MobileStoryCard / DigestRow / VisibleCard
   creating its own IntersectionObserver (50+ observers on a long feed),
   a single shared observer handles all elements via a WeakMap callback
   registry. Elements register on mount and unregister on unmount.
   =========================================================================== */

// Callback registry — maps observed elements to their visibility callbacks
const observerCallbacks = new WeakMap<Element, () => void>();
let sharedObserver: IntersectionObserver | null = null;

/**
 * Returns the singleton IntersectionObserver instance.
 * Created lazily on first call. rootMargin provides a 100px buffer
 * so elements start animating slightly before entering the viewport.
 */
export function getSharedObserver(): IntersectionObserver {
  if (sharedObserver) return sharedObserver;
  sharedObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const cb = observerCallbacks.get(entry.target);
          if (cb) {
            cb();
            observerCallbacks.delete(entry.target);
            sharedObserver?.unobserve(entry.target);
          }
        }
      }
    },
    { rootMargin: "100px" },
  );
  return sharedObserver;
}

export { observerCallbacks };

/* ---------------------------------------------------------------------------
   useInView — convenience hook for scroll-triggered entrance animation

   Returns [ref, visible]:
     ref     — attach to the DOM element to observe
     visible — flips to true once the element enters the viewport (one-shot)

   If the element is already in the viewport on mount (e.g. above the fold
   or after a filter re-render), it marks visible immediately without waiting
   for the observer callback.

   Options:
     earlyThreshold — extra px beyond viewport to treat as "already visible"
                      on mount (default 100). Prevents flash on elements just
                      below the fold during hydration.
   --------------------------------------------------------------------------- */

interface UseInViewOptions {
  earlyThreshold?: number;
}

export function useInView<T extends HTMLElement = HTMLElement>(
  options?: UseInViewOptions,
): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);
  const threshold = options?.earlyThreshold ?? 100;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // If already in viewport on mount, show immediately
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight + threshold) {
      setVisible(true);
      return;
    }

    // Guard against state updates after unmount
    let unmounted = false;
    const observer = getSharedObserver();
    observerCallbacks.set(el, () => {
      if (!unmounted) setVisible(true);
    });
    observer.observe(el);

    return () => {
      unmounted = true;
      observerCallbacks.delete(el);
      observer.unobserve(el);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return [ref, visible];
}
