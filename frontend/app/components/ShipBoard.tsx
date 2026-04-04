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
   void --ship v2 — "Form-first canvas. Graph paper. Extremely dynamic."

   Tier 1 (Hero):   Submit form always visible on canvas, graph-paper bg,
                     category pill toggle, request templates.
   Tier 2 (Compact): Summary line + Pulse Graph sparkline, ship clock.
   Tier 3 (Expand):  Kanban board + void --log (collapsed by default),
                     thread replies, ship diff summaries.

   All 7 cinematic scenes preserved. 5 new features added.
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
];

const EDITION_SLUGS: Edition[] = ['world', 'us', 'europe', 'south-asia'];

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

// ---- Organic Divider (draw-in on scroll) ----
function OrganicDivider() {
  const ref = useRef<SVGSVGElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.setAttribute('data-visible', 'true'); io.unobserve(el); }
    }, { threshold: 0.5 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <svg ref={ref} className="ship-divider" viewBox="0 0 600 4" preserveAspectRatio="none" aria-hidden="true">
      <path d="M0,2 C50,0.5 100,3.5 150,2 C200,0.5 250,3 300,2 C350,1 400,3.5 450,2 C500,0.5 550,3 600,2" />
    </svg>
  );
}

// ---- InkDroplet (splat on scroll) ----
function InkDroplet() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.setAttribute('data-visible', 'true'); io.unobserve(el); }
    }, { threshold: 0.5 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className="ship-ink-droplet" aria-hidden="true">
      <div className="ship-ink-droplet__dot" />
    </div>
  );
}

