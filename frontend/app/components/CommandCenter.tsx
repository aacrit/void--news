'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { supabase } from '../lib/supabase';

/* ==========================================================================
   void --news CEO Command Center
   Real-time operational dashboard for pipeline, bias engine, sources, and briefs.
   ========================================================================== */

// ---- Types ----

interface PipelineRun {
  id: string;
  status: string;
  articles_fetched: number | null;
  clusters_created: number | null;
  started_at: string;
  completed_at: string | null;
  created_at: string;
}

interface SourceStats {
  total: number;
  us_major: number;
  international: number;
  independent: number;
}

interface EditionStats {
  edition: string;
  articles: number;
  clusters: number;
  tiers: { us_major: number; international: number; independent: number };
}

interface BiasAxisStats {
  name: string;
  key: string;
  avg: number;
  min: number;
  max: number;
}

interface BriefStatus {
  edition: string;
  created_at: string;
  has_audio: boolean;
  has_opinion: boolean;
}

interface TerminalLine {
  text: string;
  type: 'cmd' | 'ok' | 'err' | 'info';
}

// ---- Agent Team Data ----

const AGENT_TEAM = [
  { division: 'Agent Engineering', agents: [{ name: 'agent-architect', role: 'Chief Agent Engineer' }] },
  { division: 'Quality', agents: [
    { name: 'analytics-expert', role: 'Benchmarking' },
    { name: 'bias-auditor', role: 'Ground truth' },
    { name: 'bias-calibrator', role: 'Score regression' },
    { name: 'pipeline-tester', role: 'Output validation' },
    { name: 'bug-fixer', role: 'Post-test fixes' },
  ]},
  { division: 'Infrastructure', agents: [
    { name: 'perf-optimizer', role: 'Performance' },
    { name: 'db-reviewer', role: 'Data quality' },
    { name: 'update-docs', role: 'Documentation' },
  ]},
  { division: 'Frontend', agents: [
    { name: 'frontend-builder', role: 'Build features' },
    { name: 'frontend-fixer', role: 'Fix UI bugs' },
    { name: 'responsive-specialist', role: 'Layout QA' },
    { name: 'uat-tester', role: 'Browser QA' },
  ]},
  { division: 'Pipeline', agents: [
    { name: 'feed-intelligence', role: 'RSS & content' },
    { name: 'nlp-engineer', role: 'Bias scoring' },
    { name: 'source-curator', role: 'Source vetting' },
  ]},
  { division: 'Audio', agents: [{ name: 'audio-engineer', role: 'Broadcast' }] },
  { division: 'Security', agents: [{ name: 'void-ciso', role: 'Security audit' }] },
  { division: 'Product', agents: [{ name: 'ceo-advisor', role: 'Strategy' }] },
  { division: 'Branding', agents: [{ name: 'logo-designer', role: 'Brand identity' }] },
];

// ---- Terminal Commands ----

const TERMINAL_COMMANDS: Record<string, { desc: string; cli: string }> = {
  'pipeline': { desc: 'Run full pipeline', cli: 'cd /home/aacrit/projects/void-news && python -m pipeline.main' },
  'validate': { desc: 'Run bias validation', cli: 'cd /home/aacrit/projects/void-news && python pipeline/validation/runner.py' },
  'validate --quick': { desc: 'Quick validation', cli: 'cd /home/aacrit/projects/void-news && python pipeline/validation/runner.py --quick' },
  'validate --verbose': { desc: 'Verbose validation', cli: 'cd /home/aacrit/projects/void-news && python pipeline/validation/runner.py --verbose' },
  'rerank': { desc: 'Re-rank stories', cli: 'cd /home/aacrit/projects/void-news && python pipeline/rerank.py' },
  'refresh-audio': { desc: 'Regenerate audio', cli: 'cd /home/aacrit/projects/void-news && python pipeline/refresh_audio.py' },
  'build': { desc: 'Build frontend', cli: 'cd /home/aacrit/projects/void-news/frontend && npm run build' },
  'deploy': { desc: 'Deploy to Pages', cli: 'cd /home/aacrit/projects/void-news && git push origin claude/deploy' },
  'security': { desc: 'Security audit', cli: 'claude --agent void-ciso "Run full security audit"' },
  'bias-audit': { desc: 'Full bias audit', cli: 'claude /bias-audit' },
  'daily-ops': { desc: 'Daily operations', cli: 'claude /daily-ops' },
  'full-audit': { desc: 'Full system audit', cli: 'claude /full-audit' },
  'help': { desc: 'Show commands', cli: '' },
};

// ---- Helpers ----

function timeAgo(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function ragClass(value: number, thresholds: { green: number; amber: number }): string {
  if (value >= thresholds.green) return 'cc-rag-green';
  if (value >= thresholds.amber) return 'cc-rag-amber';
  return 'cc-rag-red';
}

function fmtDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return 'running...';
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  const mins = Math.floor(ms / 60000);
  if (mins < 1) return '<1m';
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Morning';
  if (h < 17) return 'Afternoon';
  return 'Evening';
}

// ---- Component ----

