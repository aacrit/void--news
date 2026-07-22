'use client';

import Link from 'next/link';
import ThemeToggle from '../../components/ThemeToggle';
import LogoIcon from '../../components/LogoIcon';

/* Barricade Press topbar — bespoke chrome, but leads with the shared void mark
   (LogoIcon) exactly like void --news (LogoFull) and void --history, so the
   brand reads consistent across the family. */
export default function RevoltTopbar() {
  return (
    <header className="rev-topbar">
      <Link href="/revolt" className="rev-topbar__brand" aria-label="void --revolt home">
        <span className="rev-topbar__mark" aria-hidden="true">
          <LogoIcon size={24} animation="idle" />
        </span>
        <span className="rev-topbar__wordmark">void <b>--revolt</b></span>
      </Link>
      <span className="rev-topbar__spacer" />
      <Link href="/revolt" className="rev-topbar__link">The Archive</Link>
      <Link href="/revolt/active" className="rev-topbar__link">The Living</Link>
      <Link href="/revolt/compare" className="rev-topbar__link">Compare</Link>
      <Link href="/" className="rev-topbar__link">void --news</Link>
      <ThemeToggle />
    </header>
  );
}
