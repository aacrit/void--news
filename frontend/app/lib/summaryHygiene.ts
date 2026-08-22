/* ---------------------------------------------------------------------------
   summaryHygiene — belt-and-suspenders guard against raw scraped excerpts.

   The pipeline's step-8d.6 summary floor guarantees every displayed top-50
   cluster gets a clean, on-topic summary (LLM or deterministic rule-based).
   This is the last line of defence: if a summary still slips through looking
   like a raw scraped excerpt (CMS artifacts, a photo/byline credit, a trailing
   "- outlet.com" suffix, or run-together words from a bad extraction), we drop
   it so the card falls back to its neutral "N sources reporting" pending line
   instead of rendering the garbage.
   --------------------------------------------------------------------------- */

// Obvious CMS / newsroom-scaffolding + syndication artifacts that never belong
// in an editorial summary. Kept conservative to avoid false positives on real
// prose.
const RAW_EXCERPT_PATTERNS: RegExp[] = [
  /\bWhy it matters:/i,
  /\bthe big picture:/i,
  /\bgo deeper:/i,
  /\bread more:/i,
  /\bkeep reading:/i,
  /\bsign up for/i,
  /\bsubscribe to/i,
  /\badvertisement\b/i,
  /\bphoto(?:graph)?:\s/i,
  /\bimage caption\b/i,
  /\bgetty images\b/i,
  // Photo/byline credit like "(John Smith/AFP)" or "(AP Photo/...)".
  /\([^)]*\/\s*(?:AFP|AP|Reuters|Getty|EPA|Bloomberg|Anadolu|Xinhua|AAP)\b/i,
  // Trailing outlet-domain suffix like " - reuters.com" / " — bbc.co.uk".
  /[\s\-–—]+[a-z0-9-]+\.(?:com|org|net|gov|co\.[a-z]{2})\s*$/i,
  // Broken-extraction glue that carries NO camel seam (so the longCamel check
  // below misses it): a digit fused to a word by "=" ("43=second"), or a close
  // paren fused directly to the next word ("(MEE)Off"). Real prose puts a space
  // after ")" and never writes "n=word" without spaces.
  /[a-z0-9]=[a-z]/i,
  /\)[A-Za-z]/,
];

/** True when a non-empty summary looks like a raw scraped excerpt, not prose. */
export function isRawExcerpt(summary: string): boolean {
  const s = (summary ?? "").trim();
  if (!s) return false;

  for (const re of RAW_EXCERPT_PATTERNS) {
    if (re.test(s)) return true;
  }

  // Run-together words from a broken extraction ("reportingThe minister saidThe").
  // Only count camel seams inside genuinely LONG tokens (>= 12 chars): legit
  // short camel terms repeated in real prose (mRNA, iPhone, eBay, iOS, macOS)
  // must not fire. A real extraction artifact is a long concatenated word, so
  // flag when two or more long tokens carry an internal lowercase->uppercase seam.
  // ("mRNA" is 4 chars and never counts, however often it repeats.)
  const longCamel = s
    .split(/\s+/)
    .filter((t) => t.length >= 12 && /[a-z][A-Z]/.test(t)).length;
  if (longCamel >= 2) return true;

  // A single absurdly long token is almost always concatenated words / a URL
  // slug that survived extraction.
  if (/\S{40,}/.test(s)) return true;

  return false;
}

/* ---------------------------------------------------------------------------
   Defamation guard (P0, 2026-08-11)
   ----------------------------------------------------------------------------
   A contested, criminal, or reputationally damaging claim about a NAMED person,
   stated in Void's own voice with no attribution to the reporting outlet, is a
   defamation exposure (a live summary asserted, unattributed, that a named
   individual "celebrated the October 7 terror attacks"). We drop any sentence
   that pairs a reputational-harm predicate with NO attribution cue. Conservative
   by design: only clear harm phrasings fire, and an attributed sentence
   ("according to the New York Post, ...") is kept. When in doubt we drop the
   sentence, never the other way. This is a render-time last line of defence; the
   pipeline prompt + post-check are the durable fix.
   --------------------------------------------------------------------------- */

