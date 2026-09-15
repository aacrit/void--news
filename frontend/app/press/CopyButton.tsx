"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * CopyButton — a small press-room affordance for the boilerplate blocks.
 * Copies the given plain text to the clipboard and confirms with a brief
 * "Copied" state. Structural voice (Inter), mono confirmation tick. Keyboard
 * accessible, focus-visible, and reduced-motion safe (the confirmation is a
 * text swap, not an animation).
 */
export default function CopyButton({
  text,
  label = "Copy",
}: {
  text: string;
  label?: string;
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  const onCopy = useCallback(async () => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for older WebKit / non-secure contexts.
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.style.position = "absolute";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard unavailable: leave the text selectable, do nothing loud.
    }
  }, [text]);

  return (
    <button
      type="button"
      className="press-copy"
      onClick={onCopy}
      data-copied={copied ? "true" : undefined}
      aria-live="polite"
    >
      <span aria-hidden="true" className="press-copy__icon">
        {copied ? "✓" : "⧉"}
      </span>
      {copied ? "Copied" : label}
    </button>
  );
}
