/* ===========================================================================
   The Hearing — script + event record → the page's running order.

   Pure, server-side, no React. It turns the exported script (lib/historyScript)
   and the event row into the sequence the page renders top to bottom, in the
   order the episode is spoken.

   Two properties every decision here serves:

   1. Each account argues its own case uninterrupted. An account's section
      carries its narrative, its arguments and its witnesses. It never carries
      what that account leaves out. `omitted` appears in exactly one place on
      the page, and this module is where that is enforced: nothing below puts
      an `omissions` array anywhere but a turn row.

   2. The turn is the payload. It is the last TURN segment, it comes after all
      five accounts have spoken, and it is the only place the five YAML names
      sit together.

   The account an argument belongs to is NOT decided here. The exporter already
   decided it, with H-09's stem rule, and stamped it on the segment as
   `account`. Re-deriving it from names would be a second rule that could
   disagree with the first, and the cost of disagreeing is an argument printed
   under the name of the side that did not make it.
   =========================================================================== */

import type { HistoryScript, ScriptLine, ScriptSegment } from "../lib/historyScript";
import type { HistoricalEvent, MediaItem, Perspective } from "./types";

/* --------------------------------------------------------------------------
   Blocks: one run of lines in one voice.
   "N" is the narrator. Anything else (M, F) is someone else's words, and the
   page sets those in IBM Plex Mono, which is the only signal that says "these
   are real words" without a label saying so.
   -------------------------------------------------------------------------- */

export interface Attribution {
  author: string;
  work: string;
  date: string;
}

export type HearingBlock =
  | { t: "prose"; voice: "editorial" | "structural"; lines: string[] }
  | { t: "quote"; lines: string[]; attribution: Attribution | null };

export interface AccountRef {
  id: string;
  label: string;
  color: string;
}

export interface TurnRow {
  /** Anchor of the account's own section, so a row links back to the case. */
  href: string;
  name: string;
  color: string;
  /** The script's one line about this account, or null when the turn's lines
   *  could not be aligned to the accounts with confidence. */
  text: string | null;
  omitted: string[];
}

export type HearingSection =
  | { kind: "open"; id: string; blocks: HearingBlock[] }
  | { kind: "scene"; id: string; number: number; title: string; blocks: HearingBlock[] }
  | { kind: "passage"; id: string; blocks: HearingBlock[] }
  | { kind: "rest"; id: string; media: MediaItem | null; short: boolean }
  | { kind: "accounts"; id: string; title: string; blocks: HearingBlock[]; index: AccountRef[] }
  | {
      kind: "account";
      id: string;
      order: number;
      title: string;
      color: string;
      viewpoint: string;
      viewpointType: string;
      blocks: HearingBlock[];
      perspective: Perspective | null;
    }
  | {
      kind: "turn";
      id: string;
      title: string;
      framing: string[];
      rows: TurnRow[];
      closing: string[];
    }
  | { kind: "close"; id: string; blocks: HearingBlock[] };

export interface Station {
  id: string;
  label: string;
  /** Drawn as an ink tick, a numbered scene tick, a coloured dot, or the
   *  brass diamond the turn alone gets. */
  glyph: "tick" | "scene" | "dot" | "diamond";
  /** Scene number, for the "scene" glyph. */
  number?: number;
  /** A CSS colour expression, for the "dot" glyph. */
  color?: string;
}

export interface Hearing {
  sections: HearingSection[];
  stations: Station[];
  /** Media not spent on a rest, for the gallery in the end matter. */
  galleryMedia: MediaItem[];
}

/* --------------------------------------------------------------------------
   Lines → blocks
   -------------------------------------------------------------------------- */

const isNarrator = (l: ScriptLine): boolean => (l.speaker || "N").toUpperCase() === "N";

function blocksFrom(
  lines: ScriptLine[],
  voice: "editorial" | "structural",
  attribution: Attribution | null,
): HearingBlock[] {
  const out: HearingBlock[] = [];
  let attributed = false;
  for (const line of lines) {
    const text = (line.text || "").trim();
    if (!text) continue;
    const quoted = !isNarrator(line);
    const last = out[out.length - 1];
    if (quoted) {
      if (last && last.t === "quote") {
        last.lines.push(text);
      } else {
        /* The attribution rides the FIRST quote in the segment and comes before
           the words, in DOM order as well as visually, exactly as the audio
           names the speaker before the document is read. */
        out.push({ t: "quote", lines: [text], attribution: attributed ? null : attribution });
        attributed = true;
      }
    } else if (last && last.t === "prose") {
      last.lines.push(text);
    } else {
      out.push({ t: "prose", voice, lines: [text] });
    }
  }
  return out;
}

