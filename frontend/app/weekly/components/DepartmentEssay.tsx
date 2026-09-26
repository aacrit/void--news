"use client";

/* ---------------------------------------------------------------------------
   A front-of-book department: Technology, Sports & Culture.

   These have been WRITTEN every week since the section was built and stored by
   nothing. `_generate_tech_brief` and `_generate_sports` each burn a Gemini
   call and produce a 500-700 word piece; the row that saves the issue had only
   a comment where the write should have been, so the only trace they left was
   as context for the audio script. Rendering them is what turns a two-essay
   page into an issue with a front of book.

   At 400-700 words these DO set in two columns. That is the other half of the
   measure rule in Feature.tsx: a block this length is about one screen tall,
   so the reader never scrolls down and back up, and two columns is what makes
   a page read as a page rather than as a post.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyDepartment } from "../types";
import { essayParagraphs } from "../format";
import { DepartmentPlate, ImgCaption } from "./furniture";
import { useImageStatus, useScrollReveal } from "../hooks";

export default function DepartmentEssay({
  department,
  issueNumber,
  page,
}: {
  department: WeeklyDepartment;
  issueNumber: number;
  page: number;
}) {
  const [ref, visible] = useScrollReveal(0.08);
  const img = useImageStatus(department.image_url);
  const paras = essayParagraphs(department.text || "");
  if (paras.length === 0) return null;

  const headingId = `wk-dept-${department.slug}-heading`;
  const showImage = !!department.image_url && !img.failed;

  return (
    <section
      id={`wk-dept-${department.slug}`}
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-department wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby={headingId}
    >
      <DepartmentPlate
        label={department.label}
        issueNumber={issueNumber}
        page={page}
        id={headingId}
      />

      {showImage && (
        <figure className="wk-department__figure">
          <div className="wk-department__image-wrap">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={img.ref}
              src={department.image_url!}
              alt=""
              className={`wk-department__image${img.loaded ? " wk-department__image--loaded" : ""}`}
              loading="lazy"
              decoding="async"
              onLoad={img.onLoad}
              onError={img.onError}
            />
          </div>
          <ImgCaption
            caption={department.image_caption}
            credit={department.image_attribution}
          />
        </figure>
      )}

      {department.headline?.trim() && (
        <h3 className="wk-department__headline">{department.headline}</h3>
      )}
      <div className="wk-department__text">
        {paras.map((p, i) => <p key={i}>{p}</p>)}
      </div>
    </section>
  );
}
