// @ts-nocheck  — one-off dev tooling script (js-yaml has no bundled types)
/* One-off: emit data/revolt/events/<slug>.yaml from the frontend mock data, so
   the DB content matches exactly what the site already renders. Skips
   french-revolution (hand-authored canary is richer). Run:
     cd frontend && npx --yes tsx scripts/exportRevoltYaml.ts
*/
import { writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';
import { MOCK_REVOLUTIONS } from '../app/revolt/mockData';
import type { Revolution } from '../app/revolt/types';

const OUT_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'revolt', 'events');

/** Drop undefined keys; keep explicit null. */
function clean<T extends Record<string, unknown>>(o: T): T {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(o)) if (v !== undefined) out[k] = v;
  return out as T;
}

function toYaml(r: Revolution): Record<string, unknown> {
  return clean({
    slug: r.slug,
    title: r.title,
    subtitle: r.subtitle,
    date_display: r.dateDisplay,
    date_start: r.dateStart,
    date_end: r.dateEnd,
    date_precision: 'year',
    era: r.era,
    region: r.region,
    country: r.country,
    revolt_type: r.revoltType,
    status: r.status,
    summary: r.summary,
    significance: r.significance,
    analytical_outlook: r.analyticalOutlook,
    grievances: r.grievances.map((g) => ({ kind: g.kind, intensity: g.intensity, evidence: g.evidence })),
    structural_pressures: r.structuralPressures,
    repression_level: r.repressionLevel,
    actors: r.actors.map((a) => ({
      actor_type: a.actorType, name: a.name, description: a.description,
      role_in_arc: a.roleInArc, defected: a.defected,
    })),
    tactics: r.tactics.map((t) => ({ tactic_type: t.tacticType, description: t.description, prominence: t.prominence })),
    resistance_type: r.resistanceType,
    phases: r.phases.map((p) => clean({
      phase: p.phase, label: p.label, date_start: p.dateStart,
      t_start: p.tStart, t_end: p.tEnd, intensity: p.intensity,
      reached: p.reached, summary: p.summary, key_events: p.keyEvents,
    })),
    ate_its_children: r.ateItsChildren,
    outcome: r.outcome,
    peak_participation_pct: r.peakParticipationPct ?? null,
    peak_participation_display: r.peakParticipationDisplay,
    crossed_participation_threshold: r.crossedParticipationThreshold ?? null,
    military_defection: r.militaryDefection,
    foreign_intervention: r.foreignIntervention,
    duration_days: r.durationDays ?? null,
    death_toll: r.deathToll,
    death_toll_low: r.deathTollLow ?? null,
    death_toll_high: r.deathTollHigh ?? null,
    regime_before: r.regimeBefore,
    regime_after: r.regimeAfter,
    democratization_delta: r.democratizationDelta ?? null,
    success_factors: r.successFactors.map((f) => clean({
      factor_key: f.factorKey, label: f.label, framework: f.framework,
      status: f.status, direction: f.direction, base_rate: f.baseRate,
      rationale: f.rationale, sources: f.sources, as_of: f.asOf, confidence: f.confidence,
    })),
    key_figures: r.keyFigures.map((k) => clean({ name: k.name, role: k.role, born: k.born, died: k.died, wikipedia: k.wikipedia })),
    legacy_points: r.legacyPoints,
    hero_image_url: r.heroImage,
    hero_image_attribution: r.heroAttribution,
    related_revolt_slugs: r.relatedRevoltSlugs,
    related_history_slugs: r.relatedHistorySlugs,
    live_query: r.liveQuery ? clean({ ...r.liveQuery }) : undefined,
    analysis_reviewed_at: r.analysisReviewedAt,
    prediction_confidence: r.predictionConfidence,
    is_published: r.published,
    // relations consumed by the loader (not columns)
    perspectives: r.perspectives.map((p) => ({
      viewpoint: p.viewpoint, viewpoint_type: p.viewpointType, region_origin: p.regionOrigin,
      narrative: p.narrative, key_arguments: p.keyArguments, sources: [],
      notable_quotes: p.notableQuotes, emphasized: p.emphasized, omitted: p.omitted,
    })),
    media: r.media.map((m) => clean({
      media_type: m.type, title: m.caption, source_url: m.url,
      attribution: m.attribution, license: 'public-domain', creation_date: m.year,
    })),
    connections: r.connections.map((c) => ({ target_slug: c.targetSlug, connection_type: c.type, description: c.description })),
  });
}

let n = 0;
for (const r of MOCK_REVOLUTIONS) {
  if (r.slug === 'french-revolution') continue; // keep the hand-authored canary
  const doc = yaml.dump(toYaml(r), { lineWidth: -1, noRefs: true });
  writeFileSync(join(OUT_DIR, `${r.slug}.yaml`), doc, 'utf8');
  n += 1;
  console.log(`wrote ${r.slug}.yaml`);
}
console.log(`\n${n} files written to ${OUT_DIR}`);
