import type { Metadata } from 'next';
import { PHASE_SKELETON, phaseSpec } from '../../anatomy';
import type { PhaseKey } from '../../types';
import PhaseBrowserClient from './PhaseBrowserClient';

export function generateStaticParams() {
  return PHASE_SKELETON.map((p) => ({ phase: p.key }));
}

export async function generateMetadata({ params }: { params: Promise<{ phase: string }> }): Promise<Metadata> {
  const { phase } = await params;
  const label = phaseSpec(phase as PhaseKey)?.label ?? phase;
  return {
    title: `Revolutions that reached ${label} — void --revolt`,
    description: `Every revolution in the archive whose arc reached the ${label} stage.`,
  };
}

export default function PhasePage({ params }: { params: Promise<{ phase: string }> }) {
  return <PhaseBrowserClient slugPromise={params} />;
}
