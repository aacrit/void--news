"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import { useAudio } from "../components/AudioProvider";
import OnAirPanel from "../components/OnAirPanel";
import { episodeFromBrief, type HistoryAudioPayload, type ProgrammeKind } from "../lib/episode";
import type { WeeklyDigestData } from "../lib/types";
import AudioPlay from "./AudioPlay";
import { NEW_RECORDING_LABEL } from "../history/edition";

/* ---------------------------------------------------------------------------
   AudioPortal: /audio is the player (CEO 2026-10-03).

   The page used to be a listing of three programmes with a Play button each,
   and the console a reader actually listens in lived only in the sidebar.
   Now a reader lands on that console. Above it, a switch between the three
   programmes; under it, the chosen programme's episodes.

   The switch CHOOSES WHAT IS LISTED; it never touches the element. Playing
   is always a press on an episode's own button, which calls the provider's
   play(ep): the one rule every play button in the product follows. On
   arrival with nothing loaded, today's On Air is offered to the idle player
   (load, never play, never interrupt), so the console is never empty.
   --------------------------------------------------------------------------- */

export interface PortalHistoryEpisode extends HistoryAudioPayload {
  slug: string;
  chapterCount: number;
  clock: string;
  /** A first-listener edition (manifest `edition`). */
  newRecording: boolean;
}

export interface PortalIssue {
  issue: WeeklyDigestData;
  label: string;
  dateline: string;
  clock: string | null;
}

interface Props {
  daily: { headline: string | null; dateline: string; clock: string } | null;
  issues: PortalIssue[];
  /** The latest issue's recording was withdrawn by a correction. */
  withdrawnLabel: string | null;
  history: PortalHistoryEpisode[];
}

const PROGRAMMES: { kind: ProgrammeKind; name: string; cadence: string }[] = [
  { kind: "daily", name: "On Air", cadence: "Daily" },
  { kind: "weekly", name: "The Argument", cadence: "Sundays" },
  { kind: "history", name: "History", cadence: "One event per episode" },
];

