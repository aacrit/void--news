"use client";

import { useState, useRef, useEffect } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

const PlayIcon = () => (
  <svg width="11" height="13" viewBox="0 0 11 13" fill="currentColor" aria-hidden="true">
    <path d="M1 1.5v10l9-5z" />
  </svg>
);

const PauseIcon = () => (
  <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="2.5" height="10" rx="0.5" />
    <rect x="6.5" y="1" width="2.5" height="10" rx="0.5" />
  </svg>
);

export default function MobileBriefPill({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, handlePlayPause,
    isPlayerVisible, setPlayerVisible,
  } = state;

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

  if (!brief) return (
    <div className="mbp" role="complementary" aria-label="Daily Brief">
      <div className="mbp__pill">
        <ScaleIcon size={16} animation="analyzing" />
        <span className="mbp__pill-cmd">void --tl;dr</span>
        <span className="mbp__pill-sep" aria-hidden="true">&middot;</span>
        <span className="mbp__pill-label" style={{ opacity: 0.4 }}>Loading&hellip;</span>
      </div>
    </div>
  );

  const hasAudio = !!brief.audio_url;

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

  // OnAir: trigger floating player
  const handleOnairClick = () => {
    hapticConfirm();
    setPlayerVisible(true);
    if (!isPlaying) handlePlayPause();
  };

  return (
    <div className="mbp" role="complementary" aria-label="Daily Brief">
      <div className={`mbp__pill${pillExpanded ? " mbp__pill--open" : ""}`}>
        <button
          className="mbp__pill-main"
          onClick={() => { hapticLight(); setPillExpanded((v) => !v); }}
          type="button" aria-expanded={pillExpanded} aria-controls="mbp-content"
        >
          <LogoIcon size={14} animation="idle" />
          <span className="mbp__pill-cmd">void --tl;dr</span>
          <span className="mbp__pill-sep" aria-hidden="true">&middot;</span>
          <span className="mbp__pill-label">{pillLabel}</span>
        </button>
        {hasAudio && !pillExpanded && (
          <button
            className="mbp__onair-play"
            onClick={(e) => { e.stopPropagation(); handleOnairClick(); }}
            type="button"
            aria-label={isPlaying ? "Now playing" : "Play broadcast"}
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>
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
              <LogoIcon size={14} animation="idle" />
              <span className="mbp__label-human">News Brief</span>
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
                <LogoIcon size={14} animation="idle" />
                <span className="mbp__label-human">Editorial</span>
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

          {/* OnAir removed — handled by FloatingPlayer */}
        </div>
      </div>
    </div>
  );
}
