"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import SigilWordmark from "../components/SigilWordmark";

/* ==========================================================================
   GamesHub — void --games Landing Page
   Cinematic dark theater experience. Five-layer depth stack:
     1. Background image — blurred atmospheric smoke, parallax on mouse
     2. Film grain — animated feTurbulence drift
     3. Vignette — radial edge darkening
     4. Ambient particles — floating amber dust motes
     5. Content — cards, masthead, transmission counter

   Entrance sequence: staged cascade from darkness (see games.css).
   Rack focus on card hover. Dolly-in exit on card click.
   ========================================================================== */

/* --------------------------------------------------------------------------
   Game Sigil Components — inline SVG marks
   -------------------------------------------------------------------------- */

function SigilUndertow({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--undertow${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M4,14 C8,9 12,9 16,14 C20,19 24,19 28,14"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M6,22 C10,19 14,19 18,22 C22,25 26,25 28,22"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        opacity="0.4"
      />
    </svg>
  );
}

function SigilWire({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--wire${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <polyline
        points="3,16 10,16 13,16 15,8 17,24 19,12 21,16 22,16 29,16"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SigilRun({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--run${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <line x1="6" y1="16" x2="20" y2="16" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <polyline points="17,11 22,16 17,21" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="3" y1="16" x2="8" y2="16" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.3" />
    </svg>
  );
}

function SigilFrame({ className }: { className?: string }) {
  return (
    <svg
      className={`game-sigil game-sigil--frame${className ? ` ${className}` : ""}`}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <polyline points="8,6 4,6 4,26 8,26" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="24,6 28,6 28,26 24,26" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="14" y1="16" x2="18" y2="16" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5" />
      <line x1="16" y1="14" x2="16" y2="18" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.5" />
    </svg>
  );
}

function GameSigil({ game }: { game: string }) {
  switch (game) {
    case "UNDERTOW": return <SigilUndertow />;
    case "THE FRAME": return <SigilFrame />;
    case "VOID RUN": return <SigilRun />;
    case "THE WIRE": return <SigilWire />;
    default: return null;
  }
}

/* --------------------------------------------------------------------------
   Void Mascot — the signal character. Diamond head, stick figure, living idle.
   Spring-based sway: body tilts 2.4s, head counter-lags 0.35s, arms balance.
   -------------------------------------------------------------------------- */

function VoidMascot() {
  return (
    <div className="void-mascot-wrap" aria-hidden="true">
      <svg
        viewBox="0 0 60 82"
        className="void-mascot"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        overflow="visible"
      >
        {/* Root sway group — pivots at the waist (30, 54) */}
        <g className="vm-body" style={{ transformOrigin: "30px 54px" }}>

          {/* Head group — counter-lags the body sway */}
          <g className="vm-head-group" style={{ transformOrigin: "30px 15px" }}>
            {/* Diamond head: ◇ — the void signal */}
            <polygon
              className="vm-head"
              points="30,2 44,15 30,28 16,15"
              stroke="var(--cin-amber, #c9a84c)"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
            {/* Core dot — pulses like a heartbeat */}
            <circle
              className="vm-core"
              cx="30"
              cy="15"
              r="2.2"
              fill="var(--cin-amber, #c9a84c)"
              style={{ transformOrigin: "30px 15px" }}
            />
          </g>

          {/* Spine — connects head to hips */}
          <line
            x1="30" y1="28"
            x2="30" y2="54"
            stroke="rgba(245,240,232,0.7)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />

          {/* Left arm — swings opposite to body lean */}
          <line
            className="vm-arm-l"
            x1="30" y1="36"
            x2="15" y2="50"
            stroke="rgba(245,240,232,0.55)"
            strokeWidth="1.4"
            strokeLinecap="round"
            style={{ transformOrigin: "30px 36px" }}
          />

          {/* Right arm — mirrors left arm (opposite phase) */}
          <line
            className="vm-arm-r"
            x1="30" y1="36"
            x2="45" y2="50"
            stroke="rgba(245,240,232,0.55)"
            strokeWidth="1.4"
            strokeLinecap="round"
            style={{ transformOrigin: "30px 36px" }}
          />

          {/* Left leg */}
          <line
            className="vm-leg-l"
            x1="30" y1="54"
            x2="20" y2="74"
            stroke="rgba(245,240,232,0.6)"
            strokeWidth="1.4"
            strokeLinecap="round"
            style={{ transformOrigin: "30px 54px" }}
          />

          {/* Right leg */}
          <line
            className="vm-leg-r"
            x1="30" y1="54"
            x2="40" y2="74"
            stroke="rgba(245,240,232,0.6)"
            strokeWidth="1.4"
            strokeLinecap="round"
            style={{ transformOrigin: "30px 54px" }}
          />
        </g>
      </svg>
    </div>
  );
}

/* --------------------------------------------------------------------------
   Games Wordmark — inline SVG with animation classes
   -------------------------------------------------------------------------- */

function GamesWordmark() {
  return (
    <div className="games-hub__wordmark-wrap" role="img" aria-label="Games">
      <SigilWordmark product="GAMES" height={40} />
    </div>
  );
}

/* --------------------------------------------------------------------------
   Particle System — 8 floating amber dust motes
   -------------------------------------------------------------------------- */

interface Particle {
  x0: string;
  y0: string;
  dx: string;
  dy: string;
  dur: string;
  delay: string;
}

function generateParticles(): Particle[] {
  const particles: Particle[] = [];
  for (let i = 0; i < 8; i++) {
    particles.push({
      x0: `${10 + (i * 11) % 80}%`,
      y0: `${15 + ((i * 17 + 7) % 70)}%`,
      dx: `${((i % 2 === 0 ? 1 : -1) * (60 + (i * 23) % 140))}px`,
      dy: `${-100 - (i * 31) % 200}px`,
      dur: `${10 + (i * 3) % 8}s`,
      delay: `${(i * 1.7) % 10}s`,
    });
  }
  return particles;
}

/* --------------------------------------------------------------------------
   Transmission Counter — countdown to next daily reset (midnight UTC)
   -------------------------------------------------------------------------- */

function useResetCountdown() {
  const [text, setText] = useState("");

  useEffect(() => {
    function update() {
      const now = new Date();
      const tomorrow = new Date(Date.UTC(
        now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1, 0, 0, 0
      ));
      const diff = tomorrow.getTime() - now.getTime();
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      setText(`${h}h ${String(m).padStart(2, "0")}m`);
    }
    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, []);

  return text;
}

/* --------------------------------------------------------------------------
   Game Data
   -------------------------------------------------------------------------- */

const ACTIVE_GAMES = [
  {
    name: "UNDERTOW",
    href: "/games/undertow",
    tagline: "every text has a tide",
    description: "Four cultural artifacts. One axis. Order them from pole to pole.",
    badge: "DAILY",
  },
  {
    name: "THE FRAME",
    href: "/games/frame",
    tagline: "see through the frame",
    description: "Four outlets. One story. Rank the headlines from left to right.",
    badge: "DAILY",
  },
  {
    name: "VOID RUN",
    href: "/games/run",
    tagline: "run until the signal breaks",
    description: "An endless runner through corridors of language. You are the signal. The obstacles are noise.",
    badge: "ENDLESS",
  },
];

const COMING_SOON = [
  {
    name: "THE WIRE",
    tagline: "Headline or hallucination? Spot the AI-generated story.",
  },
];

/* --------------------------------------------------------------------------
   GamesHub Component
   -------------------------------------------------------------------------- */

export default function GamesHub() {
  const [mounted, setMounted] = useState(false);
  const [exiting, setExiting] = useState(false);
  const bgRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const resetCountdown = useResetCountdown();
  const [particles] = useState<Particle[]>(() => generateParticles());

  // Mount trigger — starts entrance sequence after paint
  useEffect(() => {
    const timer = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Parallax on mouse move — shifts background layer (same system as UNDERTOW)
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;

    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 30;
      const y = (e.clientY / window.innerHeight - 0.5) * 20;
      bgRef.current?.style.setProperty("--px", `${x}px`);
      bgRef.current?.style.setProperty("--py", `${y}px`);
    };
    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // Dolly-in exit: card click triggers scale-up + fade, then navigate
  const handleCardClick = useCallback((e: React.MouseEvent, href: string) => {
    e.preventDefault();
    setExiting(true);
    setTimeout(() => router.push(href), 300);
  }, [router]);

  const today = mounted
    ? new Date().toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : "\u00A0";

  return (
    <div className={`games-hub${mounted ? " games-hub--mounted" : ""}${exiting ? " games-hub--exiting" : ""}`}>

      {/* Layer 1: Background image — heavily blurred, dark overlay, parallax */}
      <div className="games-hub__bg" ref={bgRef} aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?w=1920&q=80&auto=format&fit=crop"
          alt=""
          className="games-hub__bg-img"
          loading="eager"
        />
        <div className="games-hub__bg-overlay" />
      </div>

      {/* Layer 2: Film grain */}
      <div className="games-hub__grain" aria-hidden="true">
        <svg width="0" height="0" aria-hidden="true">
          <filter id="hub-grain">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.65"
              numOctaves="3"
              stitchTiles="stitch"
              result="noise"
            />
            <feColorMatrix type="saturate" values="0" in="noise" result="mono" />
          </filter>
        </svg>
        <div className="games-hub__grain-layer" />
      </div>

      {/* Layer 3: Vignette */}
      <div className="games-hub__vignette" aria-hidden="true" />

      {/* Layer 3b: Ambient glow */}
      <div className="games-hub__ambient-glow" aria-hidden="true" />

      {/* Layer 4: Ambient particles — projector dust motes */}
      <div className="games-hub__particles" aria-hidden="true">
        {particles.map((p, i) => (
          <div
            key={i}
            className="games-hub__particle"
            style={{
              "--x0": p.x0,
              "--y0": p.y0,
              "--dx": p.dx,
              "--dy": p.dy,
              "--dur": p.dur,
              "--delay": p.delay,
            } as React.CSSProperties}
          />
        ))}
      </div>

      {/* Layer 5: Content */}
      <div className="games-hub__content">
        {/* Navigation */}
        <nav className="games-hub__nav" aria-label="Navigation">
          <Link href="/" className="games-hub__back">
            <span aria-hidden="true">&larr;</span>
            {" "}Void News
          </Link>
        </nav>

        {/* Masthead */}
        <header className="games-hub__masthead">
          <VoidMascot />
          <h1>
            <GamesWordmark />
          </h1>
          <p className="games-hub__subtitle">
            every text has a tide
          </p>
          <svg
            className="games-hub__divider"
            viewBox="0 0 600 4"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path d="M0,2 C50,0.5 100,3.5 150,2 C200,0.5 250,3 300,2 C350,1 400,3.5 450,2 C500,0.5 550,3 600,2" />
          </svg>
        </header>

        {/* Active games — cards with rack focus */}
        <section className="games-hub__cards" aria-label="Active games">
          {ACTIVE_GAMES.map((game, i) => (
            <Link
              key={game.name}
              href={game.href}
              onClick={(e) => handleCardClick(e, game.href)}
              className={`games-hub__card games-hub__card--featured${i === 0 ? " games-hub__card--hero" : ""}${game.name === "UNDERTOW" ? " games-hub__card--undertow" : ""}`}
              style={{ "--card-index": i } as React.CSSProperties}
            >
              <div className="games-hub__card-badge">{game.badge}</div>
              <div className="games-hub__card-content">
                <div className="games-hub__card-header">
                  <GameSigil game={game.name} />
                  <h2 className="games-hub__card-name">{game.name}</h2>
                </div>
                <p className="games-hub__card-tagline">{game.description}</p>
                <div className="games-hub__card-meta">
                  <span className="games-hub__card-date" suppressHydrationWarning>
                    {today}
                  </span>
                  <span className="games-hub__card-id">#{i + 1}</span>
                </div>
              </div>
              <div className="games-hub__card-cta" aria-hidden="true">
                PLAY &rarr;
              </div>
            </Link>
          ))}
        </section>

        {/* Coming soon */}
        <section className="games-hub__upcoming" aria-label="Coming soon">
          <h2 className="games-hub__section-label">COMING SOON</h2>
          <div className="games-hub__ghost-grid">
            {COMING_SOON.map((game) => (
              <div
                key={game.name}
                className="games-hub__card games-hub__card--ghost"
                aria-disabled="true"
              >
                <div className="games-hub__card-content">
                  <div className="games-hub__card-header">
                    <GameSigil game={game.name} />
                    <h3 className="games-hub__card-name">{game.name}</h3>
                  </div>
                  <p className="games-hub__card-tagline">{game.tagline}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Transmission counter */}
        <div className="games-hub__transmission" aria-hidden="true">
          <p className="games-hub__transmission-text" suppressHydrationWarning>
            TRANSMISSION RECEIVED &middot; {ACTIVE_GAMES.length} GAMES ACTIVE &middot; DAILY RESET IN {resetCountdown || "--h --m"}
          </p>
        </div>

        {/* Footer */}
        <footer className="games-hub__footer">
          <p className="games-hub__footer-text">
            Media literacy, gamified. From{" "}
            <Link href="/" className="games-hub__footer-link">Void News</Link>.
          </p>
        </footer>
      </div>
    </div>
  );
}
