import type { Metadata } from 'next';
import ActiveTracker from '../components/ActiveTracker';

export const metadata: Metadata = {
  title: 'The Living — void --revolt',
  description: 'Uprisings and revolutions underway now, placed on the arc and weighed against the historical record. Analytical, not predictive.',
};

export default function ActivePage() {
  return <ActiveTracker />;
}
