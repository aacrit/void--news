import HistoryTopbar from "./components/HistoryTopbar";
import HistoryFooter from "./components/HistoryFooter";

/* ===========================================================================
   History Layout — Wraps all /history routes
   Applies .hist-page container, includes topbar and footer.
   =========================================================================== */

export default function HistoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="hist-page">
      {/* Desk-lamp vignette overlay */}
      <div className="hist-vignette" aria-hidden="true" />
      <HistoryTopbar />
      <main id="main-content">{children}</main>
      <HistoryFooter />
    </div>
  );
}
