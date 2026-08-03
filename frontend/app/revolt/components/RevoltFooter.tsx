import Link from 'next/link';

export default function RevoltFooter() {
  return (
    <footer className="rev-footer">
      <div className="rev-shell">
        <p>
          <b>Revolt</b> reads the world&rsquo;s revolutions against one shared anatomy. The active
          portal is analytical, not predictive, and not an endorsement of any movement.
        </p>
        <p style={{ marginTop: '0.75rem' }}>
          <Link href="/">Void News</Link> &middot; <Link href="/history">History</Link> &middot;{' '}
          <Link href="/revolt/active">The Living</Link>
        </p>
      </div>
    </footer>
  );
}