// ---- Pulse Graph (Feature #3) ----
function PulseGraph({ requests }: { requests: ShipRequest[] }) {
  const svgRef = useRef<SVGSVGElement>(null);

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
      ref={svgRef}
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
   MAIN COMPONENT
   =========================================================================== */

export default function ShipBoard() {
  const [requests, setRequests] = useState<ShipRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [votedIds, setVotedIds] = useState<Set<string>>(new Set());
  const fingerprintRef = useRef<string>('');
  const isMobile = useIsMobile();

  // Expandable sections
  const [boardOpen, setBoardOpen] = useState(false);
  const [logOpen, setLogOpen] = useState(false);

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
  const grouped: Record<ShipStatus, ShipRequest[]> = { submitted: [], triaged: [], building: [], shipped: [], wontship: [] };
  for (const r of requests) { if (grouped[r.status]) grouped[r.status].push(r); }
  for (const status of STATUS_ORDER) {
    if (status === 'shipped') {
      grouped[status].sort((a, b) => new Date(b.shipped_at || b.created_at).getTime() - new Date(a.shipped_at || a.created_at).getTime());
    } else {
      grouped[status].sort((a, b) => b.votes - a.votes || new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    }
  }

  // Recent activity (5 most recent)
  const recentActivity = useMemo(() =>
    requests
      .slice()
      .sort((a, b) => new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
      .slice(0, 5),
    [requests]
  );

  const visibleStatuses = isMobile
    ? STATUS_ORDER.filter(s => grouped[s].length > 0 || s === 'submitted')
    : STATUS_ORDER;

  return (
    <main className="ship-page" data-dash-expanded={boardOpen || logOpen || undefined}>
      {/* ---- Back nav + theme ---- */}
      <nav className="ship-cold-open-back" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Link href="/" className="ship-page__back" aria-label="Back to void --news">&larr; void --news</Link>
        <ThemeToggle />
      </nav>

      {/* ---- Header ---- */}
      <header className="ship-page__header ship-cold-open-header">
        <div className="ship-page__brand">
          <Link href="/" aria-label="void --news home" className="ship-page__logo">
            <LogoFull height={22} />
          </Link>
          <span className="ship-page__brand-suffix">--ship</span>
        </div>
        <h1 className="ship-page__title">Request, vote, watch it deploy.</h1>
        <p className="ship-page__subtitle">
          Submit bugs and features. The ones you vote for get built — often within hours.
        </p>
      </header>

      {/* ==== TIER 1: FORM-FIRST CANVAS ==== */}
      <section className="ship-form-canvas ship-hero-form ship-cold-open-metrics" aria-label="Submit a request">
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
                Slow down — max {RATE_LIMIT_MAX} requests per hour.
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
      </section>

      <InkDroplet />
      <OrganicDivider />

      {/* ==== TIER 2: COMPACT DASHBOARD ==== */}
      {!loading && (
        <section className="ship-dashboard ship-cold-open-column" aria-label="Dashboard summary">
          <div className="ship-dashboard__summary">
            <div className="ship-dashboard__metrics">
              <span className={`ship-dashboard__metric ship-dashboard__metric--gold${metricsLanded ? ' ship-dashboard__metric--landed' : ''}`}>
                {displayMetrics.totalShipped} shipped
              </span>
              <span className="ship-dashboard__sep" aria-hidden="true">&middot;</span>
              <span className={`ship-dashboard__metric${metricsLanded ? ' ship-dashboard__metric--landed' : ''}`}>
                {displayMetrics.openCount} open
              </span>
              <span className="ship-dashboard__sep" aria-hidden="true">&middot;</span>
              <span className={`ship-dashboard__metric ship-dashboard__metric--gold${metricsLanded ? ' ship-dashboard__metric--landed' : ''}`}>
                avg {displayMetrics.avgShipTimeHours > 0 ? `${displayMetrics.avgShipTimeHours.toFixed(1)}h` : '\u2014'}
              </span>
            </div>
            <PulseGraph requests={requests} />
          </div>
          <div className="ship-dashboard__actions">
            <button
              className={`ship-dashboard__toggle${boardOpen ? ' ship-dashboard__toggle--open' : ''}`}
              onClick={() => setBoardOpen(v => !v)}
              aria-expanded={boardOpen}
              aria-controls="ship-board-section"
            >
              {boardOpen ? '\u25B4 Hide Board' : '\u25BE View Board'}
            </button>
            <button
              className={`ship-dashboard__toggle${logOpen ? ' ship-dashboard__toggle--open' : ''}`}
              onClick={() => setLogOpen(v => !v)}
              aria-expanded={logOpen}
              aria-controls="ship-log-section"
            >
              {logOpen ? '\u25B4 Hide Log' : '\u25BE View Log'}
            </button>
          </div>
        </section>
      )}

      {/* ---- Recent Activity (always visible) ---- */}
      {!loading && (
        <section className="ship-recent ship-cold-open-column" aria-label="Recent activity">
          <h2 className="ship-recent__title">Recent</h2>
          <div className="ship-recent__list">
            {recentActivity.length === 0 ? (
              <p className="ship-recent__empty">No requests yet. Be the first to submit one above.</p>
            ) : recentActivity.map(r => (
              <div key={r.id} className={`ship-recent__item ship-recent__item--${r.status}`}>
                <span className={`ship-recent__status ship-recent__status--${r.status}`}>
                  {STATUS_LABELS[r.status]}
                </span>
                <span className="ship-recent__item-title">{r.title}</span>
                <span className="ship-recent__time">{timeAgo(r.updated_at || r.created_at)}</span>
                {['submitted', 'triaged', 'building'].includes(r.status) && (
                  <span className="ship-recent__clock">{elapsedTimer(r.created_at)}</span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <OrganicDivider />
      <InkDroplet />

      {/* ==== TIER 3: EXPANDABLE BOARD ==== */}
      {boardOpen && !loading && (
        <section
          id="ship-board-section"
          className="ship-board-section ship-board-section--open"
          aria-label="Ship request board"
        >
          {/* Loading skeleton */}
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
            <div className="ship-board" role="region" aria-label="Kanban board">
              {visibleStatuses.map(status => (
                <section
                  key={status}
                  className={`ship-column ship-column--${status}`}
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
                        fingerprint={fingerprintRef.current}
                        replies={replyMap[req.id] || []}
                        onRepliesLoaded={(id, replies) => setReplyMap(prev => ({ ...prev, [id]: replies }))}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ==== TIER 3: EXPANDABLE LOG ==== */}
      {logOpen && !loading && requests.length > 0 && (
        <section
          id="ship-log-section"
          className="ship-log ship-board-section--open"
          aria-label="void --log activity feed"
        >
          <h2 className="ship-log__title">void --log</h2>
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
        </section>
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
}) {
  const r = request;
  const isShipped = r.status === 'shipped';
  const isBuilding = r.status === 'building';
  const isWontShip = r.status === 'wontship';
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
              {hasVoted ? '\u25B2' : '\u25B3'}
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
            {diffOpen ? '\u25B4 Hide changes' : '\u25BE View changes'}
          </button>
          {diffOpen && (
            <div className="ship-card__diff-content">{r.shipped_diff_summary}</div>
          )}
        </div>
      )}

      {isWontShip && r.ceo_response && (
        <div className="ship-card__ceo-response"><span className="ship-card__ceo-label">CEO Response</span>{r.ceo_response}</div>
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
