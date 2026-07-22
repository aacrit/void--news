import Link from 'next/link';

/* Barricade Press topbar — bespoke chrome (like history's topbar). */
export default function RevoltTopbar() {
  return (
    <header className="rev-topbar">
      <Link href="/revolt" className="rev-topbar__brand" aria-label="void --revolt home">
        void <b>--revolt</b>
      </Link>
      <span className="rev-topbar__spacer" />
      <Link href="/revolt" className="rev-topbar__link">The Archive</Link>
      <Link href="/revolt/active" className="rev-topbar__link">The Living</Link>
      <Link href="/revolt/compare" className="rev-topbar__link">Compare</Link>
      <Link href="/" className="rev-topbar__link">void --news</Link>
    </header>
  );
}
