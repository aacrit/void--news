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
import type { ShipRequest, ShipStatus, ShipCategory, ShipArea } from '../lib/types';

/* ==========================================================================
   void --ship — "Request, vote, watch it deploy."
   Public Kanban board for bugs/features. Realtime via Supabase.
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

/* ===========================================================================
   MAIN COMPONENT
   =========================================================================== */

export default function ShipBoard() {
  const [requests, setRequests] = useState<ShipRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [votedIds, setVotedIds] = useState<Set<string>>(new Set());
  const fingerprintRef = useRef<string>('');

  useEffect(() => {
    fingerprintRef.current = generateFingerprint();
    setVotedIds(getVotedIds());
    fetchShipRequests().then(data => { setRequests(data); setLoading(false); });
    const unsub = subscribeToShipRequests((payload) => {
      setRequests(prev => {
        if (payload.eventType === 'INSERT') return [payload.new, ...prev];
        if (payload.eventType === 'UPDATE') return prev.map(r => r.id === payload.new.id ? payload.new : r);
        if (payload.eventType === 'DELETE') return prev.filter(r => r.id !== payload.old.id);
        return prev;
      });
    });
    return unsub;
  }, []);

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

  const metrics = computeMetrics(requests);

  return (
    <div className="ship-page">
      <Link href="/" className="ship-page__back" aria-label="Back to void --news">&larr; void --news</Link>

      <header className="ship-page__header">
        <p className="ship-page__brand">void --ship</p>
        <h1 className="ship-page__title">Request, vote, watch it deploy.</h1>
        <p className="ship-page__subtitle">
          Submit bugs and features. The ones you vote for get built — often within hours.
          Every shipped item links to its commit.
        </p>
      </header>

      <div className="ship-metrics">
        <div className="ship-metrics__item">
          <span className="ship-metrics__value ship-metrics__value--gold">{metrics.totalShipped}</span>
          <span className="ship-metrics__label">Shipped</span>
        </div>
        <div className="ship-metrics__item">
          <span className="ship-metrics__value">{metrics.openCount}</span>
          <span className="ship-metrics__label">Open</span>
        </div>
        <div className="ship-metrics__item">
          <span className="ship-metrics__value">{metrics.totalRequests}</span>
          <span className="ship-metrics__label">Total</span>
        </div>
        <div className="ship-metrics__item">
          <span className="ship-metrics__value ship-metrics__value--gold">
            {metrics.avgShipTimeHours > 0 ? `${metrics.avgShipTimeHours.toFixed(1)}h` : '\u2014'}
          </span>
          <span className="ship-metrics__label">Avg Ship Time</span>
        </div>
      </div>

      <div className="ship-actions">
        <button className="ship-actions__submit-btn" onClick={() => setShowForm(true)}>+ Submit Request</button>
      </div>

      {loading ? (
        <p style={{ textAlign: 'center', color: 'var(--fg-muted)', fontFamily: 'var(--font-data)', fontSize: 'var(--text-sm)' }}>Loading requests...</p>
      ) : (
        <div className="ship-board">
          {STATUS_ORDER.map(status => (
            <div key={status} className={`ship-column ship-column--${status}`}>
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
                  <ShipCard key={req.id} request={req} hasVoted={votedIds.has(req.id)} onVote={handleVote} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && <SubmitForm onClose={() => setShowForm(false)} fingerprint={fingerprintRef.current} />}
    </div>
  );
}

/* ===========================================================================
   SHIP CARD
   =========================================================================== */

function ShipCard({ request, hasVoted, onVote }: { request: ShipRequest; hasVoted: boolean; onVote: (id: string) => void }) {
  const r = request;
  const isShipped = r.status === 'shipped';
  const isBuilding = r.status === 'building';
  const isWontShip = r.status === 'wontship';

  return (
    <div className={`ship-card${isShipped ? ' ship-card--shipped' : ''}${isBuilding ? ' ship-card--building' : ''}${isWontShip ? ' ship-card--wontship' : ''}`}>
      <div className="ship-card__top">
        <span className={`ship-card__badge ship-card__badge--${r.category}`}>{r.category}</span>
        <span className="ship-card__badge">{r.area}</span>
        {r.priority && <span className={`ship-card__priority ship-card__priority--${r.priority}`}>{r.priority.toUpperCase()}</span>}
      </div>
      <p className="ship-card__title">{r.title}</p>
      <p className="ship-card__desc">{r.description}</p>
      <div className="ship-card__meta">
        <span className="ship-card__time">{timeAgo(r.created_at)}</span>
        <button
          className={`ship-card__vote${hasVoted ? ' ship-card__vote--voted' : ''}`}
          onClick={() => onVote(r.id)}
          aria-label={hasVoted ? `Voted (${r.votes})` : `Vote (${r.votes})`}
          title={hasVoted ? 'Already voted' : 'Upvote this request'}
        >
          <span className="ship-card__vote-arrow">{hasVoted ? '\u25B2' : '\u25B3'}</span>
          {r.votes}
        </button>
      </div>
      {isBuilding && r.claude_branch && (
        <div className="ship-card__branch"><span className="ship-card__pulse" />{r.claude_branch}</div>
      )}
      {isShipped && (
        <div className="ship-card__shipped-info">
          {r.shipped_at && <div className="ship-card__ship-time">Shipped in {shipDuration(r.created_at, r.shipped_at)}</div>}
          {r.shipped_commit && <div className="ship-card__commit">{r.shipped_commit.slice(0, 7)}</div>}
        </div>
      )}
      {isWontShip && r.ceo_response && (
        <div className="ship-card__ceo-response"><span className="ship-card__ceo-label">CEO Response</span>{r.ceo_response}</div>
      )}
      {r.status === 'triaged' && r.ceo_response && (
        <div className="ship-card__ceo-response"><span className="ship-card__ceo-label">Response</span>{r.ceo_response}</div>
      )}
    </div>
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

  useEffect(() => { titleRef.current?.focus(); }, []);

  const canSubmit = title.trim().length >= 5 && description.trim().length >= 10 && !submitting;
  const rateLimited = !checkRateLimit();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || rateLimited) return;
    // Honeypot: if filled by bot, silently "succeed"
    if (honeypot) { setSuccess(true); return; }
    setSubmitting(true);
    setError('');
    const deviceInfo = typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 180) : null;
    const result = await submitShipRequest({ title: title.trim(), description: description.trim(), category, area, device_info: deviceInfo, ip_hash: fingerprint });
    if (result) { recordSubmission(); setSuccess(true); } else { setError('Failed to submit. Please try again.'); }
    setSubmitting(false);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div className="ship-form-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <form className="ship-form" onSubmit={handleSubmit} aria-label="Submit a request">
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

            {error && <p className="ship-form__error">{error}</p>}

            <div className="ship-form__footer">
              <button type="button" className="ship-form__btn ship-form__btn--cancel" onClick={onClose}>Cancel</button>
              <button type="submit" className="ship-form__btn ship-form__btn--submit" disabled={!canSubmit || rateLimited}>
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </>
        )}
      </form>
    </div>
  );
}
