'use client';

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import Link from 'next/link';
import LogoFull from './LogoFull';
import ThemeToggle from './ThemeToggle';
import {
  fetchShipRequests,
  submitShipRequest,
  voteOnShipRequest,
  subscribeToShipRequests,
  fetchShipReplies,
  submitShipReply,
  subscribeToShipReplies,
  generateFingerprint,
} from '../lib/supabase';
import type { ShipRequest, ShipReply, ShipStatus, ShipCategory, Edition } from '../lib/types';

/* ==========================================================================
   void --ship v3 — "Mission Control"

   A single-viewport dashboard on desktop (>=1024px): the page owns 100dvh and
   only inner panels scroll. Top bar (brand + live metrics + sparkline) sits over
   a three-column main area — Submit / The Board / Known Observations — with a
   short bottom strip (recent ticker + personal touch + log + Discord placeholder).

   Mobile (<768px): the same content stacked into a normal scrollable column.
   Tablet (768-1023): stacked, no fixed-height trap.

   Every Supabase wiring, spam guard, and ShipCard feature from v2 is preserved.
   ========================================================================== */

const STATUS_ORDER: ShipStatus[] = ['submitted', 'triaged', 'building', 'shipped', 'wontship', 'deferred', 'not_feasible'];
const STATUS_LABELS: Record<ShipStatus, string> = {
  submitted: 'Submitted',
  triaged: 'Triaged',
  building: 'Building',
  shipped: 'Shipped',
  wontship: "Won't Ship",
  deferred: 'Deferred',
  not_feasible: 'Not Feasible',
};

// Terminal / closed states. These collect in a single "Resolved" board column
// (a 7-column Kanban is too wide) where each card wears its own status tag.
const CLOSED_STATUSES: ShipStatus[] = ['wontship', 'deferred', 'not_feasible'];

// The Kanban columns actually rendered: the four active-flow states plus one
// combined Resolved pile for every closed status. Left-to-right pipeline.
interface BoardColumn { key: string; label: string; statuses: ShipStatus[]; }
const BOARD_COLUMNS: BoardColumn[] = [
  { key: 'submitted', label: 'Submitted', statuses: ['submitted'] },
  { key: 'triaged', label: 'Triaged', statuses: ['triaged'] },
  { key: 'building', label: 'Building', statuses: ['building'] },
  { key: 'shipped', label: 'Shipped', statuses: ['shipped'] },
  { key: 'resolved', label: 'Resolved', statuses: CLOSED_STATUSES },
];

const CATEGORY_OPTIONS: { value: ShipCategory; label: string }[] = [
  { value: 'bug', label: 'Bug' },
  { value: 'feature', label: 'Feature' },
];

// ---- Known Observations ----
// Radical transparency about current limitations, paired with what we are doing
// about each. Framed as "what we watch and how we are improving it," never as
// apology. Chip labels are deliberately quiet so they do not read as Kanban
// columns. Copy is show-don't-tell and free of em/en dashes (locked project rule).
type ObservationChip = 'tuning' | 'by-design' | 'roadmap' | 'known';
const CHIP_LABELS: Record<ObservationChip, string> = {
  tuning: 'Actively tuning',
  'by-design': 'By design',
  roadmap: 'On the roadmap',
  known: 'Known',
};
interface Observation { claim: string; note: string; optimizing: string; chip: ObservationChip; }
const OBSERVATIONS: Observation[] = [
  {
    claim: 'Clustering can split or double up.',
    note: 'Sometimes one event lands on two cards, or two near-identical stories both appear.',
    optimizing: 'We retune the merge thresholds every run and added a same-event cap so one story cannot fill the front page.',
    chip: 'tuning',
  },
  {
    claim: 'The bias score is a signal, not a verdict.',
    note: 'Every score is rule-based and traces to specific words in the coverage. Thin coverage reads as no clear lean.',
    optimizing: 'We keep expanding the lexicons and calibrating against known outlet ratings. The Deep Dive shows the full distribution behind every score.',
    chip: 'by-design',
  },
  {
    claim: 'Summaries thin out down the feed.',
    note: 'The top stories get the fullest write-ups. Lower-ranked cards can read more mechanically, or surface a raw excerpt.',
    optimizing: 'The summarizer now covers all fifty displayed stories, and a sanitizer repairs run-ons and stray credits before they ship.',
    chip: 'tuning',
  },
  {
    claim: 'Coverage skews English-language.',
    note: '1,016 sources span 158 countries, but well-resourced English outlets dominate the mix.',
    optimizing: 'We are widening the non-English source list and weighting regional outlets up where a story is local to them.',
    chip: 'roadmap',
  },
  {
    claim: 'Figures can differ between cards.',
    note: 'Death tolls and counts come from different outlets reporting at different hours, so the same event may show one number here and another there.',
    optimizing: 'We surface source count and spread so you can see how firm a number is. Cross-card reconciliation is on the list.',
    chip: 'known',
  },
  {
    claim: 'The feed moves once a day.',
    note: 'One run at 11:00 UTC. Breaking news mid-day waits for the next edition.',
    optimizing: 'The once-a-day rhythm is deliberate, a newspaper not a scroll. A lighter mid-day refresh is under consideration.',
    chip: 'by-design',
  },
  {
    claim: 'A tabloid headline occasionally slips through.',
    note: 'The sanitizer neutralizes shouty, clickbait headlines, but a raw one can get past it before we catch it.',
    optimizing: "We keep growing the desensationalizer's shout list and clickbait rules as new ones appear.",
    chip: 'tuning',
  },
  {
    claim: 'Generated prose is imperfect.',
    note: 'The weekly essays and daily brief are machine-drafted under strict rules. An occasional clunky line gets through.',
    optimizing: 'Every generated line runs a show-dont-tell and no-em-dash check. Failures get retried or flagged.',
    chip: 'known',
  },
];

const EDITION_SLUGS: Edition[] = ['world'];

// ---- Templates ----
const BUG_TEMPLATE = `## What happened\n\n## What I expected\n\n## Steps to reproduce\n1. \n2. \n`;
const FEATURE_TEMPLATE = `## What I want\n\n## Why it matters\n\n`;

// ---- Rate limit: max 5 submissions per hour ----
const RATE_LIMIT_KEY = 'void-ship-submissions';
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW = 3600000;

// ---- Reply rate limit: max 3 replies per hour ----
const REPLY_RATE_LIMIT_KEY = 'void-ship-replies';
const REPLY_RATE_LIMIT_MAX = 3;

function checkRateLimit(): boolean {
  try {
    const raw = localStorage.getItem(RATE_LIMIT_KEY);
    if (!raw) return true;
    const timestamps: number[] = JSON.parse(raw);
    const now = Date.now();
    return timestamps.filter(t => now - t < RATE_LIMIT_WINDOW).length < RATE_LIMIT_MAX;
  } catch { return true; }
}

