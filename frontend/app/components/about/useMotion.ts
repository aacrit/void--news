"use client";

import { useEffect, useState } from "react";

/* ---------------------------------------------------------------------------
   useMotion — lazily loads Motion One (the `motion` package) on the client.

   Returns null until loaded, so beats render their static final state first
   and "upgrade" to physics once the chunk arrives. Because the import is
   dynamic and lives only under the about/onboarding tree (itself reached via
   dynamic import from the feed), `motion` never enters the main feed bundle.
   --------------------------------------------------------------------------- */

type MotionModule = typeof import("motion");

export function useMotion(enabled = true): MotionModule | null {
  const [mod, setMod] = useState<MotionModule | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let live = true;
    import("motion").then((m) => { if (live) setMod(m); }).catch(() => { /* static fallback */ });
    return () => { live = false; };
  }, [enabled]);

  return mod;
}
