"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticLight, hapticMedium, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export default function MobileBriefPill({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered,
    audioCallbackRef, handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
  } = state;

  const [pillExpanded, setPillExpanded] = useState(false);
  const pillContentRef = useRef<HTMLDivElement>(null);
  const [pillContentHeight, setPillContentHeight] = useState(0);
  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);
  const [radioOpen, setRadioOpen] = useState(false);

  const tldrRef = useRef<HTMLDivElement>(null);
  const opinionRef = useRef<HTMLDivElement>(null);
  const radioRef = useRef<HTMLDivElement>(null);
  const [tldrHeight, setTldrHeight] = useState(0);
  const [opinionHeight, setOpinionHeight] = useState(0);
  const [radioHeight, setRadioHeight] = useState(0);

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
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([e]) => {
      const h = e.borderBoxSize?.[0]?.blockSize ?? e.target.getBoundingClientRect().height;
      setRadioHeight(h);
    });
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [radioOpen]);

  useEffect(() => {
    if (!pillContentRef.current) return;
    const ro = new ResizeObserver(([e]) => setPillContentHeight(e.contentRect.height));
    ro.observe(pillContentRef.current);
    return () => ro.disconnect();
  }, [pillExpanded, tldrExpanded, opinionExpanded, radioOpen]);

  const waveformBars = useMemo(() =>
    Array.from({ length: 20 }, (_, i) => 8 + Math.sin(i * 0.65) * 14 + Math.sin(i * 1.3) * 5),
  []);

  if (!brief) return (
    <div className="mbp" role="complementary" aria-label="Daily Brief">
      <div className="mbp__pill">
        <ScaleIcon size={12} animation="analyzing" />
        <span className="mbp__pill-cmd">void --tl;dr</span>
        <span className="mbp__pill-sep" aria-hidden="true">&middot;</span>
        <span className="mbp__pill-label" style={{ opacity: 0.4 }}>Loading&hellip;</span>
      </div>
    </div>
  );

  const hasAudio = !!brief.audio_url;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;
  const speedLabel = `${playbackSpeed}x`;

  const effectiveOpinionStart = brief.opinion_start_seconds ?? (brief.opinion_text ? displayDuration * 0.6 : null);
  const hasOpinionSection = brief.opinion_text != null;
  const opinionPct = brief.opinion_start_seconds != null && displayDuration > 0
    ? (brief.opinion_start_seconds / displayDuration) * 100
    : hasOpinionSection ? 60 : 100;
  const inOpinion = hasOpinionSection && effectiveOpinionStart !== null && currentTime >= effectiveOpinionStart;

  const tldrSentences = brief.tldr_text.split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrPreview = tldrSentences.slice(0, 2).join(" ");
  const tldrRest = tldrSentences.slice(2).join(" ");
  const tldrHasMore = tldrRest.length > 0;

  const opinionSentences = brief.opinion_text ? brief.opinion_text.split(/(?<=[.!?])\s+/).filter(Boolean) : [];
  const opinionPreview = opinionSentences.slice(0, 2).join(" ");
  const opinionRest = opinionSentences.slice(2).join(" ");
  const opinionHasMore = opinionRest.length > 0;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const pillLabel = brief.tldr_headline || "Today\u2019s brief";

  return (
    <div className="mbp" role="complementary" aria-label="Daily Brief">
      {hasAudio && <audio id="void-onair-audio" ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />}

      <div className={`mbp__pill${pillExpanded ? " mbp__pill--open" : ""}`}>
        <button
          className="mbp__pill-main"
          onClick={() => { hapticLight(); setPillExpanded((v) => !v); }}
          type="button" aria-expanded={pillExpanded} aria-controls="mbp-content"
        >
          <ScaleIcon size={12} animation="idle" />
          <span className="mbp__pill-cmd">void --tl;dr</span>
          <span className="mbp__pill-sep" aria-hidden="true">&middot;</span>
          <span className="mbp__pill-label">{pillLabel}</span>
        </button>
        {hasAudio && !pillExpanded && (
          <button
            className="mbp__onair-play"
            onClick={(e) => { e.stopPropagation(); hapticConfirm(); handlePlayPause(); }}
            type="button"
            aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
          >
            <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
          </button>
        )}
        {hasAudio && !pillExpanded && durationMin && !isPlaying && (
          <span className="mbp__onair-dur">{durationMin}m</span>
        )}
        <button
          className="mbp__pill-chevron-btn"
          onClick={() => { hapticLight(); setPillExpanded((v) => !v); }}
          type="button" aria-expanded={pillExpanded} aria-label={pillExpanded ? "Collapse brief" : "Expand brief"}
        >
          <span className="mbp__pill-chevron" aria-hidden="true">&#9662;</span>
        </button>
      </div>

      <div id="mbp-content" className="mbp__content" style={{
        height: pillExpanded ? pillContentHeight : 0,
        transition: pillExpanded ? "height 350ms var(--spring-snappy)" : "height 250ms var(--ease-out)",
      }}>
        <div ref={pillContentRef} className="mbp__content-inner">
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
                type="button" aria-expanded={tldrExpanded}>{tldrExpanded ? "Less" : "Read more"}</button>
            )}
          </section>

          {brief.opinion_text && <hr className="mbp__rule" />}

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
                  type="button" aria-expanded={opinionExpanded}>{opinionExpanded ? "Less" : "Read more"}</button>
              )}
            </section>
          )}

          {/* OnAir pill + expanding player */}
          <div className="mbp__onair-zone">
            <hr className="mbp__rule" />
            <div className="mbp__onair-center">
              <button
                className={`skb__onair-pill${isPlaying ? " skb__onair-pill--active" : ""}${radioOpen ? " skb__onair-pill--open" : ""}`}
                onClick={() => {
                  hapticConfirm();
                  if (!hasAudio) return;
                  setRadioOpen((v) => !v);
                  if (!isPlaying && !radioOpen) handlePlayPause();
                }}
                type="button"
                aria-label={radioOpen ? "Close player" : hasAudio ? "Play broadcast" : "Audio unavailable"}
                aria-expanded={radioOpen}
              >
                {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
                <ScaleIcon size={12} animation={isPlaying ? "analyzing" : "idle"} />
                <span className="skb__onair-label">void --onair</span>
                {hasAudio ? (
                  isPlaying ? (
                    <span className="skb__onair-dur">{formatTime(currentTime)} / {formatTime(displayDuration || 0)}</span>
                  ) : (
                    durationMin && <span className="skb__onair-dur">{durationMin} min</span>
                  )
                ) : (
                  <span className="skb__onair-dur">twice daily</span>
                )}
              </button>

              {/* eslint-disable-next-line react/no-unknown-property */}
              <div className="skb__radio" inert={!radioOpen ? true : undefined} style={{
                height: radioOpen ? radioHeight : 0,
                transition: radioOpen ? "height 400ms var(--spring-bouncy, ease)" : "height 250ms var(--ease-out, ease)",
              }}>
                <div ref={radioRef} className={`skb__radio-inner${isPlaying ? " skb__radio-inner--live" : ""}`}>
                  <div className={`skb__waveform${isPlaying ? " skb__waveform--active" : ""}`} aria-hidden="true">
                    {waveformBars.map((h, i) => (
                      <div key={i} className="skb__waveform-bar" style={{ height: `${h}px`, animationDelay: `${i * 55}ms` }} />
                    ))}
                  </div>
                  <div className="skb__transport">
                    <button className="skb__transport-skip" onClick={() => skipBackward()} type="button" aria-label="Back 15s">-15</button>
                    <button className={`skb__transport-play${isPlaying ? " skb__transport-play--active" : ""}`}
                      onClick={() => { hapticMedium(); handlePlayPause(); }} type="button"
                      aria-label={isPlaying ? "Pause" : "Play"}>
                      <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                    </button>
                    <button className="skb__transport-skip" onClick={() => skipForward()} type="button" aria-label="Forward 15s">+15</button>
                  </div>
                  <div className="skb__radio-controls">
                    <div className="skb__radio-sections">
                      <button className={`skb__radio-sec${!inOpinion ? " skb__radio-sec--active" : ""}`}
                        onClick={() => seekTo(0)} type="button">News</button>
                      {hasOpinionSection && (
                        <button className={`skb__radio-sec${inOpinion ? " skb__radio-sec--active" : ""}`}
                          onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
                          type="button">Opinion</button>
                      )}
                    </div>
                    <button className="skb__radio-speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                      type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
                  </div>
                  <div className="skb__radio-bar-wrap">
                    <div className="skb__radio-bar">
                      <div className="skb__radio-buffer" style={{ width: `${buffered}%` }} />
                      <div className="skb__radio-fill" style={{ width: `${progress}%` }} />
                      {hasOpinionSection && <span className="skb__radio-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
                    </div>
                    <input type="range" className="skb__radio-input" min={0} max={displayDuration || 100}
                      value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek"
                      aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`} />
                  </div>
                  <div className="skb__radio-time">{formatTime(currentTime)} / {formatTime(displayDuration || 0)}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
