"use client";

import { useEffect, useState, useCallback } from "react";

/* ===========================================================================
   StorySpine — Sticky section navigation with scroll-spy.
   A slim bar above the reading column on desktop, a sticky segmented bar
   under the topbar on mobile. Clicking a section smooth-scrolls to its
   anchor; an IntersectionObserver tracks which section is in view and lights
   the matching label. Lets the reader orient and jump instead of scrolling
   blind through the whole dossier.
   =========================================================================== */

export interface SpineSection {
  id: string;
  label: string;
}

interface StorySpineProps {
  sections: SpineSection[];
}

export default function StorySpine({ sections }: StorySpineProps) {
  const [activeId, setActiveId] = useState(sections[0]?.id ?? "");

  useEffect(() => {
    const els = sections
      .map((s) => document.getElementById(s.id))
      .filter((el): el is HTMLElement => el !== null);
    if (els.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        /* Pick the entry nearest the top that is intersecting */
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActiveId(visible[0].target.id);
      },
      /* Bias the active band to the upper third of the viewport */
      { rootMargin: "-20% 0px -55% 0px", threshold: 0 }
    );

    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [sections]);

  const jump = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    setActiveId(id);
  }, []);

  if (sections.length < 2) return null;

  return (
    <nav className="hist-spine" aria-label="Sections of this story">
      <ul className="hist-spine__list">
        {sections.map((s) => (
          <li key={s.id} className="hist-spine__item">
            <button
              type="button"
              className={`hist-spine__link${
                s.id === activeId ? " hist-spine__link--active" : ""
              }`}
              aria-current={s.id === activeId ? "true" : undefined}
              onClick={() => jump(s.id)}
            >
              {s.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
