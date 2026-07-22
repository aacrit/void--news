'use client';

import { use } from 'react';
import type { PhaseKey } from '../../types';
import { phaseSpec } from '../../anatomy';
import { fetchRevolutionsByPhase } from '../../data';
import RevoltBrowser from '../../components/RevoltBrowser';

export default function PhaseBrowserClient({ slugPromise }: { slugPromise: Promise<{ phase: string }> }) {
  const { phase } = use(slugPromise);
  const spec = phaseSpec(phase as PhaseKey);
  const label = spec?.label ?? phase;
  return (
    <RevoltBrowser
      kicker="void --revolt · by phase"
      heading={`Reached ${label}`}
      blurb={spec?.gloss ?? `Revolutions whose arc reached the ${label} stage.`}
      fetcher={() => fetchRevolutionsByPhase(phase)}
      dep={phase}
    />
  );
}
