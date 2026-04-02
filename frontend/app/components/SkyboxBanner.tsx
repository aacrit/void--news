"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { DailyBriefState } from "./DailyBrief";
import LogoIcon from "./LogoIcon";
import { hapticLight } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

type ExpandedSection = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief } = state;

  const [expandedSection, setExpandedSection] = useState<ExpandedSection>(null);
  const [announcement, setAnnouncement] = useState("");

  // Focus management refs
  const collapseRef = useRef<HTMLButtonElement>(null);
  const expandTldrRef = useRef<HTMLButtonElement>(null);
  const expandOpinionRef = useRef<HTMLButtonElement>(null);
  const prevSectionRef = useRef<ExpandedSection>(null);

  useEffect(() => {
    const prev = prevSectionRef.current;
    if (expandedSection && !prev) {
      requestAnimationFrame(() => collapseRef.current?.focus());
    } else if (!expandedSection && prev) {
      requestAnimationFrame(() => {
        if (prev === "tldr") expandTldrRef.current?.focus();
        else expandOpinionRef.current?.focus();
      });
    }
    prevSectionRef.current = expandedSection;
  }, [expandedSection]);

  if (!brief) return (
    <div className="skb skb--compact anim-cold-open-skybox" role="complementary" aria-label="Daily Brief">
      <div className="skb__compact">
        <div className="skb__compact-header">
          <div className="skb__compact-cols">
            <div className="skb__compact-col">
              <div className="skb__compact-label">
                <LogoIcon size={16} animation="analyzing" />
                <span className="skb__compact-human">News Brief</span>
                <span className="skb__compact-cmd">void --tl;dr</span>
              </div>
              <span className="skb__compact-loading">Loading today&rsquo;s brief&hellip;</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const isCompact = expandedSection === null;

  const toggleSection = useCallback((section: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSection(prev => {
      const next = prev === section ? null : section;
      if (next) {
        setAnnouncement(`Daily brief expanded, showing ${next === "tldr" ? "news brief" : "editorial opinion"}.`);
      } else {
        setAnnouncement("Daily brief collapsed.");
      }
      return next;
    });
  }, []);

  const collapseAll = useCallback(() => {
    hapticLight();
    setExpandedSection(null);
    setAnnouncement("Daily brief collapsed.");
  }, []);

  const rootClass = [
    "skb",
    "anim-cold-open-skybox",
    isCompact ? "skb--compact" : "skb--section-open",
    expandedSection ? `skb--show-${expandedSection}` : "",
  ].filter(Boolean).join(" ");

  return (
    <>
      <div aria-live="polite" className="sr-only">{announcement}</div>

      <div className={rootClass} role="complementary" aria-label="Daily Brief">

        {/* ── COMPACT MODE ── */}
        {isCompact && (
          <div className="skb__compact">
              <div className={`skb__compact-cols${!brief.opinion_text ? " skb__compact-cols--single" : ""}`}>
                {/* TL;DR column — entire column is clickable to expand */}
                <button
                  ref={expandTldrRef}
                  className="skb__compact-col skb__compact-col--tldr"
                  onClick={() => toggleSection("tldr")}
                  type="button"
                  aria-expanded={false}
                  aria-label="Expand news brief"
                >
                  <div className="skb__compact-label">
                    <LogoIcon size={16} animation="idle" className="skb__compact-logo" />
                    <span className="skb__compact-human">News Brief</span>
                    <span className="skb__compact-cmd">void --tl;dr</span>
                    {brief.created_at && <span className="skb__compact-time">{timeAgo(brief.created_at)}</span>}
                  </div>
                  {brief.tldr_headline && <h3 className="skb__compact-hl skb__compact-hl--tldr">{brief.tldr_headline}</h3>}
                  <p className="skb__compact-preview skb__compact-preview--tldr">{brief.tldr_text}</p>
                  <span className="skb__compact-expand" aria-hidden="true">&#9662;</span>
                </button>

                {/* Opinion column — entire column is clickable to expand */}
                {brief.opinion_text && (
                  <button
                    ref={expandOpinionRef}
                    className="skb__compact-col skb__compact-col--opinion"
                    onClick={() => toggleSection("opinion")}
                    type="button"
                    aria-expanded={false}
                    aria-label="Expand editorial opinion"
                  >
                    <div className="skb__compact-label">
                      <LogoIcon size={16} animation="idle" className="skb__compact-logo" />
                      <span className="skb__compact-human">Editorial</span>
                      <span className="skb__compact-cmd">void --opinion</span>
                      {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
                    </div>
                    {brief.opinion_headline && <h3 className="skb__compact-hl skb__compact-hl--opinion">{brief.opinion_headline}</h3>}
                    <p className="skb__compact-preview skb__compact-preview--opinion">{brief.opinion_text}</p>
                    <span className="skb__compact-expand" aria-hidden="true">&#9662;</span>
                  </button>
                )}
              </div>

          </div>
        )}

        {/* ── EXPANDED MODE ── */}
        {!isCompact && (
          <>
            <div className="skb__topbar">
              <div className="skb__topbar-right">
                {expandedSection === "tldr" && brief.opinion_text && (
                  <button
                    className="skb__topbar-chip"
                    onClick={() => toggleSection("opinion")}
                    type="button"
                    aria-label="Switch to editorial"
                  >
                    <LogoIcon size={12} animation="none" className="skb__topbar-chip-logo" />
                    <span className="skb__topbar-chip-human">Editorial</span>
                    <span className="skb__topbar-chip-cmd">void --opinion</span>
                    {brief.opinion_lean && <span className={`skb__lean-badge skb__lean-badge--sm ${leanMod}`}>{leanLabel}</span>}
                    <span className="skb__topbar-chip-caret" aria-hidden="true">&#9662;</span>
                  </button>
                )}
                {expandedSection === "opinion" && (
                  <button
                    className="skb__topbar-chip"
                    onClick={() => toggleSection("tldr")}
                    type="button"
                    aria-label="Switch to news brief"
                  >
                    <LogoIcon size={12} animation="none" className="skb__topbar-chip-logo" />
                    <span className="skb__topbar-chip-human">News Brief</span>
                    <span className="skb__topbar-chip-cmd">void --tl;dr</span>
                    <span className="skb__topbar-chip-caret" aria-hidden="true">&#9662;</span>
                  </button>
                )}

                <button
                  ref={collapseRef}
                  className="skb__topbar-collapse"
                  onClick={collapseAll}
                  type="button"
                  aria-label="Collapse daily brief"
                >
                  <span aria-hidden="true">&#9652;</span>
                </button>
              </div>
            </div>

            <div className="skb__section-content">
              {expandedSection === "tldr" && (
                <div className="skb__section skb__section--tldr">
                  <div className="skb__section-label">
                    <LogoIcon size={18} animation="idle" />
                    <span className="skb__section-label-human">News Brief</span>
                    <span className="skb__section-label-cmd">void --tl;dr</span>
                    {brief.created_at && <span className="skb__section-label-time">{timeAgo(brief.created_at)}</span>}
                  </div>
                  {brief.tldr_headline && <h3 className="skb__section-hl skb__section-hl--tldr">{brief.tldr_headline}</h3>}
                  <div className="skb__section-body skb__section-body--tldr">
                    {brief.tldr_text.split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
                </div>
              )}

              {expandedSection === "opinion" && (
                <div className="skb__section skb__section--opinion">
                  <div className="skb__section-label">
                    <LogoIcon size={18} animation="idle" />
                    <span className="skb__section-label-human">Editorial</span>
                    <span className="skb__section-label-cmd">void --opinion</span>
                    {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
                  </div>
                  {brief.opinion_headline && <h3 className="skb__section-hl skb__section-hl--opinion">{brief.opinion_headline}</h3>}
                  <div className="skb__section-body skb__section-body--opinion">
                    {(brief.opinion_text || "").split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}
