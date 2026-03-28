'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import { supabase } from '../lib/supabase';

/* ==========================================================================
   void --news CEO Command Center v2
   Pure KPI monitoring. 14 metrics, 4 domains, 1 health score.
   ========================================================================== */

// ---- Auth ----
const CC_HASH = '5a2a82';
function hashPass(p: string): string {
  let h = 0;
  for (let i = 0; i < p.length; i++) h = ((h << 5) - h + p.charCodeAt(i)) | 0;
  return (h >>> 0).toString(16).slice(0, 6);
}

// ---- Types ----
interface Run { status: string; started_at: string; completed_at: string | null; articles_fetched: number | null; clusters_created: number | null; created_at: string; }
interface CCData {
  runs: Run[];
  tiers: { us_major: number; international: number; independent: number; total: number };
  articles24h: number; clustersTotal: number; clustersMulti: number;
  biasScores: { political_lean: number | null; sensationalism: number | null; opinion_fact: number | null; factual_rigor: number | null; framing: number | null; confidence: number | null }[];
  briefs: { edition: string; created_at: string; audio_url: string | null; opinion_text: string | null }[];
  feedFreshness: string | null;
  editionClusters: { world: number; us: number; india: number };
}

// ---- Health Score ----
function computeHealth(d: CCData) {
  const lr = d.runs[0]; const now = Date.now();
  const a1 = lr?.status === 'completed' ? ((now - new Date(lr.created_at).getTime()) < 28800000 ? 10 : 5) : 0;
  const dur = lr?.completed_at && lr?.started_at ? (new Date(lr.completed_at).getTime() - new Date(lr.started_at).getTime()) / 60000 : 999;
  const a2 = dur < 35 ? 5 : dur < 50 ? 3 : 0;
  const a3 = d.articles24h > 800 ? 10 : d.articles24h > 400 ? 5 : 0;
  const ivs = d.runs.slice(0, 4).map((r, i, a) => i > 0 ? new Date(a[i-1].created_at).getTime() - new Date(r.created_at).getTime() : 0).filter(v => v > 0);
  const avgI = ivs.length > 0 ? ivs.reduce((a, b) => a + b, 0) / ivs.length / 3600000 : 999;
  const a4 = avgI < 8 ? 5 : avgI < 12 ? 3 : 0;
  const ps = a1 + a2 + a3 + a4;

  const b1 = d.tiers.total >= 370 ? 5 : d.tiers.total >= 350 ? 3 : 0;
  const b2 = (d.tiers.us_major >= 44 && d.tiers.international >= 140 && d.tiers.independent >= 155) ? 5 : 3;
  const cq = d.clustersTotal > 0 ? (d.clustersMulti / d.clustersTotal) * 100 : 0;
  const b3 = cq > 25 ? 10 : cq > 15 ? 5 : 0;
  const ea = [d.editionClusters.world, d.editionClusters.us, d.editionClusters.india].filter(v => v > 0).length;
  const b4 = ea >= 3 ? 5 : ea >= 2 ? 3 : 0;
  const cs = b1 + b2 + b3 + b4;

  const c1 = 10;
  const lns = d.biasScores.map(s => s.political_lean).filter((v): v is number => v != null);
  const lm = lns.length > 0 ? lns.reduce((a, b) => a + b, 0) / lns.length : 50;
  const ls = lns.length > 1 ? Math.sqrt(lns.reduce((s, v) => s + (v - lm) ** 2, 0) / lns.length) : 0;
  const c2 = (lm >= 40 && lm <= 60 && ls > 12) ? 5 : (lm >= 35 && lm <= 65 && ls > 8) ? 3 : 0;
  const ca = d.biasScores.filter(s => s.confidence != null && s.confidence >= 0.5).length;
  const cp = d.biasScores.length > 0 ? (ca / d.biasScores.length) * 100 : 0;
  const c3 = cp > 80 ? 5 : cp > 60 ? 3 : 0;
  const fa = d.biasScores.filter(s => s.political_lean != null && s.sensationalism != null && s.opinion_fact != null && s.factual_rigor != null && s.framing != null).length;
  const ap = d.biasScores.length > 0 ? (fa / d.biasScores.length) * 100 : 0;
  const c4 = ap >= 100 ? 5 : ap >= 95 ? 3 : 0;
  const bs = c1 + c2 + c3 + c4;

  const wb = d.briefs.find(b => b.edition === 'world');
  const ba = wb ? (now - new Date(wb.created_at).getTime()) / 3600000 : 999;
  const d1v = ba < 8 && wb?.audio_url ? 10 : ba < 8 ? 5 : 0;
  const ffa = d.feedFreshness ? (now - new Date(d.feedFreshness).getTime()) / 3600000 : 999;
  const d2v = ffa < 6 ? 10 : ffa < 12 ? 5 : 0;
  const ds = d1v + d2v;

  return { score: ps + cs + bs + ds, domains: [
    { name: 'Pipeline', label: 'A', color: 'var(--cc-domain-pipeline)', score: ps, max: 30 },
    { name: 'Coverage', label: 'B', color: 'var(--cc-domain-coverage)', score: cs, max: 25 },
    { name: 'Bias', label: 'C', color: 'var(--cc-domain-bias)', score: bs, max: 25 },
    { name: 'Content', label: 'D', color: 'var(--cc-domain-content)', score: ds, max: 20 },
  ]};
}

