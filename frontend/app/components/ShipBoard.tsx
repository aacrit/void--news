'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import {
  fetchShipRequests,
  submitShipRequest,
  voteOnShipRequest,
  subscribeToShipRequests,
  generateFingerprint,
} from '../lib/supabase';
import type { ShipRequest, ShipStatus, ShipCategory, ShipArea, Edition } from '../lib/types';

/* ==========================================================================
   void --ship — "Request, vote, watch it deploy."
   Public Kanban board for bugs/features. Realtime via Supabase.
   7-scene cinematic motion. Full accessibility (focus trap, ARIA).
   ========================================================================== */

const STATUS_ORDER: ShipStatus[] = ['submitted', 'triaged', 'building', 'shipped', 'wontship'];
const STATUS_LABELS: Record<ShipStatus, string> = {
  submitted: 'Submitted',
  triaged: 'Triaged',
  building: 'Building',
  shipped: 'Shipped',
  wontship: "Won't Ship",
};

const CATEGORY_OPTIONS: { value: ShipCategory; label: string }[] = [
  { value: 'bug', label: 'Bug' },
  { value: 'feature', label: 'Feature' },
  { value: 'enhancement', label: 'Enhancement' },
];

const AREA_OPTIONS: { value: ShipArea; label: string }[] = [
  { value: 'frontend', label: 'Frontend' },
  { value: 'pipeline', label: 'Pipeline' },
  { value: 'bias', label: 'Bias Engine' },
  { value: 'audio', label: 'Audio' },
  { value: 'design', label: 'Design' },
  { value: 'other', label: 'Other' },
];

const EDITION_SLUGS: Edition[] = ['world', 'us', 'europe', 'south-asia'];

// ---- Rate limit: max 5 submissions per hour ----
const RATE_LIMIT_KEY = 'void-ship-submissions';
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW = 3600000;

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

