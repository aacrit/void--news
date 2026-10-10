import type { Metadata } from "next";
import Link from "next/link";
import "../styles/prose-page.css";
import "./privacy.css";
import { ROSTER_SOURCES_TEXT } from "../lib/rosterConfig";

export const metadata: Metadata = {
  title: "Privacy | Void News",
  description:
    "Reading Void News stores nothing about you. Sending feedback stores your note, a coarse device class and a salted hash of your IP address. This page names every field.",
};

/* Every column the Worker writes (worker/schema.sql plus worker/migrations/)
   is named below in a <code> tag, and frontend/test/privacy-facts.test.mjs
   fails when a column exists that this page does not name. Add the column
   here in the same commit that adds it there. */
export default function PrivacyPage() {
  return (
    <article className="privacy">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      <header className="privacy__hdr">
        <p className="privacy__eyebrow">Void News / privacy</p>
        <h1>What we collect. What we don&rsquo;t.</h1>
        <p className="privacy__updated">Last updated 2026-10-02.</p>
      </header>

      <section>
        <h2>While you read: nothing.</h2>
        <p>
          The website at <code>news.voidvision.org</code> requires no account.
          We do not run analytics. We do not place cookies. We do not
          fingerprint your browser as you read. We do not load third-party
          scripts for advertising or marketing. Every reader sees the same
          stories in the same order, so there is no profile to keep.
        </p>
        <ul>
          <li>
            A few <code>localStorage</code> entries remember your theme, the
            notices and tours you dismissed, a count of your visits that times
            those notices, your audio playback speed, and a local send limit
            for the feedback form. They stay on your device.
          </li>
          <li>
            Our host, Cloudflare, logs request metadata such as IP addresses
            for its own security and uptime work. We do not read or export
            those logs.
          </li>
        </ul>
      </section>

      <section>
        <h2>If you send feedback: these fields.</h2>
        <p>
          The feedback form posts to our API on Cloudflare Workers, which
          writes one row to a Cloudflare D1 database. The row holds exactly
          these fields.
        </p>
        <ul>
          <li><code>title</code> and <code>description</code>: the subject and message you typed.</li>
          <li><code>category</code>: the kind of note you picked, an idea or a bug.</li>
          <li><code>area</code> and <code>edition_context</code>: fixed values the form sends (<code>other</code> and empty).</li>
          <li>
            <code>device_info</code>: a coarse device class and browser family,
            such as &ldquo;mobile safari&rdquo; or &ldquo;desktop firefox&rdquo;.
            Never the full browser identification string. Notes sent before
            2026-10-02 stored that full string, cut at 180 characters.
          </li>
          <li>
            <code>ip_hash</code>: a SHA-256 hash of your IP address joined to
            a secret salt. Your IP address itself is not stored. The hash lets
            us limit how many notes, votes and replies one connection can send
            in an hour. While the salt stays secret, the hash cannot be turned
            back into your address.
          </li>
          <li><code>id</code>, <code>created_at</code> and <code>updated_at</code>: a random identifier and two timestamps.</li>
          <li>
            Fields only we fill in, after we read the note:{" "}
            <code>status</code>, <code>priority</code>, <code>votes</code>,{" "}
            <code>ceo_response</code>, <code>claude_branch</code>,{" "}
            <code>shipped_commit</code>, <code>shipped_diff_summary</code>,{" "}
            <code>triaged_at</code> and <code>shipped_at</code>.
          </li>
        </ul>
        <p>
          The API can also record a vote or a reply on a note. The site offers
          neither at present. A vote row holds <code>id</code>,{" "}
          <code>request_id</code> (the note it is for), <code>ip_hash</code>,{" "}
          <code>fingerprint</code> and <code>created_at</code>. A reply row
          holds <code>id</code>, <code>request_id</code>, <code>body</code>{" "}
          (the reply text), <code>ip_hash</code>, <code>fingerprint</code>{" "}
          and <code>created_at</code>. Since 2026-10-02 the{" "}
          <code>fingerprint</code> field holds the same IP hash; before that it
          held a short hash your browser computed from its identification
          string, language, screen size and time zone.
        </p>
        <p>
          Your note, its category and its timestamps can be read back through
          the API. The device class and the IP hash cannot.
        </p>
      </section>

      <section>
        <h2>From article sources: public content only.</h2>
        <p>
          The pipeline reads RSS feeds and public article URLs from the {ROSTER_SOURCES_TEXT}
          sources listed at <Link href="/sources">/sources</Link>. We store
          article text, publish timestamps, the source name, and our
          rule-based bias scores. We do not scrape paywalled content. Our
          crawler names itself as VoidNewsBot and follows each site&rsquo;s
          robots.txt.
        </p>
      </section>

      <section>
        <h2>What we do not do.</h2>
        <ul>
          <li>We do not run advertising or paid promotion of any kind.</li>
          <li>We do not personalize the news feed for any reader. The same stories appear in the same order for everyone, every day.</li>
          <li>We do not sell or share feedback rows with anyone.</li>
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
          Feedback rows have no automatic expiry yet. They stay in the
          database until we delete them by hand. To have a note you sent
          removed, write to the address below with its subject and the day you
          sent it.
        </p>
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
