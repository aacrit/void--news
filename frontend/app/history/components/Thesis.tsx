import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import PrintMast from "../../components/PrintMast";
import type { HistoricalEvent, ConnectionType } from "../types";
import type {
  ThesisAdjudication, ThesisAnalysisBlock, ThesisBlock, ThesisContestedBlock, ThesisDoc,
  ThesisExhibitBlock, ThesisExtractRef, ThesisListBlock, ThesisParaBlock, ThesisPositionBlock,
  ThesisSection, ThesisSentence,
} from "../thesis";
import type { Station } from "../hearing";
import { HOOKS, CTAS } from "../hooks";
import EventHero, { HERO_ID } from "./EventHero";
import SpineRail from "./SpineRail";
import ThesisEpisode from "./ThesisEpisode";
import ThesisReturn from "./ThesisReturn";
import { FreeCopyLink, NoFreeCopy, SourceMark, isInsecureOrigin } from "./ThesisSourceLink";

/* ===========================================================================
   The Thesis — the History event page once its ledger clears the bar.

   The page is the rendering of the ledger (proposal §3, §7). Every factual
   sentence carries a note; a note names a source and a locator and links to
   the free copy; an exhibit prints the extract with its provenance first; a
   position prints its holders, what it rests on, what it claims, what it
   omits, and the verdict this thesis reached when it tested the claim against
   the primary record; an analysis prints its method, its rows and the result
   that recomputes from them. The historian's own sentences are marked.

   Server markup throughout, with the same three islands the Hearing has (the
   rail, the Listen button, and here the play glyph on an episode block).
   Nothing a reader reads needs JavaScript: the notes are anchors, the mobile
   note disclosure is a native <details>, the contested blocks are tables.

   Not rendered, deliberately: `significance` and `legacy_points` (the moral
   the format refuses), and the five YAML perspectives, which the positions
   replace (CEO decision 6).
   =========================================================================== */

const CONNECTION_PRIORITY: Record<ConnectionType, number> = {
  caused: 4, consequence: 3, "response-to": 3, influenced: 2, parallel: 1,
};
const CONNECTION_GLYPH: Record<ConnectionType, string> = {
  caused: "↓", consequence: "↑", "response-to": "↑", influenced: "·", parallel: "·",
};

/* A ledger names a producing body by an id (`uk-government`); the reader gets
   its name, which the exporter carries in `producerLabels` from
   data/history/producers.yaml. tests/test_history_thesis.py fails when a
   ledger uses an id with no label, so the fallback to the id is a guard, not
   a path a committed page takes. */
const producerName = (doc: ThesisDoc, p: string) => doc.producerLabels?.[p] ?? p;

const RENDERING_LABEL = {
  "official-parallel": "Official parallel text",
  "void-translation": "Void translation, not a published quotation",
};

/* Two inline markers the thesis writes: *emphasis* and nothing else. */
function inline(text: string): ReactNode[] {
  const parts = text.split(/(\*[^*]+\*)/g);
  return parts.map((p, i) =>
    p.startsWith("*") && p.endsWith("*") && p.length > 2 ? <em key={i}>{p.slice(1, -1)}</em> : <span key={i}>{p}</span>,
  );
}

const noteId = (n: number) => `n${n}`;
const refId = (n: number) => `ref${n}`;
const sidenoteId = (n: number) => `sn${n}`;

/* --------------------------------------------------------------------------
   Sentences and notes
   -------------------------------------------------------------------------- */

function Sentence({ s, doc }: { s: ThesisSentence; doc: ThesisDoc }) {
  return (
    <>
      <span className={s.interpretive ? "hist-th-i" : undefined} data-interpretive={s.interpretive ? "true" : undefined}>
        {inline(s.text)}
        {s.interpretive && <span className="sr-only"> (the reading of this thesis)</span>}
      </span>
      {s.notes.map((n) => {
        const note = doc.notes[n - 1];
        return (
          <sup key={n} className="hist-th-sup">
            <a
              href={`#${noteId(n)}`}
              id={refId(n)}
              className="hist-th-ref"
              aria-label={`Note ${n}: ${note?.short ?? ""}`}
              aria-describedby={sidenoteId(n)}
            >
              {n}
            </a>
          </sup>
        );
      })}{" "}
    </>
  );
}

