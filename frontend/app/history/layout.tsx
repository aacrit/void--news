import '../styles/history.css';

/* ===========================================================================
   History Layout: wraps all /history routes.
   Applies the .hist-page container (archival paper, palette, vignette).
   The masthead and footer are the site's own, mounted once in the root
   layout and skinned by this section's accent; History has no topbar of its
   own. Decorative overlays removed (foxing, laid paper lines). Vignette kept
   at reduced opacity.
   =========================================================================== */

export default function HistoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="hist-page hist-page--clean">
      {/* Progressive enhancement: if JS fails, reveal all content */}
      <noscript>
        <style>{`.hist-reveal { opacity: 1 !important; transform: none !important; filter: none !important; transition: none !important; }`}</style>
      </noscript>
      {/* Desk-lamp vignette overlay (halved opacity via hist-page--clean) */}
      <div className="hist-vignette" aria-hidden="true" />
      <main id="main-content">{children}</main>
    </div>
  );
}
