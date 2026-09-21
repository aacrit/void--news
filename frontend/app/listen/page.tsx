import type { Metadata } from "next";
import Link from "next/link";
import { pageMetadata, SITE_URL } from "../lib/siteMeta";
import CopyButton from "../press/CopyButton";
import "../styles/prose-page.css";
import "../privacy/privacy.css";
import "../press/press.css";
import "./listen.css";

export const metadata: Metadata = pageMetadata({
  title: "Listen | Void News",
  description:
    "Three programmes, three podcast feeds: On Air every day, The Argument on Sundays, History one event at a time. Paste a feed address into any podcast app.",
  path: "/listen/",
});

/* The three shows. Feed addresses are absolute because they are meant to be
   pasted into another app, not followed in this one. No counts, no dates:
   nothing here should go stale between pipeline runs. */
const SHOWS = [
  {
    key: "onair",
    title: "On Air",
    cadence: "Daily",
    line: "Four stories, under fifteen minutes.",
    feed: `${SITE_URL}/podcast-world.xml`,
    href: "/onair",
    section: "On Air",
  },
  {
    key: "argument",
    title: "The Argument",
    cadence: "Sundays",
    line: "Two benches, one story.",
    feed: `${SITE_URL}/podcast-weekly.xml`,
    href: "/weekly",
    section: "Weekly",
  },
  {
    key: "history",
    title: "History",
    cadence: "One event per episode",
    line: "About a quarter of an hour each.",
    feed: `${SITE_URL}/podcast-history.xml`,
    href: "/history",
    section: "History",
  },
] as const;

export default function ListenPage() {
  return (
    <article className="press listen">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      <header className="press__hdr">
        <p className="press__eyebrow">Void News / Listen</p>
        <h1>Listen</h1>
        <p className="press__lede">
          Three programmes, three feeds. Paste a feed address into any podcast
          app.
        </p>
      </header>

      <section className="press-block" aria-label="Podcast feeds">
        <ul className="listen-shows">
          {SHOWS.map((show, i) => (
            <li key={show.key} className="listen-show">
              <p className="press-kicker">
                <span className="press-kicker__n">
                  {String(i + 1).padStart(2, "0")}
                </span>
                {show.cadence}
              </p>
              <h2 className="listen-show__title">{show.title}</h2>
              <p className="listen-show__line">{show.line}</p>
              <div className="listen-show__feed">
                <code className="listen-show__url">{show.feed}</code>
                <CopyButton text={show.feed} label="Copy feed address" />
              </div>
              <p className="listen-show__link">
                <Link href={show.href}>Open {show.section} on the site</Link>
              </p>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
