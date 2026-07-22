import type { Metadata } from 'next';
import RevoltLanding from './components/RevoltLanding';

export const metadata: Metadata = {
  title: 'void --revolt | The anatomy of revolution',
  description:
    'Every major revolution laid over one shared anatomy: grievances, the spark, the phases, the reckoning. Plus a living portal into the uprisings happening now.',
};

export default function RevoltPage() {
  return <RevoltLanding />;
}
