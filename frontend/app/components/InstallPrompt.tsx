"use client";

import { useState, useEffect } from "react";
import { hapticConfirm } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   InstallPrompt — PWA install banner
   Only appears on 2nd+ visit. Compact bottom banner, above bottom nav.
   Dismissal stored for 30 days. Uses beforeinstallprompt event.
   --------------------------------------------------------------------------- */

const VISITS_KEY = "void-news-visits";
const DISMISS_KEY = "void-news-install-dismissed";
const DISMISS_DURATION_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

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

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [showIOSGuide, setShowIOSGuide] = useState(false);

  useEffect(() => {
    // Already installed — never show
    if (isStandalone()) return;

    // Track visit count
    let visits = 1;
    try {
      visits = parseInt(localStorage.getItem(VISITS_KEY) || "0", 10) + 1;
      localStorage.setItem(VISITS_KEY, String(visits));
    } catch {
      // localStorage unavailable — abort silently
      return;
    }

    // Check if dismissed recently
    try {
      const dismissed = localStorage.getItem(DISMISS_KEY);
      if (dismissed) {
        const dismissedAt = parseInt(dismissed, 10);
        if (Date.now() - dismissedAt < DISMISS_DURATION_MS) return;
      }
    } catch {
      return;
    }

    // Only show on 2nd+ visit
    if (visits < 2) return;

    // iOS: no beforeinstallprompt event — show manual guide
    if (isIOS()) {
      setShowIOSGuide(true);
      setVisible(true);
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

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
      className="install-prompt"
      role="complementary"
      aria-label="Install void --news as an app"
    >
      <span className="install-prompt__text">
        {showIOSGuide ? (
          <>Tap <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ verticalAlign: "middle", margin: "0 2px" }}><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg> then &ldquo;Add to Home Screen&rdquo;</>
        ) : (
          <>Install <span style={{ fontFamily: "var(--font-data)", letterSpacing: "-0.02em" }}>void --news</span></>
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