// ---- Edition auto-detect (F21) ----
function detectEdition(): Edition | null {
  if (typeof window === 'undefined') return null;
  // Check URL search params
  const params = new URLSearchParams(window.location.search);
  const fromParam = params.get('edition');
  if (fromParam && EDITION_SLUGS.includes(fromParam as Edition)) return fromParam as Edition;
  // Check referrer for edition slug
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

// ---- Metrics countup easing (Scene 5) ----
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

/* ===========================================================================
   MAIN COMPONENT
   =========================================================================== */

export default function ShipBoard() {
  const [requests, setRequests] = useState<ShipRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [votedIds, setVotedIds] = useState<Set<string>>(new Set());
  const fingerprintRef = useRef<string>('');
  const submitBtnRef = useRef<HTMLButtonElement>(null);
  const isMobile = useIsMobile();

  // F20: track IDs that arrived via INSERT (not UPDATE)
  const newIdsRef = useRef<Set<string>>(new Set());
  // Scene 6: track IDs that just transitioned to shipped
  const [justShippedIds, setJustShippedIds] = useState<Set<string>>(new Set());

  // Scene 5: animated metric values
  const [animatedMetrics, setAnimatedMetrics] = useState<{
    totalShipped: number; openCount: number; totalRequests: number; avgShipTimeHours: number;
  } | null>(null);
  const [metricsLanded, setMetricsLanded] = useState(false);
  const metricsAnimatedRef = useRef(false);

  useEffect(() => {
    fingerprintRef.current = generateFingerprint();
    setVotedIds(getVotedIds());
    fetchShipRequests().then(data => {
      setRequests(data);
      setLoading(false);
    });
    const unsub = subscribeToShipRequests((payload) => {
      setRequests(prev => {
        if (payload.eventType === 'INSERT') {
          // F20: track new inserts for animation
          newIdsRef.current.add(payload.new.id);
          return [payload.new, ...prev];
        }
        if (payload.eventType === 'UPDATE') {
          // Scene 6: detect shipped transitions
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
    return unsub;
  }, []);

  // Scene 5: countup animation after data loads
  useEffect(() => {
    if (loading || metricsAnimatedRef.current || requests.length === 0) return;
    metricsAnimatedRef.current = true;
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
  }, [loading, requests]);

  // When metrics change after initial animation, update instantly
  const liveMetrics = computeMetrics(requests);
  const displayMetrics = animatedMetrics && !metricsLanded ? animatedMetrics : liveMetrics;

  const handleVote = useCallback(async (requestId: string) => {
    if (votedIds.has(requestId)) return;
    const fp = fingerprintRef.current;
    const success = await voteOnShipRequest(requestId, fp);
    if (success) {
      recordVote(requestId);
      setVotedIds(prev => new Set([...prev, requestId]));
      setRequests(prev => prev.map(r => r.id === requestId ? { ...r, votes: r.votes + 1 } : r));
    }
  }, [votedIds]);

  // Group by status
  const grouped: Record<ShipStatus, ShipRequest[]> = { submitted: [], triaged: [], building: [], shipped: [], wontship: [] };
  for (const r of requests) { if (grouped[r.status]) grouped[r.status].push(r); }
  for (const status of STATUS_ORDER) {
    if (status === 'shipped') {
      grouped[status].sort((a, b) => new Date(b.shipped_at || b.created_at).getTime() - new Date(a.shipped_at || a.created_at).getTime());
    } else {
      grouped[status].sort((a, b) => b.votes - a.votes || new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
  }

  // F06: on mobile, hide empty columns (except submitted which always shows)
  const visibleStatuses = isMobile
    ? STATUS_ORDER.filter(s => grouped[s].length > 0 || s === 'submitted')
    : STATUS_ORDER;

  return (
    <main className="ship-page">
      <nav className="ship-cold-open-back">
        <Link href="/" className="ship-page__back" aria-label="Back to void --news">&larr; void --news</Link>
      </nav>

      <header className="ship-page__header ship-cold-open-header">
        <p className="ship-page__brand">void --ship</p>
        <h1 className="ship-page__title">Request, vote, watch it deploy.</h1>
        <p className="ship-page__subtitle">
          Submit bugs and features. The ones you vote for get built — often within hours.
          Every shipped item links to its commit.
        </p>
      </header>

      <div className="ship-metrics ship-cold-open-metrics">
        <div className="ship-metrics__item">
          <span className={`ship-metrics__value ship-metrics__value--gold${metricsLanded ? ' ship-metrics__value--landed' : ''}`}>
            {displayMetrics.totalShipped}
          </span>
          <span className="ship-metrics__label">Shipped</span>
        </div>
        <div className="ship-metrics__item">
          <span className={`ship-metrics__value${metricsLanded ? ' ship-metrics__value--landed' : ''}`}>
            {displayMetrics.openCount}
          </span>
          <span className="ship-metrics__label">Open</span>
        </div>
        <div className="ship-metrics__item">
          <span className={`ship-metrics__value${metricsLanded ? ' ship-metrics__value--landed' : ''}`}>
            {displayMetrics.totalRequests}
          </span>
          <span className="ship-metrics__label">Total</span>
        </div>
        <div className="ship-metrics__item">
          <span className={`ship-metrics__value ship-metrics__value--gold${metricsLanded ? ' ship-metrics__value--landed' : ''}`}>
            {displayMetrics.avgShipTimeHours > 0 ? `${displayMetrics.avgShipTimeHours.toFixed(1)}h` : '\u2014'}
          </span>
          <span className="ship-metrics__label">Avg Ship Time</span>
        </div>
      </div>

      <div className="ship-actions ship-cold-open-actions">
        <button
          ref={submitBtnRef}
          className="ship-actions__submit-btn"
          onClick={() => setShowForm(true)}
        >
          + Submit Request
        </button>
      </div>

      {loading ? (
        <div className="ship-board__loading" aria-label="Loading requests">
          {STATUS_ORDER.map(status => (
            <div key={status} className="ship-board__loading-col">
              <div className="ship-board__loading-header" />
              <div className="ship-board__loading-card" />
              <div className="ship-board__loading-card ship-board__loading-card--short" />
            </div>
          ))}
        </div>
      ) : (
        <div className="ship-board" role="region" aria-label="Ship request board">
          {visibleStatuses.map(status => (
            <section
              key={status}
              className={`ship-column ship-column--${status} ship-cold-open-column${!isMobile && grouped[status].length === 0 ? '' : ''}`}
              aria-label={`${STATUS_LABELS[status]} requests`}
            >
              <div className="ship-column__header">
                <span className="ship-column__title">{STATUS_LABELS[status]}</span>
                <span className="ship-column__count">{grouped[status].length}</span>
              </div>
              <div className="ship-column__cards">
                {grouped[status].length === 0 ? (
                  <div className="ship-column__empty">
                    {status === 'submitted' ? 'No requests yet' : status === 'shipped' ? 'Nothing shipped yet' : 'Empty'}
                  </div>
                ) : grouped[status].map(req => (
                  <ShipCard
                    key={req.id}
                    request={req}
                    hasVoted={votedIds.has(req.id)}
                    onVote={handleVote}
                    isNew={newIdsRef.current.has(req.id)}
                    onAnimationEnd={() => newIdsRef.current.delete(req.id)}
                    isJustShipped={justShippedIds.has(req.id)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {showForm && (
        <SubmitForm
          onClose={() => {
            setShowForm(false);
            submitBtnRef.current?.focus();
          }}
          fingerprint={fingerprintRef.current}
        />
      )}
    </main>
  );
}

/* ===========================================================================
   SHIP CARD
   =========================================================================== */

function ShipCard({
  request,
  hasVoted,
  onVote,
  isNew,
  onAnimationEnd,
  isJustShipped,
}: {
  request: ShipRequest;
  hasVoted: boolean;
  onVote: (id: string) => void;
  isNew: boolean;
  onAnimationEnd: () => void;
  isJustShipped: boolean;
}) {
  const r = request;
  const isShipped = r.status === 'shipped';
  const isBuilding = r.status === 'building';
  const isWontShip = r.status === 'wontship';

  // F11: expandable descriptions
  const [expanded, setExpanded] = useState(false);
  const descRef = useRef<HTMLParagraphElement>(null);
  const [isClamped, setIsClamped] = useState(false);

  useEffect(() => {
    const el = descRef.current;
    if (!el) return;
    // Check if text is actually clamped
    setIsClamped(el.scrollHeight > el.clientHeight + 1);
  }, [r.description]);

  // Scene 3: vote arrow pop
  const [arrowPop, setArrowPop] = useState(false);
  const handleVoteClick = useCallback(() => {
    onVote(r.id);
    if (!hasVoted) {
      setArrowPop(true);
    }
  }, [onVote, r.id, hasVoted]);

  const classes = [
    'ship-card',
    isShipped && 'ship-card--shipped',
    isBuilding && 'ship-card--building',
    isWontShip && 'ship-card--wontship',
    isNew && 'ship-card--new',
    isJustShipped && 'ship-card--just-shipped',
  ].filter(Boolean).join(' ');

  return (
    <article
      className={classes}
      onAnimationEnd={isNew ? onAnimationEnd : undefined}
    >
      <div className="ship-card__top">
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
        <button
          className="ship-card__expand"
          onClick={() => setExpanded(true)}
          aria-label="Show full description"
        >
          more
        </button>
      )}
      {expanded && (
        <button
          className="ship-card__expand"
          onClick={() => setExpanded(false)}
          aria-label="Collapse description"
        >
          less
        </button>
      )}
      <div className="ship-card__meta">
        <span className="ship-card__time">{timeAgo(r.created_at)}</span>
        <button
          className={`ship-card__vote${hasVoted ? ' ship-card__vote--voted' : ''}`}
          onClick={handleVoteClick}
          aria-label={hasVoted ? `Voted (${r.votes})` : `Vote (${r.votes})`}
          title={hasVoted ? 'Already voted' : 'Upvote this request'}
        >
          <span
            className={`ship-card__vote-arrow${arrowPop ? ' ship-card__vote-arrow--pop' : ''}`}
            onAnimationEnd={() => setArrowPop(false)}
          >
            {hasVoted ? '\u25B2' : '\u25B3'}
          </span>
          {r.votes}
        </button>
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
            <a
              className="ship-card__commit"
              href={`https://github.com/aacrit/void--news/commit/${r.shipped_commit}`}
              target="_blank"
              rel="noopener"
            >
              {r.shipped_commit.slice(0, 7)}
            </a>
          )}
        </div>
      )}
      {isWontShip && r.ceo_response && (
        <div className="ship-card__ceo-response"><span className="ship-card__ceo-label">CEO Response</span>{r.ceo_response}</div>
      )}
      {r.status === 'triaged' && r.ceo_response && (
        <div className="ship-card__ceo-response"><span className="ship-card__ceo-label">Response</span>{r.ceo_response}</div>
      )}
    </article>
  );
}

/* ===========================================================================
   SUBMIT FORM
   =========================================================================== */

function SubmitForm({ onClose, fingerprint }: { onClose: () => void; fingerprint: string }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<ShipCategory>('feature');
  const [area, setArea] = useState<ShipArea>('other');
  const [honeypot, setHoneypot] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // F21: auto-detect edition context
  const editionRef = useRef<Edition | null>(detectEdition());

  useEffect(() => { titleRef.current?.focus(); }, []);

  const canSubmit = title.trim().length >= 5 && description.trim().length >= 10 && !submitting;
  const rateLimited = !checkRateLimit();

  // F10: unsaved changes guard
  const hasUnsavedChanges = title.trim().length > 0 || description.trim().length > 0;

  const guardedClose = useCallback(() => {
    if (hasUnsavedChanges && !success) {
      if (!confirm('Discard unsaved changes?')) return;
    }
    onClose();
  }, [hasUnsavedChanges, success, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || rateLimited) return;
    // Honeypot: if filled by bot, silently "succeed"
    if (honeypot) { setSuccess(true); return; }
    setSubmitting(true);
    setError('');
    const deviceInfo = typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 180) : null;
    const result = await submitShipRequest({
      title: title.trim(),
      description: description.trim(),
      category,
      area,
      edition_context: editionRef.current,
      device_info: deviceInfo,
      ip_hash: fingerprint,
    });
    if (result) { recordSubmission(); setSuccess(true); } else { setError('Failed to submit. Please try again.'); }
    setSubmitting(false);
  };

  // F01: focus trap + Escape with unsaved guard
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        guardedClose();
        return;
      }
      // Focus trap: cycle Tab within form
      if (e.key === 'Tab' && formRef.current) {
        const focusable = formRef.current.querySelectorAll<HTMLElement>(
          'input:not([tabindex="-1"]), textarea, select, button:not([disabled])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [guardedClose]);

  return (
    <div
      className="ship-form-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Submit a request"
      onClick={(e) => { if (e.target === e.currentTarget) guardedClose(); }}
    >
      <form ref={formRef} className="ship-form" onSubmit={handleSubmit}>
        {success ? (
          <div className="ship-form__success">
            <div className="ship-form__success-icon" aria-hidden="true">&#9998;</div>
            <p className="ship-form__success-text">Request submitted. It will appear on the board momentarily.</p>
            <div className="ship-form__footer" style={{ justifyContent: 'center', marginTop: 'var(--space-4)' }}>
              <button type="button" className="ship-form__btn ship-form__btn--cancel" onClick={onClose}>Close</button>
            </div>
          </div>
        ) : (
          <>
            <h2 className="ship-form__title">Submit a Request</h2>
            {rateLimited && <div className="ship-form__rate-limit">Slow down — max {RATE_LIMIT_MAX} requests per hour.</div>}

            {/* Honeypot */}
            <div className="ship-form__honeypot" aria-hidden="true">
              <label htmlFor="ship-website">Website</label>
              <input id="ship-website" type="text" value={honeypot} onChange={(e) => setHoneypot(e.target.value)} tabIndex={-1} autoComplete="off" />
            </div>

            <div className="ship-form__group">
              <label className="ship-form__label" htmlFor="ship-title">Title</label>
              <input ref={titleRef} id="ship-title" className="ship-form__input" type="text" maxLength={120} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Brief description of the bug or feature" required />
              <div className="ship-form__char-count"><span className={title.length > 100 ? 'ship-form__char-count--warn' : ''}>{title.length}/120</span></div>
            </div>

            <div className="ship-form__group">
              <label className="ship-form__label" htmlFor="ship-desc">Description</label>
              <textarea id="ship-desc" className="ship-form__textarea" maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What should happen? What happens instead? Steps to reproduce?" required />
              <div className="ship-form__char-count"><span className={description.length > 1800 ? 'ship-form__char-count--warn' : ''}>{description.length}/2000</span></div>
            </div>

            <div className="ship-form__row">
              <div className="ship-form__group">
                <label className="ship-form__label" htmlFor="ship-category">Type</label>
                <select id="ship-category" className="ship-form__select" value={category} onChange={(e) => setCategory(e.target.value as ShipCategory)}>
                  {CATEGORY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div className="ship-form__group">
                <label className="ship-form__label" htmlFor="ship-area">Area</label>
                <select id="ship-area" className="ship-form__select" value={area} onChange={(e) => setArea(e.target.value as ShipArea)}>
                  {AREA_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>

            {error && <p className="ship-form__error" role="alert">{error}</p>}

            <div className="ship-form__footer">
              <button type="button" className="ship-form__btn ship-form__btn--cancel" onClick={guardedClose}>Cancel</button>
              <button
                type="submit"
                className={`ship-form__btn ship-form__btn--submit${submitting ? ' ship-form__btn--loading' : ''}`}
                disabled={!canSubmit || rateLimited}
              >
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
