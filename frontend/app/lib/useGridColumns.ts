"use client";

import { useEffect, useState } from "react";

/** How many cards a desktop feed row holds, from the same bands
 *  styles/responsive.css lays the grid out in: 2 from 768px, 3 from 1024px,
 *  4 from 1440px, and one fewer (never under 2) while the On Air pane is open
 *  (html[data-onair-pane]), because the pane takes that width from the feed.
 *  The inline Deep Dive opens after the end of the opened card's row, so this
 *  has to agree with the CSS, and a resize or the pane opening keeps it so. */
export function useGridColumns(): number {
  const [cols, setCols] = useState(4);
  useEffect(() => {
    const q3 = window.matchMedia("(min-width: 1024px)");
    const q4 = window.matchMedia("(min-width: 1440px)");
    const root = document.documentElement;
    const read = () => {
      const base = q4.matches ? 4 : q3.matches ? 3 : 2;
      const pane = q3.matches && root.hasAttribute("data-onair-pane");
      setCols(pane ? Math.max(2, base - 1) : base);
    };
    read();
    q3.addEventListener("change", read);
    q4.addEventListener("change", read);
    const mo = new MutationObserver(read);
    mo.observe(root, { attributes: true, attributeFilter: ["data-onair-pane"] });
    return () => {
      q3.removeEventListener("change", read);
      q4.removeEventListener("change", read);
      mo.disconnect();
    };
  }, []);
  return cols;
}