function recordSubmission(): void {
  try {
    const raw = localStorage.getItem(RATE_LIMIT_KEY);
    const timestamps: number[] = raw ? JSON.parse(raw) : [];
    timestamps.push(Date.now());
    const recent = timestamps.filter(t => Date.now() - t < RATE_LIMIT_WINDOW);
    localStorage.setItem(RATE_LIMIT_KEY, JSON.stringify(recent));
  } catch { /* noop */ }
}

function checkReplyRateLimit(): boolean {
  try {
    const raw = localStorage.getItem(REPLY_RATE_LIMIT_KEY);
    if (!raw) return true;
    const timestamps: number[] = JSON.parse(raw);
    const now = Date.now();
    return timestamps.filter(t => now - t < RATE_LIMIT_WINDOW).length < REPLY_RATE_LIMIT_MAX;
  } catch { return true; }
}

function recordReply(): void {
  try {
    const raw = localStorage.getItem(REPLY_RATE_LIMIT_KEY);
    const timestamps: number[] = raw ? JSON.parse(raw) : [];
    timestamps.push(Date.now());
    const recent = timestamps.filter(t => Date.now() - t < RATE_LIMIT_WINDOW);
    localStorage.setItem(REPLY_RATE_LIMIT_KEY, JSON.stringify(recent));
  } catch { /* noop */ }
}

// ---- Vote tracking ----
const VOTES_KEY = 'void-ship-votes';

function getVotedIds(): Set<string> {
  try {
    const raw = localStorage.getItem(VOTES_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch { return new Set(); }
}

function recordVote(id: string): void {
  try {
    const voted = getVotedIds();
    voted.add(id);
    localStorage.setItem(VOTES_KEY, JSON.stringify([...voted]));
  } catch { /* noop */ }
}

// ---- Time helpers ----
function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function shipDuration(created: string, shipped: string): string {
  const diff = new Date(shipped).getTime() - new Date(created).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

function elapsedTimer(created: string): string {
  const diff = Date.now() - new Date(created).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ${mins % 60}m`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h`;
}

function computeMetrics(requests: ShipRequest[]) {
  const shipped = requests.filter(r => r.status === 'shipped');
  const open = requests.filter(r => ['submitted', 'triaged', 'building'].includes(r.status));
  let avgShipTime = 0;
  if (shipped.length > 0) {
    const totalMs = shipped.reduce((sum, r) => {
      if (!r.shipped_at) return sum;
      return sum + (new Date(r.shipped_at).getTime() - new Date(r.created_at).getTime());
    }, 0);
    const validCount = shipped.filter(r => r.shipped_at).length;
    if (validCount > 0) avgShipTime = totalMs / validCount / 3600000;
  }
  return { totalShipped: shipped.length, openCount: open.length, totalRequests: requests.length, avgShipTimeHours: avgShipTime };
}

// ---- Edition auto-detect ----
function detectEdition(): Edition | null {
  if (typeof window === 'undefined') return null;
  const params = new URLSearchParams(window.location.search);
  const fromParam = params.get('edition');
  if (fromParam && EDITION_SLUGS.includes(fromParam as Edition)) return fromParam as Edition;
  try {
    const ref = document.referrer;
    if (ref) {
      for (const slug of EDITION_SLUGS) {
        if (ref.includes(`/${slug}`)) return slug;
      }
    }
  } catch { /* noop */ }
  return null;
}

// ---- Metrics countup easing ----
function easeOutPoly(t: number): number {
  return 1 - Math.pow(1 - t, 3.5);
}

// ---- Mobile detection ----
function useIsMobile(breakpoint = 768): boolean {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < breakpoint);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, [breakpoint]);
  return isMobile;
}

// ---- Reduced-motion detection ----
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}

// ---- Pulse Graph (30-day sparkline) ----
function PulseGraph({ requests }: { requests: ShipRequest[] }) {
  const { submittedPath, shippedPath } = useMemo(() => {
    const now = Date.now();
    const thirtyDaysAgo = now - 30 * 24 * 60 * 60 * 1000;
    const dayBins: { submitted: number[]; shipped: number[] } = { submitted: Array(30).fill(0), shipped: Array(30).fill(0) };

    for (const r of requests) {
      const createdMs = new Date(r.created_at).getTime();
      if (createdMs >= thirtyDaysAgo) {
        const dayIdx = Math.min(29, Math.floor((createdMs - thirtyDaysAgo) / (24 * 60 * 60 * 1000)));
        dayBins.submitted[dayIdx]++;
      }
      if (r.shipped_at) {
        const shippedMs = new Date(r.shipped_at).getTime();
        if (shippedMs >= thirtyDaysAgo) {
          const dayIdx = Math.min(29, Math.floor((shippedMs - thirtyDaysAgo) / (24 * 60 * 60 * 1000)));
          dayBins.shipped[dayIdx]++;
        }
      }
    }

    const maxVal = Math.max(1, ...dayBins.submitted, ...dayBins.shipped);
    const toPath = (bins: number[]) => {
      const points = bins.map((v, i) => {
        const x = (i / 29) * 280;
        const y = 34 - (v / maxVal) * 30;
        return `${x},${y}`;
      });
      return `M${points.join(' L')}`;
    };

    return { submittedPath: toPath(dayBins.submitted), shippedPath: toPath(dayBins.shipped) };
  }, [requests]);

  return (
    <svg
      className="ship-pulse-graph"
      viewBox="0 0 280 36"
      preserveAspectRatio="none"
      aria-label="Request activity over the last 30 days"
      role="img"
    >
      <path className="ship-pulse-graph__submitted" d={submittedPath} />
      <path className="ship-pulse-graph__shipped" d={shippedPath} />
    </svg>
  );
}


/* ===========================================================================
   QUICK SUBMIT — shared "note into the ship queue" control.

   Reuses submitShipRequest + the submission rate limit + honeypot + fingerprint.
   Two callers: "Suggest a fix" (preset title "Re: {claim}") and "Got an idea?"
   (title derived from the note). Both file a feature request.
   =========================================================================== */

function deriveIdeaTitle(note: string): string {
  const firstLine = note.trim().split('\n')[0].trim();
  const t = firstLine.slice(0, 80).trim();
  return t.length >= 5 ? t : 'Reader idea';
}

