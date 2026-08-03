"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "../../components/ThemeToggle";
import SigilWordmark from "../../components/SigilWordmark";

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
  const backLabel = isLanding ? "Back to Void News" : "Back to History";

  return (
    <header className="hist-topbar hist-cold-open--topbar" role="banner">
      <Link href={backHref} className="hist-topbar__back" aria-label={backLabel}>
        <span className="hist-topbar__arrow" aria-hidden="true">&larr;</span>
        <SigilWordmark product="HISTORY" height={24} accent="var(--palette-history)" />
      </Link>
      <div className="hist-topbar__actions">
        <Link href="/revolt" className="hist-topbar__revolt" title="Revolt: the anatomy of revolution" aria-label="Go to Revolt, the anatomy of revolution">
          <span className="hist-topbar__revolt-cmd">Revolt</span>
          <span className="hist-topbar__revolt-arrow" aria-hidden="true">&rarr;</span>
        </Link>
        <ThemeToggle />
      </div>
    </header>
  );
}
