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

      <div className="verdict__cta">
        {presentation === "overlay" ? (
          <button className="verdict__go" onClick={onComplete} autoFocus>Start reading</button>
        ) : (
          <Link href="/" className="verdict__go">Read today&rsquo;s feed</Link>
        )}
        <p className="verdict__fine">No signup. No paywall. No tracking.</p>
        <Link href="/history" className="verdict__secondary">Or explore the archive &rarr;</Link>
      </div>
    </section>
  );
}
