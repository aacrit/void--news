import HistoryTopbar from "./components/HistoryTopbar";
import HistoryFooter from "./components/HistoryFooter";

/* ===========================================================================
   History Layout — Wraps all /history routes
   Applies .hist-page container, includes topbar and footer.
   Decorative overlays removed (foxing, laid paper lines).
   Vignette kept at reduced opacity.
   =========================================================================== */

export default function HistoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="hist-page hist-page--clean">
      {/* Desk-lamp vignette overlay (halved opacity via hist-page--clean) */}
      <div className="hist-vignette" aria-hidden="true" />
      <HistoryTopbar />
      <main id="main-content">{children}</main>
      <HistoryFooter />
    </div>
  );
}
