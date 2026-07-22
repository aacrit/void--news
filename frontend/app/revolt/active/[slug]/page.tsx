import type { Metadata } from 'next';
import { MOCK_ACTIVE, MOCK_REVOLUTIONS } from '../../mockData';
import { HOOKS } from '../../hooks';
import ActiveDetailClient from './ActiveDetailClient';

export function generateStaticParams() {
  return MOCK_ACTIVE.map((r) => ({ slug: r.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const r = MOCK_REVOLUTIONS.find((x) => x.slug === slug);
  const title = r?.title ?? slug.replace(/-/g, ' ');
  return {
    title: `${title} — void --revolt`,
    description: HOOKS[slug] ?? r?.subtitle ?? 'A live movement weighed against the historical record.',
  };
}

export default function ActiveSlugPage({ params }: { params: Promise<{ slug: string }> }) {
  return <ActiveDetailClient slugPromise={params} />;
}
