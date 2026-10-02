"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ComponentProps } from "react";

/* ---------------------------------------------------------------------------
   ChromeLink: a link in the shared chrome (masthead, footer, tab bar) that
   prefetches on intent rather than on sight.

   Every page carries the masthead and the footer, and between them they link
   every section. A plain <Link> prefetches its route the moment it scrolls
   into view, and with each route's RSC payload the router preloads that
   route's stylesheets: up to eight CSS chunks per page that the page never
   used ("preloaded but not used within a few seconds", audit 2 F7, P2-4),
   plus a dozen payload fetches, on every load, for routes the reader mostly
   never opens. Here the route is fetched when the pointer reaches the link or
   focus lands on it, which is still ahead of the click.
   --------------------------------------------------------------------------- */

type Props = Omit<ComponentProps<typeof Link>, "prefetch">;

export default function ChromeLink({ href, onPointerEnter, onFocus, onTouchStart, ...rest }: Props) {
  const router = useRouter();
  const target = typeof href === "string" ? href : href.pathname ?? "/";
  const warm = () => {
    try { router.prefetch(target); } catch { /* prefetch is a hint */ }
  };
  return (
    <Link
      href={href}
      prefetch={false}
      onPointerEnter={(e) => { warm(); onPointerEnter?.(e); }}
      onFocus={(e) => { warm(); onFocus?.(e); }}
      onTouchStart={(e) => { warm(); onTouchStart?.(e); }}
      {...rest}
    />
  );
}
