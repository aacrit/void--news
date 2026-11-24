import "../styles/ig-render.css";

/* ---------------------------------------------------------------------------
   IG route layout — bare canvas for Playwright screenshots.

   The root layout still wraps this (Next.js layout composition), but the
   ig-render.css imported here hides MobileNav, FloatingPlayer, the skip-to-
   content link, and removes body background. Playwright captures a clean
   1080×1350 frame with no chrome.

   This layout serves both /ig/render/[postId] (screenshot output) and
   /admin/ig (the approval surface). The admin surface gets a `data-mode`
   class so it can re-enable readable styling.
   --------------------------------------------------------------------------- */

export default function IgLayout({ children }: { children: React.ReactNode }) {
  return <div className="ig-root">{children}</div>;
}
