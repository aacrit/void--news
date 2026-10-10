import Link from "next/link";
import type { Story } from "../lib/types";
import { storyShapeLabel } from "../lib/biasColors";
import { splitBriefParagraphs } from "../lib/briefText";
import {
  type ArticleTier,
  assignTier,
  distributeStories,
  splitDecks,
} from "./paperUtils";
import PrintButton from "./PrintButton";
import "./paper.css";

/* ---------------------------------------------------------------------------
   Paper: the printable front page.

   Server component. Every value it renders arrives as a prop from
   app/paper/page.tsx, which reads build-data/feed.json through the same
   fetchInitialFeed() the home page uses. So Paper carries the same stories in
   the same order, dated with the same edition dateline, and nothing here
   consults the viewer's clock.

   What this page does NOT do, by decision (2026-09-21): no classifieds, no
   weather, no city datelines, no issue number counted from an invented epoch,
   no editor's note. NavBar and Footer are mounted once in the root layout, so
   Paper renders neither, nor its own theme toggle.
   --------------------------------------------------------------------------- */

export interface PaperContentProps {
  /** The printed twenty, already filtered and sliced by the page. */
  stories: Story[];
  /** Pipeline completed_at ISO, for the <time> machine value. */
  builtAt: string | null;
  /** Build-time, UTC, deterministic edition date, e.g. "Sep 21, 2026". */
  editionDateline: string;
  /** The Brief's TL;DR body, or null when the run produced none. */
  tldr: string | null;
  /** Distinct printed_on dates in the permanent archive, or null if unknown. */
  editionNumber: number | null;
}

/* --- One article ---------------------------------------------------------- */

function Article({ story, tier }: { story: Story; tier: ArticleTier }) {
  const { decks, body } = splitDecks(story.summary, tier);
  const sigil = story.sigilData;
  // The front page's own word for this story (storyShapeLabel), so the
  // printed twenty cannot caption a story differently from its card.
  const lean = storyShapeLabel(sigil.biasSpread, !!sigil.unscored);
  const count = story.source?.count ?? sigil.sourceCount ?? 0;
  const href = story.permalink ?? `/?story=${encodeURIComponent(story.id)}`;

  return (
    <article className={`np-article np-article--${tier}`}>
      <h2 className="np-article__headline">
        <Link href={href} className="np-article__headline-link">
          <span className="np-article__headline-text">{story.title}</span>
        </Link>
      </h2>

      {decks.map((deck, i) => (
        <p
          key={i}
          className={`np-article__deck np-article__deck--${i + 1}`}
        >
          {deck}
        </p>
      ))}

      <p className="np-article__byline">
        {count} {count === 1 ? "source": "sources"}
      </p>

      <p className="np-article__summary">{body}</p>

      <p className="np-article__meta">{lean.text}</p>
    </article>
  );
}

/* --- The page ------------------------------------------------------------- */

export default function PaperContent({
  stories,
  builtAt,
  editionDateline,
  tldr,
  editionNumber,
}: PaperContentProps) {
  const { lead, zoneA, zoneB, zoneC } = distributeStories(stories);
  const briefParagraphs = splitBriefParagraphs(tldr);

  // Rank position drives the tier. Document order is rank order: lead, zone A,
  // zone B, zone C. The P-02 gate reads the headlines out of the served HTML in
  // that order and compares them with the front page's.
  let rank = 0;
  const next = () => assignTier(rank++);

  return (
    <div className="np-root" id="main-content" role="main">
      <header className="np-masthead">
        <hr className="np-masthead__top-rule" />
        <h1 className="np-masthead__nameplate">Paper</h1>
        <hr className="np-double-rule" aria-hidden="true" />
        <div className="np-masthead__info">
          <span className="np-masthead__info-left">
            {editionNumber ? `Edition ${editionNumber}`: ""}
          </span>
          <span className="np-masthead__info-center">
            <time dateTime={builtAt ?? undefined}>{editionDateline}</time>
          </span>
          <span className="np-masthead__info-right">Void News</span>
        </div>
        <hr className="np-double-rule" aria-hidden="true" />
        <p className="np-masthead__standfirst">
          Today&rsquo;s front page, in the order it prints. Every headline opens
          its Deep Dive.
        </p>
      </header>

      {briefParagraphs.length > 0 && (
        <section className="np-brief" aria-label="The Brief">
          <p className="np-brief__label">The Brief</p>
          <div className="np-brief__text">
            {briefParagraphs.map((para, i) => (
              <p key={i}>{para}</p>
            ))}
          </div>
        </section>
      )}

      {stories.length > 0 && (
        <>
          {lead && (
            <div className="np-front__lead">
              <Article story={lead} tier={next()} />
            </div>
          )}
          <div className="np-front__zones">
            <div className="np-front__zone-a">
              {zoneA.map((story) => (
                <Article key={story.id} story={story} tier={next()} />
              ))}
            </div>
            <div className="np-front__zone-b">
              {zoneB.map((story) => (
                <Article key={story.id} story={story} tier={next()} />
              ))}
            </div>
            <div className="np-front__zone-c">
              {zoneC.map((story) => (
                <Article key={story.id} story={story} tier={next()} />
              ))}
            </div>
          </div>
        </>
      )}

      <footer className="np-colophon">
        <hr className="np-colophon__rule" />
        <p>
          Void News &middot;{" "}
          <time dateTime={builtAt ?? undefined}>{editionDateline}</time>
        </p>
        <p>
          <Link href="/" className="np-colophon__link">
            The feed
          </Link>
        </p>
      </footer>

      <PrintButton />
    </div>
  );
}
