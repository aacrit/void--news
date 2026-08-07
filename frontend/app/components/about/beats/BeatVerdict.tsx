"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import Sigil from "../../Sigil";
import { demoSigil } from "../demoSigil";
import { BEATS, NUMBERS } from "../../../film/data";
import { useReducedMotion } from "../../../film/useReducedMotion";
import { useMotion } from "../useMotion";

/* ---------------------------------------------------------------------------
   Beat 4 — "Read with clarity."
   Three archetype marks spring in: broad+sourced = trust; thin+one-corner =
   scrutinize. Numbers + the final CTA. CTA differs by presentation:
   overlay → onComplete(); page → link to the feed.
   --------------------------------------------------------------------------- */

const BEAT = BEATS[3];

const ARCHETYPES = [
  { key: "broad", label: "Broad, sourced", verdict: "Well sourced", data: demoSigil(28, 16, 12) },
  { key: "consensus", label: "Center, deep", verdict: "Most reliable", data: demoSigil(50, 3, 14) },
  { key: "thin", label: "One corner, thin", verdict: "Scrutinize", data: demoSigil(78, 6, 3) },
];

/* The full page map for the closing step — every live destination, each in its
   own brand accent so the family reads as branded, not a grey link list. Colors
   mirror the product-family palette used across About and the nav. */
const EXPLORE = [
  { name: "Today's Feed", sub: "The front page, ranked once", href: "/", accentLight: "#9A5638", accentDark: "#D89A7C" },
  { name: "Sources", sub: "All 1,016, on one axis", href: "/sources", accentLight: "#3F7A5A", accentDark: "#77B994" },
  { name: "On Air", sub: "The daily brief, read aloud", href: "/onair", accentLight: "#2E8B7D", accentDark: "#4DAFA0" },
  { name: "Feedback", sub: "Tell us what to build or fix", href: "/ship", accentLight: "#BE4326", accentDark: "#D2593A" },
] as const;

interface Props {
  presentation: "page" | "overlay";
  onComplete?: () => void;
}

export default function BeatVerdict({ presentation, onComplete }: Props) {
  const reduced = useReducedMotion();
  const motion = useMotion(!reduced.current);
  const rootRef = useRef<HTMLElement>(null);
  const tilesRef = useRef<(HTMLDivElement | null)[]>([]);
  const played = useRef(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    if (reduced.current || !motion) {
      tilesRef.current.forEach((el) => { if (el) { el.style.opacity = "1"; el.style.transform = "none"; } });
      return;
    }
    const stop = motion.inView(root, () => {
      if (played.current) return;
      played.current = true;
      tilesRef.current.forEach((el, i) => {
        if (!el) return;
        motion.animate(el, { opacity: [0, 1], transform: ["translateY(18px) scale(0.96)", "translateY(0) scale(1)"] },
          { type: "spring", stiffness: 200, damping: 22, delay: i * 0.12 });
      });
    }, { amount: 0.4 });
    return () => stop();
  }, [motion, reduced]);

  return (
    <section className="beat beat--verdict" ref={rootRef} aria-labelledby="beat-verdict-h">
      <div className="beat__head">
        <h2 id="beat-verdict-h" className="beat__headline">{BEAT.headline}</h2>
        <p className="beat__body">{BEAT.body}</p>
      </div>

      <div className="verdict__marks">
        {ARCHETYPES.map((a, i) => (
          <div
            key={a.key}
            className="verdict__mark"
            ref={(el) => { tilesRef.current[i] = el; }}
            style={{ opacity: 0 }}
          >
            <Sigil data={a.data} size="lg" instant />
            <span className="verdict__mark-label">{a.label}</span>
            <span className={`verdict__mark-verdict verdict__mark-verdict--${a.key}`}>{a.verdict}</span>
          </div>
        ))}
      </div>

      <ul className="verdict__numbers" aria-label="By the numbers">
        {NUMBERS.map((n) => (
          <li key={n.label}><span className="verdict__num">{n.value}</span><span className="verdict__num-label">{n.label}</span></li>
        ))}
      </ul>

      <div className="verdict__final">
        <p className="verdict__final-eyebrow">Where to next</p>
        <h3 className="verdict__final-h">Explore everything.</h3>

        {presentation === "overlay" ? (
          <button className="verdict__go" onClick={onComplete} autoFocus>Start reading &rarr;</button>
        ) : (
          <Link href="/" className="verdict__go">Read today&rsquo;s feed &rarr;</Link>
        )}
        <p className="verdict__fine">No signup. No paywall. No tracking.</p>

        <nav className="verdict__map" aria-label="Everything on Void">
          {EXPLORE.map((e) => (
            <Link
              key={e.name}
              href={e.href}
              className="verdict__map-link"
              style={{ ["--acc-l" as string]: e.accentLight, ["--acc-d" as string]: e.accentDark }}
            >
              <span className="verdict__map-name">{e.name}</span>
              <span className="verdict__map-sub">{e.sub}</span>
            </Link>
          ))}
        </nav>

        <p className="verdict__map-note">
          Every story opens a Deep Dive. The daily Opinion column runs on the feed and is read aloud On Air.
        </p>
      </div>
    </section>
  );
}
