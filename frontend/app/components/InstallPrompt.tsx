"use client";

import { useState, useEffect, useRef } from "react";
import { hapticConfirm } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   InstallPrompt: PWA install banner
   Only appears on 2nd+ visit, AND only after the reader has engaged
   (scrolled ~one viewport OR ~20s elapsed). It never paints on first frame,
   never covers a story card (it publishes its height so the scroll container
   reserves room), and it shows at most once every 14 days.
   Uses the beforeinstallprompt event; iOS gets a manual Add to Home Screen guide.
   --------------------------------------------------------------------------- */

const VISITS_KEY = "void-news-visits";
const DISMISS_KEY = "void-news-install-dismissed";
const SEEN_KEY = "void-news-install-seen";
// Show at most once per this window (whether dismissed or merely seen).
const SUPPRESS_DURATION_MS = 14 * 24 * 60 * 60 * 1000; // 14 days
// Reveal after this long even if the reader has not scrolled a full viewport.
const ENGAGE_TIMEOUT_MS = 20 * 1000; // 20 seconds

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

function isIOS(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !("MSStream" in window);
}

function suppressedRecently(): boolean {
  try {
    for (const key of [DISMISS_KEY, SEEN_KEY]) {
      const raw = localStorage.getItem(key);
      if (!raw) continue;
      const ts = parseInt(raw, 10);
      if (!Number.isNaN(ts) && Date.now() - ts < SUPPRESS_DURATION_MS) return true;
    }
  } catch {
    // localStorage unavailable. Treat as suppressed so we never nag blindly.
    return true;
  }
  return false;
}

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const promptElRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Already installed: never show
    if (isStandalone()) return;

    // Track visit count
    let visits = 1;
    try {
      visits = parseInt(localStorage.getItem(VISITS_KEY) || "0", 10) + 1;
      localStorage.setItem(VISITS_KEY, String(visits));
    } catch {
      // localStorage unavailable, abort silently
      return;
    }

    // Shown or dismissed within the suppression window; stay quiet.
    if (suppressedRecently()) return;

    // Only show on 2nd+ visit
    if (visits < 2) return;

    const ios = isIOS();
    if (ios) setShowIOSGuide(true);

    // Captured install event (non-iOS). Held until the reader engages.
    const promptRef: { current: BeforeInstallPromptEvent | null } = { current: null };
    let engaged = false;
    let revealed = false;

    const clearEngageListeners = () => {
      window.clearTimeout(timer);
      window.removeEventListener("scroll", onScroll);
    };

    const tryReveal = () => {
      if (revealed || !engaged) return;
      // Need something to show: the iOS guide, or a captured install prompt.
      if (!ios && !promptRef.current) return;
      revealed = true;
      try {
        localStorage.setItem(SEEN_KEY, String(Date.now()));
      } catch {
        // continue
      }
      setVisible(true);
      clearEngageListeners();
    };

    const markEngaged = () => {
      engaged = true;
      tryReveal();
    };

    const onScroll = () => {
      // One viewport of scrolling counts as engagement.
      if (window.scrollY >= window.innerHeight) markEngaged();
    };

    const timer = window.setTimeout(markEngaged, ENGAGE_TIMEOUT_MS);
    window.addEventListener("scroll", onScroll, { passive: true });

    const handler = (e: Event) => {
      e.preventDefault();
      promptRef.current = e as BeforeInstallPromptEvent;
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      // If the reader already engaged before the event fired, reveal now.
      tryReveal();
    };

    if (!ios) window.addEventListener("beforeinstallprompt", handler);

    return () => {
      clearEngageListeners();
      if (!ios) window.removeEventListener("beforeinstallprompt", handler);
    };
  }, []);

  // Reserve room so the banner never covers a story card. Publish its measured
  // height to the scroll container via a body attribute + CSS variable.
  useEffect(() => {
    if (typeof document === "undefined") return;
    const body = document.body;
    if (visible) {
      const h = promptElRef.current?.offsetHeight ?? 0;
      const clearance = h > 0 ? h + 16 : 72; // banner height + breathing room
      body.style.setProperty("--install-prompt-clearance", `${clearance}px`);
      body.setAttribute("data-install-prompt", "true");
    } else {
      body.removeAttribute("data-install-prompt");
      body.style.removeProperty("--install-prompt-clearance");
    }
    return () => {
      body.removeAttribute("data-install-prompt");
      body.style.removeProperty("--install-prompt-clearance");
    };
  }, [visible]);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    hapticConfirm();
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setVisible(false);
      setDeferredPrompt(null);
    }
  };

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      // continue
    }
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      ref={promptElRef}
      className="install-prompt"
      role="complementary"
      aria-label="Install Void News as an app"
    >
      <span className="install-prompt__text">
        {showIOSGuide ? (
          <>Tap <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ verticalAlign: "middle", margin: "0 2px" }}><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg> then &ldquo;Add to Home Screen&rdquo;</>
        ) : (
          <>Install <span style={{ fontFamily: "var(--font-data)", letterSpacing: "-0.02em" }}>Void News</span></>
        )}
      </span>
      <div className="install-prompt__actions">
        {!showIOSGuide && (
          <button
            className="install-prompt__btn install-prompt__btn--install"
            onClick={handleInstall}
            aria-label="Install app"
          >
            Install
          </button>
        )}
        <button
          className="install-prompt__btn install-prompt__btn--dismiss"
          onClick={handleDismiss}
          aria-label="Dismiss install prompt"
        >
          ×
        </button>
      </div>
    </div>
  );
}
