import type { Metadata } from 'next';
import { MOCK_HISTORICAL, MOCK_REVOLUTIONS } from '../mockData';
import { HOOKS } from '../hooks';
import RevoltDetailClient from './RevoltDetailClient';

/* Static export: prerender every concluded revolution. Sourced from the mock
   registry (never a hand-maintained array), so a loaded revolution can't 404. */
export function generateStaticParams() {
  return MOCK_HISTORICAL.map((r) => ({ slug: r.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const r = MOCK_REVOLUTIONS.find((x) => x.slug === slug);
  const title = r?.title ?? slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return {
    title: `${title} — void --revolt`,
    description: HOOKS[slug] ?? r?.subtitle ?? 'The anatomy of a revolution.',
  };
}

export default function RevoltSlugPage({ params }: { params: Promise<{ slug: string }> }) {
  return <RevoltDetailClient slugPromise={params} />;
}
