"use client";

/* ---------------------------------------------------------------------------
   The cover.

   A magazine's cover and its opening spread are different objects and do
   different jobs. This carries the nameplate, the issue line, the cover
   headline and the coverlines, and NO body copy. The spread below it (see
   CoverOpening) carries the kicker, the deck, the dateline and the lede —
   previously both rendered the same headline over the same photograph, back to
   back, which is the one thing a cover must never do.

   The 7-second auto-scroll that used to live here is gone. A magazine does not
   turn its own page; the scroll cue is the invitation, and the reader decides.
   --------------------------------------------------------------------------- */

import type React from "react";
import { ImgCaption } from "./furniture";
import { useImageStatus } from "../hooks";

export default function CinematicCover({
  nameplate,
  issueLine,
  headline,
  coverlines,
  imageUrl,
  imageCaption,
  imageAttribution,
}: {
  nameplate: React.ReactNode;
  issueLine: string;
  headline: string;
  coverlines: string[];
  imageUrl?: string | null;
  imageCaption?: string | null;
  imageAttribution?: string | null;
}) {
  // `onError` alone misses a prerendered image that failed before hydration,
  // which left the cover in its image variant with near-white furniture over a
  // scrim covering nothing, under a credit for a picture that was not there.
  const img = useImageStatus(imageUrl);
  const hasImage = !!imageUrl && !img.failed;

  const scrollToPageOne = () => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document
      .getElementById("wk-page-1")
      ?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };

  return (
    <section
      className={`wk-cover${hasImage ? " wk-cover--has-image" : " wk-cover--type"}`}
      aria-labelledby="wk-cover-headline"
    >
      {hasImage && (
        <div className="wk-cover__media" aria-hidden="true">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={img.ref}
            src={imageUrl!}
            alt=""
            className={`wk-cover__img${img.loaded ? " wk-cover__img--loaded" : ""}`}
            loading="eager"
            fetchPriority="high"
            decoding="async"
            onLoad={img.onLoad}
            onError={img.onError}
          />
          <div className="wk-cover__scrim" />
        </div>
      )}

      <div className="wk-cover__furniture">
        <div className="wk-cover__top">
          <div className="wk-cover__nameplate">{nameplate}</div>
          <p className="wk-cover__issue">{issueLine}</p>
        </div>

        <div className="wk-cover__bottom">
          {/* The largest text on the page, and it was a <p>. It is the issue's
              <h1>: the cover headline is the top of the document, every
              department plate below it is an h2, and each piece's own headline
              is an h3. It also names this section through aria-labelledby, so
              the cover is a landmark rather than content outside one. */}
          <h1 id="wk-cover-headline" className="wk-cover__headline">{headline}</h1>

          {coverlines.length > 0 && (
            <div className="wk-cover__coverlines">
              <span className="wk-cover__coverlines-label">Also inside</span>
              <ul className="wk-cover__coverlines-list">
                {coverlines.map((line, i) => (
                  <li key={i} className="wk-cover__coverline">{line}</li>
                ))}
              </ul>
            </div>
          )}

          <button
            type="button"
            className="wk-cover__cue"
            onClick={scrollToPageOne}
            aria-label="Open the issue"
          >
            <span className="wk-cover__kicker">See through the void</span>
            <svg className="wk-cover__chevron" viewBox="0 0 24 14" aria-hidden="true">
              <path
                d="M2 2 L12 11 L22 2"
                stroke="currentColor"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>

        {hasImage && (imageCaption || imageAttribution) && (
          <div className="wk-cover__credit">
            <ImgCaption caption={imageCaption} credit={imageAttribution} />
          </div>
        )}
      </div>
    </section>
  );
}
