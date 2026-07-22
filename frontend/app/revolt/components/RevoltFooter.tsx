import Link from 'next/link';

export default function RevoltFooter() {
  return (
    <footer className="rev-footer">
      <div className="rev-shell">
        <p>
          void <b>--revolt</b> reads the world&rsquo;s revolutions against one shared anatomy. The active
          portal is analytical, not predictive, and not an endorsement of any movement.
        </p>
        <p style={{ marginTop: '0.75rem' }}>
          <Link href="/">void --news</Link> &middot; <Link href="/history">void --history</Link> &middot;{' '}
          <Link href="/revolt/active">The Living</Link>
        </p>
      </div>
    </footer>
  );
}
