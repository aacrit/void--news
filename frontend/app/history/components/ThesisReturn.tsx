"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/* ===========================================================================
   ThesisReturn: the one way back.

   Every note in the Notes section used to carry its own RETURN link, a
   hundred copies of one word down the foot of the page. This is the single
   control that replaces them, fixed in one place (bottom right, clear of the
   audio pill on the left and above the phone's tab bar), in two states:

     * after a jump to a note, "Back to the text": it returns to the exact
       citation the reader left, scrolls it into view and gives it focus;
     * otherwise, once the reader is well into the page, "Top".

   The note anchors are untouched: a citation is still an <a href="#nN">, the
   jump is the browser's own, and with JavaScript off it all still works (the
   browser's Back returns from a note). This island only listens.

   Keyboard and screen reader: the control is a real <button> with a name that
   says where it goes; after a jump focus moves to the note itself (so the
   note is what is read), a polite live region says how to get back, and
   Escape returns from anywhere outside a form field. Reduced motion is read
   at the moment of the move, and the show and hide are opacity only.
   =========================================================================== */

function reducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

type Mode = "hidden" | "top" | "return";

export default function ThesisReturn() {
  const [mode, setMode] = useState<Mode>("hidden");
  const [note, setNote] = useState<string | null>(null);
  const [announce, setAnnounce] = useState("");
  const origin = useRef<HTMLElement | null>(null);
  const deep = useRef(false);

  const clearReturn = useCallback(() => {
    origin.current = null;
    setNote(null);
    setMode(deep.current ? "top" : "hidden");
  }, []);

  const goBack = useCallback(() => {
    const el = origin.current;
    if (!el || !el.isConnected) { clearReturn(); return; }
    el.scrollIntoView({ block: "center", behavior: reducedMotion() ? "auto" : "smooth" });
    el.focus({ preventScroll: true });
    setAnnounce("");
    clearReturn();
  }, [clearReturn]);

  const goTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
    const target = document.getElementById("main-content") ?? document.querySelector("h1");
    if (target instanceof HTMLElement) {
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
    }
  }, []);

  /* A citation click anywhere in the thesis arms the return. */
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a[href^='#n']");
      if (!(a instanceof HTMLAnchorElement) || !a.closest(".hist-th")) return;
      const id = a.getAttribute("href")!.slice(1);
      if (!/^n\d+$/.test(id)) return;
      if (a.closest(".hist-th-notes")) return;
      origin.current = a;
      setNote(id.slice(1));
      setMode("return");
      setAnnounce(`Note ${id.slice(1)}. Press Escape or use Back to the text to return.`);
      /* After the browser's own jump, hand focus to the note so the note is
         what a screen reader reads next. */
      window.setTimeout(() => {
        const li = document.getElementById(id);
        if (li) {
          if (!li.hasAttribute("tabindex")) li.setAttribute("tabindex", "-1");
          li.focus({ preventScroll: true });
        }
      }, 0);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  /* Escape returns, unless the key belongs to something else. */
  useEffect(() => {
    if (mode !== "return") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape" || e.defaultPrevented) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.closest("input, textarea, select, [contenteditable='true'], [role='dialog']"))) return;
      e.preventDefault();
      goBack();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mode, goBack]);

  /* The reader who scrolls back to the citation on their own has returned:
     once the jump has landed on the note, a citation that leaves the viewport
     and comes back ends the offer. Nothing counts until the note is reached,
     because a smooth jump from above scrolls straight past the citation on
     its way down. */
  useEffect(() => {
    if (mode !== "return" || !origin.current || !note || typeof IntersectionObserver === "undefined") return;
    const target = document.getElementById(`n${note}`);
    let arrived = false;
    let originVisible = true;
    let leftAfterArrival = false;
    const originIO = new IntersectionObserver((entries) => {
      for (const en of entries) {
        originVisible = en.isIntersecting;
        if (!arrived) continue;
        if (!originVisible) leftAfterArrival = true;
        else if (leftAfterArrival) clearReturn();
      }
    });
    const noteIO = new IntersectionObserver((entries) => {
      if (entries.some((en) => en.isIntersecting)) {
        arrived = true;
        if (!originVisible) leftAfterArrival = true;
        noteIO.disconnect();
      }
    });
    originIO.observe(origin.current);
    if (target) noteIO.observe(target); else arrived = true;
    return () => { originIO.disconnect(); noteIO.disconnect(); };
  }, [mode, note, clearReturn]);

  /* "Top" once the reader is two screens in. A passive listener that reads
     one number and does no layout, coalesced to a frame. */
  useEffect(() => {
    let raf = 0;
    const read = () => {
      raf = 0;
      const d = window.scrollY > window.innerHeight * 2;
      if (d === deep.current) return;
      deep.current = d;
      setMode((m) => (m === "return" ? m : d ? "top" : "hidden"));
    };
    const onScroll = () => { if (!raf) raf = window.requestAnimationFrame(read); };
    read();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); if (raf) window.cancelAnimationFrame(raf); };
  }, []);

  const isReturn = mode === "return";
  return (
    <>
      <button
        type="button"
        className="hist-th-return"
        data-mode={mode}
        /* Hidden is visibility: hidden in the sheet, which takes it out of
           the tab order and the accessibility tree together. */
        aria-label={isReturn ? `Back to the text at note ${note}` : "Back to the top of the page"}
        onClick={isReturn ? goBack : goTop}
      >
        <svg className="hist-th-return__glyph" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
          {isReturn
            ? <path d="M6.5 3.5 3 7l3.5 3.5M3.25 7h6.25a3.5 3.5 0 0 1 0 7H7.5" />
            : <path d="M3 2.5h10M8 13.5V6M4.5 9.5 8 6l3.5 3.5" />}
        </svg>
        <span className="hist-th-return__label">{isReturn ? "Back to the text" : "Top"}</span>
      </button>
      <p className="sr-only" aria-live="polite">{announce}</p>
    </>
  );
}
