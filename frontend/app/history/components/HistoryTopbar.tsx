"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "../../components/ThemeToggle";
import LogoIcon from "../../components/LogoIcon";

/* ===========================================================================
   HistoryTopbar — Sticky navigation for void --history
   Pattern: same as weekly's .wk-topbar — back arrow + brand + theme toggle.
   Logo icon as brand mark, organic ink dot separator, section label.
   On the landing page (/history), the back link goes to the main site.
   On sub-pages (/history/[slug], /history/era/*, /history/region/*),
   the back link goes to /history.
   =========================================================================== */

export default function HistoryTopbar() {
  const pathname = usePathname();
  const isLanding = pathname === "/history" || pathname === "/history/";
  const backHref = isLanding ? "/" : "/history";
  const backLabel = isLanding ? "Back to void --news" : "Back to void --history";

  return (
    <header className="hist-topbar hist-cold-open--topbar" role="banner">
      <Link href={backHref} className="hist-topbar__back" aria-label={backLabel}>
        <span className="hist-topbar__arrow" aria-hidden="true">&larr;</span>
        <span className="hist-topbar__logo" aria-hidden="true">
          <LogoIcon size={22} animation="idle" />
        </span>
        <span className="hist-topbar__dot" aria-hidden="true" />
        <span className="hist-topbar__section">history</span>
        <span className="hist-topbar__subtitle">The Archive</span>
      </Link>
      <div className="hist-topbar__actions">
        <ThemeToggle />
      </div>
    </header>
  );
}
