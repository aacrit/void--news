"use client";

import { useLayoutEffect, useRef, useCallback } from "react";

/* ---------------------------------------------------------------------------
   useHeightMorph — FLIP-style height continuity for content swaps.

   For containers whose expand/collapse REPLACES their content (the Skybox
   brief, the mobile brief pill), the height used to jump in a single frame
   while the incoming content faded in afterwards: two beats. This hook makes
   the swap ONE continuous motion — call capture() immediately before the state
   change; after React commits the new content, the container's height animates
   from the captured value to its new natural value on the same timeline the
   incoming content fades in on.

   Height is a layout property, but this animates a single container (not a
   list), which is exactly the accordion pattern used elsewhere (InlineDeepDive,
   .mbp__expand). Respects prefers-reduced-motion (instant swap).
   --------------------------------------------------------------------------- */
export function useHeightMorph<T extends HTMLElement>(
  dep: unknown,
  duration = 280,
) {
  const ref = useRef<T | null>(null);
  const prevHeightRef = useRef<number | null>(null);

  /** Call right before the state change that swaps the container's content. */
  const capture = useCallback(() => {
    prevHeightRef.current = ref.current?.offsetHeight ?? null;
  }, []);

  useLayoutEffect(() => {
    const el = ref.current;
    const prev = prevHeightRef.current;
    prevHeightRef.current = null;
    if (!el || prev == null) return;
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (typeof el.animate !== "function") return;
    const next = el.offsetHeight;
    if (Math.abs(next - prev) < 2) return;

    const prevOverflow = el.style.overflow;
    el.style.overflow = "hidden";
    const anim = el.animate(
      [{ height: `${prev}px` }, { height: `${next}px` }],
      { duration, easing: "cubic-bezier(0.22, 1, 0.36, 1)" }, // --ease-cinematic
    );
    const settle = () => {
      el.style.overflow = prevOverflow;
    };
    anim.onfinish = settle;
    anim.oncancel = settle;
    return () => anim.cancel();
    // The dep IS the signal that content swapped; duration is stable in practice.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);

  return { ref, capture };
}