export default function AudioPortal({ daily, issues, withdrawnLabel, history }: Props) {
  const a = useAudio();
  const [chosen, setChosen] = useState<ProgrammeKind | null>(null);
  const offered = useRef(false);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  /* The sidebar's dialog form stands down here; close it if it was open. */
  useEffect(() => {
    if (a.isPanelOpen) a.setPanelOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Offer today's programme to an idle player, once. */
  useEffect(() => {
    if (offered.current || a.nowPlaying || !a.brief) return;
    const ep = episodeFromBrief(a.brief);
    if (!ep) return;
    offered.current = true;
    a.load(ep);
  }, [a, a.brief, a.nowPlaying]);

  const selected: ProgrammeKind = chosen ?? a.nowPlaying?.kind ?? "daily";
  const index = PROGRAMMES.findIndex((p) => p.kind === selected);

  const onTabKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    const to = e.key === "Home" ? 0 : e.key === "End" ? PROGRAMMES.length - 1
      : step ? (index + step + PROGRAMMES.length) % PROGRAMMES.length : -1;
    if (to < 0) return;
    e.preventDefault();
    setChosen(PROGRAMMES[to].kind);
    tabRefs.current[to]?.focus();
  };

  const latest: Record<ProgrammeKind, string | null> = {
    daily: daily?.headline ?? null,
    weekly: issues[0]?.issue.cover_headline ?? null,
    history: history[0]?.title ?? null,
  };

  return (
    <div className="audio-portal">
      <div className="audio-switch" role="tablist" aria-label="Programmes">
        {PROGRAMMES.map((p, i) => {
          const on = p.kind === selected;
          return (
            <button
              key={p.kind}
              ref={(el) => { tabRefs.current[i] = el; }}
              type="button"
              role="tab"
              id={`audio-tab-${p.kind}`}
              aria-selected={on}
              aria-controls={`audio-panel-${p.kind}`}
              tabIndex={on ? 0 : -1}
              data-programme={p.kind}
              className={`audio-switch__tab${on ? " audio-switch__tab--on" : ""}${a.nowPlaying?.kind === p.kind && a.isPlaying ? " audio-switch__tab--live" : ""}`}
              onClick={() => setChosen(p.kind)}
              onKeyDown={onTabKey}
            >
              <span className="audio-switch__name">{p.name}</span>
              <span className="audio-switch__cadence">{p.cadence}</span>
              {latest[p.kind] && <span className="audio-switch__latest">{latest[p.kind]}</span>}
            </button>
          );
        })}
      </div>

      <section
        role="tabpanel"
        id="audio-panel-daily"
        aria-labelledby="audio-tab-daily"
        hidden={selected !== "daily"}
        className="audio-prog audio-prog--onair"
      >
        {daily ? (
          <div className="audio-row">
            <div className="audio-row__text">
              <span className="audio-row__title">{daily.headline ?? "Today's programme"}</span>
              <span className="audio-row__meta">{daily.dateline} · {daily.clock}</span>
            </div>
            <AudioPlay kind="daily" label="Play today's programme" compact />
          </div>
        ) : (
          <p className="audio-prog__line">No programme has been published yet.</p>
        )}
        <p className="audio-prog__note">Earlier editions are under Previous episodes in the player.</p>
      </section>

      <section
        role="tabpanel"
        id="audio-panel-weekly"
        aria-labelledby="audio-tab-weekly"
        hidden={selected !== "weekly"}
        className="audio-prog audio-prog--argument"
      >
        {withdrawnLabel && (
          <p className="audio-prog__line" data-weekly-audio="withdrawn">
            The recording of {withdrawnLabel} was withdrawn after a correction.{" "}
            <Link href="/weekly#corrections" className="audio-prog__open">Read the correction</Link>
          </p>
        )}
        {issues.length > 0 ? (
          <ol className="audio-list">
            {issues.map((it) => (
              <li key={it.issue.id} className="audio-row">
                <div className="audio-row__text">
                  <span className="audio-row__title">{it.issue.cover_headline}</span>
                  <span className="audio-row__meta">
                    {it.label} · {it.dateline}{it.clock ? ` · ${it.clock}` : ""}
                  </span>
                </div>
                <AudioPlay kind="weekly" label={`Play ${it.label}`} compact issue={it.issue} />
              </li>
            ))}
          </ol>
        ) : withdrawnLabel ? null : (
          <p className="audio-prog__line">No recording is published.</p>
        )}
      </section>

      <section
        role="tabpanel"
        id="audio-panel-history"
        aria-labelledby="audio-tab-history"
        hidden={selected !== "history"}
        className="audio-prog audio-prog--history"
      >
        <p className="audio-prog__note">{history.length} episodes, newest first.</p>
        <ol className="audio-episodes">
          {history.map((e) => (
            <li key={e.slug} className="audio-episode">
              <div className="audio-episode__text">
                <Link href={`/history/${e.slug}`} className="audio-episode__title">{e.title}</Link>
                <span className="audio-episode__meta">
                  {e.clock}{e.chapterCount ? ` · ${e.chapterCount} chapters` : ""}
                  {e.newRecording ? ` · ${NEW_RECORDING_LABEL}` : ""}
                </span>
              </div>
              <AudioPlay kind="history" label={`Play ${e.title}`} compact payload={e} />
            </li>
          ))}
        </ol>
      </section>

      {/* After the lists in the DOM, so on a phone the chosen programme's
          episodes sit right under the switch; from 1024px the grid sets the
          console on the left and the list beside it. */}
      <div className="audio-console">
        {a.nowPlaying ? (
          <OnAirPanel inline />
        ) : (
          <p className="audio-console__idle">Nothing is loaded. Choose an episode above.</p>
        )}
      </div>
    </div>
  );
}
