import { UNVERIFIED_LABEL, UNVERIFIED_TITLE } from "../lib/verification";

/* The label a TL;DR, Opinion or On Air broadcast wears when its grounding
   pass did not complete (lib/verification.ts). Text, not an icon: it has to
   read the same to a screen reader as to the eye. */
export default function UnverifiedLabel() {
  return (
    <span className="unverified-label" title={UNVERIFIED_TITLE}>
      {UNVERIFIED_LABEL}
    </span>
  );
}
