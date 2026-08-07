import type { Metadata } from "next";
import Link from "next/link";
import { BASE_PATH } from "../lib/utils";
import CopyButton from "./CopyButton";
import "../styles/about.css";
import "../privacy/privacy.css";
import "./press.css";

export const metadata: Metadata = {
  title: "Press | Void News",
  description:
    "Press room for Void News: an independent daily news reader that shows the lean and character of every story. Boilerplate, facts, brand assets, and contacts for journalists.",
};

const BOILER_SHORT =
  "Void News is an independent daily news reader that shows the political lean and editorial character of every story. It gathers reporting from 1,016 sources across 158 countries into one shared edition of fifty stories, ranked once a day, the same for every reader.";

const BOILER_LONG =
  "Void News is an independent daily news reader. Each day it gathers reporting from more than a thousand outlets across 158 countries, groups the coverage of each event together, and scores every story on six axes: political lean, sensationalism, opinion versus reporting, factual rigor, framing, and how an outlet has covered a subject over time. Every score is produced by a documented, transparent method and carries a written explanation, so a reader sees not only where a story sits but why.\n\nThere are no accounts, no trackers, and no personalized feed. The fifty most-covered stories are ranked once a day, in the same order for everyone, on the principle that a shared set of facts matters more than an engaging one. Void News is an independent product of Void, with no outside investors, published at news.voidvision.org.";

