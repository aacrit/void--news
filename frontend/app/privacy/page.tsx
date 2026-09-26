import type { Metadata } from "next";
import Link from "next/link";
import "../styles/prose-page.css";
import "./privacy.css";
import { ROSTER_SOURCES_TEXT } from "../lib/rosterConfig";

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
        <p className="privacy__updated">Last updated 2026-09-21.</p>
      </header>

      <section>
        <h2>From readers: nothing.</h2>
        <p>
          The website at <code>news.voidvision.org</code> requires no account.
          We do not run analytics. We do not place cookies for tracking. We do
          not fingerprint your browser as you read. We do not load third-party
          scripts for advertising or marketing. The newspaper principle: every
          reader sees the same stories in the same order. There is no profile to
          maintain and no behavior to record.
        </p>
        <p>
          A few narrow exceptions, all minimal:
        </p>
        <ul>
          <li>
            A few <code>localStorage</code> entries remember your theme,
            dismissed notices, and a local send limit for the feedback form.
            None of them leave your device.
          </li>
          <li>
            If you send feedback, we store what you wrote plus a coarse one-way
            hash of your browser profile, used only to rate-limit abuse, and only
            when you choose to send it. Nothing else.
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
          The pipeline reads RSS feeds and public article URLs from the {ROSTER_SOURCES_TEXT}
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
          Article text lives in the pipeline&rsquo;s working database for about a
          week, and a compressed snapshot of that database is kept as a build
          artifact for up to 90 days.
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