/* A note's short form is "<work>, <locator>". The two are set apart on the
   page (the work, then the locator in the data voice), so the split is taken
   back off the short form only when the locator really is its tail. */
function splitCite(short: string, locator: string | null): [string, string | null] {
  if (locator && short.endsWith(`, ${locator}`)) return [short.slice(0, -(locator.length + 2)), locator];
  return [short, locator];
}

/* One citation, one structure everywhere it is printed: the work, then a row
   holding the locator and the actions (the exhibit, the free copy). */
function Cite({ short, locator, exhibit, freeCopy }: {
  short: string; locator: string | null; exhibit: number | null; freeCopy: string | null;
}) {
  const [title, loc] = splitCite(short, locator);
  return (
    <span className="hist-th-cite">
      <span className="hist-th-cite__title">{title}</span>
      <span className="hist-th-cite__meta">
        {loc && <span className="hist-th-cite__loc">{loc}</span>}
        {exhibit && (
          <a href={`#exhibit-${exhibit}`} className="hist-th-note__link">
            Exhibit {exhibit}
          </a>
        )}
        {freeCopy ? <FreeCopyLink href={freeCopy} name={title} /> : <NoFreeCopy />}
      </span>
    </span>
  );
}

function NoteBody({ n, doc }: { n: number; doc: ThesisDoc }) {
  const note = doc.notes[n - 1];
  if (!note) return null;
  return (
    <>
      <span className="hist-th-num">{n}</span>
      <Cite short={note.short} locator={note.locatorLabel} exhibit={note.exhibit} freeCopy={note.freeCopy} />
    </>
  );
}

