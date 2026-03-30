"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/* ---------------------------------------------------------------------------
   KeyboardShortcuts — Hidden overlay triggered by ?
   Power-user feature: J/K navigate stories, Enter opens Deep Dive,
   Escape closes it, arrow keys navigate between stories in Deep Dive.
   --------------------------------------------------------------------------- */

const SHORTCUTS = [
  { keys: ["J"], action: "Next story" },
  { keys: ["K"], action: "Previous story" },
  { keys: ["Enter"], action: "Open void --deep-dive" },
  { keys: ["Esc"], action: "Close panel" },
  { keys: ["\u2190", "\u2192"], action: "Prev/next story" },
  { keys: ["?"], action: "Toggle this overlay" },
];

export function KeyboardShortcutsOverlay() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<Element | null>(null);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      // Don't trigger when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) return;

      if (e.key === "?" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (!open) {
          previousFocusRef.current = document.activeElement;
        }
        setOpen((v) => !v);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }

    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  // Focus management: move focus into dialog on open, restore on close
  useEffect(() => {
    if (open) {
      // Focus the panel on open
      requestAnimationFrame(() => {
        panelRef.current?.focus();
      });
    } else if (previousFocusRef.current) {
      // Restore focus to previously focused element
      const el = previousFocusRef.current as HTMLElement;
      if (typeof el.focus === "function") el.focus();
      previousFocusRef.current = null;
    }
  }, [open]);

  // Focus trap: Tab wraps within the dialog
  const handleTrapKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "Tab") return;

    const panel = panelRef.current;
    if (!panel) return;

    const focusable = panel.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) {
      // Nothing to trap, keep focus on panel itself
      e.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (e.shiftKey) {
      // Shift+Tab at first (or panel itself) => wrap to last
      if (document.activeElement === first || document.activeElement === panel) {
        e.preventDefault();
        last.focus();
      }
    } else {
      // Tab at last => wrap to first
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  if (!open) return null;

  return (
    <div
      className="kbd-overlay"
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div
        ref={panelRef}
        className="kbd-overlay__panel"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleTrapKeyDown}
        tabIndex={-1}
      >
        <h3 className="kbd-overlay__title">Keyboard Shortcuts</h3>
        <div className="kbd-overlay__list">
          {SHORTCUTS.map((s) => (
            <div key={s.action} className="kbd-overlay__row">
              <div className="kbd-overlay__keys">
                {s.keys.map((k) => (
                  <kbd key={k} className="kbd-overlay__key">{k}</kbd>
                ))}
              </div>
              <span className="kbd-overlay__action">{s.action}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/** Hook for J/K story navigation in the feed */
export function useStoryKeyboardNav(
  stories: { id: string }[],
  onStorySelect: (index: number) => void,
  deepDiveOpen: boolean,
) {
  const [focusedIndex, setFocusedIndex] = useState(-1);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't interfere when Deep Dive is open or typing in inputs
      if (deepDiveOpen) return;
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) return;

      if (e.key === "j" || e.key === "J") {
        e.preventDefault();
        setFocusedIndex((prev) => {
          const next = Math.min(prev + 1, stories.length - 1);
          // Scroll the focused card into view
          const el = document.querySelector(`[data-story-index="${next}"]`);
          el?.scrollIntoView({ behavior: "smooth", block: "center" });
          return next;
        });
      } else if (e.key === "k" || e.key === "K") {
        e.preventDefault();
        setFocusedIndex((prev) => {
          const next = Math.max(prev - 1, 0);
          const el = document.querySelector(`[data-story-index="${next}"]`);
          el?.scrollIntoView({ behavior: "smooth", block: "center" });
          return next;
        });
      } else if ((e.key === "Enter" || e.key === "o") && focusedIndex >= 0) {
        e.preventDefault();
        onStorySelect(focusedIndex);
      }
    },
    [stories.length, deepDiveOpen, focusedIndex, onStorySelect],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Reset focus when stories change
  useEffect(() => {
    setFocusedIndex(-1);
  }, [stories]);

  return focusedIndex;
}
