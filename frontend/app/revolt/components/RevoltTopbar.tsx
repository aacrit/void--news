'use client';

import Link from 'next/link';
import ThemeToggle from '../../components/ThemeToggle';
import SectionNameplate from '../../components/SectionNameplate';

/* Barricade Press topbar — bespoke chrome, but it leads with the same section
   nameplate History and Weekly use (VOID NEWS | Revolt), because Revolt is a
   section of Void News and not a product beside it. The VOID REVOLT lockup it
   used to carry claimed the second; the separate "Void News" text link at the
   far right, which existed only to get back, goes with it. */
export default function RevoltTopbar() {
  return (
    <header className="rev-topbar">
      <SectionNameplate
        section="Revolt"
        href="/revolt"
        height={20}
        accent="var(--palette-revolt)"
        className="rev-topbar__brand"
      />
      <span className="rev-topbar__spacer" />
      <Link href="/revolt" className="rev-topbar__link">The Archive</Link>
      <Link href="/revolt/active" className="rev-topbar__link">The Living</Link>
      <Link href="/revolt/compare" className="rev-topbar__link">Compare</Link>
      <ThemeToggle />
    </header>
  );
}