function Para({ block, doc, className }: { block: ThesisParaBlock; doc: ThesisDoc; className?: string }) {
  const notes = block.sentences.flatMap((s) => s.notes);
  return (
    <div className={`hist-th-para${className ? ` ${className}` : ""}`}>
      {/* Desktop: the notes in the right margin, from the paragraph's first
          line. The aside comes BEFORE the text because it is a float: a float
          starts where it sits in the flow, so this is what puts it level with
          the paragraph, and a float is out of the flow, so a long run of notes
          runs on beside the next paragraphs instead of holding them down
          (history-thesis.css, "1280px and up"). */}
      {notes.length > 0 && (
        <aside className="hist-th-sidenotes" role="note" aria-label={`Notes ${notes[0]}${notes.length > 1 ? ` to ${notes[notes.length - 1]}` : ""}`}>
          <ol className="hist-th-sidenotes__list" start={notes[0]}>
            {notes.map((n) => (
              <li key={n} id={sidenoteId(n)} className="hist-th-sidenote" value={n}>
                <NoteBody n={n} doc={doc} />
              </li>
            ))}
          </ol>
        </aside>
      )}
      <p className="hist-th-p">
        {block.sentences.map((s, i) => (
          <Sentence key={i} s={s} doc={doc} />
        ))}
      </p>
      {notes.length > 0 && (
        /* Phone: the same notes, inline, under the paragraph, as a native disclosure. */
        <details className="hist-th-inline">
          <summary className="hist-th-inline__summary">
            {notes.length === 1 ? `Note ${notes[0]}` : `Notes ${notes[0]} to ${notes[notes.length - 1]}`}
          </summary>
          <ol className="hist-th-inline__list" start={notes[0]}>
            {notes.map((n) => (
              <li key={n} className="hist-th-inline__note" value={n}>
                <NoteBody n={n} doc={doc} />
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

/* --------------------------------------------------------------------------
   Extracts, exhibits, episodes
   -------------------------------------------------------------------------- */

function ExtractText({ x }: { x: ThesisExtractRef | ThesisExhibitBlock }) {
  const lang = "language" in x && x.language ? x.language : "en";
  return (
    <>
      <blockquote className="hist-th-extract" lang={lang} cite={x.url ?? undefined}>
        {x.text}
      </blockquote>
      {x.rendering && (
        <blockquote className={`hist-th-extract hist-th-extract--rendering hist-th-extract--${x.rendering.kind}`} lang="en">
          <span className="hist-th-extract__label">{RENDERING_LABEL[x.rendering.kind]}</span>
          {x.rendering.text}
        </blockquote>
      )}
    </>
  );
}

function Exhibit({ block }: { block: ThesisExhibitBlock }) {
  const isDoc = block.kind === "document";
  const eyebrow = [`Exhibit ${block.n}`, isDoc ? "Document" : block.kind === "map" ? "Map" : "Photograph",
    [block.creator, block.date].filter(Boolean).join(", ")].filter(Boolean);
  return (
    <figure className="hist-th-exhibit" id={`exhibit-${block.n}`} data-kind={block.kind}>
      <figcaption className="hist-th-exhibit__cap">
        <p className="hist-th-exhibit__eyebrow">
          {eyebrow.map((e, i) => (
            <span key={i}>{e}</span>
          ))}
        </p>
        <p className="hist-th-exhibit__title">{block.title}</p>
      </figcaption>
      {isDoc ? (
        <ExtractText x={block} />
      ) : (
        block.image && (
          <img className="hist-th-exhibit__img" src={block.image} alt={block.shows ?? block.title} loading="lazy" />
        )
      )}
      <div className="hist-th-exhibit__prov">
        <dl className="hist-th-prov">
          {isDoc && block.locatorLabel && (
            <div><dt>Locator</dt><dd>{block.locatorLabel}</dd></div>
          )}
          <div><dt>Held by</dt><dd>{block.repository}{block.accession ? `, ${block.accession}` : ""}</dd></div>
          <div><dt>Rights</dt><dd>{block.licence}</dd></div>
          {!isDoc && block.shows && (
            <div><dt>Shows</dt><dd>{block.shows}</dd></div>
          )}
          {!isDoc && block.doesNotShow && (
            <div><dt>Does not show</dt><dd>{block.doesNotShow}</dd></div>
          )}
          {isDoc && block.notes && block.notes.length > 0 && (
            <div><dt>Text layer</dt><dd>{block.notes.join("; ")}</dd></div>
          )}
        </dl>
        {block.url ? (
          <FreeCopyLink
            href={block.url}
            name={`Exhibit ${block.n}, ${block.title}`}
            label={isDoc ? undefined : `Open the file page of Exhibit ${block.n}, ${block.title}`}
            className="hist-th-exhibit__link"
          />
        ) : (
          isDoc && <NoFreeCopy />
        )}
      </div>
    </figure>
  );
}

/* --------------------------------------------------------------------------
   Analysis: the thesis's own finding, with its working
   -------------------------------------------------------------------------- */

function Analysis({ block, doc }: { block: ThesisAnalysisBlock; doc: ThesisDoc }) {
  const resultText = Array.isArray(block.result)
    ? block.result.map((v) => String(v)).join(" to ")
    : typeof block.result === "number" ? String(block.result) : String(block.result ?? "");
  return (
    <section className="hist-th-analysis" id={`analysis-${block.id}`} aria-labelledby={`analysis-${block.id}-h`}>
      <p className="hist-th-analysis__eyebrow">
        <span>Analysis</span>
        <span className="hist-th-analysis__own">The finding of this thesis, from the rows below</span>
      </p>
      <h4 id={`analysis-${block.id}-h`} className="hist-th-analysis__title">{block.title}</h4>
      <p className="hist-th-analysis__method"><span className="hist-th-label">Method</span> {block.method}</p>
      <div className="hist-th-tablewrap">
        <table className="hist-th-table">
          <caption className="sr-only">Rows the analysis is computed from, each traced to an extract</caption>
          <thead>
            <tr>
              {block.columns.map((c) => (
                <th key={c} scope="col">{c.replace(/_/g, " ")}</th>
              ))}
              <th scope="col">Extract</th>
            </tr>
          </thead>
          <tbody>
            {block.rows.map((r, i) => (
              <tr key={i}>
                {block.columns.map((c) => {
                  const v = r.cells[c] === null || r.cells[c] === undefined ? "" : String(r.cells[c]);
                  const label = c === "producer" ? doc.producerLabels?.[v] : undefined;
                  return (
                    <td key={c} className={c === "producer" && !label ? "hist-th-table__id" : undefined}>{label ?? v}</td>
                  );
                })}
                <td>
                  <a href={`#${noteId(r.note)}`} className="hist-th-ref hist-th-ref--cell" aria-label={`Note ${r.note}: ${r.short}, ${r.locatorLabel}`}>
                    {r.note}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hist-th-analysis__result"><span className="hist-th-label">Computed</span> over {block.rowCount} rows, {block.compute}; result {resultText}</p>
      <p className="hist-th-analysis__finding">{block.finding}</p>
      <p className="hist-th-analysis__confidence">
        <span className="hist-th-label">Confidence</span> {block.confidence}.{" "}
        <span className="hist-th-label">Against it</span> {block.against}
      </p>
      <span className="sr-only">{doc.slug}</span>
    </section>
  );
}

/* --------------------------------------------------------------------------
   Positions and their adjudication
   -------------------------------------------------------------------------- */

function Adjudication({ a, k, doc }: { a: ThesisAdjudication; k: number; doc: ThesisDoc }) {
  return (
    <li className="hist-th-verdict" data-verdict={a.verdict}>
      <p className="hist-th-verdict__claim">
        <span className="hist-th-verdict__chip">{a.verdictLabel}</span>
        <span className="hist-th-verdict__text">{a.claim}</span>
      </p>
      <p className="hist-th-verdict__basis">
        {a.basis === "absence" ? "Rests on an absence in the free record" : "Rests on documents from"}
        {a.basis === "presence" && a.producers.length > 0 && `: ${a.producers.map((p) => producerName(doc, p)).join("; ")}`}
        {a.oneSided && a.basis === "presence" && ". One producer, so the verdict is capped at qualified"}
        .
      </p>
      <p className="hist-th-verdict__reasoning">{a.reasoning}</p>
      {a.restsOn.length > 0 && (
        <details className="hist-th-verdict__extracts">
          <summary className="hist-th-verdict__summary">
            {a.restsOn.length === 1 ? "The extract it rests on" : `The ${a.restsOn.length} extracts it rests on`}
          </summary>
          <ol className="hist-th-verdict__list">
            {a.restsOn.map((x, i) => (
              <li key={`${k}-${i}`} className="hist-th-verdict__item">
                <p className="hist-th-verdict__cite">
                  <Cite short={x.short} locator={x.locatorLabel} exhibit={x.exhibit} freeCopy={x.freeCopy} />
                </p>
                <ExtractText x={x} />
              </li>
            ))}
          </ol>
        </details>
      )}
    </li>
  );
}

function Position({ block, doc }: { block: ThesisPositionBlock; doc: ThesisDoc }) {
  return (
    <article
      className="hist-th-position"
      id={`position-${block.id}`}
      style={{ "--hist-account-color": `var(--hist-persp-${block.color})` } as CSSProperties}
      aria-labelledby={`position-${block.id}-h`}
    >
      <h3 id={`position-${block.id}-h`} className="hist-th-position__name">
        <span className="hist-th-chip" aria-hidden="true" />
        {block.name}
      </h3>
      <dl className="hist-th-position__dl">
        <div>
          <dt>Holders</dt>
          <dd>{block.holders.join("; ")}</dd>
        </div>
        <div>
          <dt>Rests on</dt>
          <dd>
            <ul className="hist-th-position__sources">
              {block.restsOn.map((r) => (
                <li key={r.source}>
                  {r.freeCopy ? (
                    <a href={r.freeCopy} rel="noopener noreferrer" target="_blank" data-origin={isInsecureOrigin(r.freeCopy) ? "insecure" : undefined}>{r.short}</a>
                  ) : (
                    r.short
                  )}
                  <span className="hist-th-position__tag">Tier {r.tier}{r.byHolder ? ", by a holder" : ""}{!r.freeCopy ? ", not read free" : ""}</span>
                </li>
              ))}
            </ul>
          </dd>
        </div>
        <div>
          <dt>Claims</dt>
          <dd>{block.claim}</dd>
        </div>
        <div>
          <dt>Omits</dt>
          <dd>{block.omits}</dd>
        </div>
        {block.describedBy.length > 0 && (
          <div>
            <dt>As described by</dt>
            <dd>
              <ul className="hist-th-position__sources">
                {block.describedBy.map((x, i) => (
                  <li key={i}>
                    {x.freeCopy ? <a href={x.freeCopy} rel="noopener noreferrer" target="_blank" data-origin={isInsecureOrigin(x.freeCopy) ? "insecure" : undefined}>{x.short}</a> : x.short}
                    <span className="hist-th-position__tag">{x.locatorLabel}{x.exhibit ? `, exhibit ${x.exhibit}` : ""}</span>
                    <ExtractText x={x} />
                  </li>
                ))}
              </ul>
            </dd>
          </div>
        )}
      </dl>
      {block.adjudications.length > 0 && (
        <div className="hist-th-tested">
          <p className="hist-th-tested__label">Tested against the primary record</p>
          <ol className="hist-th-tested__list">
            {block.adjudications.map((a, i) => (
              <Adjudication key={i} a={a} k={i} doc={doc} />
            ))}
          </ol>
        </div>
      )}
    </article>
  );
}

function Contested({ block }: { block: ThesisContestedBlock }) {
  return (
    <div className="hist-th-tablewrap hist-th-contested" id={`contested-${block.id}`}>
      <table className="hist-th-table hist-th-table--contested">
        <caption className="hist-th-contested__caption">{block.claim}</caption>
        <thead>
          <tr>
            <th scope="col">Position</th>
            <th scope="col">Holds</th>
            <th scope="col">Rests on</th>
          </tr>
        </thead>
        <tbody>
          {block.rows.map((r, i) => (
            <tr key={i} style={{ "--hist-account-color": `var(--hist-persp-${r.color})` } as CSSProperties}>
              <th scope="row">
                <span className="hist-th-chip" aria-hidden="true" />
                <a href={`#position-${r.position}`} className="hist-th-contested__pos">{r.positionName ?? r.position}</a>
              </th>
              <td>{r.holds}</td>
              <td>
                <a href={`#${noteId(r.note)}`} className="hist-th-ref hist-th-ref--cell" aria-label={`Note ${r.note}: ${r.short}`}>{r.note}</a>{" "}
                <span className="hist-th-contested__cite">{r.short}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OmitsList({ block, doc }: { block: ThesisListBlock; doc: ThesisDoc }) {
  return (
    <ul className="hist-th-omits">
      {block.items.map((it, i) => (
        <li
          key={i}
          className="hist-th-omit"
          style={it.color ? ({ "--hist-account-color": `var(--hist-persp-${it.color})` } as CSSProperties) : undefined}
        >
          <span className="hist-omission-bullet--hollow" aria-hidden="true" />
          <span className="hist-th-omit__text">
            {it.sentences.map((s, j) => (
              <Sentence key={j} s={s} doc={doc} />
            ))}
            {it.against && (
              <a href={`#position-${it.against}`} className="hist-th-omit__against">
                cuts against {it.againstName ?? it.against}
              </a>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* --------------------------------------------------------------------------
   Sections
   -------------------------------------------------------------------------- */

interface AudioBits {
  id: string; title: string; subtitle: string; audioUrl: string | null;
  durationSeconds: number; chapters: NonNullable<HistoricalEvent["audioChapters"]> | null;
}

function Blocks({ blocks, doc, audio, paraClass }: { blocks: ThesisBlock[]; doc: ThesisDoc; audio: AudioBits; paraClass?: string }) {
  return (
    <>
      {blocks.map((b, i) => {
        switch (b.t) {
          case "para": return <Para key={i} block={b} doc={doc} className={paraClass} />;
          case "list": return <OmitsList key={i} block={b} doc={doc} />;
          case "exhibit": return <Exhibit key={i} block={b} />;
          case "episode": return (
            <ThesisEpisode key={i} chapter={b.chapter} title={b.title} kind={b.kind} startTime={b.startTime} lines={b.lines} event={audio} />
          );
          case "analysis": return <Analysis key={i} block={b} doc={doc} />;
          case "position": return <Position key={i} block={b} doc={doc} />;
          case "contested": return <Contested key={i} block={b} />;
          default: return null;
        }
      })}
    </>
  );
}

function Record({ section, doc, audio }: { section: ThesisSection; doc: ThesisDoc; audio: AudioBits }) {
  const st = doc.standing;
  return (
    <section id="record" className="hist-th-section hist-th-record" aria-labelledby="record-h">
      <h2 id="record-h" className="hist-th-h2">{section.title}</h2>
      <Blocks blocks={section.blocks} doc={doc} audio={audio} />
      <dl className="hist-th-standing" aria-label="What this thesis holds">
        <div><dt>Primary documents held with extracts</dt><dd>{st.tier_a_with_extract} of {st.tier_a}</dd></div>
        <div><dt>Scholarship verified to exist as named</dt><dd>{st.tier_b_verified} of {st.tier_b}</dd></div>
        <div><dt>Of which read at a free copy and pinned</dt><dd>{st.tier_b_pinned}</dd></div>
        <div><dt>Positions, each with a source by a holder</dt><dd>{st.positions_with_holder_source} of {st.positions}</dd></div>
        <div><dt>Sources from the region or in its languages</dt><dd>{st.regional}</dd></div>
        <div><dt>Exhibits with full provenance</dt><dd>{st.exhibits}</dd></div>
        <div><dt>Findings of this thesis, with their working</dt><dd>{st.analyses}</dd></div>
        <div><dt>Extracts stored verbatim</dt><dd>{st.extracts}</dd></div>
      </dl>
      {doc.regionalSourcesNote && <p className="hist-th-p hist-th-p--note">{doc.regionalSourcesNote}</p>}
      {doc.gaps.length > 0 && (
        <div className="hist-th-gaps">
          <h3 className="hist-th-h3 hist-th-h3--quiet">What the free record could not reach</h3>
          <ul className="hist-th-gaps__list">
            {doc.gaps.map((g, i) => (
              <li key={i} className="hist-th-gap">
                <span className="hist-th-gap__what">{g.what}</span>
                <span className="hist-th-gap__status">{g.status}</span>
                {g.tried.length > 0 && (
                  <span className="hist-th-gap__tried">
                    <span className="hist-th-label">Tried</span>
                    {g.tried.map((u, j) => (
                      <a key={j} href={u} rel="noopener noreferrer" target="_blank" className="hist-th-gap__url">{new URL(u).hostname}</a>
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Section({ section, doc, audio }: { section: ThesisSection; doc: ThesisDoc; audio: AudioBits }) {
  switch (section.kind) {
    case "question":
      return (
        <section id="question" className="hist-th-section hist-th-question" aria-labelledby="question-h">
          <h2 id="question-h" className="hist-th-h2">{section.title}</h2>
          {/* The one question the thesis asks, from its front matter, before
              the paragraphs that earn it. TH-01 asserts it is on the page. */}
          <p className="hist-th-question__ask">{doc.question}</p>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} paraClass="hist-th-para--editorial" />
          {doc.claims.length > 0 && (
            <ol className="hist-th-claims" aria-label="The claims this thesis makes">
              {doc.claims.map((c, i) => (
                <li key={i} className="hist-th-claim">
                  <span className="hist-th-num">{i + 1}</span>
                  <span className="hist-th-claim__text">{c}</span>
                </li>
              ))}
            </ol>
          )}
          <p className="hist-th-key">
            <span className="hist-th-key__item"><span className="hist-th-i hist-th-key__swatch">Shaded</span> sentences are the reading of this thesis</span>
          </p>
        </section>
      );
    case "event":
      return (
        <section id="event" className="hist-th-section hist-th-argument-head hist-th-event-head" aria-labelledby="event-h">
          <h2 id="event-h" className="hist-th-h2">{section.title}</h2>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    case "event-section":
      return (
        <section id={section.id} className="hist-th-section hist-th-argument hist-th-event" aria-labelledby={`${section.id}-h`}>
          <h3 id={`${section.id}-h`} className="hist-th-h3">
            <span className="hist-th-h3__num">{section.number}</span>
            <span className="hist-th-h3__title">{section.title.replace(/^\d+\.\s*/, "")}</span>
          </h3>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    case "record":
      return <Record section={section} doc={doc} audio={audio} />;
    case "argument":
      return (
        <section id="argument" className="hist-th-section hist-th-argument-head" aria-labelledby="argument-h">
          <h2 id="argument-h" className="hist-th-h2">{section.title}</h2>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    case "argument-section":
      return (
        <section id={section.id} className="hist-th-section hist-th-argument" aria-labelledby={`${section.id}-h`}>
          <h3 id={`${section.id}-h`} className="hist-th-h3">
            <span className="hist-th-h3__num">{section.number}</span>
            <span className="hist-th-h3__title">{section.title.replace(/^\d+\.\s*/, "")}</span>
          </h3>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    case "historiography":
      return (
        <section id="historiography" className="hist-th-section hist-th-historiography" aria-labelledby="historiography-h">
          <h2 id="historiography-h" className="hist-th-h2">{section.title}</h2>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    case "contested":
      return (
        <section id="disagreements" className="hist-th-section hist-th-disagreements" aria-labelledby="disagreements-h">
          <h3 id="disagreements-h" className="hist-th-h3 hist-th-h3--plain">{section.title}</h3>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    case "omits":
      return (
        <section id="omits" className="hist-th-section hist-th-omits-section" aria-labelledby="omits-h">
          <h2 id="omits-h" className="hist-th-h2">{section.title}</h2>
          <p className="hist-th-p hist-th-p--quiet">Statements about this ledger, not about the world. Each is attached to the position it cuts against.</p>
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
    default:
      return (
        <section id={section.id} className="hist-th-section" aria-labelledby={`${section.id}-h`}>
          {section.level === 2
            ? <h2 id={`${section.id}-h`} className="hist-th-h2">{section.title}</h2>
            : <h3 id={`${section.id}-h`} className="hist-th-h3 hist-th-h3--plain">{section.title}</h3>}
          <Blocks blocks={section.blocks} doc={doc} audio={audio} />
        </section>
      );
  }
}

/* --------------------------------------------------------------------------
   The page
   -------------------------------------------------------------------------- */

interface ThesisProps {
  event: HistoricalEvent;
  doc: ThesisDoc;
  nextEvent: { slug: string; title: string } | null;
}

export function thesisStations(doc: ThesisDoc): Station[] {
  const out: Station[] = [];
  /* A holistic thesis (§15) has two numbered runs: the event's sections carry
     the scene numbers, and the contested questions take the diamond the turn
     wears, so the rail never shows two stations numbered 1. */
  const holistic = doc.sections.some((s) => s.kind === "event-section");
  for (const s of doc.sections) {
    if (s.kind === "question") out.push({ id: "question", label: "The question", glyph: "tick" });
    else if (s.kind === "event") out.push({ id: "event", label: s.title, glyph: "tick" });
    else if (s.kind === "event-section" && s.number !== null)
      out.push({ id: s.id, label: s.title.replace(/^\d+\.\s*/, ""), glyph: "scene", number: s.number });
    else if (s.kind === "record") out.push({ id: "record", label: "The record", glyph: "tick" });
    else if (s.kind === "argument" && holistic) out.push({ id: "argument", label: s.title, glyph: "tick" });
    else if (s.kind === "argument-section" && s.number !== null && holistic)
      out.push({ id: s.id, label: s.title.replace(/^\d+\.\s*/, ""), glyph: "diamond" });
    else if (s.kind === "argument-section" && s.number !== null)
      out.push({ id: s.id, label: s.title.replace(/^\d+\.\s*/, ""), glyph: "scene", number: s.number });
    else if (s.kind === "historiography") out.push({ id: "historiography", label: "The historiography", glyph: "tick" });
    else if (s.kind === "contested") out.push({ id: "disagreements", label: "Where the record disagrees", glyph: "diamond" });
    else if (s.kind === "omits") out.push({ id: "omits", label: "What the record omits", glyph: "tick" });
  }
  out.push({ id: "notes", label: "Notes", glyph: "tick" });
  out.push({ id: "sources", label: "Sources", glyph: "tick" });
  return out;
}

export default function Thesis({ event, doc, nextEvent }: ThesisProps) {
  const audio: AudioBits = {
    id: event.id, title: event.title, subtitle: event.subtitle, audioUrl: event.audioUrl ?? null,
    durationSeconds: event.audioDuration ?? 0, chapters: event.audioChapters ?? null,
  };
  const stations = thesisStations(doc);
  const threads = [...event.connections]
    .sort((a, b) => (CONNECTION_PRIORITY[b.type] ?? 0) - (CONNECTION_PRIORITY[a.type] ?? 0))
    .slice(0, 3);
  /* Grid children of the spine: the body (every section of the thesis, in
     one box so a run of sidenotes can carry on past a section's end), notes,
     sources, the end matter. */
  const rows = 4;

  return (
    <div className="hist-event-detail hist-hearing-page hist-thesis-page" data-thesis={doc.status}>
      <PrintMast path={`/history/${event.slug}/`} />
      <EventHero event={event} />

      <div className="hist-hearing hist-th">
        <div className="hist-rail-slot" style={{ "--hist-rail-span": rows } as CSSProperties}>
          <SpineRail stations={stations} heroId={HERO_ID} />
        </div>

        <div className="hist-th-body">
          {doc.sections.map((s) => (
            <Section key={s.id} section={s} doc={doc} audio={audio} />
          ))}
        </div>

        {/* ── NOTES ── */}
        <section id="notes" className="hist-th-section hist-th-notes" aria-labelledby="notes-h">
          <h2 id="notes-h" className="hist-th-h2">Notes</h2>
          <ol className="hist-th-notes__list">
            {doc.notes.map((n) => (
              <li key={n.n} id={noteId(n.n)} className="hist-th-note" value={n.n}>
                <NoteBody n={n.n} doc={doc} />
              </li>
            ))}
          </ol>
        </section>

        {/* ── SOURCES: the ledger as a bibliography, verified entries only ── */}
        <section id="sources" className="hist-th-section hist-th-sources" aria-labelledby="sources-h">
          <h2 id="sources-h" className="hist-th-h2">Sources</h2>
          <p className="hist-th-p hist-th-p--quiet">Only entries verified to exist as named are printed. An entry with a free copy links to it; an entry read at that copy is marked as held.</p>
          <p className="hist-th-key">
            <span className="hist-th-key__item"><SourceMark /> opens the free copy in a new tab</span>
            <span className="hist-th-key__item"><SourceMark struck /> no free copy was found</span>
          </p>
          {doc.sources.map((tier) => (
            <div key={tier.tier} className="hist-th-tier">
              <h3 className="hist-th-h3 hist-th-h3--plain">
                <span className="hist-th-tier__letter">{tier.tier}</span> {tier.name}
              </h3>
              <ol className="hist-th-tier__list">
                {tier.entries.map((e) => (
                  <li key={e.id} id={`src-${e.id}`} className="hist-th-source">
                    <span className="hist-th-source__cite">{e.citation}</span>
                    <span className="hist-th-cite__meta hist-th-source__meta">
                      {e.language !== "en" && <span>In {e.language.toUpperCase()}</span>}
                      {e.pinned && <span>Held as extracts</span>}
                      {e.verifiedAt && <span>Verified {e.verifiedAt}</span>}
                      {e.freeCopy ? (
                        <FreeCopyLink href={e.freeCopy} name={e.citation} className="hist-th-source__link" />
                      ) : (
                        <NoFreeCopy />
                      )}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </section>

        {/* ── THE EVENT: end matter kept from the Hearing ── */}
        <section className="hist-record hist-th-endmatter" aria-labelledby="hist-record-h">
          <h2 id="hist-record-h" className="hist-record__label">The event</h2>
          {event.keyFigures.length > 0 && (
            <div className="hist-record__block">
              <h3 className="hist-record__subhead">Key figures</h3>
              <ul className="hist-record__figures">
                {event.keyFigures.map((f) => (
                  <li key={f.name} className="hist-record__figure">
                    <span className="hist-record__figure-name">{f.name}</span>
                    <span className="hist-record__figure-role">{f.role}</span>
                    {(f.born || f.died) && (
                      <span className="hist-record__figure-years">{f.born ?? "?"} to {f.died ?? "?"}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {threads.length > 0 && (
            <div className="hist-record__block">
              <h3 className="hist-record__subhead">Threads</h3>
              <ul className="hist-record__threads">
                {threads.map((c) => (
                  <li key={c.targetSlug}>
                    <Link href={`/history/${c.targetSlug}`} className="hist-record__thread">
                      <span className="hist-record__thread-glyph" aria-hidden="true">{CONNECTION_GLYPH[c.type] ?? "·"}</span>
                      <span className="hist-record__thread-title">{c.targetTitle}</span>
                      <span className="hist-record__thread-hook">{HOOKS[c.targetSlug] || c.description}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="hist-record__exits">
            {nextEvent && (
              <Link href={`/history/${nextEvent.slug}`} className="hist-record__next">
                {CTAS[nextEvent.slug] || `Next: ${nextEvent.title}`} →
              </Link>
            )}
            <Link href="/history" className="hist-record__archive">Return to The Archive</Link>
          </div>
        </section>
      </div>
      <ThesisReturn />
    </div>
  );
}
