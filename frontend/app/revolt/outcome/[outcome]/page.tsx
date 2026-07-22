import type { Metadata } from 'next';
import { OUTCOME_LABELS } from '../../anatomy';
import OutcomeBrowserClient from './OutcomeBrowserClient';

export function generateStaticParams() {
  return Object.keys(OUTCOME_LABELS).map((outcome) => ({ outcome }));
}

export async function generateMetadata({ params }: { params: Promise<{ outcome: string }> }): Promise<Metadata> {
  const { outcome } = await params;
  const label = OUTCOME_LABELS[outcome as keyof typeof OUTCOME_LABELS] ?? outcome;
  return {
    title: `Revolutions that ${label.toLowerCase()} — void --revolt`,
    description: `Every revolution in the archive that ${label.toLowerCase()}, laid over one shared anatomy.`,
  };
}

export default function OutcomePage({ params }: { params: Promise<{ outcome: string }> }) {
  return <OutcomeBrowserClient slugPromise={params} />;
}
