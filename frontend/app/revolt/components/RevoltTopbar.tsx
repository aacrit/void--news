'use client';

import Link from 'next/link';
import ThemeToggle from '../../components/ThemeToggle';
import SigilWordmark from '../../components/SigilWordmark';

/* Barricade Press topbar — bespoke chrome, but leads with the shared void mark
   (LogoIcon) exactly like void --news (LogoFull) and void --history, so the
   brand reads consistent across the family. */
export default function RevoltTopbar() {
  return (
    <header className="rev-topbar">
      <Link href="/revolt" className="rev-topbar__brand" aria-label="Revolt home">
        <SigilWordmark product="REVOLT" height={24} accent="var(--palette-revolt)" />
      </Link>
      <span className="rev-topbar__spacer" />
      <Link href="/revolt" className="rev-topbar__link">The Archive</Link>
      <Link href="/revolt/active" className="rev-topbar__link">The Living</Link>
      <Link href="/revolt/compare" className="rev-topbar__link">Compare</Link>
      <Link href="/" className="rev-topbar__link">Void News</Link>
      <ThemeToggle />
    </header>
  );
}
