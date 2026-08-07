import type { Metadata } from "next";
import Link from "next/link";
import "../styles/about.css";
import "./privacy.css";

export const metadata: Metadata = {
  title: "Privacy | Void News",
  description:
    "Void News collects no reader data. No accounts, no tracking, no analytics. This page describes what we do and do not collect.",
};

export default function PrivacyPage() {
  return (
    <article className="privacy">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      <header className="privacy__hdr">
        <p className="privacy__eyebrow">Void News / privacy</p>
        <h1>What we collect. What we don&rsquo;t.</h1>
        <p className="privacy__updated">Last updated 2026-05-14.</p>
      </header>

      <section>
        <h2>From readers: nothing.</h2>
        <p>
          The website at <code>news.voidvision.org</code> requires no account.
          We do not run analytics. We do not place cookies for tracking. We do
          not fingerprint browsers. We do not load third-party scripts for
          advertising or marketing. The newspaper principle: every reader sees
          the same stories in the same order. There is no profile to maintain
          and no behavior to record.
        </p>
        <p>
          The two exceptions, both technical and minimal:
        </p>
        <ul>
          <li>
            A local <code>localStorage</code> entry remembers your selected
            theme (light or dark). It never leaves your device.
          </li>
          <li>
            Hosting providers (Cloudflare Pages) log request metadata for
            DDoS protection and uptime. We do not access or process those logs.
          </li>
        </ul>
      </section>

      <section>
        <h2>From article sources: public content only.</h2>
        <p>
          The pipeline reads RSS feeds and public article URLs from the 1,016
          sources listed at <Link href="/sources">/sources</Link>. We store
          article text, publish timestamps, the source name, and our
          rule-based bias scores. We do not scrape paywalled content. We do
          not store anything from a source that is not publicly accessible.
        </p>
      </section>

      <section>
        <h2>What we do not do.</h2>
        <ul>
          <li>We do not run advertising or paid promotion of any kind.</li>
          <li>We do not personalize the news feed for any reader. The same stories appear in the same order for everyone, every day.</li>
        </ul>
      </section>

      <section>
        <h2>Children.</h2>
        <p>
          Void News is not designed for or directed at children under 13.
          We do not knowingly collect any information from anyone under 13.
        </p>
      </section>

      <section>
        <h2>Data retention.</h2>
        <p>
          Article text is retained until the cleanup job removes stale rows
          (currently 30 days for unranked articles, longer for clustered
          stories).
        </p>
      </section>

      <section>
        <h2>Contact.</h2>
        <p>
          Privacy questions: <a href="mailto:privacy@voidvision.org">privacy@voidvision.org</a>.
          Press questions: see <Link href="/press">/press</Link>.
        </p>
      </section>

      <p className="privacy__footer">
        This policy may change. The change log will appear here above the
        &ldquo;Last updated&rdquo; date.
      </p>
    </article>
  );
}
