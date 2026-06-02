"use client";

import Link from "next/link";

/* ==========================================================================
   ArchiveTeaser — One event. Two witnesses. The same day.
   Used in /about between The Worlds and The Verdict chapters.
   Shows, without telling, what void --history does.
   ========================================================================== */

interface Props {
  active: boolean;
}

const WITNESSES = [
  {
    quote:
      "The decision to partition was taken reluctantly and with the knowledge that it would cause suffering. But the alternative was worse.",
    speaker: "Lord Mountbatten",
    role: "Last Viceroy of India · August 15, 1947",
  },
  {
    quote:
      "The vivisection of a whole nation, body and soul, is no way to independence.",
    speaker: "Mahatma Gandhi",
    role: "Statement on Partition · June 1947",
  },
];

export default function ArchiveTeaser({ active }: Props) {
  return (
    <div className={`film-archive-teaser${active ? " film-archive-teaser--in" : ""}`}>
      <p className="film-archive-teaser__locator">India · Pakistan · 1947</p>
      <p className="film-archive-teaser__event">The Partition of India</p>

      <div className="film-archive-teaser__witnesses">
        {WITNESSES.map((w, i) => (
          <figure key={i} className={`film-archive-teaser__witness film-archive-teaser__witness--${i === 0 ? "a" : "b"}`}
            style={{ transitionDelay: `${200 + i * 180}ms` }}>
            <blockquote className="film-archive-teaser__quote">{w.quote}</blockquote>
            <figcaption className="film-archive-teaser__attr">
              <span className="film-archive-teaser__speaker">{w.speaker}</span>
              <span className="film-archive-teaser__role">{w.role}</span>
            </figcaption>
          </figure>
        ))}
      </div>

      <Link href="/history" className="film-archive-teaser__cta">
        <span className="film-archive-teaser__cta-cli">void --history</span>
        <span className="film-archive-teaser__cta-arrow" aria-hidden="true">→</span>
      </Link>
    </div>
  );
}
