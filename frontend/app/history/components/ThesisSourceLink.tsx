/* ===========================================================================
   ThesisSourceLink: the one mark for "open the original document".

   Every place the thesis offers the free copy of a source (a note, a
   sidenote, the bibliography, an exhibit, the extracts under a verdict) used
   to print the words FREE COPY in small capitals, run on after the citation.
   It read as one more piece of the citation rather than as a way out to the
   document. This is a glyph instead: a page with an arrow leaving its corner,
   the external document, drawn inline in currentColor so it takes the
   section's brass and the reader's scheme. The words live on as the link's
   accessible name and its tooltip, so nothing a screen reader heard is lost.

   Where the ledger holds no free copy the same page is drawn struck through
   and muted: the same grammar, never a link.
   =========================================================================== */

function PageGlyph({ struck }: { struck?: boolean }) {
  return (
    <svg
      className="hist-th-srcmark__glyph"
      width="20"
      height="16"
      viewBox="0 0 20 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {/* A page with a folded corner and two lines of text: a document. */}
      <path d="M1.75 1.75h6l3 3v9.5h-9z" />
      <path d="M7.75 1.75v3h3" />
      {struck ? (
        /* Struck through: there is no copy to open. */
        <path d="M0.75 14.75 11.75 1.25" />
      ) : (
        <>
          <path d="M4 8.25h4M4 11h4" />
          {/* The arrow leaving it: open it, elsewhere. */}
          <path d="M12.75 9.5 18.25 4M14.75 4h3.5v3.5" />
        </>
      )}
    </svg>
  );
}

interface FreeCopyLinkProps {
  href: string;
  /** What the copy is of, for the accessible name: "Open the free copy of <name>". */
  name: string;
  /** Overrides the accessible name's verb phrase (an image's file page is not a free copy). */
  label?: string;
  className?: string;
}

export function FreeCopyLink({ href, name, label, className }: FreeCopyLinkProps) {
  const accessible = label ?? `Open the free copy of ${name}`;
  return (
    <a
      href={href}
      className={`hist-th-srcmark hist-th-srcmark--link${className ? ` ${className}` : ""}`}
      rel="noopener noreferrer"
      target="_blank"
      aria-label={`${accessible} (opens in a new tab)`}
      title={label ?? "Open the free copy (new tab)"}
    >
      <PageGlyph />
    </a>
  );
}

/** The mark alone, not a link: for the key that explains it. */
export function SourceMark({ struck }: { struck?: boolean }) {
  return (
    <span className={`hist-th-srcmark hist-th-srcmark--${struck ? "none" : "key"}`} aria-hidden="true">
      <PageGlyph struck={struck} />
    </span>
  );
}

export function NoFreeCopy() {
  return (
    <span className="hist-th-srcmark hist-th-srcmark--none" role="img" aria-label="No free copy" title="No free copy">
      <PageGlyph struck />
    </span>
  );
}