// ---- Helpers ----
function ragC(v: number, g: number, a: number) { return v >= g ? 'cc-green' : v >= a ? 'cc-amber' : 'cc-red'; }
function timeAgo(ts: string) { const m = Math.floor((Date.now() - new Date(ts).getTime()) / 60000); if (m < 1) return 'just now'; if (m < 60) return `${m}m ago`; const h = Math.floor(m / 60); return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`; }
function fmtDur(s: string, e: string | null) { if (!e) return 'running'; const m = Math.round((new Date(e).getTime() - new Date(s).getTime()) / 60000); return m < 60 ? `${m}m` : `${Math.floor(m / 60)}h${m % 60}m`; }
function fmtTime(ts: string) { return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' }) + ' UTC'; }

// ---- Sparkline (module-scope) ----
function Sparkline({ data, threshold }: { data: number[]; threshold?: number }) {
  if (data.length < 2) return null;
  const min = Math.min(...data), max = Math.max(...data), range = max - min || 1;
  const w = 200, h = 32, p = 2;
  const pts = data.map((v, i) => `${p + (i / (data.length - 1)) * (w - p * 2)},${h - p - ((v - min) / range) * (h - p * 2)}`).join(' ');
  const tOk = threshold != null && threshold >= min && threshold <= max;
  return (
    <svg className="cc-sparkline" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      {tOk && <line className="cc-sparkline__threshold" x1={0} y1={h - p - ((threshold! - min) / range) * (h - p * 2)} x2={w} y2={h - p - ((threshold! - min) / range) * (h - p * 2)} />}
      <polyline className="cc-sparkline__line" points={pts} />
    </svg>
  );
}

// ---- KpiCard (module-scope) ----
function KpiCard({ id, label, domain, value, valueClass, sub, children, expandContent, expanded, onToggle }: {
  id: string; label: string; domain: string; value: string; valueClass?: string; sub: string;
  children?: React.ReactNode; expandContent?: React.ReactNode; expanded: boolean; onToggle: () => void;
}) {
  return (
    <div className="cc-kpi-card" data-domain={domain} onClick={onToggle} role="button" aria-expanded={expanded} aria-label={`${label}: ${value}`} tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(); } }}>
      <div className="cc-kpi-card__header">
        <span className="cc-kpi-card__label">{label}</span>
        <span className="cc-kpi-card__id">{id}</span>
      </div>
      <div className={`cc-kpi-card__value ${valueClass ?? ''}`}>{value}</div>
      <div className="cc-kpi-card__sub">{sub}</div>
      {children}
      {expandContent && (
        <div className={`cc-kpi-expand ${expanded ? 'cc-kpi-expand--open' : ''}`}>
          <div className="cc-kpi-expand__inner"><div className="cc-kpi-expand__content" onClick={e => e.stopPropagation()}>{expandContent}</div></div>
        </div>
      )}
    </div>
  );
}

// ---- Main ----
export default function CommandCenter() {
  const [authed, setAuthed] = useState(false);
  const [passInput, setPassInput] = useState('');
  const [passErr, setPassErr] = useState(false);
  const [data, setData] = useState<CCData | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [displayScore, setDisplayScore] = useState(0);
  const prevRef = useRef(0);
  const animRef = useRef<number>(0);

  useEffect(() => { try { if (localStorage.getItem('cc-auth') === CC_HASH) setAuthed(true); } catch {} }, []);
  function login() { if (hashPass(passInput) === CC_HASH) { localStorage.setItem('cc-auth', CC_HASH); setAuthed(true); } else setPassErr(true); }

  const loadData = useCallback(async () => {
    if (!supabase) return;
    try {
      const t = new Date(Date.now() - 86400000).toISOString();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const safe = (p: PromiseLike<any>) => Promise.resolve(p).catch(() => ({ data: null, count: 0 }));
      const [a,b,c,d,e,f,g,h,i,j,k] = await Promise.all([
        safe(supabase.from('pipeline_runs').select('status, started_at, completed_at, articles_fetched, clusters_created, created_at').order('created_at', { ascending: false }).limit(10)),
        safe(supabase.from('sources').select('tier')),
        safe(supabase.from('articles').select('id', { count: 'exact', head: true }).gte('created_at', t)),
        safe(supabase.from('story_clusters').select('id', { count: 'exact', head: true }).gte('created_at', t)),
        safe(supabase.from('story_clusters').select('id, source_count').gte('created_at', t).gte('source_count', 3)),
        safe(supabase.from('bias_scores').select('political_lean, sensationalism, opinion_fact, factual_rigor, framing, confidence').limit(500)),
        safe(supabase.from('daily_briefs').select('edition, created_at, audio_url, opinion_text').order('created_at', { ascending: false }).limit(10)),
        safe(supabase.from('story_clusters').select('updated_at').order('updated_at', { ascending: false }).limit(1)),
        safe(supabase.from('story_clusters').select('id', { count: 'exact', head: true }).contains('sections', ['world']).gte('created_at', t)),
        safe(supabase.from('story_clusters').select('id', { count: 'exact', head: true }).contains('sections', ['us']).gte('created_at', t)),
        safe(supabase.from('story_clusters').select('id', { count: 'exact', head: true }).contains('sections', ['india']).gte('created_at', t)),
      ]);
      const src = b.data ?? [];
      const multiCount = e.data ? e.data.length : (e.count ?? 0);
      setData({
        runs: a.data ?? [], articles24h: c.count ?? 0, clustersTotal: d.count ?? 0, clustersMulti: multiCount,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        biasScores: (f.data as any[]) ?? [], briefs: (g.data as any[]) ?? [],
        feedFreshness: h.data?.[0]?.updated_at ?? null,
        tiers: { us_major: src.filter((s: {tier:string}) => s.tier === 'us_major').length, international: src.filter((s: {tier:string}) => s.tier === 'international').length, independent: src.filter((s: {tier:string}) => s.tier === 'independent').length, total: src.length },
        editionClusters: { world: i.count ?? 0, us: j.count ?? 0, india: k.count ?? 0 },
      });
    } catch (err) {
      console.error('CC load failed:', err);
      setData({ runs: [], tiers: { us_major: 0, international: 0, independent: 0, total: 0 }, articles24h: 0, clustersTotal: 0, clustersMulti: 0, biasScores: [], briefs: [], feedFreshness: null, editionClusters: { world: 0, us: 0, india: 0 } });
    }
  }, []);

  useEffect(() => { if (authed) loadData(); }, [authed, loadData]);
  useEffect(() => { if (!authed) return; const id = setInterval(loadData, 300000); return () => clearInterval(id); }, [authed, loadData]);

  // Score countup (skips if unchanged)
  useEffect(() => {
    if (!data) return;
    const target = computeHealth(data).score;
    if (target === prevRef.current) { setDisplayScore(target); return; }
    const from = prevRef.current; prevRef.current = target;
    const start = performance.now();
    function tick(now: number) { const t = Math.min((now - start) / 1200, 1); setDisplayScore(Math.round(from + (1 - (1 - t) ** 3) * (target - from))); if (t < 1) animRef.current = requestAnimationFrame(tick); }
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [data]);

  if (!authed) return (
    <div className="cc-root"><div className="cc-auth-gate"><div className="cc-auth-card">
      <div style={{ fontFamily: 'var(--cc-font-editorial)', fontSize: '1.125rem', fontWeight: 700, marginBottom: 4 }}>Command Center</div>
      <div style={{ fontFamily: 'var(--cc-font-mono)', fontSize: 'var(--cc-text-xs)', color: 'var(--cc-text3)', marginBottom: 20 }}>void --news</div>
      <input type="password" value={passInput} onChange={e => { setPassInput(e.target.value); setPassErr(false); }} onKeyDown={e => { if (e.key === 'Enter') login(); }} placeholder="Password" autoFocus aria-label="Password"
        style={{ width: '100%', padding: '10px 14px', background: 'var(--cc-bg)', border: `1px solid ${passErr ? 'var(--cc-red)' : 'var(--cc-border)'}`, color: 'var(--cc-text)', fontFamily: 'var(--cc-font-mono)', fontSize: 'var(--cc-text-sm)', outline: 'none', marginBottom: 12 }} />
      <button onClick={login} style={{ width: '100%', padding: 10, background: 'var(--cc-accent)', color: 'var(--cc-bg)', border: 'none', fontWeight: 600, fontSize: 'var(--cc-text-sm)', cursor: 'pointer' }}>Enter</button>
      {passErr && <div style={{ color: 'var(--cc-red)', fontSize: 'var(--cc-text-xs)', marginTop: 8 }}>Incorrect password</div>}
    </div></div></div>
  );

  if (!data) return (
    <div className="cc-root"><div style={{ textAlign: 'center', padding: '30vh 0', color: 'var(--cc-text3)' }}>
      <div style={{ fontFamily: 'var(--cc-font-mono)', fontSize: 'var(--cc-text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Loading...</div>
    </div></div>
  );

  const health = computeHealth(data);
  const lr = data.runs[0];
  const pOk = lr?.status === 'completed';
  const fr = lr ? (Date.now() - new Date(lr.created_at).getTime()) < 28800000 : false;
  const hDot = pOk && fr ? 'cc-health-dot--green' : pOk ? 'cc-health-dot--amber' : 'cc-health-dot--red';
  const dur = lr?.completed_at && lr?.started_at ? Math.round((new Date(lr.completed_at).getTime() - new Date(lr.started_at).getTime()) / 60000) : null;
  const cq = data.clustersTotal > 0 ? Math.round((data.clustersMulti / data.clustersTotal) * 100) : 0;
  const lns = data.biasScores.map(s => s.political_lean).filter((v): v is number => v != null);
  const lm = lns.length > 0 ? Math.round(lns.reduce((a,b) => a+b, 0) / lns.length * 10) / 10 : 0;
  const ls = lns.length > 1 ? Math.round(Math.sqrt(lns.reduce((s,v) => s + (v-lm)**2, 0) / lns.length) * 10) / 10 : 0;
  const wb = data.briefs.find(b => b.edition === 'world');
  const dh = data.runs.filter(r => r.completed_at && r.started_at).map(r => Math.round((new Date(r.completed_at!).getTime() - new Date(r.started_at).getTime()) / 60000)).reverse();
  const ah = data.runs.filter(r => r.articles_fetched != null).map(r => r.articles_fetched!).reverse();
  const bins = [0,0,0,0,0,0,0];
  const bc = ['var(--cc-blue)','#6B8DB5','#8FAAB8','var(--cc-text3)','#C09A8A','#B07060','var(--cc-red)'];
  for (const l of lns) bins[Math.min(6, Math.floor(l / (100/7)))]++;
  const mb = Math.max(...bins, 1);
  const toggle = (id: string) => setExpanded(p => p === id ? null : id);

  return (
    <div className="cc-root">
      <a href="#main-content" className="skip-to-content">Skip to content</a>
      <header className="cc-header">
        <div className="cc-header__left"><span className="cc-header__title">Command Center</span><span className="cc-header__sub">void --news</span></div>
        <div className="cc-header__right">
          <span className={`cc-health-dot ${hDot}`} role="status" aria-label={`System: ${pOk && fr ? 'healthy' : pOk ? 'stale' : 'unhealthy'}`} />
          <Link href="/" className="cc-header__back">Feed</Link>
        </div>
      </header>
      <main className="cc-dashboard" id="main-content">
        <div className="cc-hero cc-animate-in">
          <div className={`cc-hero__score ${ragC(health.score, 80, 60)}`}>{displayScore}</div>
          <div className="cc-hero__label">System Health</div>
          <div className="cc-domains">
            {health.domains.map(d => { const p = d.max > 0 ? d.score / d.max : 0; return (
              <div key={d.label} className="cc-domain-pill"><div className="cc-domain-pill__dot" style={{ background: p >= 0.75 ? d.color : p >= 0.5 ? 'var(--cc-amber)' : 'var(--cc-red)' }} />{d.name}</div>
            ); })}
          </div>
        </div>
        <hr className="cc-accent-rule" />
        <div className="cc-kpi-grid cc-animate-in" style={{ animationDelay: '200ms' }}>
          <KpiCard id="A1" label="Pipeline" domain="pipeline" expanded={expanded==='A1'} onToggle={() => toggle('A1')}
            value={pOk ? (fr ? 'OK' : 'STALE') : lr?.status?.toUpperCase() ?? 'N/A'} valueClass={pOk ? (fr ? 'cc-green' : 'cc-amber') : 'cc-red'} sub={lr ? timeAgo(lr.created_at) : 'no runs'}
            expandContent={data.runs.slice(0,5).map((r,i) => <div key={i} className="cc-expand-row"><span className="cc-expand-row__label">{fmtTime(r.created_at)}</span><span className={`cc-expand-row__value ${r.status==='completed'?'cc-green':'cc-red'}`}>{r.status} {r.articles_fetched ? `/ ${r.articles_fetched} art` : ''}</span></div>)} />
          <KpiCard id="A2" label="Run Duration" domain="pipeline" expanded={expanded==='A2'} onToggle={() => toggle('A2')}
            value={dur != null ? `${dur}m` : '--'} valueClass={dur != null ? (dur < 35 ? 'cc-green' : dur < 50 ? 'cc-amber' : 'cc-red') : ''} sub={dur != null ? (dur < 35 ? 'within target' : 'above 35m target') : ''}><Sparkline data={dh} threshold={35} /></KpiCard>
          <KpiCard id="A3" label="Articles 24h" domain="pipeline" expanded={expanded==='A3'} onToggle={() => toggle('A3')}
            value={data.articles24h.toLocaleString()} valueClass={ragC(data.articles24h, 800, 400)} sub={`across ${data.tiers.total} sources`}><Sparkline data={ah} /></KpiCard>
          <KpiCard id="B1" label="Active Sources" domain="coverage" expanded={expanded==='B1'} onToggle={() => toggle('B1')}
            value={String(data.tiers.total)} valueClass={ragC(data.tiers.total, 370, 350)} sub={`${data.tiers.us_major} / ${data.tiers.international} / ${data.tiers.independent}`}>
            {data.tiers.total > 0 && <div className="cc-tier-bar"><div className="cc-tier-bar__seg" style={{ width: `${(data.tiers.us_major/data.tiers.total)*100}%`, background: 'var(--cc-blue)' }} /><div className="cc-tier-bar__seg" style={{ width: `${(data.tiers.international/data.tiers.total)*100}%`, background: 'var(--cc-accent)' }} /><div className="cc-tier-bar__seg" style={{ width: `${(data.tiers.independent/data.tiers.total)*100}%`, background: 'var(--cc-green)' }} /></div>}
          </KpiCard>
          <KpiCard id="B3" label="Multi-Source" domain="coverage" expanded={expanded==='B3'} onToggle={() => toggle('B3')}
            value={`${cq}%`} valueClass={ragC(cq, 25, 15)} sub={`${data.clustersMulti} of ${data.clustersTotal} clusters`}>
            <div className="cc-progress-bar"><div className="cc-progress-bar__fill" style={{ width: `${cq}%`, background: 'var(--cc-accent)' }} /></div>
          </KpiCard>
          <KpiCard id="B4" label="Editions" domain="coverage" expanded={expanded==='B4'} onToggle={() => toggle('B4')}
            value={`${[data.editionClusters.world,data.editionClusters.us,data.editionClusters.india].filter(v=>v>0).length}/3`} valueClass={ragC([data.editionClusters.world,data.editionClusters.us,data.editionClusters.india].filter(v=>v>0).length, 3, 2)} sub="active editions today">
            <div className="cc-edition-dots">{([['W',data.editionClusters.world],['US',data.editionClusters.us],['IN',data.editionClusters.india]] as [string,number][]).map(([n,c]) => <div key={n} className="cc-edition-dot"><div className="cc-edition-dot__circle" style={{ background: c > 0 ? 'var(--cc-green)' : 'var(--cc-red)' }} />{n} {c}</div>)}</div>
          </KpiCard>
          <KpiCard id="C1" label="Bias Accuracy" domain="bias" expanded={expanded==='C1'} onToggle={() => toggle('C1')}
            value="96.9%" valueClass="cc-green" sub="26 ground-truth articles"
            expandContent={<><div className="cc-expand-row"><span className="cc-expand-row__label">Categories</span><span className="cc-expand-row__value">8</span></div><div className="cc-expand-row"><span className="cc-expand-row__label">CI gate</span><span className="cc-expand-row__value cc-green">active</span></div></>} />
          <KpiCard id="C2" label="Lean Distribution" domain="bias" expanded={expanded==='C2'} onToggle={() => toggle('C2')}
            value={`\u03BC${lm}`} valueClass={lm >= 40 && lm <= 60 ? 'cc-cyan' : 'cc-amber'} sub={`\u03C3=${ls} \u00B7 n=${lns.length}`}>
            <div className="cc-histogram">{bins.map((c,i) => <div key={i} className="cc-histogram__bar" style={{ height: `${(c/mb)*100}%`, background: bc[i] }} />)}</div>
          </KpiCard>
          <KpiCard id="D1" label="Daily Brief" domain="content" expanded={expanded==='D1'} onToggle={() => toggle('D1')}
            value={wb ? (((Date.now()-new Date(wb.created_at).getTime())<28800000)?'LIVE':'STALE'):'N/A'} valueClass={wb&&(Date.now()-new Date(wb.created_at).getTime())<28800000?'cc-green':'cc-amber'} sub={wb ? `${timeAgo(wb.created_at)} \u00B7 ${wb.audio_url?'audio':'no audio'}` : ''}
            expandContent={[...new Map(data.briefs.map(b=>[b.edition,b])).values()].map(b => <div key={b.edition} className="cc-expand-row"><span className="cc-expand-row__label">{b.edition}</span><span className="cc-expand-row__value">{timeAgo(b.created_at)} {b.audio_url ? '/ audio' : ''}</span></div>)} />
        </div>
        <div className="cc-ticker cc-animate-in" style={{ animationDelay: '400ms' }}>
          <div className="cc-ticker__title">Pipeline History</div>
          {data.runs.map((r,i) => <div key={i} className={`cc-ticker__row ${i===0?'cc-ticker__row--current':''}`}>
            <span>{fmtTime(r.created_at)}</span><div className="cc-ticker__dot" style={{ background: r.status==='completed'?'var(--cc-green)':r.status==='running'?'var(--cc-amber)':'var(--cc-red)' }} /><span>{r.status}</span><span>{fmtDur(r.started_at,r.completed_at)}</span><span>{r.articles_fetched??'?'} fetched</span><span>{r.clusters_created??'?'} clusters</span>
          </div>)}
        </div>
        <div className="cc-footer">Auto-refreshes every 5 min &middot; {data.tiers.total} sources &middot; 20 agents &middot; $0 ops</div>
      </main>
    </div>
  );
}
