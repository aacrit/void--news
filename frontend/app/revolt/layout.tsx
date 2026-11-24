import '../styles/revolt.css';
import ErrorBoundary from '../components/ErrorBoundary';
import RevoltTopbar from './components/RevoltTopbar';
import RevoltFooter from './components/RevoltFooter';

/* ===========================================================================
   void --revolt layout — wraps all /revolt routes.
   Applies the .revolt-page container ("Barricade Press"), topbar + footer,
   and an ErrorBoundary. Static export: no server data fetch here.
   =========================================================================== */

export default function RevoltLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="revolt-page">
      <noscript>
        <style>{`.rev-reel { overflow: visible !important; } .rev-frame--unreached { opacity: 1 !important; }`}</style>
      </noscript>
      <RevoltTopbar />
      <main id="main-content">
        <ErrorBoundary>{children}</ErrorBoundary>
      </main>
      <RevoltFooter />
    </div>
  );
}
