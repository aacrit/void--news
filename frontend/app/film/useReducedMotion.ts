import { useRef, useEffect } from "react";

/** Shared hook — checks prefers-reduced-motion once on mount. */
export function useReducedMotion(): React.MutableRefObject<boolean> {
  const ref = useRef(false);
  useEffect(() => {
    ref.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);
  return ref;
}