const CC_PASS_HASH = '5a2a82'; // derived from password — client-side gate only
function hashPass(p: string): string {
  let h = 0;
  for (let i = 0; i < p.length; i++) h = ((h << 5) - h + p.charCodeAt(i)) | 0;
  return (h >>> 0).toString(16).slice(0, 6);
}

export default function CommandCenter() {
  // Auth gate
  const [authed, setAuthed] = useState(false);
  const [passInput, setPassInput] = useState('');
  const [passError, setPassError] = useState(false);

  useEffect(() => {
    try {
      if (localStorage.getItem('cc-auth') === CC_PASS_HASH) setAuthed(true);
    } catch {}
  }, []);

  function handleLogin() {
    if (hashPass(passInput) === CC_PASS_HASH) {
      localStorage.setItem('cc-auth', CC_PASS_HASH);
      setAuthed(true);
      setPassError(false);
    } else {
      setPassError(true);
    }
  }

  // State
  const [loading, setLoading] = useState(true);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [sourceStats, setSourceStats] = useState<SourceStats>({ total: 0, us_major: 0, international: 0, independent: 0 });
  const [editionStats, setEditionStats] = useState<EditionStats[]>([]);
  const [biasStats, setBiasStats] = useState<BiasAxisStats[]>([]);
  const [briefStatuses, setBriefStatuses] = useState<BriefStatus[]>([]);
  const [articleCount24h, setArticleCount24h] = useState(0);
  const [clusterStats, setClusterStats] = useState({ total: 0, multiSource: 0 });
  const [expandedPulse, setExpandedPulse] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [terminalLines, setTerminalLines] = useState<TerminalLine[]>([
    { text: 'void --news command center initialized', type: 'info' },
    { text: 'type "help" for available commands', type: 'info' },
  ]);
  const [terminalInput, setTerminalInput] = useState('');
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ---- Data Fetching ----

  const loadData = useCallback(async () => {
    if (!supabase) {
      setLoading(false);
      return;
    }

    try {
      // Parallel queries
      const [
        runsRes,
        sourcesRes,
        articles24hRes,
        clustersRes,
        multiSourceRes,
        biasRes,
        briefsRes,
        worldArticlesRes,
        usArticlesRes,
        indiaArticlesRes,
      ] = await Promise.all([
        // Recent pipeline runs
        supabase
          .from('pipeline_runs')
          .select('id, status, articles_fetched, clusters_created, started_at, completed_at, created_at')
          .order('created_at', { ascending: false })
          .limit(10),
        // Source count by tier
        supabase.from('sources').select('tier'),
        // Articles in last 24h
        supabase
          .from('articles')
          .select('id', { count: 'exact', head: true })
          .gte('created_at', new Date(Date.now() - 86400000).toISOString()),
        // Total clusters
        supabase
          .from('story_clusters')
          .select('id', { count: 'exact', head: true }),
        // Clusters with 3+ sources (count only)
        supabase
          .from('story_clusters')
          .select('id', { count: 'exact', head: true })
          .gte('source_count', 3),
        // Bias score averages
        supabase
          .from('bias_scores')
          .select('political_lean, sensationalism, opinion_fact, factual_rigor, framing')
          .limit(500),
        // Daily brief statuses
        supabase
          .from('daily_briefs')
          .select('edition, created_at, audio_url, opinion_text')
          .order('created_at', { ascending: false })
          .limit(5),
        // Edition articles: world
        supabase
          .from('articles')
          .select('id', { count: 'exact', head: true })
          .eq('section', 'world'),
        // Edition articles: us
        supabase
          .from('articles')
          .select('id', { count: 'exact', head: true })
          .eq('section', 'us'),
        // Edition articles: india
        supabase
          .from('articles')
          .select('id', { count: 'exact', head: true })
          .eq('section', 'india'),
      ]);

      // Pipeline runs
      if (runsRes.data) setPipelineRuns(runsRes.data);

      // Source stats
      if (sourcesRes.data) {
        const sources = sourcesRes.data;
        setSourceStats({
          total: sources.length,
          us_major: sources.filter((s: { tier: string }) => s.tier === 'us_major').length,
          international: sources.filter((s: { tier: string }) => s.tier === 'international').length,
          independent: sources.filter((s: { tier: string }) => s.tier === 'independent').length,
        });
      }

      // Articles 24h
      setArticleCount24h(articles24hRes.count ?? 0);

      // Cluster stats
      const totalClusters = clustersRes.count ?? 0;
      const multiSource = multiSourceRes.count ?? 0;
      setClusterStats({ total: totalClusters, multiSource });

      // Bias stats
      if (biasRes.data && biasRes.data.length > 0) {
        const scores = biasRes.data;
        const axes: { name: string; key: string }[] = [
          { name: 'Political Lean', key: 'political_lean' },
          { name: 'Sensationalism', key: 'sensationalism' },
          { name: 'Opinion/Fact', key: 'opinion_fact' },
          { name: 'Factual Rigor', key: 'factual_rigor' },
          { name: 'Framing', key: 'framing' },
        ];
        const stats = axes.map(axis => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const vals = scores.map((s: any) => s[axis.key]).filter((v: unknown) => v != null) as number[];
          if (vals.length === 0) return { ...axis, avg: 0, min: 0, max: 0 };
          const avg = vals.reduce((a: number, b: number) => a + b, 0) / vals.length;
          return { ...axis, avg: Math.round(avg * 10) / 10, min: Math.min(...vals), max: Math.max(...vals) };
        });
        setBiasStats(stats);
      }

      // Brief statuses
      if (briefsRes.data) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const briefs = briefsRes.data.map((b: any) => ({
          edition: b.edition,
          created_at: b.created_at,
          has_audio: !!b.audio_url,
          has_opinion: !!b.opinion_text,
        }));
        // Deduplicate by edition (keep latest)
        const seen = new Set<string>();
        const unique = briefs.filter((b: BriefStatus) => {
          if (seen.has(b.edition)) return false;
          seen.add(b.edition);
          return true;
        });
        setBriefStatuses(unique);
      }

      // Edition stats
      const editions: EditionStats[] = [
        { edition: 'World', articles: 0, clusters: 0, tiers: { us_major: 0, international: 0, independent: 0 } },
        { edition: 'US', articles: usArticlesRes.count ?? 0, clusters: 0, tiers: { us_major: 0, international: 0, independent: 0 } },
        { edition: 'India', articles: indiaArticlesRes.count ?? 0, clusters: 0, tiers: { us_major: 0, international: 0, independent: 0 } },
      ];
      // World gets a special count from cluster articles
      if (worldArticlesRes.count != null) {
        editions[0].articles = worldArticlesRes.count;
      }
      setEditionStats(editions);

    } catch (err) {
      console.error('Command Center data load failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ---- Keyboard Shortcuts ----

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;

      switch (e.key) {
        case 't': setDrawerOpen(prev => !prev); break;
        case '/': {
          e.preventDefault();
          setDrawerOpen(true);
          setTerminalOpen(true);
          setTimeout(() => inputRef.current?.focus(), 100);
          break;
        }
        case '?': setShortcutsOpen(true); break;
        case 'Escape':
          if (shortcutsOpen) setShortcutsOpen(false);
          else if (drawerOpen) setDrawerOpen(false);
          else setExpandedPulse(null);
          break;
        case 'r': loadData(); showToast('Refreshing data...'); break;
        case '1': case '2': case '3': case '4': case '5': case '6': {
          const keys = ['pipeline', 'sources', 'bias', 'articles', 'clusters', 'brief'];
          const idx = parseInt(e.key) - 1;
          setExpandedPulse(prev => prev === keys[idx] ? null : keys[idx]);
          break;
        }
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [loadData, shortcutsOpen, drawerOpen]);

  // ---- Terminal ----

  function processCommand(cmd: string) {
    const trimmed = cmd.trim().toLowerCase();
    const newLines: TerminalLine[] = [{ text: `$ ${cmd}`, type: 'cmd' }];

    if (trimmed === 'help' || trimmed === '?') {
      newLines.push({ text: 'Available commands:', type: 'info' });
      Object.entries(TERMINAL_COMMANDS).forEach(([key, val]) => {
        if (key !== 'help') {
          newLines.push({ text: `  ${key.padEnd(22)} ${val.desc}`, type: 'info' });
        }
      });
      newLines.push({ text: '', type: 'info' });
      newLines.push({ text: 'Keyboard: t=drawer /=terminal ?=help r=refresh 1-6=pulse Esc=close', type: 'info' });
    } else if (trimmed === 'status') {
      const lastRun = pipelineRuns[0];
      newLines.push({ text: `Pipeline: ${lastRun?.status ?? 'unknown'} (${lastRun ? timeAgo(lastRun.created_at) : 'never'})`, type: lastRun?.status === 'completed' ? 'ok' : 'err' });
      newLines.push({ text: `Sources: ${sourceStats.total} active`, type: 'ok' });
      newLines.push({ text: `Articles (24h): ${articleCount24h}`, type: 'info' });
      newLines.push({ text: `Clusters: ${clusterStats.total} total, ${clusterStats.multiSource} with 3+ sources`, type: 'info' });
    } else if (trimmed === 'clear') {
      setTerminalLines([]);
      setTerminalInput('');
      return;
    } else if (TERMINAL_COMMANDS[trimmed]) {
      const command = TERMINAL_COMMANDS[trimmed];
      newLines.push({ text: command.desc, type: 'ok' });
      if (command.cli) {
        newLines.push({ text: `Copy and run:`, type: 'info' });
        newLines.push({ text: command.cli, type: 'ok' });
      }
    } else {
      newLines.push({ text: `Unknown command: ${trimmed}. Type "help" for commands.`, type: 'err' });
    }

    setTerminalLines(prev => [...prev, ...newLines]);
    setTerminalInput('');
    setTimeout(() => {
      terminalRef.current?.scrollTo({ top: terminalRef.current.scrollHeight, behavior: 'smooth' });
    }, 50);
  }

  // ---- Toast ----

  function showToast(msg: string) {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast(msg);
    toastTimerRef.current = setTimeout(() => setToast(null), 2500);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard'));
  }

  // ---- Derived Data ----

  const lastRun = pipelineRuns[0];
  const pipelineHealthy = lastRun?.status === 'completed';
  const lastRunAge = lastRun ? (Date.now() - new Date(lastRun.created_at).getTime()) / 3600000 : Infinity;
  const pipelineFresh = lastRunAge < 8; // 4x daily = every 6h, 8h buffer
  const healthDot = pipelineHealthy && pipelineFresh ? 'cc-health-dot--green' : pipelineHealthy ? 'cc-health-dot--amber' : 'cc-health-dot--red';

  const validationPassRate = 96.9; // from CLAUDE.md — last known accuracy
  const clusterQuality = clusterStats.total > 0 ? Math.round((clusterStats.multiSource / clusterStats.total) * 100) : 0;

  const latestBrief = briefStatuses[0];
  const briefFresh = latestBrief ? (Date.now() - new Date(latestBrief.created_at).getTime()) < 28800000 : false; // 8h

  const totalArticles = editionStats.reduce((a, e) => a + e.articles, 0);
  const maxEditionArticles = Math.max(...editionStats.map(e => e.articles), 1);

  // ---- Render ----

  if (!authed) {
    return (
      <div className="cc-root">
        <div className="cc-auth-gate">
          <div className="cc-auth-card">
            <svg width="32" height="32" viewBox="0 0 40 40" fill="none" style={{ margin: '0 auto 16px' }}>
              <circle cx="20" cy="20" r="14" stroke="currentColor" strokeWidth="2.5" fill="none" />
              <line x1="10" y1="24" x2="30" y2="24" stroke="currentColor" strokeWidth="2" />
              <line x1="12" y1="16" x2="12" y2="24" stroke="currentColor" strokeWidth="1.5" />
              <line x1="28" y1="18" x2="28" y2="24" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="12" cy="15" r="2" fill="currentColor" />
              <circle cx="28" cy="17" r="2" fill="currentColor" />
            </svg>
            <h2 style={{ fontFamily: 'var(--cc-font-editorial)', fontSize: 'var(--cc-text-lg)', marginBottom: '4px' }}>Command Center</h2>
            <p style={{ color: 'var(--cc-text3)', fontSize: 'var(--cc-text-sm)', marginBottom: '20px' }}>void --news</p>
            <input
              type="password"
              value={passInput}
              onChange={e => { setPassInput(e.target.value); setPassError(false); }}
              onKeyDown={e => { if (e.key === 'Enter') handleLogin(); }}
              placeholder="Password"
              autoFocus
              style={{
                width: '100%',
                padding: '10px 14px',
                background: 'var(--cc-bg)',
                border: `1px solid ${passError ? 'var(--cc-red)' : 'var(--cc-border)'}`,
                borderRadius: 'var(--cc-radius-sm)',
                color: 'var(--cc-text)',
                fontFamily: 'var(--cc-font-mono)',
                fontSize: 'var(--cc-text-sm)',
                outline: 'none',
                marginBottom: '12px',
              }}
            />
            <button
              onClick={handleLogin}
              style={{
                width: '100%',
                padding: '10px',
                background: 'var(--cc-accent)',
                color: 'var(--cc-bg)',
                border: 'none',
                borderRadius: 'var(--cc-radius-sm)',
                fontWeight: 600,
                fontSize: 'var(--cc-text-sm)',
                cursor: 'pointer',
              }}
            >
              Enter
            </button>
            {passError && <p style={{ color: 'var(--cc-red)', fontSize: 'var(--cc-text-xs)', marginTop: '8px' }}>Incorrect password</p>}
          </div>
        </div>
      </div>
    );
  }

  if (!supabase) {
    return (
      <div className="cc-root">
        <div className="cc-empty" style={{ marginTop: '20vh' }}>
          <p style={{ fontSize: '1.125rem', marginBottom: '8px' }}>Unable to connect to data source</p>
          <p style={{ color: 'var(--cc-text3)' }}>Supabase configuration is missing.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="cc-root">
      {/* ---- Header ---- */}
      <header className="cc-header">
        <div className="cc-header__left">
          <div className="cc-header__logo">
            <svg width="20" height="20" viewBox="0 0 40 40" fill="none">
              <circle cx="20" cy="20" r="14" stroke="currentColor" strokeWidth="2.5" fill="none" />
              <line x1="10" y1="24" x2="30" y2="24" stroke="currentColor" strokeWidth="2" />
              <line x1="12" y1="16" x2="12" y2="24" stroke="currentColor" strokeWidth="1.5" />
              <line x1="28" y1="18" x2="28" y2="24" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="12" cy="15" r="2" fill="currentColor" />
              <circle cx="28" cy="17" r="2" fill="currentColor" />
            </svg>
            <span className="cc-header__logo-text">Command Center</span>
          </div>
          <span className="cc-header__subtitle">void --news</span>
        </div>
        <div className="cc-header__right">
          <span className={`cc-health-dot ${healthDot}`} role="status" aria-label={`System health: ${pipelineHealthy && pipelineFresh ? 'healthy' : pipelineHealthy ? 'stale' : 'unhealthy'}`} title="System health" />
          <a href="/" className="cc-header__back">Back to Feed</a>
        </div>
      </header>

      {/* ---- Main Dashboard ---- */}
      <main className="cc-dashboard" id="main-content">

        {/* Morning Brief Banner */}
        <div className="cc-brief">
          <div className="cc-brief__icon">{pipelineHealthy && pipelineFresh ? '\u2600' : pipelineHealthy ? '\u26A0' : '\u26A1'}</div>
          <div className="cc-brief__content">
            <div className="cc-brief__greeting">
              {getGreeting()}, Aacrit.
            </div>
            <div className="cc-brief__status">
              {loading ? 'Loading system status...' : (
                <>
                  {pipelineHealthy && pipelineFresh
                    ? `System healthy. Last pipeline ${timeAgo(lastRun!.created_at)} \u2014 ${lastRun!.articles_fetched ?? 0} articles across ${sourceStats.total} sources. ${articleCount24h} articles ingested in last 24h.`
                    : pipelineHealthy
                    ? `Pipeline completed ${timeAgo(lastRun!.created_at)} but data may be stale. Consider triggering a run.`
                    : lastRun
                    ? `Pipeline ${lastRun.status} ${timeAgo(lastRun.created_at)}. Investigate and re-run.`
                    : 'No pipeline runs found. Run the pipeline to populate data.'
                  }
                  {briefFresh && latestBrief?.has_audio ? ' Daily brief with audio is live.' : briefFresh ? ' Daily brief is live (no audio).' : ''}
                </>
              )}
            </div>
          </div>
          <button className="cc-brief__action" onClick={() => { processCommand('status'); setDrawerOpen(true); setTerminalOpen(true); }}>
            Status
          </button>
        </div>

        {/* Pulse Cards */}
        <div className="cc-pulse">
          {/* 1. Pipeline */}
          <div className="cc-pulse-col">
            <button
              className={`cc-pulse-card ${expandedPulse === 'pipeline' ? 'cc-pulse-card--expanded' : ''}`}
              onClick={() => setExpandedPulse(expandedPulse === 'pipeline' ? null : 'pipeline')}
              aria-expanded={expandedPulse === 'pipeline'}
              aria-label="Pipeline status"
            >
              <div className={`cc-pulse-card__value ${pipelineHealthy ? (pipelineFresh ? 'cc-rag-green' : 'cc-rag-amber') : 'cc-rag-red'}`}>
                {loading ? '--' : pipelineHealthy ? (pipelineFresh ? 'OK' : 'STALE') : lastRun?.status?.toUpperCase() ?? 'N/A'}
              </div>
              <div className="cc-pulse-card__label">Pipeline</div>
              {lastRun && <div className="cc-pulse-card__sub">{timeAgo(lastRun.created_at)}</div>}
            </button>
            <div className={`cc-pulse-expand ${expandedPulse === 'pipeline' ? 'cc-pulse-expand--open' : ''}`}>
              <div>
                {pipelineRuns.slice(0, 5).map(run => (
                  <div key={run.id} className="cc-pulse-expand__row">
                    <span className="cc-pulse-expand__label">{timeAgo(run.created_at)}</span>
                    <span className={`cc-pulse-expand__value ${run.status === 'completed' ? 'cc-rag-green' : 'cc-rag-red'}`}>
                      {run.status} {run.articles_fetched ? `(${run.articles_fetched} articles)` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 2. Sources */}
          <div className="cc-pulse-col">
            <button
              className={`cc-pulse-card ${expandedPulse === 'sources' ? 'cc-pulse-card--expanded' : ''}`}
              onClick={() => setExpandedPulse(expandedPulse === 'sources' ? null : 'sources')}
              aria-expanded={expandedPulse === 'sources'}
              aria-label="Source coverage"
            >
              <div className={`cc-pulse-card__value ${ragClass(sourceStats.total, { green: 350, amber: 300 })}`}>
                {loading ? '--' : sourceStats.total}
              </div>
              <div className="cc-pulse-card__label">Sources</div>
              <div className="cc-pulse-card__sub">3 tiers</div>
            </button>
            <div className={`cc-pulse-expand ${expandedPulse === 'sources' ? 'cc-pulse-expand--open' : ''}`}>
              <div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">US Major</span>
                  <span className="cc-pulse-expand__value">{sourceStats.us_major}</span>
                </div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">International</span>
                  <span className="cc-pulse-expand__value">{sourceStats.international}</span>
                </div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">Independent</span>
                  <span className="cc-pulse-expand__value">{sourceStats.independent}</span>
                </div>
              </div>
            </div>
          </div>

          {/* 3. Bias Accuracy */}
          <div className="cc-pulse-col">
            <button
              className={`cc-pulse-card ${expandedPulse === 'bias' ? 'cc-pulse-card--expanded' : ''}`}
              onClick={() => setExpandedPulse(expandedPulse === 'bias' ? null : 'bias')}
              aria-expanded={expandedPulse === 'bias'}
              aria-label="Bias accuracy"
            >
              <div className={`cc-pulse-card__value ${ragClass(validationPassRate, { green: 95, amber: 90 })}`}>
                {loading ? '--' : `${validationPassRate}%`}
              </div>
              <div className="cc-pulse-card__label">Bias Accuracy</div>
              <div className="cc-pulse-card__sub">validation suite</div>
            </button>
            <div className={`cc-pulse-expand ${expandedPulse === 'bias' ? 'cc-pulse-expand--open' : ''}`}>
              <div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">Ground-truth articles</span>
                  <span className="cc-pulse-expand__value">26</span>
                </div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">Categories tested</span>
                  <span className="cc-pulse-expand__value">8</span>
                </div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">CI gate</span>
                  <span className="cc-pulse-expand__value cc-rag-green">active</span>
                </div>
                <div className="cc-cli-block">
                  python pipeline/validation/runner.py --verbose
                  <button className="cc-cli-block__copy" onClick={(e) => { e.stopPropagation(); copyToClipboard('python pipeline/validation/runner.py --verbose'); }}>Copy</button>
                </div>
              </div>
            </div>
          </div>

          {/* 4. Articles 24h */}
          <div className="cc-pulse-col">
            <button
              className={`cc-pulse-card ${expandedPulse === 'articles' ? 'cc-pulse-card--expanded' : ''}`}
              onClick={() => setExpandedPulse(expandedPulse === 'articles' ? null : 'articles')}
              aria-expanded={expandedPulse === 'articles'}
              aria-label="Articles ingested in last 24 hours"
            >
              <div className={`cc-pulse-card__value ${ragClass(articleCount24h, { green: 500, amber: 200 })}`}>
                {loading ? '--' : articleCount24h.toLocaleString()}
              </div>
              <div className="cc-pulse-card__label">Articles 24h</div>
              <div className="cc-pulse-card__sub">{totalArticles > 0 ? `${totalArticles.toLocaleString()} total` : ''}</div>
            </button>
            <div className={`cc-pulse-expand ${expandedPulse === 'articles' ? 'cc-pulse-expand--open' : ''}`}>
              <div>
                {editionStats.map(e => (
                  <div key={e.edition} className="cc-pulse-expand__row">
                    <span className="cc-pulse-expand__label">{e.edition}</span>
                    <span className="cc-pulse-expand__value">{e.articles.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 5. Cluster Quality */}
          <div className="cc-pulse-col">
            <button
              className={`cc-pulse-card ${expandedPulse === 'clusters' ? 'cc-pulse-card--expanded' : ''}`}
              onClick={() => setExpandedPulse(expandedPulse === 'clusters' ? null : 'clusters')}
              aria-expanded={expandedPulse === 'clusters'}
              aria-label="Cluster quality"
            >
              <div className={`cc-pulse-card__value ${ragClass(clusterQuality, { green: 20, amber: 10 })}`}>
                {loading ? '--' : `${clusterQuality}%`}
              </div>
              <div className="cc-pulse-card__label">3+ Source</div>
              <div className="cc-pulse-card__sub">{clusterStats.total} clusters</div>
            </button>
            <div className={`cc-pulse-expand ${expandedPulse === 'clusters' ? 'cc-pulse-expand--open' : ''}`}>
              <div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">Total clusters</span>
                  <span className="cc-pulse-expand__value">{clusterStats.total}</span>
                </div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">Multi-source (3+)</span>
                  <span className="cc-pulse-expand__value cc-rag-green">{clusterStats.multiSource}</span>
                </div>
                <div className="cc-pulse-expand__row">
                  <span className="cc-pulse-expand__label">Gemini cap</span>
                  <span className="cc-pulse-expand__value">25 calls/run</span>
                </div>
              </div>
            </div>
          </div>

          {/* 6. Daily Brief */}
          <div className="cc-pulse-col">
            <button
              className={`cc-pulse-card ${expandedPulse === 'brief' ? 'cc-pulse-card--expanded' : ''}`}
              onClick={() => setExpandedPulse(expandedPulse === 'brief' ? null : 'brief')}
              aria-expanded={expandedPulse === 'brief'}
              aria-label="Daily brief status"
            >
              <div className={`cc-pulse-card__value ${briefFresh ? 'cc-rag-green' : 'cc-rag-amber'}`}>
                {loading ? '--' : briefFresh ? 'LIVE' : latestBrief ? 'STALE' : 'N/A'}
              </div>
              <div className="cc-pulse-card__label">Daily Brief</div>
              {latestBrief && <div className="cc-pulse-card__sub">{timeAgo(latestBrief.created_at)}</div>}
            </button>
            <div className={`cc-pulse-expand ${expandedPulse === 'brief' ? 'cc-pulse-expand--open' : ''}`}>
              <div>
                {briefStatuses.map(b => (
                  <div key={b.edition} className="cc-pulse-expand__row">
                    <span className="cc-pulse-expand__label">{b.edition}</span>
                    <span className="cc-pulse-expand__value">
                      {timeAgo(b.created_at)} {b.has_audio ? '\uD83C\uDF99' : ''} {b.has_opinion ? '\u270D' : ''}
                    </span>
                  </div>
                ))}
                <div className="cc-cli-block">
                  python pipeline/refresh_audio.py
                  <button className="cc-cli-block__copy" onClick={(e) => { e.stopPropagation(); copyToClipboard('python pipeline/refresh_audio.py'); }}>Copy</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="cc-section">
          <div className="cc-section__title">Actions</div>
          <div className="cc-actions">
            <button className="cc-action-btn" onClick={() => { processCommand('pipeline'); setDrawerOpen(true); setTerminalOpen(true); }}>
              <span className="cc-action-btn__icon">{'\u25B6'}</span>
              <span className="cc-action-btn__label">Run Pipeline</span>
              <span className="cc-action-btn__meta">4x daily cron</span>
            </button>
            <button className="cc-action-btn" onClick={() => { processCommand('validate'); setDrawerOpen(true); setTerminalOpen(true); }}>
              <span className="cc-action-btn__icon">{'\u2696'}</span>
              <span className="cc-action-btn__label">Bias Validation</span>
              <span className="cc-action-btn__meta">26 articles / $0</span>
            </button>
            <button className="cc-action-btn" onClick={() => { processCommand('daily-ops'); setDrawerOpen(true); setTerminalOpen(true); }}>
              <span className="cc-action-btn__icon">{'\uD83D\uDCCA'}</span>
              <span className="cc-action-btn__label">Daily Ops</span>
              <span className="cc-action-btn__meta">3-way health check</span>
            </button>
            <button className="cc-action-btn" onClick={() => { processCommand('security'); setDrawerOpen(true); setTerminalOpen(true); }}>
              <span className="cc-action-btn__icon">{'\uD83D\uDD12'}</span>
              <span className="cc-action-btn__label">Security</span>
              <span className="cc-action-btn__meta">OWASP + RLS</span>
            </button>
            <button className="cc-action-btn" onClick={() => { processCommand('bias-audit'); setDrawerOpen(true); setTerminalOpen(true); }}>
              <span className="cc-action-btn__icon">{'\uD83D\uDD0D'}</span>
              <span className="cc-action-btn__label">Bias Audit</span>
              <span className="cc-action-btn__meta">4-agent cycle</span>
            </button>
            <button className="cc-action-btn" onClick={() => { processCommand('full-audit'); setDrawerOpen(true); setTerminalOpen(true); }}>
              <span className="cc-action-btn__icon">{'\u2699'}</span>
              <span className="cc-action-btn__label">Full Audit</span>
              <span className="cc-action-btn__meta">5-way parallel</span>
            </button>
          </div>
        </div>

        {/* Pipeline Runs */}
        <div className="cc-section">
          <div className="cc-section__title">
            <span className={`cc-section__dot ${pipelineHealthy ? 'cc-section__dot--green' : 'cc-section__dot--red'}`} />
            Pipeline Runs
          </div>
          <div className="cc-runs">
            {loading ? (
              <div className="cc-empty">Loading...</div>
            ) : pipelineRuns.length === 0 ? (
              <div className="cc-empty">No pipeline runs found</div>
            ) : pipelineRuns.map(run => (
              <div key={run.id} className="cc-run">
                <div className="cc-run__dot" style={{ background: run.status === 'completed' ? 'var(--cc-green)' : run.status === 'running' ? 'var(--cc-amber)' : 'var(--cc-red)' }} />
                <div className="cc-run__name">{run.status === 'completed' ? 'Pipeline Run' : run.status}</div>
                <div className="cc-run__articles">{run.articles_fetched ?? '?'} articles</div>
                <div className="cc-run__time">{fmtDuration(run.started_at || run.created_at, run.completed_at)}</div>
                <div className="cc-run__ago">{timeAgo(run.created_at)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Edition Coverage */}
        <div className="cc-section">
          <div className="cc-section__title">Edition Coverage</div>
          <div className="cc-editions">
            {editionStats.map(edition => (
              <div key={edition.edition} className="cc-edition-card">
                <div className="cc-edition-card__header">
                  <span className="cc-edition-card__name">{edition.edition}</span>
                  <span className="cc-edition-card__count">{edition.articles.toLocaleString()}</span>
                </div>
                <div className="cc-edition-bar">
                  <div
                    className="cc-edition-bar__fill"
                    style={{
                      width: `${(edition.articles / maxEditionArticles) * 100}%`,
                      background: edition.edition === 'World' ? 'var(--cc-blue)' : edition.edition === 'US' ? 'var(--cc-accent)' : 'var(--cc-green)',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bias Score Distribution */}
        {biasStats.length > 0 && (
          <div className="cc-section">
            <div className="cc-section__title">Bias Score Distribution</div>
            <div className="cc-bias-dist">
              {biasStats.map(axis => (
                <div key={axis.key} className="cc-bias-axis">
                  <div className="cc-bias-axis__name">{axis.name}</div>
                  <div className="cc-bias-axis__avg">{axis.avg}</div>
                  <div className="cc-bias-axis__range">{axis.min} - {axis.max}</div>
                  <div className="cc-bias-axis__bar">
                    <div className="cc-bias-axis__bar-fill" style={{ width: `${axis.avg}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Source Tier Breakdown */}
        <div className="cc-section">
          <div className="cc-section__title">Source Tiers</div>
          <div className="cc-source-health">
            <div className="cc-tier-card">
              <div className="cc-tier-card__name">US Major</div>
              <div className="cc-tier-card__count cc-rag-blue">{sourceStats.us_major}</div>
              <div className="cc-tier-card__label">AP, Reuters, NYT, Fox, CNN...</div>
            </div>
            <div className="cc-tier-card">
              <div className="cc-tier-card__name">International</div>
              <div className="cc-tier-card__count" style={{ color: 'var(--cc-accent)' }}>{sourceStats.international}</div>
              <div className="cc-tier-card__label">BBC, Al Jazeera, DW, NHK...</div>
            </div>
            <div className="cc-tier-card">
              <div className="cc-tier-card__name">Independent</div>
              <div className="cc-tier-card__count cc-rag-green">{sourceStats.independent}</div>
              <div className="cc-tier-card__label">ProPublica, Bellingcat, The Markup...</div>
            </div>
          </div>
        </div>

      </main>

      {/* ---- Agent Drawer Toggle ---- */}
      <button className="cc-drawer-toggle" onClick={() => setDrawerOpen(true)} aria-label="Open agent team drawer">
        AGENTS
      </button>

      {/* ---- Backdrop ---- */}
      <div
        className={`cc-backdrop ${drawerOpen ? 'cc-backdrop--visible' : ''}`}
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />

      {/* ---- Agent Drawer ---- */}
      <div className={`cc-drawer ${drawerOpen ? 'cc-drawer--open' : ''}`} role="dialog" aria-label="Agent Team" aria-modal="true">
        <div className="cc-drawer__header">
          <span className="cc-drawer__title">Agent Team</span>
          <span className="cc-drawer__count">20</span>
          <button className="cc-drawer__close" onClick={() => setDrawerOpen(false)} aria-label="Close drawer">{'\u00D7'}</button>
        </div>
        <div className="cc-drawer__body">
          {AGENT_TEAM.map(div => (
            <div key={div.division} className="cc-drawer__division">
              <div className="cc-drawer__division-name">{div.division}</div>
              {div.agents.map(agent => (
                <div key={agent.name} className="cc-agent">
                  <div className="cc-agent__dot" />
                  <span className="cc-agent__name">{agent.name}</span>
                  <span className="cc-agent__role">{agent.role}</span>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Terminal */}
        <div className="cc-terminal-section">
          <button className="cc-terminal-toggle" onClick={() => setTerminalOpen(prev => !prev)} aria-expanded={terminalOpen} aria-label="Toggle terminal">
            <span style={{ transform: terminalOpen ? 'rotate(180deg)' : undefined, transition: 'transform 0.2s', display: 'inline-block' }}>{'\u25BC'}</span>
            <span>Terminal</span>
          </button>
          {terminalOpen && (
            <div className="cc-terminal__body">
              <div className="cc-terminal__output" ref={terminalRef}>
                {terminalLines.map((line, i) => (
                  <div key={i} className={`cc-terminal__line cc-terminal__line--${line.type}`}>{line.text}</div>
                ))}
              </div>
              <div className="cc-terminal__input-row">
                <span className="cc-terminal__prompt">$</span>
                <input
                  ref={inputRef}
                  className="cc-terminal__input"
                  value={terminalInput}
                  onChange={e => setTerminalInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter' && terminalInput.trim()) processCommand(terminalInput); }}
                  placeholder="Type a command..."
                  autoComplete="off"
                  spellCheck={false}
                  aria-label="Terminal command input"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ---- Footer ---- */}
      <footer className="cc-footer">
        <span>Bias Engine v1</span>
        <span className="cc-footer__sep">|</span>
        <span>{sourceStats.total} sources</span>
        <span className="cc-footer__sep">|</span>
        <span>20 agents</span>
        <span className="cc-footer__sep">|</span>
        <span>$0 ops</span>
      </footer>

      {/* ---- Keyboard Shortcuts ---- */}
      {shortcutsOpen && (
        <div className="cc-shortcuts-overlay" onClick={() => setShortcutsOpen(false)} role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
          <div className="cc-shortcuts-card" onClick={e => e.stopPropagation()}>
            <div className="cc-shortcuts-card__header">
              <span>Keyboard Shortcuts</span>
              <button onClick={() => setShortcutsOpen(false)} aria-label="Close shortcuts" style={{ fontSize: '1.25rem', cursor: 'pointer', background: 'none', border: 'none', color: 'inherit', minWidth: '44px', minHeight: '44px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>{'\u00D7'}</button>
            </div>
            <div className="cc-shortcut"><span>Toggle Agent Drawer</span><kbd>t</kbd></div>
            <div className="cc-shortcut"><span>Focus Terminal</span><kbd>/</kbd></div>
            <div className="cc-shortcut"><span>Refresh Data</span><kbd>r</kbd></div>
            <div className="cc-shortcut"><span>Keyboard Help</span><kbd>?</kbd></div>
            <div className="cc-shortcut"><span>Close Panel / Overlay</span><kbd>Esc</kbd></div>
            <div className="cc-shortcut"><span>Expand Pulse Cards</span><kbd>1-6</kbd></div>
          </div>
        </div>
      )}

      {/* ---- Toast ---- */}
      <div className={`cc-toast ${toast ? 'cc-toast--visible' : ''}`}>{toast}</div>
    </div>
  );
}
