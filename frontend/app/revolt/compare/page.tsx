import type { Metadata } from 'next';
import ComparisonLab from '../components/ComparisonLab';

export const metadata: Metadata = {
  title: 'Comparison Lab — void --revolt',
  description: 'Lay 2 to 4 revolutions over one shared anatomy and overlay their trajectories on the Brinton phase arc.',
};

export default function ComparePage() {
  return <ComparisonLab />;
}
