import type { Metadata } from "next";
import Link from "next/link";
import { BASE_PATH } from "../lib/utils";
import "../styles/about.css";
import "../privacy/privacy.css";

export const metadata: Metadata = {
  title: "Press — void --news",
  description:
    "Press kit and media inquiries for void --news. Coverage requests, interviews, methodology questions, and brand assets.",
};

export default function PressPage() {
  return (
    <article className="press">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      <header className="press__hdr">
        <p className="press__eyebrow">void --news / press</p>
        <h1>For journalists, critics, researchers.</h1>
        <p className="press__byline">
          Bias methodology, source curation, and editorial decisions are
          documented. Ask anything.
        </p>
      </header>

      <section>
        <h2>One paragraph.</h2>
        <p>
          void --news is a news aggregator that scores every individual
          article on six bias axes using rule-based NLP (no machine learning
          black box), reads 1,016 sources across 158 countries, and presents
          one importance-ranked feed to every reader. No accounts, no
          tracking, no personalization, free forever. The product was built
          to invert what personalization did to the news: same stories, same
          order, for everyone.
        </p>
      </section>

      <section>
        <h2>What you can quote.</h2>
        <ul>
          <li>Article-level bias scores, with the rule-based reasoning trace exposed in the UI.</li>
          <li>Per-topic per-outlet exponential moving average of lean (the Outlet Tracking axis).</li>
          <li>Source roster (3 tiers: 43 US major, 373 international, 597 independent — see <Link href="/sources">/sources</Link>).</li>
          <li>The 6-axis methodology, including which signals each axis uses and where the &quot;unscored&quot; gate fires.</li>
          <li>The daily editorial brief, including the editorial opinion section (clearly labeled).</li>
        </ul>
      </section>

      <section>
        <h2>What we will not do.</h2>
        <ul>
          <li>We will not provide off-the-record commentary on specific journalists or outlets.</li>
          <li>We will not personalize the feed for press demos. You see what every other reader sees.</li>
          <li>We will not share private user data because we do not collect any.</li>
        </ul>
      </section>

      <section className="press__kit">
        <h2 style={{ marginTop: 0 }}>Press kit</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          <li className="press__kit-item">
            <span>Brand mark (SVG, ink)</span>
            <a href={`${BASE_PATH}/icon.svg`} download>
              icon.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Brand mark (PNG, transparent)</span>
            <a href={`${BASE_PATH}/apple-touch-icon.png`} download>
              icon@180.png
            </a>
          </li>
          <li className="press__kit-item">
            <span>Open Graph card</span>
            <a href={`${BASE_PATH}/og-image.svg`} download>
              og-image.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Manifesto page (link)</span>
            <Link href="/about">/about</Link>
          </li>
          <li className="press__kit-item">
            <span>Methodology page (the six axes)</span>
            <Link href="/about#the-instrument">/about#the-instrument</Link>
          </li>
          <li className="press__kit-item">
            <span>Source list</span>
            <Link href="/sources">/sources</Link>
          </li>
        </ul>
      </section>

      <section>
        <h2>Founder.</h2>
        <p>
          Built and operated by Aacrit. Background in product and engineering.
          Independent project. No outside investors.
        </p>
      </section>

      <section>
        <h2>Contact.</h2>
        <div className="press__contact">
          <p style={{ margin: 0 }}>
            <strong>Press inquiries:</strong>{" "}
            <a href="mailto:press@void-news.pages.dev">
              press@void-news.pages.dev
            </a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>Methodology questions:</strong>{" "}
            <a href="mailto:methodology@void-news.pages.dev">
              methodology@void-news.pages.dev
            </a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>Instagram:</strong> <a href="https://instagram.com/void.news" rel="noopener noreferrer">@void.news</a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>Bluesky:</strong> <a href="https://bsky.app/profile/void.news" rel="noopener noreferrer">@void.news</a>
          </p>
        </div>
        <p>
          Response time: typically within 24 hours. Earlier on weekdays.
        </p>
      </section>

      <p className="press__footer">
        Privacy questions: <Link href="/privacy">/privacy</Link>.
      </p>
    </article>
  );
}
