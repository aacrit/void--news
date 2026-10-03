"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import "../styles/experimental.css";

/* ---------------------------------------------------------------------------
   ExperimentalBanner: one slim, dismissible line, site-wide, BELOW the
   masthead and only from the second visit on.

   A first-time reader, often arriving from a shared link, should meet a
   headline before a bug-report request. The masthead's "experimental" badge
   carries the posture on the first visit. A visit is counted once per
   browser session; a dismissal lasts fourteen days. Renders only after mount
   (the localStorage read cannot be hydrated), and reads nothing when storage
   is unavailable. No em dashes in the copy.
   --------------------------------------------------------------------------- */

const VISITS_KEY = "void-exp-banner-visits";
const SESSION_KEY = "void-exp-banner-session";
const DISMISS_KEY = "void-exp-banner-dismissed-at";
const DISMISS_DAYS = 14;

export default function ExperimentalBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      const dismissedAt = parseInt(localStorage.getItem(DISMISS_KEY) || "0", 10);
      if (dismissedAt && Date.now() - dismissedAt < DISMISS_DAYS * 86_400_000) return;

      let visits = parseInt(localStorage.getItem(VISITS_KEY) || "0", 10);
      if (!sessionStorage.getItem(SESSION_KEY)) {
        visits += 1;
        localStorage.setItem(VISITS_KEY, String(visits));
        sessionStorage.setItem(SESSION_KEY, "1");
      }
      if (visits >= 2) setVisible(true);
    } catch {
      /* storage unavailable: never nag blindly */
    }
  }, []);

  const dismiss = () => {
    setVisible(false);
    try {
      localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      /* noop */
    }
  };

  if (!visible) return null;

  return (
    <div className="exp-banner" role="region" aria-label="Experimental notice">
      <p className="exp-banner__text">
        Void News is experimental.{" "}
        <Link href="/ship" className="exp-banner__link">
          Tell us what breaks.
        </Link>
      </p>
      <button
        type="button"
        className="exp-banner__dismiss"
        onClick={dismiss}
        aria-label="Dismiss experimental notice"
      >
        &times;
      </button>
    </div>
  );
}
