"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import "../styles/experimental.css";

/* ---------------------------------------------------------------------------
   ExperimentalBanner — one slim, dismissible line, site-wide. Renders only
   after mount (avoids a hydration mismatch on the localStorage read) and stays
   dismissed via localStorage. No em dashes in the copy.
   --------------------------------------------------------------------------- */

const DISMISS_KEY = "void-exp-banner-dismissed";

export default function ExperimentalBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem(DISMISS_KEY) !== "1") setVisible(true);
    } catch {
      setVisible(true);
    }
  }, []);

  const dismiss = () => {
    setVisible(false);
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* noop */
    }
  };

  if (!visible) return null;

  return (
    <div className="exp-banner" role="region" aria-label="Experimental notice">
      <p className="exp-banner__text">
        void --news is experimental. Things will change.{" "}
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
