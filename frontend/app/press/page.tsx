import type { Metadata } from "next";
import Link from "next/link";
import { BASE_PATH } from "../lib/utils";
import "../styles/about.css";
import "../privacy/privacy.css";
import "./press.css";

export const metadata: Metadata = {
  title: "Press | Void News",
  description:
    "Press kit and media inquiries for Void News. Coverage requests, interviews, methodology questions, and brand assets.",
};

export default function PressPage() {
  return (
    <article className="press">
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News feed
      </Link>

      <header className="press__hdr">
        <p className="press__eyebrow">Void News / press</p>
        <h1>For journalists, critics, researchers.</h1>
        <p className="press__byline">
          Bias methodology, source curation, and editorial decisions are
          documented. Ask anything.
        </p>
      </header>

      <div className="press-ledger" aria-label="Void News at a glance">
        <div className="press-stat">
          <div className="press-stat__n">1,016</div>
          <div className="press-stat__l">Sources, across 3 credibility tiers</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">158</div>
          <div className="press-stat__l">Countries represented</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">6</div>
          <div className="press-stat__l">Bias axes, scored per article</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">50</div>
          <div className="press-stat__l">Stories in the daily edition</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">1&times;</div>
          <div className="press-stat__l">Published once a day</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">$0</div>
          <div className="press-stat__l">Spent scoring bias. It is all rule-based.</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">0</div>
          <div className="press-stat__l">Accounts, trackers, or recommendation feeds</div>
        </div>
        <div className="press-stat">
          <div className="press-stat__n">100%</div>
          <div className="press-stat__l">Deterministic: same text, same score</div>
        </div>
      </div>

      <div className="press-principle">
        <p>
          <strong>Free to read, and built to stay that way.</strong> No paywall
          on the news, no trackers, no feed tuned to you, no paying for a better
          rank. If Void News ever earns money, it will be from optional
          membership, tools, or licensing our analysis, never from the front
          page.
        </p>
      </div>

      <section>
        <h2>One paragraph.</h2>
        <p>
          Void News is a news aggregator that scores every individual
          article on six bias axes using rule-based NLP (no machine learning
          black box), reads 1,016 sources across 158 countries, and presents
          one importance-ranked feed to every reader. No accounts, no
          tracking, no personalization, free to read. The product was built
          to invert what personalization did to the news: same stories, same
          order, for everyone.
        </p>
      </section>

      <section>
        <h2>How the bias read works.</h2>
        <p>
          This is the part journalists ask about, so here it is plainly. Void
          News scores each article on six axes using rule-based language
          analysis, no large language model, no black box. The scoring is
          deterministic: the same text always produces the same score, and every
          score ships with a written rationale.
        </p>

        <div className="press-callout">
          <strong>
            We do not judge a story by its outlet alone, and we do not judge it
            by its words alone. We use both.
          </strong>{" "}
          A score weighs the outlet&rsquo;s measured track record and the
          specific language of the article in front of you. On a short wire
          dispatch there is not much text to read, so the outlet&rsquo;s history
          carries more weight; on a full feature, the article&rsquo;s own words
          lead. The balance shifts with how much there is to actually read.
        </div>

        <div className="press-spectrum" aria-label="Political lean spectrum: left is blue, center is green, right is red">
          <div className="press-spectrum__bar" aria-hidden="true">
            <i style={{ flex: 1, background: "var(--bias-left)" }} />
            <i style={{ flex: 1, background: "linear-gradient(90deg, var(--bias-left), var(--bias-center))" }} />
            <i style={{ flex: 1, background: "var(--bias-center)" }} />
            <i style={{ flex: 1, background: "linear-gradient(90deg, var(--bias-center), var(--bias-right))" }} />
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
            <p>Left to right placement, blending the outlet&rsquo;s track record with the article&rsquo;s own language.</p>
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
            <h3>Per-topic tracking</h3>
            <p>How an outlet tends to cover a given subject over time, not just today.</p>
          </div>
        </div>
      </section>

      <section>
        <h2>Boilerplate.</h2>
        <p className="press-boiler__hint">For editors and reporters. Copy as is.</p>

        <div className="press-boiler">
          <p className="press-boiler__label">Short</p>
          <p>
            Void News is an independent daily news reader that scores the
            political lean and editorial character of every story with
            transparent, rule-based analysis, drawing on 1,016 sources across
            158 countries, in one shared edition of fifty stories, the same for
            every reader.
          </p>
        </div>

        <div className="press-boiler">
          <p className="press-boiler__label">Long</p>
          <p>
            Void News gathers each day&rsquo;s reporting from more than a
            thousand outlets across 158 countries, groups the coverage of each
            event together, and scores every article on six axes: political
            lean, sensationalism, opinion versus reporting, factual rigor,
            framing, and per-topic tendency. The analysis is rule-based and
            deterministic rather than an opaque model: each score weighs both
            the outlet&rsquo;s measured track record and the article&rsquo;s own
            language, and carries a written rationale.
          </p>
          <p>
            There are no accounts, no trackers, and no personalized feed. The
            fifty most-covered stories are ranked once a day, in the same order
            for everyone, on the principle that a shared set of facts matters
            more than an engaging one. Void News is an independent project with
            no outside investors, and is available at news.voidvision.org.
          </p>
        </div>
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
        <h2 style={{ marginTop: 0 }}>Brand assets</h2>
        <p style={{ marginTop: 0, color: "var(--fg-tertiary)", fontSize: 14 }}>
          Logos are vector SVG. Use the color version on light grounds and the
          reversed (white) version on dark or photographic grounds. Do not
          recolor the bias spectrum. Full usage rules live in the internal pack.
        </p>
        <ul style={{ listStyle: "none", padding: 0 }}>
          <li className="press__kit-item">
            <span>Void News logo (horizontal, color)</span>
            <a href={`${BASE_PATH}/brand/logos/void-news-horizontal-color.svg`} download>
              void-news-horizontal-color.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Void News logo (horizontal, reversed)</span>
            <a href={`${BASE_PATH}/brand/logos/void-news-horizontal-reversed.svg`} download>
              void-news-horizontal-reversed.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Void News mark (Sigil icon, color)</span>
            <a href={`${BASE_PATH}/brand/logos/void-news-icon-color.svg`} download>
              void-news-icon-color.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Void News mark (Sigil icon, reversed)</span>
            <a href={`${BASE_PATH}/brand/logos/void-news-icon-reversed.svg`} download>
              void-news-icon-reversed.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Animated Sigil (bias-sweep, SVG)</span>
            <a href={`${BASE_PATH}/brand/void-news-sigil-animated.svg`} download>
              void-news-sigil-animated.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Void History logo (horizontal, color)</span>
            <a href={`${BASE_PATH}/brand/logos/void-history-horizontal-color.svg`} download>
              void-history-horizontal-color.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Void Weekly logo (horizontal, color)</span>
            <a href={`${BASE_PATH}/brand/logos/void-weekly-horizontal-color.svg`} download>
              void-weekly-horizontal-color.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Void Vision logo (horizontal, color)</span>
            <a href={`${BASE_PATH}/brand/logos/void-vision-horizontal-color.svg`} download>
              void-vision-horizontal-color.svg
            </a>
          </li>
          <li className="press__kit-item">
            <span>Color reference (all palettes, hex)</span>
            <a href={`${BASE_PATH}/brand/colors.md`} download>
              colors.md
            </a>
          </li>
          <li className="press__kit-item">
            <span>Social share card (Open Graph, 1200x630)</span>
            <a href={`${BASE_PATH}/og-image.png`} download>
              og-image.png
            </a>
          </li>
        </ul>
        <p style={{ marginBottom: 0, color: "var(--fg-tertiary)", fontSize: 14 }}>
          Team and partners: the full internal brand pack (every lockup, icon,
          and wordmark across color, one-color, and reversed treatments, plus
          guidelines) lives at <code>brand/index.html</code> in the repository.
        </p>
      </section>

      <section className="press__kit">
        <h2 style={{ marginTop: 0 }}>Reference pages</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          <li className="press__kit-item">
            <span>Manifesto page</span>
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
            <a href="mailto:press@voidvision.org">
              press@voidvision.org
            </a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>Methodology questions:</strong>{" "}
            <a href="mailto:methodology@voidvision.org">
              methodology@voidvision.org
            </a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>Instagram:</strong> <a href="https://instagram.com/voidvision.media" rel="noopener noreferrer">@voidvision.media</a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>X:</strong> <a href="https://x.com/voidvisionx" rel="noopener noreferrer">@voidvisionx</a>
          </p>
          <p style={{ margin: 0 }}>
            <strong>Bluesky:</strong> <a href="https://bsky.app/profile/voidvisionmedia.bsky.social" rel="noopener noreferrer">@voidvisionmedia</a>
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