// A reputational-harm verb aimed at a terror/atrocity/abuse object, e.g.
// "celebrated the October 7 terror attacks", "applauded Islamic terror".
const REPUTATIONAL_HARM =
  /\b(celebrat|applaud|prais|laud|endors|glorif|justif|condon|cheer|support|back|defend|champion)\w*\s+(?:\w+\s+){0,4}(terror|terrorism|terrorist|attack|massacre|genocide|jihad|extremis|antisemit|nazism|nazi|hamas|hezbollah|rape|molest|p(?:a?e)dophil|abuse|assault|insurrection)/i;
// A criminal/atrocity identity stated as bare fact, e.g. "is a convicted rapist".
const CRIMINAL_FACT =
  /\b(?:is|was|are|were)\s+(?:a\s+|an\s+|the\s+)?(?:convicted\s+|alleged\s+|suspected\s+)?(terrorist|rapist|p(?:a?e)dophile|murderer|fraudster|abuser|molester|criminal|extremist)\b/i;
// Direct criminal allegations that must carry a source ("charged with", etc.).
const CRIMINAL_ALLEGATION =
  /\b(accused of|charged with|indicted (?:for|on)|convicted of|found guilty of|arrested for|perpetrat(?:ed|or))\b/i;
// In-text attribution to a reporting outlet, official source, or a direct quote.
const ATTRIBUTION_CUE =
  /\b(accord(?:ing) to|reported by|as reported|reportedly|said|says|stated|told\s+[A-Z]|per\s+[A-Z]|alleged by|prosecutors|indictment|police said|court (?:documents|filings|records)|lawsuit|complaint|according)\b/i;
