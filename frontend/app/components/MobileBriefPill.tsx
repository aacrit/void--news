"use client";

import { useState, useRef, useEffect } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticLight, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   MobileBriefPill — Mobile-optimized skybox with TL;DR, Opinion, OnAir CTA

   Single-column stacked layout. Each section has independent "read more"
   expand/collapse. OnAir CTA triggers the persistent AudioPlayer.
   --------------------------------------------------------------------------- */

export default function MobileBriefPill({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, handlePlayPause, setExpanded, setPlayerVisible } = state;

  const [pillExpanded, setPillExpanded] = useState(false);
  const pillContentRef = useRef<HTMLDivElement>(null);
  const [pillContentHeight, setPillContentHeight] = useState(0);

  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);

  const tldrRef = useRef<HTMLDivElement>(null);
  const opinionRef = useRef<HTMLDivElement>(null);
  const [tldrHeight, setTldrHeight] = useState(0);
  const [opinionHeight, setOpinionHeight] = useState(0);

  useEffect(() => {
    if (!tldrRef.current) return;
    const ro = new ResizeObserver(([e]) => setTldrHeight(e.contentRect.height));
    ro.observe(tldrRef.current);
    return () => ro.disconnect();
  }, [tldrExpanded]);

  useEffect(() => {
    if (!opinionRef.current) return;
    const ro = new ResizeObserver(([e]) => setOpinionHeight(e.contentRect.height));
    ro.observe(opinionRef.current);
    return () => ro.disconnect();
  }, [opinionExpanded]);

  useEffect(() => {
    if (!pillContentRef.current) return;
    const ro = new ResizeObserver(([e]) => setPillContentHeight(e.contentRect.height));
    ro.observe(pillContentRef.current);
    return () => ro.disconnect();
  }, [pillExpanded, tldrExpanded, opinionExpanded]);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  const tldrSentences = brief.tldr_text.split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrPreview = tldrSentences.slice(0, 2).join(" ");
  const tldrRest = tldrSentences.slice(2).join(" ");
  const tldrHasMore = tldrRest.length > 0;

  const opinionSentences = brief.opinion_text
    ? brief.opinion_text.split(/(?<=[.!?])\s+/).filter(Boolean)
    : [];
  const opinionPreview = opinionSentences.slice(0, 2).join(" ");
  const opinionRest = opinionSentences.slice(2).join(" ");
  const opinionHasMore = opinionRest.length > 0;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right"
    : "skb-lean--center";

  const pillLabel = brief.tldr_headline || "Today\u2019s brief";

  return (
    <div className="mbp" role="complementary" aria-label="Daily Brief">
      {/* Collapsed pill */}
      <button
        className={`mbp__pill${pillExpanded ? " mbp__pill--open" : ""}`}
        onClick={() => { hapticLight(); setPillExpanded((v) => !v); }}
        type="button"
        aria-expanded={pillExpanded}
        aria-controls="mbp-content"
      >
        <ScaleIcon size={12} animation="idle" />
        <span className="mbp__pill-cmd">void --tl;dr</span>
        <span className="mbp__pill-sep" aria-hidden="true">&middot;</span>
        <span className="mbp__pill-label">{pillLabel}</span>
        <span className="mbp__pill-chevron" aria-hidden="true">&#9662;</span>
      </button>

      {/* Expandable content */}
      <div
        id="mbp-content"
        className="mbp__content"
        style={{
          height: pillExpanded ? pillContentHeight : 0,
          transition: pillExpanded
            ? "height 350ms var(--spring-snappy)"
            : "height 250ms var(--ease-out)",
        }}
      >
        <div ref={pillContentRef} className="mbp__content-inner">
          {/* TL;DR */}
          <section className="mbp__section" aria-label="void --tl;dr">
            <div className="mbp__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="mbp__cmd">void --tl;dr</span>
              {brief.created_at && <span className="mbp__time">{timeAgo(brief.created_at)}</span>}
            </div>
            {brief.tldr_headline && <h3 className="mbp__hl mbp__hl--tldr">{brief.tldr_headline}</h3>}
            <p className="mbp__preview mbp__preview--tldr">{tldrPreview}</p>
            <div className="mbp__expand" style={{
              height: tldrExpanded ? tldrHeight : 0,
              transition: tldrExpanded ? "height 350ms var(--spring-snappy)" : "height 200ms var(--ease-out)",
            }}>
              <div ref={tldrRef} className="mbp__expand-inner">
                <p className="mbp__expand-text mbp__expand-text--tldr">{tldrRest}</p>
              </div>
            </div>
            {tldrHasMore && (
              <button className="mbp__more" onClick={() => { hapticLight(); setTldrExpanded((v) => !v); }}
                type="button" aria-expanded={tldrExpanded}>{tldrExpanded ? "less" : "read more"}</button>
            )}
          </section>

          {brief.opinion_text && <hr className="mbp__rule" />}

          {/* Opinion */}
          {brief.opinion_text && (
            <section className="mbp__section" aria-label="void --opinion">
              <div className="mbp__label">
                <ScaleIcon size={12} animation="idle" />
                <span className="mbp__cmd">void --opinion</span>
                {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
              </div>
              {brief.opinion_headline && <h3 className="mbp__hl mbp__hl--opinion">{brief.opinion_headline}</h3>}
              <p className="mbp__preview mbp__preview--opinion">{opinionPreview}</p>
              <div className="mbp__expand" style={{
                height: opinionExpanded ? opinionHeight : 0,
                transition: opinionExpanded ? "height 350ms var(--spring-snappy)" : "height 200ms var(--ease-out)",
              }}>
                <div ref={opinionRef} className="mbp__expand-inner">
                  <p className="mbp__expand-text mbp__expand-text--opinion">{opinionRest}</p>
                </div>
              </div>
              {opinionHasMore && (
                <button className="mbp__more" onClick={() => { hapticLight(); setOpinionExpanded((v) => !v); }}
                  type="button" aria-expanded={opinionExpanded}>{opinionExpanded ? "less" : "read more"}</button>
              )}
            </section>
          )}

          {/* OnAir pill — always visible, triggers persistent AudioPlayer */}
          <div className="mbp__onair-zone">
            <hr className="mbp__rule" />
            <div className="mbp__onair-center">
              <button
                className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}`}
                onClick={() => {
                  hapticConfirm();
                  if (hasAudio) {
                    setPlayerVisible(true);
                    if (!isPlaying) handlePlayPause();
                    setExpanded(true);
                  }
                }}
                type="button"
                disabled={!hasAudio}
                aria-label={
                  !hasAudio ? "Audio broadcast unavailable"
                    : isPlaying ? "Open audio player" : "Play broadcast"
                }
                title={!hasAudio ? "Audio broadcast generates twice daily" : undefined}
              >
                <span className="skb__radio-waves" aria-hidden="true">
                  <span className="skb__radio-wave" />
                  <span className="skb__radio-wave" />
                  <span className="skb__radio-wave" />
                </span>
                {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
                <span className="skb__onair-label">void --onair</span>
                {hasAudio ? (
                  isPlaying ? (
                    <span className="skb__onair-dur">
                      {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                    </span>
                  ) : (
                    durationMin && <span className="skb__onair-dur">{durationMin} min</span>
                  )
                ) : (
                  <span className="skb__onair-dur">twice daily</span>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
