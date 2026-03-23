import type { Edition } from "../lib/types";
import { Globe, Flag } from "@phosphor-icons/react";

/* Ashoka Chakra — circle + 12 spokes, stroke only. Cleanly readable at 14–18px. */
function IndiaIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="2" strokeWidth="1" />
      {Array.from({ length: 12 }, (_, i) => {
        const angle = (i * 30 * Math.PI) / 180;
        const x1 = 12 + 2.4 * Math.cos(angle);
        const y1 = 12 + 2.4 * Math.sin(angle);
        const x2 = 12 + 9 * Math.cos(angle);
        const y2 = 12 + 9 * Math.sin(angle);
        return (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} strokeWidth="1" />
        );
      })}
    </svg>
  );
}

/* Crown — simplified Tudor crown, stroke only. Represents UK monarchy/state. */
function UKIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 17h16M4 17l2-10 4 4 2-6 2 6 4-4 2 10" strokeWidth="1.5" />
      <line x1="4" y1="19" x2="20" y2="19" strokeWidth="1.5" />
    </svg>
  );
}

/* Maple Leaf — simplified 5-point leaf, stroke only. */
function CanadaIcon({ size }: { size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path
        d="M12 3l-1.5 4-3-1.5 1 3.5-4 .5 3 2.5-1.5 3h3L12 21l2.5-6h3l-1.5-3 3-2.5-4-.5 1-3.5-3 1.5z"
        strokeWidth="1.5"
      />
    </svg>
  );
}

export default function EditionIcon({ slug, size }: { slug: Edition; size: number }) {
  if (slug === "world") return <Globe size={size} weight="light" aria-hidden="true" />;
  if (slug === "us") return <Flag size={size} weight="light" aria-hidden="true" />;
  if (slug === "india") return <IndiaIcon size={size} />;
  if (slug === "uk") return <UKIcon size={size} />;
  if (slug === "canada") return <CanadaIcon size={size} />;
  return null;
}
