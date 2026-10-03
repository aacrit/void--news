"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "../../film/useReducedMotion";
import { useMotion } from "./useMotion";

/* ---------------------------------------------------------------------------
   useReveal — the shared scroll-reveal used by the page-only About sections
   (Mission, Pipeline, FAQ). Mirrors the beats' Motion One `inView` + spring
   stagger so the deeper /about sections animate in identically to the beats.

   Returns { rootRef, register }. Attach rootRef to the section; call
   register(i) as the ref for each element that should stagger in. Elements
   start at opacity 0 (set inline by the caller) and spring to full on view.
   Reduced motion / no Motion: elements are shown immediately.
   --------------------------------------------------------------------------- */

export function useReveal<T extends HTMLElement = HTMLElement>() {
  const reduced = useReducedMotion();
  const motion = useMotion(!reduced.current);
  const rootRef = useRef<T>(null);
  const items = useRef<(HTMLElement | null)[]>([]);
  const played = useRef(false);

  const register = (i: number) => (el: HTMLElement | null) => {
    items.current[i] = el;
  };

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    if (reduced.current || !motion) {
      items.current.forEach((el) => {
        if (el) { el.style.opacity = "1"; el.style.transform = "none"; }
      });
      return;
    }

    const stop = motion.inView(root, () => {
      if (played.current) return;
      played.current = true;
      items.current.forEach((el, i) => {
        if (!el) return;
        motion.animate(
          el,
          { opacity: [0, 1], transform: ["translateY(16px)", "translateY(0)"] },
          { type: "spring", stiffness: 190, damping: 24, delay: i * 0.08 },
        );
      });
    }, { amount: 0.25 });

    return () => stop();
  }, [motion, reduced]);

  return { rootRef, register };
}
