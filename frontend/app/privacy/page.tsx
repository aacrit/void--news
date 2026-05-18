import type { Metadata } from "next";
import Link from "next/link";
import "../styles/about.css";
import "./privacy.css";

export const metadata: Metadata = {
  title: "Privacy — void --news",
  description:
    "void --news collects no reader data. No accounts, no tracking, no analytics. This page describes what we do and do not collect, and the scope of our Instagram integration.",
};

export default function PrivacyPage() {
  return (
    <article className="privacy">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      <header className="privacy__hdr">
        <p className="privacy__eyebrow">void --news / privacy</p>
        <h1>What we collect. What we don&rsquo;t.</h1>
        <p className="privacy__updated">Last updated 2026-05-14.</p>
      </header>

      <section>
        <h2>From readers: nothing.</h2>
        <p>
          The website at <code>void-news.pages.dev</code> requires no account.
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
        <h2>Instagram integration scope.</h2>
        <p>
          The <code>@void.news</code> Instagram account is operated by void
          --news and uses the official Instagram Graph API for the following
          purposes:
        </p>
        <ul>
          <li>
            <strong>Publishing posts</strong> (Feed images, carousels,
            Stories, and Reels) to the <code>@void.news</code> account. Every
            post is reviewed and approved by a human in our internal review
            queue before publication.
          </li>
          <li>
            <strong>Reading insights</strong> on our own posts (impressions,
            reach, saves, shares, profile visits, link clicks). We use these
            to learn which formats perform best and tune our schedule. No
            third party receives this data.
          </li>
          <li>
            <strong>Reading comments and direct messages on our own
            content.</strong> We route press inquiries to a priority queue
            so we can respond promptly. We do not scrape comments or DMs
            from any other account.
          </li>
          <li>
            <strong>Reading mentions and hashtag results.</strong> We monitor
            public posts that tag <code>@void.news</code> or use our owned
            hashtags so we can engage substantively. We store only the post
            ID and timestamp.
          </li>
        </ul>
        <p>
          We do not buy or sell data. We do not transfer Instagram-derived
          data to any third party except where Meta itself processes it as
          part of the API request.
        </p>
      </section>

      <section>
        <h2>What we do not do.</h2>
        <ul>
          <li>We do not run advertising or paid promotion of any kind.</li>
          <li>We do not auto-follow, auto-unfollow, auto-like, or auto-DM. All such activity violates the Instagram Platform Terms and would compromise the editorial credibility this account exists to build.</li>
          <li>We do not personalize the news feed for any reader. The same stories appear in the same order for everyone, every day.</li>
        </ul>
      </section>

      <section>
        <h2>Children.</h2>
        <p>
          void --news is not designed for or directed at children under 13.
          We do not knowingly collect any information from anyone under 13.
        </p>
      </section>

      <section>
        <h2>Data retention.</h2>
        <p>
          Article text is retained until the cleanup job removes stale rows
          (currently 30 days for unranked articles, longer for clustered
          stories). Instagram insights are retained indefinitely for our own
          analysis. Direct messages we receive are retained until the
          conversation is resolved, then archived.
        </p>
      </section>

      <section>
        <h2>Contact.</h2>
        <p>
          Privacy questions: <a href="mailto:privacy@void-news.pages.dev">privacy@void-news.pages.dev</a>.
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