const QUOTE_PRESENT = /["“][^"”]{3,}["”]/;
// Reputational-harm ASSOCIATION terms (nouns/phrases). Dangerous when they float
// in a subject-less truncation fragment next to a named person ("375 million into
// ... blacklisted over alleged al-Qaeda, Taliban, and Hamas ties."). Bare org
// names are excluded so legitimate reporting ("Hamas affirmed ...") is untouched.
const REPUTATIONAL_TERM =
  /\b(?:blacklist(?:ed|ing)?|(?:terror|terrorist|al[\s-]?qaeda|taliban|hamas|hezbollah|isis|isil|jihad|militant|extremist)\s+(?:ties|links?|affiliation|connections?)|(?:ties|links?|affiliation|connections?)\s+to\s+(?:terror|terrorist|al[\s-]?qaeda|taliban|hamas|hezbollah|isis|isil|jihad|militants?|extremis)|link(?:ed|s)?\s+to\s+(?:terror|al[\s-]?qaeda|taliban|hamas|hezbollah|isis|jihad|extremis)|designat(?:ed|ion)\s+(?:as\s+)?(?:a\s+)?(?:foreign\s+)?terrorist|sympath(?:iser|izer)|radicali[sz]ed)\b/i;
// A plausible subject opens the sentence (proper noun / pronoun / article-led
// noun phrase). Fails on a bare-numeral or dangling-preposition opening.
const SUBJECT_START =
  /^["'“(]*\s*(?:He|She|They|It|The|A|An|This|That|Those|These|His|Her|Their|[A-Z][A-Za-z][A-Za-z.'’-]*)\b/;

function hasIdentifiableSubject(sentence: string): boolean {
  const s = (sentence ?? "").trim();
  if (!s) return false;
  if (/^["'“(]*\s*\$?\d/.test(s)) return false; // opens on a figure -> no subject
  return SUBJECT_START.test(s);
}

/**
 * Drop any sentence that makes a reputational-harm claim about a person with no
 * attribution. Returns the summary with such sentences removed (possibly empty,
 * in which case the card is dropped by the caller's real-summary filter).
 */
export function stripUnattributedReputationalClaims(summary: string): string {
  const s = (summary ?? "").trim();
  if (!s) return "";
  // Split into sentence chunks that CAPTURE their own trailing whitespace, so a
  // faithful reconstruction is just a concatenation. The naive split+join(" ")
  // this replaced broke every abbreviation and decimal in the feed: it cut
  // "U.S." into "U." + "S." on the period and the space-join reinserted a space
  // ("U. S.", "$22. 9", 'hear. "'). Sitewide, because this runs on every card.
  const sentences = s.match(/[^.!?]+[.!?]*\s*/g) ?? [s];
  let dropped = false;
  const kept = sentences.filter((sent) => {
    const attributed = ATTRIBUTION_CUE.test(sent) || QUOTE_PRESENT.test(sent);
    // (1) Verb-led reputational/criminal claim: keep only if attributed.
    const harm =
      REPUTATIONAL_HARM.test(sent) ||
      CRIMINAL_FACT.test(sent) ||
      CRIMINAL_ALLEGATION.test(sent);
    if (harm && !attributed) {
      dropped = true;
      return false;
    }
    // (2) Reputational-harm association term in a fragment (e.g. a truncated
    // "375 million into ... blacklisted over alleged al-Qaeda ... ties"): require
    // BOTH an identifiable subject AND attribution, else drop.
    if (REPUTATIONAL_TERM.test(sent) && !(hasIdentifiableSubject(sent) && attributed)) {
      dropped = true;
      return false;
    }
    return true;
  });
  // No sentence removed: return the ORIGINAL text untouched. Never reformat a
  // clean summary — that is what corrupted the spacing before.
  if (!dropped) return s;
  // A sentence was dropped: chunks already carry their own spacing, so a plain
  // concatenation preserves "U.S." / decimals; only collapse seams left behind.
  return kept.join("").replace(/\s+/g, " ").trim();
}

/* ---------------------------------------------------------------------------
   CSAM gate (P0, 2026-08-11)
   ----------------------------------------------------------------------------
   A story about child sexual abuse material must never emit a generated or
   scraped description of the material. Such a cluster renders as headline +
   source list ONLY; the caller blanks the body when this returns true.
   --------------------------------------------------------------------------- */
const CSAM_TOPIC =
  /\b(child (?:sexual abuse|sex abuse|pornography|porn|exploitation)|csam|sexually explicit (?:video|image|photo|material|content)s?\s+(?:involving|of|depicting)\s+(?:a\s+)?minors?|minors?\b[^.]{0,40}\b(?:sexual(?:ly)?\s+(?:abus|explicit|exploit)|molest|raped|sexually abused)|underage\s+(?:sex|porn|nude|explicit))/i;

/** True when the text is about child sexual abuse material. */
export function isCSAMTopic(text: string): boolean {
  return CSAM_TOPIC.test(text ?? "");
}

/**
 * Return a display-safe summary. Empty or raw-excerpt input yields "" so the
 * card renders its neutral "N sources reporting" pending line (a clean,
 * headline-independent fallback) rather than the raw text. Otherwise clean prose
 * passes through with any unattributed reputational-harm sentence removed.
 */
/* ---------------------------------------------------------------------------
   Orphan-fragment guard (3d, 2026-08-22)
   ----------------------------------------------------------------------------
   A truncation or a broken sentence boundary can leave a dependent clause
   standing as its own "sentence": "...Progressive Caucus PAC. when she won a
   Hayward City Council seat in 2018." A well-formed sentence never opens on a
   lowercase subordinating conjunction / relative pronoun. Drop any non-first
   sentence that does. Also strip a malformed stray straight quote left by a
   dropped figure ('announced a " investment').
   --------------------------------------------------------------------------- */
const ORPHAN_SUBORDINATE =
  /^(?:when|where|which|who|whom|whose|that|because|although|though|while|since|unless|whereas|wherein|whereby|after|before|as|if)\b/;

export function dropOrphanFragments(summary: string): string {
  const s = (summary ?? "").trim();
  if (!s) return "";
  // Strip a stray straight quote that has a space on at least one side and is
  // not a real quotation ('a " investment' -> 'a investment'); collapse spaces.
  let cleaned = s.replace(/\s"\s+/g, " ").replace(/\s"(?=[a-z])/g, " ");
  const sentences = cleaned.match(/[^.!?]+[.!?]*\s*/g) ?? [cleaned];
  let dropped = false;
  const kept = sentences.filter((sent, i) => {
    if (i === 0) return true; // never drop the lead sentence
    if (ORPHAN_SUBORDINATE.test(sent.trimStart())) {
      dropped = true;
      return false;
    }
    return true;
  });
  cleaned = (dropped ? kept.join("") : cleaned).replace(/\s+/g, " ").trim();
  return cleaned;
}

export function cleanFeedSummary(summary: string, _title?: string): string {
  const s = (summary ?? "").trim();
  if (!s) return "";
  if (isRawExcerpt(s)) return "";
  return dropOrphanFragments(stripUnattributedReputationalClaims(s));
}
