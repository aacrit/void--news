// IG inbox admin — stubbed for production static export. Same reasoning
// as ../page.tsx. Original implementation preserved in git history.

export default function IgInboxPlaceholder() {
  return (
    <main style={{ padding: 32, fontFamily: "var(--font-text, system-ui)" }}>
      <h1>IG inbox disabled in static build</h1>
      <p>
        Run <code>npm run dev</code> locally and revert this stub to read
        live comments, DMs, mentions, and hashtag candidates.
      </p>
    </main>
  );
}
