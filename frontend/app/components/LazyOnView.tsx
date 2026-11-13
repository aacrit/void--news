"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode, type CSSProperties } from "react";

/* Stable, never-changing subscriber/snapshot for IO-unsupported detection. */
const NOOP_SUBSCRIBE = () => () => {};
const isIOSupported = (): boolean => typeof IntersectionObserver !== "undefined";
const isIOSupportedServer = (): boolean => true;

/* ---------------------------------------------------------------------------
   LazyOnView — Render children only after the wrapper enters the viewport.

   Usage: wrap heavy below-the-fold sections (charts, comparative views,
   source grids) so they stay out of the initial render path. Once visible,
   the children mount and stay mounted (no re-render thrashing on scroll).

   Phase 4 of the mobile redesign uses this on DeepDive subsections to
   reduce time-to-interactive on Deep Dive open.
   --------------------------------------------------------------------------- */

interface LazyOnViewProps {
  children: ReactNode;
  /** Margin around root used by IO. e.g. "200px 0px" pre-loads slightly below the fold. */
  rootMargin?: string;
  /** Visibility threshold to fire (0 = any pixel, 1 = full element). */
  threshold?: number;
  /** Skeleton or fallback rendered before children mount. */
  placeholder?: ReactNode;
  /** Min-height so layout doesn't shift before children load. */
  minHeight?: number | string;
  /** Optional className passed to wrapper. */
  className?: string;
}

export default function LazyOnView({
  children,
  rootMargin = "200px 0px",
  threshold = 0,
  placeholder = null,
  minHeight,
  className,
}: LazyOnViewProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  // Initialize as true if IO is unsupported — avoids setState-in-effect.
  const ioSupported = useSyncExternalStore(NOOP_SUBSCRIBE, isIOSupported, isIOSupportedServer);
  const [shown, setShown] = useState(!ioSupported);

  useEffect(() => {
    if (shown) return;
    const el = wrapRef.current;
    if (!el) return;
    if (!ioSupported) return;

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setShown(true);
            io.disconnect();
            break;
          }
        }
      },
      { rootMargin, threshold },
    );

    io.observe(el);
    return () => io.disconnect();
  }, [rootMargin, threshold, shown, ioSupported]);

  const style: CSSProperties | undefined = minHeight !== undefined
    ? { minHeight: typeof minHeight === "number" ? `${minHeight}px` : minHeight }
    : undefined;

  return (
    <div ref={wrapRef} className={className} style={style}>
      {shown ? children : placeholder}
    </div>
  );
}
