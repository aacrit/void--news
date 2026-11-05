"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAudio } from "../AudioProvider";

/* ---------------------------------------------------------------------------
   VuMeter: sixteen bars driven by the real signal.

   The analyser loop used to live inside FloatingPlayer, writing into two refs
   so the pill and the broadcast pane could share one rAF. Once the pane moved
   out into its own dialog that arrangement could not hold, so the driver moved
   here: each meter owns its own loop, connects the analyser lazily on first
   play, and stops the moment the element stops.

   The skin stays with the caller. `className` and `barClassName` carry the
   site's own classes (fp__vu, onair__vu), so one driver serves two visual
   languages without a third stylesheet.

   Silence must look like silence: when playback stops the inline heights are
   cleared so the CSS resting state takes the bars back, rather than freezing
   them at the last frame as if audio were still running.
   --------------------------------------------------------------------------- */

const VU_BARS = 16;
/* The useful voice range at 44.1kHz / 2048 fftSize is roughly bins 0-180.
   Sampling the whole spectrum puts eleven of the sixteen bars in frequencies
   a spoken-word programme never reaches. */
const USEFUL_BINS = 180;
/* ~30fps. The bars are a texture, not a readout; 60fps costs twice the main
   thread for a difference nobody can see. */
const FRAME_MS = 33;

export default function VuMeter({
  className,
  barClassName,
  active,
  liveClassName,
}: {
  /** The container's classes, already computed by the caller, modifiers and
   *  all. The driver adds none of its own: each site keeps the class names its
   *  stylesheet already asserts. */
  className: string;
  barClassName: string;
  /** Whether this meter's subject is the audio in the element. A page that
   *  does not own playback shows a resting meter, not someone else's signal. */
  active: boolean;
  /** Appended once the analyser is really feeding the bars, so the CSS
   *  fallback animation can stand down. */
  liveClassName?: string;
}) {
  const { analyserRef, connectAnalyser } = useAudio();
  const containerRef = useRef<HTMLDivElement>(null);
  const rafRef = useRef<number>(0);
  const freqRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const [live, setLive] = useState(false);

  const bars = useMemo(() => Array.from({ length: VU_BARS }, (_, i) => i), []);

  const draw = useCallback(() => {
    const analyser = analyserRef?.current;
    const container = containerRef.current;
    if (!analyser || !container) return;

    if (!freqRef.current || freqRef.current.length !== analyser.frequencyBinCount) {
      freqRef.current = new Uint8Array(analyser.frequencyBinCount);
    }
    analyser.getByteFrequencyData(freqRef.current);

    const bins = freqRef.current;
    const step = Math.min(bins.length, USEFUL_BINS) / VU_BARS;
    const children = container.children;
    for (let i = 0; i < VU_BARS && i < children.length; i++) {
      const val = bins[Math.floor(i * step)] / 255;
      const el = children[i] as HTMLElement;
      el.style.height = `${8 + val * 87}%`;
      el.style.opacity = String(0.3 + val * 0.7);
    }
  }, [analyserRef]);

  const rest = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    for (const bar of Array.from(container.children)) {
      (bar as HTMLElement).style.height = "";
      (bar as HTMLElement).style.opacity = "";
    }
  }, []);

  useEffect(() => {
    if (!active) {
      cancelAnimationFrame(rafRef.current);
      setLive(false);
      rest();
      return;
    }

    if (typeof window !== "undefined"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    connectAnalyser?.();

    /* The analyser is created inside connectAnalyser's own async path, so it
       is not there on the frame that asks for it. */
    const t = setTimeout(() => {
      if (!analyserRef?.current) return;
      setLive(true);
      let last = 0;
      const loop = (ts: number) => {
        if (ts - last > FRAME_MS) {
          last = ts;
          draw();
        }
        rafRef.current = requestAnimationFrame(loop);
      };
      rafRef.current = requestAnimationFrame(loop);
    }, 100);

    return () => {
      clearTimeout(t);
      cancelAnimationFrame(rafRef.current);
    };
  }, [active, analyserRef, connectAnalyser, draw, rest]);

  return (
    <div
      ref={containerRef}
      className={live && liveClassName ? `${className} ${liveClassName}` : className}
      aria-hidden="true"
    >
      {bars.map((i) => (
        <span key={i} className={barClassName} style={{ animationDelay: `${i * 60}ms` }} />
      ))}
    </div>
  );
}
