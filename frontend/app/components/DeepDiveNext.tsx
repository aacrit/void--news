"use client";

import Link from "next/link";

/* ---------------------------------------------------------------------------
   DeepDiveNext: where a Deep Dive ends.

   Every Deep Dive used to end on a small "Show source breakdown" link and then
   the footer or the grid (audit 2026-09-26, finding 6). The product's reading
   model is the same twenty stories in the same order for everyone, so the end
   of one story offers the next one, by name, and says where the reader is.
   After the last story it says the edition is done and offers the ways out.

   One component for the three shells. The feed shells pass `onNavigate` and
   get buttons that walk the open Deep Dive in place; the static /story page
   passes hrefs and gets links.
   --------------------------------------------------------------------------- */

export interface DeepDiveNextTarget {
  title: string;
  href?: string;
}

interface DeepDiveNextProps {
  prev?: DeepDiveNextTarget | null;
  next?: DeepDiveNextTarget | null;
  /** 1-based position of this story in its edition. */
  position: number;
  total: number;
  /** Feed shells: walk in place. */
  onNavigate?: (direction: "prev" | "next") => void;
  /** Feed shells: jump back to the first story after the last. */
  onFirst?: () => void;
  /** "the Sep 25 edition" on an archived story page; omitted for today's. */
  editionLabel?: string;
}

export default function DeepDiveNext({
  prev,
  next,
  position,
  total,
  onNavigate,
  onFirst,
  editionLabel,
}: DeepDiveNextProps) {
  const where = editionLabel ? `${position} of ${total} in ${editionLabel}` : `${position} of ${total}`;

  if (!next) {
    return (
      <nav className="dd-next dd-next--end" aria-label="End of the edition">
        <p className="dd-next__kicker">{where}</p>
        <p className="dd-next__end-line">That is the edition.</p>
        <ul className="dd-next__outs">
          <li>
            {onFirst ? (
              <button type="button" className="dd-next__out" onClick={onFirst}>Back to the top story</button>
            ) : (
              <Link className="dd-next__out" href="/">Today&rsquo;s front page</Link>
            )}
          </li>
          <li><Link className="dd-next__out" href="/paper/">Print the Paper</Link></li>
          <li><Link className="dd-next__out" href="/onair/">Listen: On Air</Link></li>
        </ul>
        {prev && <PrevLink prev={prev} onNavigate={onNavigate} />}
      </nav>
    );
  }

  return (
    <nav className="dd-next" aria-label="Next story">
      <p className="dd-next__kicker">Next story <span className="dd-next__where">{where}</span></p>
      {onNavigate ? (
        <button type="button" className="dd-next__headline" onClick={() => onNavigate("next")}>
          {next.title}
          <span className="dd-next__arrow" aria-hidden="true">&rsaquo;</span>
        </button>
      ) : (
        <Link className="dd-next__headline" href={next.href ?? "/"}>
          {next.title}
          <span className="dd-next__arrow" aria-hidden="true">&rsaquo;</span>
        </Link>
      )}
      {prev && <PrevLink prev={prev} onNavigate={onNavigate} />}
    </nav>
  );
}

function PrevLink({ prev, onNavigate }: { prev: DeepDiveNextTarget; onNavigate?: (d: "prev" | "next") => void }) {
  return onNavigate ? (
    <button type="button" className="dd-next__prev" onClick={() => onNavigate("prev")}>
      <span aria-hidden="true">&lsaquo; </span>Previous: {prev.title}
    </button>
  ) : (
    <Link className="dd-next__prev" href={prev.href ?? "/"}>
      <span aria-hidden="true">&lsaquo; </span>Previous: {prev.title}
    </Link>
  );
}
