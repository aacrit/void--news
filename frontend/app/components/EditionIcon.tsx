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

export default function EditionIcon({ slug, size }: { slug: Edition; size: number }) {
  if (slug === "world") return <Globe size={size} weight="light" aria-hidden="true" />;
  if (slug === "us") return <Flag size={size} weight="light" aria-hidden="true" />;
  if (slug === "india") return <IndiaIcon size={size} />;
  return null;
}