export default function PressPage() {
  return (
    <article className="press">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      {/* ── Masthead ─────────────────────────────────────────────────────── */}
      <header className="press__hdr">
        <p className="press__eyebrow">Void News / Press room</p>
        <img
          className="press__wordmark press__wordmark--light"
          src={`${BASE_PATH}/brand/logos/void-news-horizontal-color.svg`}
          alt="Void News"
          width={546}
          height={120}
        />
        <img
          className="press__wordmark press__wordmark--dark"
          src={`${BASE_PATH}/brand/logos/void-news-horizontal-reversed.svg`}
          alt="Void News"
          width={546}
          height={120}
          aria-hidden="true"
        />
        <h1 className="press__positioning">
          An independent daily news reader that shows the lean and character of
          every story, transparently, on one shared front page.
        </h1>
        <p className="press__lede">
          The same stories, in the same order, for every reader. This page is
          for journalists, editors, and researchers. The method is documented
          and the reasoning behind every score is shown. Ask us anything.
        </p>
      </header>

      {/* ── Fast facts ───────────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-facts">
        <p className="press-kicker">
          <span className="press-kicker__n">01</span> At a glance
        </p>
        <h2 id="press-facts" className="press-vh">
          Fast facts
        </h2>
        <div className="press-ledger" aria-label="Void News at a glance">
          <div className="press-stat">
            <div className="press-stat__n">1,016</div>
            <div className="press-stat__l">Sources, across three credibility tiers</div>
          </div>
          <div className="press-stat">
            <div className="press-stat__n">158</div>
            <div className="press-stat__l">Countries represented in the feed</div>
          </div>
          <div className="press-stat">
            <div className="press-stat__n">6</div>
            <div className="press-stat__l">Axes of bias scored on every story</div>
          </div>
          <div className="press-stat">
            <div className="press-stat__n">50</div>
            <div className="press-stat__l">Stories in one daily edition</div>
          </div>
          <div className="press-stat">
            <div className="press-stat__n">1&times;</div>
            <div className="press-stat__l">Published once a day, the same for everyone</div>
          </div>
          <div className="press-stat">
            <div className="press-stat__n">$0</div>
            <div className="press-stat__l">Free to read. No paywall, no trackers, no accounts</div>
          </div>
        </div>
      </section>

      {/* ── Boilerplate ──────────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-boiler-h">
        <p className="press-kicker">
          <span className="press-kicker__n">02</span> For the record
        </p>
        <h2 id="press-boiler-h">Boilerplate</h2>
        <p className="press-boiler__hint">
          Approved language for editors and reporters. Copy it as written.
        </p>

        <div className="press-boiler">
          <div className="press-boiler__head">
            <p className="press-boiler__label">Short</p>
            <CopyButton text={BOILER_SHORT} />
          </div>
          <p>{BOILER_SHORT}</p>
        </div>

        <div className="press-boiler">
          <div className="press-boiler__head">
            <p className="press-boiler__label">Long</p>
            <CopyButton text={BOILER_LONG} />
          </div>
          <p>
            Void News is an independent daily news reader. Each day it gathers
            reporting from more than a thousand outlets across 158 countries,
            groups the coverage of each event together, and scores every story
            on six axes: political lean, sensationalism, opinion versus
            reporting, factual rigor, framing, and how an outlet has covered a
            subject over time. Every score is produced by a documented,
            transparent method and carries a written explanation, so a reader
            sees not only where a story sits but why.
          </p>
          <p>
            There are no accounts, no trackers, and no personalized feed. The
            fifty most-covered stories are ranked once a day, in the same order
            for everyone, on the principle that a shared set of facts matters
            more than an engaging one. Void News is an independent product of
            Void, with no outside investors, published at news.voidvision.org.
          </p>
        </div>
      </section>

      {/* ── What you can cite ────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-cite-h">
        <p className="press-kicker">
          <span className="press-kicker__n">03</span> Verified and quotable
        </p>
        <h2 id="press-cite-h">What you can cite</h2>
        <p>
          These are the plain facts about how Void News works. Every one is
          documented, and most are visible in the product itself.
        </p>
        <ul className="press-cite">
          <li>
            A political-lean and editorial-character read on every story, with
            the reasoning shown in the app for each score.
          </li>
          <li>
            Six axes per story: political lean, sensationalism, opinion versus
            reporting, factual rigor, framing, and how an outlet has covered a
            subject over time.
          </li>
          <li>
            A published source roster of 1,016 outlets across three credibility
            tiers and 158 countries. See{" "}
            <Link href="/sources">/sources</Link>.
          </li>
          <li>
            One shared edition of fifty stories, ranked once a day in the same
            order for every reader. No accounts, no personalization.
          </li>
          <li>
            The full methodology, including which signals each axis reads. See{" "}
            <Link href="/about">/about</Link>.
          </li>
        </ul>
      </section>

      {/* ── How the method works ─────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-method-h">
        <p className="press-kicker">
          <span className="press-kicker__n">04</span> The method, plainly
        </p>
        <h2 id="press-method-h">How the bias read works</h2>
        <p>
          This is the part journalists ask about, so here it is plainly. Void
          News reads every story on six axes of bias by a documented, transparent
          method. The reasoning behind every score is shown in the app, and the
          same story always scores the same way. The full methodology is
          published at <Link href="/about">/about</Link>.
        </p>

        <div className="press-callout">
          <strong>
            We do not judge a story by its outlet alone, and we do not judge it
            by its words alone. We use both.
          </strong>{" "}
          A score weighs the outlet&rsquo;s measured track record and the
          specific language of the article in front of you. On a short wire
          dispatch there is little text to read, so the outlet&rsquo;s history
          carries more weight. On a full feature, the article&rsquo;s own words
          lead. The balance shifts with how much there is to actually read.
        </div>

        <div
          className="press-spectrum"
          aria-label="Political lean spectrum: left is blue, center is green, right is red"
        >
          <div className="press-spectrum__bar" aria-hidden="true">
            <i style={{ flex: 1, background: "var(--bias-left)" }} />
            <i
              style={{
                flex: 1,
                background:
                  "linear-gradient(90deg, var(--bias-left), var(--bias-center))",
              }}
            />
            <i style={{ flex: 1, background: "var(--bias-center)" }} />
            <i
              style={{
                flex: 1,
                background:
                  "linear-gradient(90deg, var(--bias-center), var(--bias-right))",
              }}
            />
            <i style={{ flex: 1, background: "var(--bias-right)" }} />
          </div>
          <div className="press-spectrum__scale">
            <span>Left</span>
            <span>Center-left</span>
            <span>Center</span>
            <span>Center-right</span>
            <span>Right</span>
          </div>
        </div>

        <div className="press-axes">
          <div className="press-axis">
            <div className="press-axis__n">Axis 1</div>
            <h3>Political lean</h3>
            <p>
              Left to right placement, weighing the outlet&rsquo;s track record
              and the article&rsquo;s own language.
            </p>
          </div>
          <div className="press-axis">
            <div className="press-axis__n">Axis 2</div>
            <h3>Sensationalism</h3>
            <p>Measured, or reaching for the reader&rsquo;s pulse. Read from the words.</p>
          </div>
          <div className="press-axis">
            <div className="press-axis__n">Axis 3</div>
            <h3>Opinion vs reporting</h3>
            <p>Whether the piece is arguing a case or laying out events.</p>
          </div>
          <div className="press-axis">
            <div className="press-axis__n">Axis 4</div>
            <h3>Factual rigor</h3>
            <p>Sourcing, attribution, and hedging. The marks of careful reporting.</p>
          </div>
          <div className="press-axis">
            <div className="press-axis__n">Axis 5</div>
            <h3>Framing</h3>
            <p>Which facts are foregrounded, and which are left in the margins.</p>
          </div>
          <div className="press-axis">
            <div className="press-axis__n">Axis 6</div>
            <h3>Coverage over time</h3>
            <p>How an outlet tends to cover a given subject over time, not just today.</p>
          </div>
        </div>
      </section>

      {/* ── Working with the press ───────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-work-h">
        <p className="press-kicker">
          <span className="press-kicker__n">05</span> Ground rules
        </p>
        <h2 id="press-work-h">Working with the press</h2>
        <ul>
          <li>
            You see what every reader sees. We do not build custom or
            personalized feeds for demos.
          </li>
          <li>
            There is no private user data to request, because we do not collect
            any.
          </li>
          <li>
            Methodology questions get a real answer. The scoring is documented,
            and we will walk you through it.
          </li>
        </ul>
      </section>

      {/* ── The organization ─────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-org-h">
        <p className="press-kicker">
          <span className="press-kicker__n">06</span> Independence
        </p>
        <h2 id="press-org-h">The organization</h2>
        <p className="press-org">
          Void News is an independent product of Void, the company behind our
          news and audio work. There are no outside investors and no
          advertising. It answers to readers, not shareholders, and is built
          around a single rule: the same stories, in the same order, for
          everyone.
        </p>
      </section>

      {/* ── Brand assets ─────────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-assets-h">
        <p className="press-kicker">
          <span className="press-kicker__n">07</span> Download
        </p>
        <h2 id="press-assets-h">Brand assets</h2>
        <p className="press-boiler__hint">
          Logos are vector SVG. Use the color version on light grounds and the
          reversed (white) version on dark or photographic grounds. Do not
          recolor the bias spectrum.
        </p>
        <ul className="press-kit">
          <li className="press-kit__item">
            <span className="press-kit__name">Void News logo, horizontal (color)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-news-horizontal-color.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Void News logo, horizontal (reversed)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-news-horizontal-reversed.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Void News mark, Sigil icon (color)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-news-icon-color.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Void News mark, Sigil icon (reversed)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-news-icon-reversed.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Animated Sigil (bias-sweep)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/void-news-sigil-animated.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Void History logo, horizontal (color)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-history-horizontal-color.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Void Weekly logo, horizontal (color)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-weekly-horizontal-color.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Void Vision logo, horizontal (color)</span>
            <a
              className="press-kit__dl"
              href={`${BASE_PATH}/brand/logos/void-vision-horizontal-color.svg`}
              download
            >
              SVG
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Color reference, all palettes (hex)</span>
            <a className="press-kit__dl" href={`${BASE_PATH}/brand/colors.md`} download>
              MD
            </a>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Social share card, Open Graph (1200 &times; 630)</span>
            <a className="press-kit__dl" href={`${BASE_PATH}/og-image.png`} download>
              PNG
            </a>
          </li>
        </ul>
      </section>

      {/* ── Reference pages ──────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-ref-h">
        <p className="press-kicker">
          <span className="press-kicker__n">08</span> Read more
        </p>
        <h2 id="press-ref-h">Reference pages</h2>
        <ul className="press-kit press-kit--links">
          <li className="press-kit__item">
            <span className="press-kit__name">Mission and manifesto</span>
            <Link className="press-kit__dl" href="/about">
              /about
            </Link>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Methodology, the six axes</span>
            <Link className="press-kit__dl" href="/about">
              /about
            </Link>
          </li>
          <li className="press-kit__item">
            <span className="press-kit__name">Source list, all 1,016 outlets</span>
            <Link className="press-kit__dl" href="/sources">
              /sources
            </Link>
          </li>
        </ul>
      </section>

      {/* ── Contact ──────────────────────────────────────────────────────── */}
      <section className="press-block" aria-labelledby="press-contact-h">
        <p className="press-kicker">
          <span className="press-kicker__n">09</span> Get in touch
        </p>
        <h2 id="press-contact-h">Contact</h2>
        <div className="press-contact">
          <div className="press-contact__row">
            <span className="press-contact__k">Press inquiries</span>
            <a className="press-contact__v" href="mailto:press@voidvision.org">
              press@voidvision.org
            </a>
          </div>
          <div className="press-contact__row">
            <span className="press-contact__k">Methodology questions</span>
            <a className="press-contact__v" href="mailto:methodology@voidvision.org">
              methodology@voidvision.org
            </a>
          </div>
          <div className="press-contact__row">
            <span className="press-contact__k">Instagram</span>
            <a
              className="press-contact__v"
              href="https://instagram.com/voidvision.media"
              rel="noopener noreferrer"
            >
              @voidvision.media
            </a>
          </div>
          <div className="press-contact__row">
            <span className="press-contact__k">X</span>
            <a
              className="press-contact__v"
              href="https://x.com/voidvisionx"
              rel="noopener noreferrer"
            >
              @voidvisionx
            </a>
          </div>
          <div className="press-contact__row">
            <span className="press-contact__k">Bluesky</span>
            <a
              className="press-contact__v"
              href="https://bsky.app/profile/voidvisionmedia.bsky.social"
              rel="noopener noreferrer"
            >
              @voidvisionmedia
            </a>
          </div>
        </div>
        <p className="press-contact__note">
          Response time: typically within 24 hours, earlier on weekdays.
        </p>
      </section>

      <p className="press__footer">
        Privacy questions: <Link href="/privacy">/privacy</Link>.
      </p>
    </article>
  );
}