function QuickSubmit({
  fingerprint,
  presetTitle,
  descPrefix,
  placeholder,
  toggleLabel,
  variant,
}: {
  fingerprint: string;
  /** When set, the ship request title is fixed (Suggest a fix). Otherwise the
   *  title is derived from the note (Got an idea). */
  presetTitle?: string;
  /** Optional context line prepended to the description. */
  descPrefix?: string;
  placeholder: string;
  toggleLabel: string;
  /** 'inline' = compact suggest-a-fix; 'block' = the standing idea box. */
  variant: 'inline' | 'block';
}) {
  const [open, setOpen] = useState(variant === 'block');
  const [note, setNote] = useState('');
  const [honeypot, setHoneypot] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const canSend = note.trim().length >= 10 && !submitting;

  const send = useCallback(async () => {
    if (!canSend) return;
    if (!checkRateLimit()) { setError(`Slow down. Max ${RATE_LIMIT_MAX} submissions per hour.`); return; }
    if (honeypot) { setDone(true); return; }
    setSubmitting(true);
    setError('');
    const trimmed = note.trim();
    const description = descPrefix ? `${descPrefix}\n\n${trimmed}` : trimmed;
    const deviceInfo = typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 180) : null;
    const result = await submitShipRequest({
      title: (presetTitle ?? deriveIdeaTitle(trimmed)).slice(0, 120),
      description,
      category: 'feature',
      area: 'other',
      edition_context: null,
      device_info: deviceInfo,
      ip_hash: fingerprint,
    });
    if (result) {
      recordSubmission();
      setNote('');
      setDone(true);
    } else {
      setError('Could not send. Please try again.');
    }
    setSubmitting(false);
  }, [canSend, honeypot, note, descPrefix, presetTitle, fingerprint]);

  if (done) {
    return (
      <div className={`ship-quick ship-quick--${variant} ship-quick--done`}>
        <p className="ship-quick__done">Filed to the queue. Thank you.</p>
        <button
          type="button"
          className="ship-quick__again"
          onClick={() => { setDone(false); if (variant === 'inline') setOpen(false); }}
        >
          {variant === 'inline' ? 'Close' : 'Send another'}
        </button>
      </div>
    );
  }

  if (variant === 'inline' && !open) {
    return (
      <button type="button" className="ship-quick__toggle" onClick={() => setOpen(true)}>
        {toggleLabel}
      </button>
    );
  }

  return (
    <div className={`ship-quick ship-quick--${variant}`}>
      {variant === 'block' && <span className="ship-quick__label">{toggleLabel}</span>}
      {/* Honeypot: bots fill hidden fields; a filled value fakes success. */}
      <div className="ship-form__honeypot" aria-hidden="true">
        <label htmlFor={`ship-quick-hp-${variant}-${presetTitle ?? 'idea'}`}>Company</label>
        <input
          id={`ship-quick-hp-${variant}-${presetTitle ?? 'idea'}`}
          type="text"
          value={honeypot}
          onChange={(e) => setHoneypot(e.target.value)}
          tabIndex={-1}
          autoComplete="off"
        />
      </div>
      <textarea
        className="ship-quick__input"
        value={note}
        maxLength={1000}
        onChange={(e) => setNote(e.target.value)}
        placeholder={placeholder}
        aria-label={toggleLabel}
      />
      {error && <p className="ship-quick__error" role="alert">{error}</p>}
      <div className="ship-quick__actions">
        {variant === 'inline' && (
          <button type="button" className="ship-quick__cancel" onClick={() => { setOpen(false); setNote(''); setError(''); }}>
            Cancel
          </button>
        )}
        <button type="button" className="ship-quick__send" onClick={send} disabled={!canSend}>
          {submitting ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
}


/* ===========================================================================
   OBSERVATIONS RAIL — the signature interactive element.

   Desktop, motion allowed: a vertical ticker. One observation holds the focal
   slot expanded (claim + note + what we are doing + chip + Suggest a fix), rises
   in, and hands off to the next on a timer. Pauses on hover/focus and via an
   explicit control. "Expand all" opens every observation at once in an overlay.

   Mobile or reduced-motion: a plain scrollable list of every observation. The
   ticker region is aria-live="off" so it never spams assistive tech; the full
   list and the overlay are the accessible reading paths.
   =========================================================================== */

function ObservationChipTag({ chip }: { chip: ObservationChip }) {
  return (
    <span className={`ship-obs__chip ship-obs__chip--${chip}`}>
      <span className="ship-obs__chip-dot" aria-hidden="true" />
      {CHIP_LABELS[chip]}
    </span>
  );
}

function ObservationDetail({ obs, fingerprint }: { obs: Observation; fingerprint: string }) {
  return (
    <>
      <div className="ship-obs__row">
        <p className="ship-obs__claim">{obs.claim}</p>
        <ObservationChipTag chip={obs.chip} />
      </div>
      <p className="ship-obs__note">{obs.note}</p>
      <p className="ship-obs__optimizing">
        <span className="ship-obs__optimizing-label">What we are doing</span>
        {obs.optimizing}
      </p>
      <QuickSubmit
        fingerprint={fingerprint}
        variant="inline"
        presetTitle={`Re: ${obs.claim}`}
        descPrefix={`On the observation: "${obs.claim}"`}
        placeholder="Seen this yourself, or have a fix in mind? Tell us."
        toggleLabel="Suggest a fix"
      />
    </>
  );
}

function ObservationsRail({ fingerprint }: { fingerprint: string }) {
  const isMobile = useIsMobile();
  const prefersReduced = usePrefersReducedMotion();
  const useTicker = !isMobile && !prefersReduced;

  const [activeIndex, setActiveIndex] = useState(0);
  const [hoverPaused, setHoverPaused] = useState(false);
  const [manualPaused, setManualPaused] = useState(false);
  const [expandAll, setExpandAll] = useState(false);

  const paused = hoverPaused || manualPaused;

  useEffect(() => {
    if (!useTicker || paused || expandAll) return;
    const id = setInterval(() => {
      setActiveIndex(i => (i + 1) % OBSERVATIONS.length);
    }, 6500);
    return () => clearInterval(id);
  }, [useTicker, paused, expandAll]);

  const active = OBSERVATIONS[activeIndex];
  const upNext = [1, 2].map(o => OBSERVATIONS[(activeIndex + o) % OBSERVATIONS.length]);

  return (
    <div className="ship-rail">
      <div className="ship-rail__controls">
        <button
          type="button"
          className="ship-rail__expand-all"
          onClick={() => setExpandAll(true)}
          aria-haspopup="dialog"
        >
          Expand all
        </button>
        {useTicker && (
          <button
            type="button"
            className="ship-rail__pause"
            onClick={() => setManualPaused(p => !p)}
            aria-pressed={manualPaused}
          >
            {manualPaused ? 'Play' : 'Pause'}
          </button>
        )}
      </div>

      {useTicker ? (
        <div
          className="ship-ticker"
          onMouseEnter={() => setHoverPaused(true)}
          onMouseLeave={() => setHoverPaused(false)}
          onFocusCapture={() => setHoverPaused(true)}
          onBlurCapture={() => setHoverPaused(false)}
        >
          {/* aria-live off: the rotating focal card is decorative motion. The
              full list lives in the "Expand all" dialog for assistive tech. */}
          <div className="ship-ticker__stage" aria-live="off">
            <article key={activeIndex} className="ship-ticker__focal">
              <ObservationDetail obs={active} fingerprint={fingerprint} />
            </article>
          </div>

          <div className="ship-ticker__next" aria-hidden="true">
            <span className="ship-ticker__next-label">Up next</span>
            {upNext.map((o, i) => (
              <p key={i} className="ship-ticker__next-claim">{o.claim}</p>
            ))}
          </div>

          <div className="ship-ticker__dots" role="tablist" aria-label="Observations">
            {OBSERVATIONS.map((o, i) => (
              <button
                key={i}
                type="button"
                role="tab"
                aria-selected={i === activeIndex}
                aria-label={o.claim}
                className={`ship-ticker__dot${i === activeIndex ? ' ship-ticker__dot--active' : ''}`}
                onClick={() => setActiveIndex(i)}
              />
            ))}
          </div>
        </div>
      ) : (
        <ul className="ship-obs-list">
          {OBSERVATIONS.map((o, i) => (
            <li key={i} className="ship-obs-list__item">
              <ObservationDetail obs={o} fingerprint={fingerprint} />
            </li>
          ))}
        </ul>
      )}

      {expandAll && (
        <ShipOverlay title="Known Observations" onClose={() => setExpandAll(false)}>
          <p className="ship-overlay__intro">
            We would rather tell you where the machine still stumbles than pretend
            it does not. Here is what we are watching, and what we are doing about it.
          </p>
          <ul className="ship-obs-list ship-obs-list--overlay">
            {OBSERVATIONS.map((o, i) => (
              <li key={i} className="ship-obs-list__item">
                <ObservationDetail obs={o} fingerprint={fingerprint} />
              </li>
            ))}
          </ul>
        </ShipOverlay>
      )}
    </div>
  );
}


/* ===========================================================================
   SHIP OVERLAY — a small accessible dialog used for "Expand all" and the log.
   Esc closes, backdrop closes, focus lands on the close button.
   =========================================================================== */

function ShipOverlay({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="ship-overlay" role="presentation" onClick={onClose}>
      <div
        className="ship-overlay__panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="ship-overlay__head">
          <h2 className="ship-overlay__title">{title}</h2>
          <button ref={closeRef} type="button" className="ship-overlay__close" onClick={onClose} aria-label="Close">
            &times;
          </button>
        </div>
        <div className="ship-overlay__body">{children}</div>
      </div>
    </div>
  );
}


/* ===========================================================================
   MAIN COMPONENT
   =========================================================================== */

export default function ShipBoard() {
  const [requests, setRequests] = useState<ShipRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [votedIds, setVotedIds] = useState<Set<string>>(new Set());
  const fingerprintRef = useRef<string>('');
  const isMobile = useIsMobile();
  const prefersReduced = usePrefersReducedMotion();

  const pageRef = useRef<HTMLElement>(null);

  // Log overlay
  const [logOpen, setLogOpen] = useState(false);

  // Track IDs that arrived via INSERT (not UPDATE) for the enter animation
  const newIdsRef = useRef<Set<string>>(new Set());
  // Track IDs that just transitioned to shipped for the golden flash
  const [justShippedIds, setJustShippedIds] = useState<Set<string>>(new Set());

  // Animated metric values (count-up)
  const [animatedMetrics, setAnimatedMetrics] = useState<{
    totalShipped: number; openCount: number; totalRequests: number; avgShipTimeHours: number;
  } | null>(null);
  const [metricsLanded, setMetricsLanded] = useState(false);
  const metricsAnimatedRef = useRef(false);

  // Form state (inline, not modal)
  const [formTitle, setFormTitle] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formCategory, setFormCategory] = useState<ShipCategory>('feature');
  const [formHoneypot, setFormHoneypot] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState(false);
  const userHasTypedRef = useRef(false);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const editionRef = useRef<Edition | null>(null);

  // Reply realtime subscription
  const [replyMap, setReplyMap] = useState<Record<string, ShipReply[]>>({});

  useEffect(() => {
    fingerprintRef.current = generateFingerprint();
    editionRef.current = detectEdition();
    setVotedIds(getVotedIds());
    fetchShipRequests().then(data => {
      setRequests(data);
      setLoading(false);
    });
    const unsub = subscribeToShipRequests((payload) => {
      setRequests(prev => {
        if (payload.eventType === 'INSERT') {
          newIdsRef.current.add(payload.new.id);
          return [payload.new, ...prev];
        }
        if (payload.eventType === 'UPDATE') {
          if (payload.new.status === 'shipped' && payload.old.status !== 'shipped') {
            setJustShippedIds(s => new Set([...s, payload.new.id]));
            setTimeout(() => {
              setJustShippedIds(s => {
                const next = new Set(s);
                next.delete(payload.new.id);
                return next;
              });
            }, 600);
          }
          return prev.map(r => r.id === payload.new.id ? payload.new : r);
        }
        if (payload.eventType === 'DELETE') return prev.filter(r => r.id !== payload.old.id);
        return prev;
      });
    });

    // Subscribe to reply realtime
    const unsubReplies = subscribeToShipReplies((reply: ShipReply) => {
      setReplyMap(prev => ({
        ...prev,
        [reply.request_id]: [...(prev[reply.request_id] || []), reply],
      }));
    });

    return () => { unsub(); unsubReplies(); };
  }, []);

  // No-outer-scroll enforcement: the desktop grid pins the page to the viewport
  // height minus whatever chrome sits above it (the dismissible experimental
  // banner). Measure the page's top offset and expose it as a CSS variable so
  // `height: calc(100dvh - var(--ship-chrome-offset))` fills exactly the space
  // left. A ResizeObserver on <body> re-measures when the banner is dismissed.
  useEffect(() => {
    const el = pageRef.current;
    if (!el) return;
    const measure = () => {
      const top = el.getBoundingClientRect().top + window.scrollY;
      el.style.setProperty('--ship-chrome-offset', `${Math.max(0, Math.round(top))}px`);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(document.body);
    window.addEventListener('resize', measure);
    return () => { ro.disconnect(); window.removeEventListener('resize', measure); };
  }, []);

  // Count-up animation after data loads (skipped under reduced motion).
  useEffect(() => {
    if (loading || metricsAnimatedRef.current || requests.length === 0) return;
    metricsAnimatedRef.current = true;
    if (prefersReduced) { setMetricsLanded(true); return; }
    const target = computeMetrics(requests);
    const duration = 800;
    const stagger = 80;
    const fields: (keyof typeof target)[] = ['totalShipped', 'openCount', 'totalRequests', 'avgShipTimeHours'];
    const startTimes = fields.map((_, i) => performance.now() + i * stagger);
    const initialValues = { totalShipped: 0, openCount: 0, totalRequests: 0, avgShipTimeHours: 0 };
    setAnimatedMetrics(initialValues);
    let raf: number;
    const animate = (now: number) => {
      let allDone = true;
      const next = { ...initialValues };
      for (let i = 0; i < fields.length; i++) {
        const elapsed = now - startTimes[i];
        if (elapsed < 0) { allDone = false; continue; }
        const t = Math.min(elapsed / duration, 1);
        const eased = easeOutPoly(t);
        const key = fields[i];
        next[key] = key === 'avgShipTimeHours'
          ? eased * target[key]
          : Math.round(eased * target[key]);
        if (t < 1) allDone = false;
      }
      setAnimatedMetrics(next);
      if (allDone) {
        setAnimatedMetrics(target);
        setMetricsLanded(true);
      } else {
        raf = requestAnimationFrame(animate);
      }
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [loading, requests, prefersReduced]);

  const liveMetrics = computeMetrics(requests);
  const displayMetrics = animatedMetrics && !metricsLanded ? animatedMetrics : liveMetrics;

  const handleVote = useCallback(async (requestId: string) => {
    if (votedIds.has(requestId)) return;
    const fp = fingerprintRef.current;
    const newCount = await voteOnShipRequest(requestId, fp);
    if (newCount !== null) {
      recordVote(requestId);
      setVotedIds(prev => new Set([...prev, requestId]));
      // Use the authoritative server count returned by sync_ship_votes.
      setRequests(prev => prev.map(r => r.id === requestId ? { ...r, votes: newCount } : r));
    }
  }, [votedIds]);

  // ---- Category toggle with template injection ----
  const handleCategoryChange = useCallback((cat: ShipCategory) => {
    setFormCategory(cat);
    if (!userHasTypedRef.current && formDesc.trim() === '') {
      setFormDesc(cat === 'bug' ? BUG_TEMPLATE : FEATURE_TEMPLATE);
    }
  }, [formDesc]);

  // Track user typing
  const handleDescChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setFormDesc(e.target.value);
    if (e.target.value.trim() !== '' &&
        e.target.value !== BUG_TEMPLATE &&
        e.target.value !== FEATURE_TEMPLATE) {
      userHasTypedRef.current = true;
    }
    if (e.target.value.trim() === '') {
      userHasTypedRef.current = false;
    }
  }, []);

  // ---- Form submit ----
  const canSubmit = formTitle.trim().length >= 5 && formDesc.trim().length >= 10 && !formSubmitting;
  const rateLimited = !checkRateLimit();

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || rateLimited) return;
    if (formHoneypot) { setFormSuccess(true); return; }
    setFormSubmitting(true);
    setFormError('');
    const deviceInfo = typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 180) : null;
    const result = await submitShipRequest({
      title: formTitle.trim(),
      description: formDesc.trim(),
      category: formCategory,
      area: 'other',
      edition_context: editionRef.current,
      device_info: deviceInfo,
      ip_hash: fingerprintRef.current,
    });
    if (result) {
      recordSubmission();
      setFormSuccess(true);
    } else {
      setFormError('Failed to submit. Please try again.');
    }
    setFormSubmitting(false);
  };

  const resetForm = useCallback(() => {
    setFormTitle('');
    setFormDesc('');
    setFormCategory('feature');
    setFormSuccess(false);
    setFormError('');
    userHasTypedRef.current = false;
    titleInputRef.current?.focus();
  }, []);

  // Group by status
  const grouped: Record<ShipStatus, ShipRequest[]> = { submitted: [], triaged: [], building: [], shipped: [], wontship: [], deferred: [], not_feasible: [] };
  for (const r of requests) { if (grouped[r.status]) grouped[r.status].push(r); }
  for (const status of STATUS_ORDER) {
    if (status === 'shipped') {
      grouped[status].sort((a, b) => new Date(b.shipped_at || b.created_at).getTime() - new Date(a.shipped_at || a.created_at).getTime());
    } else {
      grouped[status].sort((a, b) => b.votes - a.votes || new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
  }

  // Recent activity (most recent first)
  const recentActivity = useMemo(() =>
    requests
      .slice()
      .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
      .slice(0, 8),
    [requests]
  );

  // On mobile the board stacks; hide empty columns (keep submitted). On desktop
  // every column stays so the pipeline reads left to right.
  const visibleColumns = isMobile
    ? BOARD_COLUMNS.filter(col => col.key === 'submitted' || col.statuses.some(s => grouped[s].length > 0))
    : BOARD_COLUMNS;

  const avgLabel = displayMetrics.avgShipTimeHours > 0
    ? `${displayMetrics.avgShipTimeHours.toFixed(1)}h`
    : 'pending';

  return (
    <main className="ship-page" ref={pageRef}>
      {/* ==== TOP BAR: brand + live metrics + sparkline ==== */}
      <header className="ship-topbar">
        <div className="ship-topbar__lead">
          <Link href="/" className="ship-topbar__back" aria-label="Back to Void News">
            &larr; <span className="ship-topbar__back-text">Void News</span>
          </Link>
          <span className="ship-topbar__lockup">
            <Link href="/" className="ship-topbar__logo" aria-label="Void News home">
              <LogoFull height={20} />
            </Link>
            <span className="ship-topbar__sep" aria-hidden="true">&middot;</span>
            <span className="ship-topbar__suffix">Ship</span>
          </span>
        </div>

        <div className="ship-topbar__metrics-wrap">
          <div className="ship-metrics" aria-label="Live ship metrics">
            <span className={`ship-metrics__item ship-metrics__item--gold${metricsLanded ? ' ship-metrics__item--landed' : ''}`}>
              <span className="ship-metrics__num">{displayMetrics.totalShipped}</span> shipped
            </span>
            <span className="ship-metrics__sep" aria-hidden="true">&middot;</span>
            <span className={`ship-metrics__item${metricsLanded ? ' ship-metrics__item--landed' : ''}`}>
              <span className="ship-metrics__num">{displayMetrics.openCount}</span> open
            </span>
            <span className="ship-metrics__sep" aria-hidden="true">&middot;</span>
            <span className={`ship-metrics__item ship-metrics__item--gold${metricsLanded ? ' ship-metrics__item--landed' : ''}`}>
              avg <span className="ship-metrics__num">{avgLabel}</span>
            </span>
          </div>
          <PulseGraph requests={requests} />
        </div>

        <div className="ship-topbar__tools">
          <ThemeToggle />
        </div>
      </header>

      {/* ==== MAIN: Submit / The Board / Known Observations ==== */}
      <div className="ship-main">
        {/* ---- LEFT: Submit ---- */}
        <section className="ship-col ship-col--submit" aria-label="Submit a request">
          <div className="ship-panel__head">
            <h2 className="ship-panel__title">Submit</h2>
            <p className="ship-panel__sub">Bugs and features. The ones you vote up get built, often within hours.</p>
          </div>
          <div className="ship-panel__scroll">
            {formSuccess ? (
              <div className="ship-form-canvas__success">
                <div className="ship-form-canvas__success-icon" aria-hidden="true">&#9998;</div>
                <p className="ship-form-canvas__success-text">Request submitted. It will appear on the board momentarily.</p>
                <button type="button" className="ship-form-canvas__reset-btn" onClick={resetForm}>
                  Submit another
                </button>
              </div>
            ) : (
              <form className="ship-form-canvas__form" onSubmit={handleFormSubmit}>
                {rateLimited && (
                  <div className="ship-form-canvas__rate-limit" role="alert">
                    Slow down. Max {RATE_LIMIT_MAX} requests per hour.
                  </div>
                )}

                {/* Honeypot */}
                <div className="ship-form__honeypot" aria-hidden="true">
                  <label htmlFor="ship-website">Website</label>
                  <input id="ship-website" type="text" value={formHoneypot} onChange={(e) => setFormHoneypot(e.target.value)} tabIndex={-1} autoComplete="off" />
                </div>

                {/* Category pill toggle */}
                <div className="ship-category-toggle" role="radiogroup" aria-label="Request type">
                  {CATEGORY_OPTIONS.map(opt => (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={formCategory === opt.value}
                      className={`ship-category-toggle__pill${formCategory === opt.value ? ' ship-category-toggle__pill--active' : ''} ship-category-toggle__pill--${opt.value}`}
                      onClick={() => handleCategoryChange(opt.value)}
                    >
                      {opt.label}
                    </button>
                  ))}
                  <div
                    className="ship-category-toggle__indicator"
                    style={{ transform: formCategory === 'bug' ? 'translateX(0)' : 'translateX(100%)' }}
                    aria-hidden="true"
                  />
                </div>

                {/* Title */}
                <div className="ship-form-canvas__field">
                  <input
                    ref={titleInputRef}
                    id="ship-title"
                    className="ship-form-canvas__title-input"
                    type="text"
                    maxLength={120}
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder="Title your request"
                    required
                    aria-label="Request title"
                  />
                  <div className="ship-form-canvas__char-count">
                    <span className={formTitle.length > 100 ? 'ship-form-canvas__char-count--warn' : ''}>{formTitle.length}/120</span>
                  </div>
                </div>

                {/* Description */}
                <div className="ship-form-canvas__field">
                  <textarea
                    id="ship-desc"
                    className="ship-form-canvas__desc-input"
                    maxLength={2000}
                    value={formDesc}
                    onChange={handleDescChange}
                    placeholder={formCategory === 'bug' ? 'Describe the bug...' : 'Describe the feature...'}
                    required
                    aria-label="Request description"
                  />
                  <div className="ship-form-canvas__char-count">
                    <span className={formDesc.length > 1800 ? 'ship-form-canvas__char-count--warn' : ''}>{formDesc.length}/2000</span>
                  </div>
                </div>

                {formError && <p className="ship-form-canvas__error" role="alert">{formError}</p>}

                <button
                  type="submit"
                  className={`ship-form-canvas__submit${formSubmitting ? ' ship-form-canvas__submit--loading' : ''}`}
                  disabled={!canSubmit || rateLimited}
                >
                  {formSubmitting ? 'Submitting...' : 'Submit Request'}
                </button>
              </form>
            )}

            {/* ---- Got an idea? A lighter path that files a feature request. ---- */}
            <div className="ship-idea">
              <QuickSubmit
                fingerprint={fingerprintRef.current}
                variant="block"
                placeholder="A rough thought is fine. What would make Void News better?"
                toggleLabel="Got an idea?"
              />
            </div>
          </div>
        </section>

        {/* ---- CENTER: The Board ---- */}
        <section className="ship-col ship-col--board" aria-label="The board">
          <div className="ship-panel__head">
            <h2 className="ship-panel__title">The Board</h2>
            <p className="ship-panel__sub">submitted to building to shipped, live.</p>
          </div>
          <div className="ship-panel__scroll ship-board__scroll">
            {loading ? (
              <div className="ship-board__loading" aria-label="Loading requests">
                {BOARD_COLUMNS.map(col => (
                  <div key={col.key} className="ship-board__loading-col">
                    <div className="ship-board__loading-header" />
                    <div className="ship-board__loading-card" />
                    <div className="ship-board__loading-card ship-board__loading-card--short" />
                  </div>
                ))}
              </div>
            ) : (
              <div className="ship-board" role="region" aria-label="Kanban board">
                {visibleColumns.map(col => {
                  const isResolved = col.key === 'resolved';
                  const cards = isResolved
                    ? col.statuses
                        .flatMap(s => grouped[s])
                        .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
                    : grouped[col.statuses[0]];
                  return (
                    <section
                      key={col.key}
                      className={`ship-column ship-column--${col.key}`}
                      aria-label={`${col.label} requests`}
                    >
                      <div className="ship-column__header">
                        <span className="ship-column__title">{col.label}</span>
                        <span className="ship-column__count">{cards.length}</span>
                      </div>
                      <div className="ship-column__cards">
                        {cards.length === 0 ? (
                          <div className="ship-column__empty">
                            {col.key === 'submitted' ? 'No requests yet' : col.key === 'shipped' ? 'Nothing shipped yet' : col.key === 'resolved' ? 'Nothing closed yet' : 'Empty'}
                          </div>
                        ) : cards.map(req => (
                          <ShipCard
                            key={req.id}
                            request={req}
                            hasVoted={votedIds.has(req.id)}
                            onVote={handleVote}
                            isNew={newIdsRef.current.has(req.id)}
                            onAnimationEnd={() => newIdsRef.current.delete(req.id)}
                            isJustShipped={justShippedIds.has(req.id)}
                            fingerprint={fingerprintRef.current}
                            replies={replyMap[req.id] || []}
                            onRepliesLoaded={(id, replies) => setReplyMap(prev => ({ ...prev, [id]: replies }))}
                            showStatusTag={isResolved}
                          />
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* ---- RIGHT: Known Observations ---- */}
        <aside className="ship-col ship-col--obs" aria-label="Known observations">
          <div className="ship-panel__head">
            <h2 className="ship-panel__title">Known Observations</h2>
            <p className="ship-panel__sub">Where the machine still stumbles, and what we are doing about it.</p>
          </div>
          <ObservationsRail fingerprint={fingerprintRef.current} />
        </aside>
      </div>

      {/* ==== BOTTOM STRIP: recent ticker + personal touch + log + Discord ==== */}
      <footer className="ship-strip">
        <div className="ship-strip__recent" aria-label="Recent activity">
          <span className="ship-strip__label">Recent</span>
          {recentActivity.length === 0 ? (
            <span className="ship-strip__empty">No requests yet. Be the first above.</span>
          ) : (
            <div className="ship-strip__items">
              {recentActivity.map(r => (
                <span key={r.id} className="ship-strip__item">
                  <span className={`ship-strip__item-status ship-strip__item-status--${r.status}`}>{STATUS_LABELS[r.status]}</span>
                  <span className="ship-strip__item-title">{r.title}</span>
                  <span className="ship-strip__item-time">{timeAgo(r.updated_at || r.created_at)}</span>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="ship-strip__aside">
          <span className="ship-strip__you" aria-label={`You have voted on ${votedIds.size} requests`}>
            you voted <span className="ship-strip__you-num">{votedIds.size}</span>
          </span>
          <button type="button" className="ship-strip__log-btn" onClick={() => setLogOpen(true)}>
            View full log
          </button>
          {/* Discord: community is coming. This is a disabled placeholder. Wire a
              real invite URL (and any webhook) in here when the server is live. */}
          <span className="ship-discord" role="note" aria-label="Discord community coming soon" title="Community is coming soon">
            <span className="ship-discord__dot" aria-hidden="true" />
            Discord &middot; coming soon
          </span>
        </div>
      </footer>

      {/* ==== SHIP LOG (overlay) ==== */}
      {logOpen && (
        <ShipOverlay title="Ship Log" onClose={() => setLogOpen(false)}>
          {requests.length === 0 ? (
            <p className="ship-overlay__intro">Nothing logged yet.</p>
          ) : (
            <div className="ship-log__entries">
              {requests
                .slice()
                .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
                .map(r => (
                  <div key={r.id} className={`ship-log__entry ship-log__entry--${r.status}`}>
                    <div className="ship-log__dot" />
                    <div className="ship-log__content">
                      <div className="ship-log__header">
                        <span className={`ship-log__status ship-log__status--${r.status}`}>{STATUS_LABELS[r.status]}</span>
                        <span className="ship-log__time">{timeAgo(r.updated_at || r.created_at)}</span>
                      </div>
                      <p className="ship-log__request-title">{r.title}</p>
                      <div className="ship-log__meta">
                        <span className={`ship-log__badge ship-log__badge--${r.category}`}>{r.category}</span>
                        {r.votes > 0 && <span className="ship-log__votes">{r.votes} vote{r.votes !== 1 ? 's' : ''}</span>}
                        {r.shipped_at && r.status === 'shipped' && (
                          <span className="ship-log__ship-time">shipped in {shipDuration(r.created_at, r.shipped_at)}</span>
                        )}
                        {r.shipped_commit && (
                          <a className="ship-log__commit" href={`https://github.com/aacrit/void--news/commit/${r.shipped_commit}`} target="_blank" rel="noopener">
                            {r.shipped_commit.slice(0, 7)}
                          </a>
                        )}
                      </div>
                      {r.ceo_response && <p className="ship-log__response">{r.ceo_response}</p>}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </ShipOverlay>
      )}
    </main>
  );
}

/* ===========================================================================
   SHIP CARD (with Ship Clock, Ship Diff, Thread Replies)
   =========================================================================== */

function ShipCard({
  request,
  hasVoted,
  onVote,
  isNew,
  onAnimationEnd,
  isJustShipped,
  fingerprint,
  replies,
  onRepliesLoaded,
  showStatusTag = false,
}: {
  request: ShipRequest;
  hasVoted: boolean;
  onVote: (id: string) => void;
  isNew: boolean;
  onAnimationEnd: () => void;
  isJustShipped: boolean;
  fingerprint: string;
  replies: ShipReply[];
  onRepliesLoaded: (id: string, replies: ShipReply[]) => void;
  /** In the merged Resolved column, print each card's own status tag. */
  showStatusTag?: boolean;
}) {
  const r = request;
  const isShipped = r.status === 'shipped';
  const isBuilding = r.status === 'building';
  const isWontShip = r.status === 'wontship';
  const isClosed = CLOSED_STATUSES.includes(r.status);
  const isOpen = ['submitted', 'triaged', 'building'].includes(r.status);

  // F11: expandable descriptions
  const [expanded, setExpanded] = useState(false);
  const descRef = useRef<HTMLParagraphElement>(null);
  const [isClamped, setIsClamped] = useState(false);

  useEffect(() => {
    const el = descRef.current;
    if (!el) return;
    setIsClamped(el.scrollHeight > el.clientHeight + 1);
  }, [r.description]);

  // Scene 3: vote arrow pop
  const [arrowPop, setArrowPop] = useState(false);
  const [inkSplash, setInkSplash] = useState(false);
  const handleVoteClick = useCallback(() => {
    onVote(r.id);
    if (!hasVoted) {
      setArrowPop(true);
      setInkSplash(true);
      setTimeout(() => setInkSplash(false), 450);
    }
  }, [onVote, r.id, hasVoted]);

  // Ship Clock (Feature #1): live timer, updates every 60s
  const [clockValue, setClockValue] = useState(() => isOpen ? elapsedTimer(r.created_at) : '');
  const [clockFrozen, setClockFrozen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setClockValue(elapsedTimer(r.created_at));
    }, 60000);
    return () => clearInterval(interval);
  }, [isOpen, r.created_at]);

  // Freeze clock when shipped via realtime
  useEffect(() => {
    if (isJustShipped && r.shipped_at) {
      setClockValue(shipDuration(r.created_at, r.shipped_at));
      setClockFrozen(true);
    }
  }, [isJustShipped, r.shipped_at, r.created_at]);

  // Ship Diff (Feature #4)
  const [diffOpen, setDiffOpen] = useState(false);

  // Thread Replies (Feature #5)
  const [threadOpen, setThreadOpen] = useState(false);
  const [replyBody, setReplyBody] = useState('');
  const [repliesLoaded, setRepliesLoaded] = useState(false);
  const [replySubmitting, setReplySubmitting] = useState(false);

  const handleThreadToggle = useCallback(async () => {
    if (!threadOpen && !repliesLoaded) {
      const fetched = await fetchShipReplies(r.id);
      onRepliesLoaded(r.id, fetched);
      setRepliesLoaded(true);
    }
    setThreadOpen(v => !v);
  }, [threadOpen, repliesLoaded, r.id, onRepliesLoaded]);

  const handleReplySubmit = useCallback(async () => {
    if (!replyBody.trim() || replySubmitting) return;
    if (!checkReplyRateLimit()) return;
    setReplySubmitting(true);
    const result = await submitShipReply(r.id, replyBody.trim(), fingerprint);
    if (result) {
      recordReply();
      setReplyBody('');
    }
    setReplySubmitting(false);
  }, [replyBody, replySubmitting, r.id, fingerprint]);

  const handleReplyKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleReplySubmit();
    }
  }, [handleReplySubmit]);

  const replyCount = replies.length;

  const classes = [
    'ship-card',
    isShipped && 'ship-card--shipped',
    isBuilding && 'ship-card--building',
    isClosed && 'ship-card--closed',
    isClosed && `ship-card--${r.status}`,
    isNew && 'ship-card--new',
    isJustShipped && 'ship-card--just-shipped',
  ].filter(Boolean).join(' ');

  return (
    <article
      className={classes}
      onAnimationEnd={isNew ? onAnimationEnd : undefined}
    >
      <div className="ship-card__top">
        {showStatusTag && (
          <span className={`ship-card__status-tag ship-card__status-tag--${r.status}`}>{STATUS_LABELS[r.status]}</span>
        )}
        <span className={`ship-card__badge ship-card__badge--${r.category}`}>{r.category}</span>
        <span className="ship-card__badge">{r.area}</span>
        {r.priority && <span className={`ship-card__priority ship-card__priority--${r.priority}`}>{r.priority.toUpperCase()}</span>}
      </div>
      <p className="ship-card__title">{r.title}</p>
      <p
        ref={descRef}
        className={`ship-card__desc${expanded ? ' ship-card__desc--expanded' : ''}`}
      >
        {r.description}
      </p>
      {isClamped && !expanded && (
        <button className="ship-card__expand" onClick={() => setExpanded(true)} aria-label="Show full description">more</button>
      )}
      {expanded && (
        <button className="ship-card__expand" onClick={() => setExpanded(false)} aria-label="Collapse description">less</button>
      )}

      {/* Ship Clock (Feature #1) */}
      {(isOpen || clockFrozen) && (
        <div className={`ship-card__clock${clockFrozen ? ' ship-card__clock--frozen' : ''}`} aria-label={`Elapsed time: ${clockValue}`}>
          {clockValue}
        </div>
      )}

      <div className="ship-card__meta">
        <span className="ship-card__time">{timeAgo(r.created_at)}</span>
        <div className="ship-card__meta-right">
          {replyCount > 0 && (
            <button className="ship-card__reply-count" onClick={handleThreadToggle} aria-label={`${replyCount} ${replyCount === 1 ? 'reply' : 'replies'}`}>
              {replyCount} {replyCount === 1 ? 'reply' : 'replies'}
            </button>
          )}
          {replyCount === 0 && (
            <button className="ship-card__reply-count" onClick={handleThreadToggle} aria-label="Add a reply">
              reply
            </button>
          )}
          <button
            className={`ship-card__vote${hasVoted ? ' ship-card__vote--voted' : ''}${inkSplash ? ' ship-card__vote--splashing' : ''}`}
            onClick={handleVoteClick}
            aria-label={hasVoted ? `Voted (${r.votes})` : `Vote (${r.votes})`}
            title={hasVoted ? 'Already voted' : 'Upvote this request'}
          >
            <span
              className={`ship-card__vote-arrow${arrowPop ? ' ship-card__vote-arrow--pop' : ''}`}
              onAnimationEnd={() => setArrowPop(false)}
            >
              {hasVoted ? '▲' : '△'}
            </span>
            {r.votes}
            {/* Ink splash micro-dots */}
            <span className="ship-card__vote-splash" />
            <span className="ship-card__vote-splash" />
            <span className="ship-card__vote-splash" />
            <span className="ship-card__vote-splash" />
          </button>
        </div>
      </div>

      {isBuilding && r.claude_branch && (
        <div className="ship-card__branch">
          <span className="ship-card__pulse" aria-hidden="true" />
          <span className="sr-only">Building</span>
          {r.claude_branch}
        </div>
      )}

      {isShipped && (
        <div className="ship-card__shipped-info">
          {r.shipped_at && <div className="ship-card__ship-time">Shipped in {shipDuration(r.created_at, r.shipped_at)}</div>}
          {r.shipped_commit && (
            <a className="ship-card__commit" href={`https://github.com/aacrit/void--news/commit/${r.shipped_commit}`} target="_blank" rel="noopener">
              {r.shipped_commit.slice(0, 7)}
            </a>
          )}
        </div>
      )}

      {/* Ship Diff (Feature #4) */}
      {isShipped && r.shipped_diff_summary && (
        <div className="ship-card__diff">
          <button className="ship-card__diff-toggle" onClick={() => setDiffOpen(v => !v)} aria-expanded={diffOpen}>
            {diffOpen ? '▴ Hide changes' : '▾ View changes'}
          </button>
          {diffOpen && (
            <div className="ship-card__diff-content">{r.shipped_diff_summary}</div>
          )}
        </div>
      )}

      {isClosed && r.ceo_response && (
        <div className="ship-card__ceo-response">
          <span className="ship-card__ceo-label">{isWontShip ? 'CEO Response' : 'Response'}</span>
          {r.ceo_response}
        </div>
      )}
      {r.status === 'triaged' && r.ceo_response && (
        <div className="ship-card__ceo-response"><span className="ship-card__ceo-label">Response</span>{r.ceo_response}</div>
      )}

      {/* Thread Replies (Feature #5) */}
      {threadOpen && (
        <div className="ship-card__thread">
          {replies.length === 0 && repliesLoaded && (
            <p className="ship-card__thread-empty">No replies yet</p>
          )}
          {replies.map(reply => (
            <div key={reply.id} className="ship-card__thread-reply">
              <span className="ship-card__thread-time">{timeAgo(reply.created_at)}</span>
              <span className="ship-card__thread-body">{reply.body}</span>
            </div>
          ))}
          <div className="ship-card__thread-input-row">
            <input
              className="ship-card__thread-input"
              type="text"
              maxLength={280}
              value={replyBody}
              onChange={(e) => setReplyBody(e.target.value)}
              onKeyDown={handleReplyKeyDown}
              placeholder="Reply..."
              aria-label="Reply to this request"
            />
            <button
              className="ship-card__thread-send"
              onClick={handleReplySubmit}
              disabled={!replyBody.trim() || replySubmitting}
              aria-label="Send reply"
            >
              &rarr;
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
