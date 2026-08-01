"use client";

import { useEffect } from "react";
import Link from "next/link";
import { BASE_PATH } from "../lib/utils";

/* ===========================================================================
   void --ship retired 2026-08 → Feedback lives at /feedback.
   Cloudflare _redirects issues an edge 301 (/ship → /feedback) on full page
   loads; this stub covers in-app navigation and any environment that does not
   honor _redirects.
   =========================================================================== */

export default function ShipPage() {
  useEffect(() => {
    window.location.replace(`${BASE_PATH}/feedback`);
  }, []);

  return (
    <main
      style={{
        maxWidth: "640px",
        margin: "0 auto",
        padding: "var(--space-7) var(--space-4)",
        textAlign: "center",
        fontFamily: "var(--font-structural)",
        color: "var(--fg-secondary)",
      }}
    >
      <p>
        void --ship is now Feedback.{" "}
        <Link href="/feedback" style={{ color: "var(--fg-accent)" }}>
          Continue to the feedback page.
        </Link>
      </p>
    </main>
  );
}
