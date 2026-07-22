'use client';

import { use } from 'react';
import type { RevoltOutcome } from '../../types';
import { OUTCOME_LABELS } from '../../anatomy';
import { fetchRevolutionsByOutcome } from '../../data';
import RevoltBrowser from '../../components/RevoltBrowser';

export default function OutcomeBrowserClient({ slugPromise }: { slugPromise: Promise<{ outcome: string }> }) {
  const { outcome } = use(slugPromise);
  const label = OUTCOME_LABELS[outcome as RevoltOutcome] ?? outcome;
  return (
    <RevoltBrowser
      kicker="void --revolt · by outcome"
      heading={label}
      blurb={`Revolutions in the archive that ${label.toLowerCase()}. The same anatomy, sorted by where it landed.`}
      fetcher={() => fetchRevolutionsByOutcome(outcome)}
      dep={outcome}
    />
  );
}
