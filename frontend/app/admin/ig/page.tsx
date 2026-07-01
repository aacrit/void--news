// IG admin — stubbed for production static export.
//
// The original page uses `dynamic = "force-dynamic"` + service-role
// Supabase reads via the server-only client. Both are forbidden by Next 16
// + `output: "export"`. The page only ever worked under `npm run dev`
// anyway. To re-enable: split this route off the static build (separate
// Next config for the admin sub-app, or implement as a CF Worker function).
// Tracked in the holistic-redesign-2026-05-15 PR — IG team to address.
//
// Original implementation preserved in git history. ReviewCard.tsx +
// PostedRow.tsx are kept on disk for reference.

export default function IgAdminPagePlaceholder() {
  return (
    <main style={{ padding: 32, fontFamily: "var(--font-text, system-ui)" }}>
      <h1>IG admin disabled in static build</h1>
      <p>
        Run <code>npm run dev</code> locally and revert this stub to use
        the original admin surface. Service-role Supabase reads require a
        runtime not available in CF Pages static export.
      </p>
    </main>
  );
}
