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

export default function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
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
        Install <span style={{ fontFamily: "var(--font-data)", letterSpacing: "-0.02em" }}>void --news</span>
      </span>
      <div className="install-prompt__actions">
        <button
          className="install-prompt__btn install-prompt__btn--install"
          onClick={handleInstall}
          aria-label="Install app"
        >
          Install
        </button>
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