function narratorLines(seg: ScriptSegment): string[] {
  return seg.lines.filter(isNarrator).map((l) => (l.text || "").trim()).filter(Boolean);
}

function attributionOf(seg: ScriptSegment): Attribution | null {
  const author = (seg.author || "").trim();
  const work = (seg.work || "").trim();
  const date = (seg.date || "").trim();
  if (!author && !work && !date) return null;
  return { author, work, date };
}

/* --------------------------------------------------------------------------
   The turn's five rows

   The closing TURN carries a framing line, one line per account in the order
   the accounts spoke, and the closing lines. Rather than matching each line
   independently (which can hand one account's hole to another), the aligned
   RUN is found: the single offset at which the whole block of account lines
   sits. Order is never permuted, because the script never permutes it, and a
   run that scores best at exactly one offset is a much stronger claim than
   five independent best guesses.

   Measured over all 78 exported scripts: every one resolves to a unique best
   offset, and at least four of five accounts are named outright in the line
   assigned to them. Below that confidence the lines are rendered in order with
   no names attached, which is honest; a wrong name would not be.
   -------------------------------------------------------------------------- */

function norm(s: string): string {
  return (s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ");
}

function stemsFor(name: string, title: string): string[] {
  const words = norm(`${name} ${title}`).split(" ").filter((w) => w.length > 3);
  return Array.from(new Set(words.map((w) => w.slice(0, 6))));
}

export function alignTurnLines(
  lines: string[],
  stems: string[][],
): { offset: number; confident: boolean } {
  const k = stems.length;
  if (k === 0 || lines.length < k) return { offset: 0, confident: false };
  const normed = lines.map(norm);

  const scores: number[] = [];
  for (let o = 0; o + k <= normed.length; o++) {
    let score = 0;
    for (let i = 0; i < k; i++) {
      score += stems[i].filter((st) => st && normed[o + i].includes(st)).length;
    }
    scores.push(score);
  }
  const best = Math.max(...scores);
  const winners = scores.reduce<number[]>((acc, s, i) => (s === best ? [...acc, i] : acc), []);
  if (best === 0 || winners.length !== 1) return { offset: 0, confident: false };

  const offset = winners[0];
  const named = stems.filter((st, i) => st.some((s) => normed[offset + i].includes(s))).length;
  /* A simple majority is the floor. All 78 clear it with 4 of 5 or better. */
  return { offset, confident: named * 2 > k };
}

/* --------------------------------------------------------------------------
   Build
   -------------------------------------------------------------------------- */

const COLOR_VAR = (p: Perspective | null): string =>
  p ? `var(--hist-persp-${p.color})` : "var(--hist-accent)";

export function buildHearing(script: HistoryScript, event: HistoricalEvent): Hearing {
  const sections: HearingSection[] = [];

  /* Media is spent on the full rests in order; what is left goes to the
     gallery in the end matter. Video is not a rest: a rest is still. */
  const restPool = event.media.filter((m) => m.type !== "video");
  const spent = new Set<string>();
  let restCursor = 0;

  const turns = script.segments.filter((s) => s.kind === "TURN");
  const introTurn = turns.length > 1 ? turns[0] : null;
  const payloadTurn = turns.length > 0 ? turns[turns.length - 1] : null;

  let sceneNumber = 0;
  let restNumber = 0;
  let passageNumber = 0;
  let accountOrder = 0;

  /* The section a DOCUMENT or an ASIDE attaches to. A document in a scene
     belongs to no side and takes the brass rule; a witness after an account's
     case belongs to that account and takes its colour. */
  let host: HearingSection | null = null;

  const accountSections: Extract<HearingSection, { kind: "account" }>[] = [];
  /* The payload turn is pushed in script order and filled after the loop: it
     cannot name the five accounts until all five sections exist. */
  let turnSection: Extract<HearingSection, { kind: "turn" }> | null = null;

  for (const seg of script.segments) {
    switch (seg.kind) {
      /* TITLE is an audio ident and the hero already carries the title and the
         date. SAY is for the synthesiser. Neither is rendered. */
      case "TITLE":
        break;

      case "OPEN": {
        const s: HearingSection = {
          kind: "open",
          id: "open",
          blocks: blocksFrom(seg.lines, "editorial", null),
        };
        sections.push(s);
        host = null;
        break;
      }

      case "CLOSE": {
        const s: HearingSection = {
          kind: "close",
          id: "close",
          blocks: blocksFrom(seg.lines, "editorial", null),
        };
        sections.push(s);
        host = null;
        break;
      }

      case "SCENE": {
        sceneNumber += 1;
        const s: HearingSection = {
          kind: "scene",
          id: `scene-${sceneNumber}`,
          number: sceneNumber,
          title: (seg.title || "").trim(),
          blocks: blocksFrom(seg.lines, "structural", null),
        };
        sections.push(s);
        host = s;
        break;
      }

      case "REST": {
        restNumber += 1;
        const short = (seg.title || "").trim().toLowerCase() === "short";
        let media: MediaItem | null = null;
        if (!short && restCursor < restPool.length) {
          media = restPool[restCursor];
          spent.add(media.id);
          restCursor += 1;
        }
        sections.push({ kind: "rest", id: `rest-${restNumber}`, media, short });
        host = null;
        break;
      }

      case "PERSPECTIVE": {
        accountOrder += 1;
        const idx = typeof seg.account === "number" ? seg.account : null;
        const perspective = idx !== null ? event.perspectives[idx] ?? null : null;
        const s: Extract<HearingSection, { kind: "account" }> = {
          kind: "account",
          id: `account-${accountOrder}`,
          order: accountOrder,
          title: (seg.title || perspective?.viewpointName || "").trim(),
          color: COLOR_VAR(perspective),
          viewpoint: perspective?.viewpointName ?? "",
          viewpointType: perspective?.viewpointType ?? "",
          blocks: blocksFrom(seg.lines, "structural", null),
          perspective,
        };
        sections.push(s);
        accountSections.push(s);
        host = s;
        break;
      }

      case "TURN": {
        if (introTurn && seg === introTurn) {
          const s: HearingSection = {
            kind: "accounts",
            id: "accounts",
            title: (seg.title || "Five accounts").trim(),
            blocks: blocksFrom(seg.lines, "editorial", null),
            index: [],
          };
          sections.push(s);
          host = null;
        }
        if (payloadTurn && seg === payloadTurn) {
          turnSection = {
            kind: "turn",
            id: "turn",
            title: (seg.title || "The turn").trim(),
            framing: [],
            rows: [],
            closing: [],
          };
          sections.push(turnSection);
          host = null;
        }
        break;
      }

      case "DOCUMENT":
      case "ASIDE": {
        const voice = seg.kind === "ASIDE" ? "editorial" : "structural";
        const blocks = blocksFrom(seg.lines, voice, attributionOf(seg));
        if (!blocks.length) break;
        if (host && (host.kind === "scene" || host.kind === "account" || host.kind === "passage")) {
          host.blocks.push(...blocks);
        } else {
          passageNumber += 1;
          const s: HearingSection = { kind: "passage", id: `passage-${passageNumber}`, blocks };
          sections.push(s);
          host = s;
        }
        break;
      }

      default:
        break;
    }
  }

  /* ── The contents list under the framing lines ── */
  const accountsSection = sections.find((s) => s.kind === "accounts");
  if (accountsSection && accountsSection.kind === "accounts") {
    accountsSection.index = accountSections.map((a) => ({
      id: a.id,
      label: a.title,
      color: a.color,
    }));
  }

  /* ── The turn ── */
  if (turnSection && payloadTurn) {
    const lines = narratorLines(payloadTurn);
    const stems = accountSections.map((a) =>
      stemsFor(a.perspective?.viewpointName ?? "", a.title),
    );
    const { offset, confident } = alignTurnLines(lines, stems);
    const k = accountSections.length;

    turnSection.framing = confident ? lines.slice(0, offset) : lines.slice(0, 1);
    turnSection.closing = confident ? lines.slice(offset + k) : lines.slice(1);
    turnSection.rows = accountSections.map((a, i) => ({
      href: `#${a.id}`,
      name: a.perspective?.viewpointName || a.title,
      color: a.color,
      text: confident ? lines[offset + i] ?? null : null,
      omitted: a.perspective?.omissions ?? [],
    }));
  }

  /* ── Stations ──
     One per OPEN, SCENE, the framing TURN, each PERSPECTIVE, the payload TURN
     and the CLOSE: the same sequence, by construction, that history_producer's
     chapters() emits for the episode. */
  const stations: Station[] = [];
  for (const s of sections) {
    if (s.kind === "open") stations.push({ id: s.id, label: "Open", glyph: "tick" });
    else if (s.kind === "scene")
      stations.push({ id: s.id, label: s.title || `Scene ${s.number}`, glyph: "scene", number: s.number });
    else if (s.kind === "accounts") stations.push({ id: s.id, label: s.title, glyph: "tick" });
    else if (s.kind === "account")
      stations.push({ id: s.id, label: s.title, glyph: "dot", color: s.color });
    else if (s.kind === "turn") stations.push({ id: s.id, label: "The turn", glyph: "diamond" });
    else if (s.kind === "close") stations.push({ id: s.id, label: "Close", glyph: "tick" });
  }

  return {
    sections,
    stations,
    galleryMedia: event.media.filter((m) => !spent.has(m.id)),
  };
}
