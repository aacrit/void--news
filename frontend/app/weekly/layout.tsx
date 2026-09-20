import "../styles/weekly.css";

export default function WeeklyLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* Progressive enhancement, copied from app/history/layout.tsx, which has
          shipped this since the section was built. Every weekly section opens
          at `opacity: 0` and is revealed by an IntersectionObserver, so with JS
          off — or with a bundle that failed to load — the whole issue is blank
          paper. The prose is in the HTML either way, which is why a crawler
          never saw the problem and a reader would have seen nothing else. */}
      <noscript>
        <style>{`.wk-reveal, .wk-reveal-child { opacity: 1 !important; transform: none !important; filter: none !important; transition: none !important; }`}</style>
      </noscript>
      {children}
    </>
  );
}
