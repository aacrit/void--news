import { headers } from "next/headers";
import {
  listIgComments,
  listIgDms,
  listIgMentions,
  listIgHashtagCandidates,
} from "../../../lib/supabase-server-ig";
import "../../../styles/ig-render.css";
import "../admin.css";
import "./inbox.css";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export function generateStaticParams() {
  return [];
}

function authOk(authHeader: string | null): boolean {
  const u = process.env.IG_ADMIN_USER;
  const p = process.env.IG_ADMIN_PASSWORD;
  if (!u || !p) return false;
  if (!authHeader?.startsWith("Basic ")) return false;
  let decoded: string;
  try {
    decoded = atob(authHeader.slice(6));
  } catch {
    return false;
  }
  const [user, pass] = decoded.split(":", 2);
  return user === u && pass === p;
}

export default async function InboxPage() {
  const h = await headers();
  if (!authOk(h.get("authorization"))) {
    return (
      <div className="ig-admin-unauth">
        <h1>/admin/ig/inbox</h1>
        <p>Auth required.</p>
      </div>
    );
  }

  const [comments, dms, mentions, hashtags] = await Promise.all([
    listIgComments(30),
    listIgDms(30),
    listIgMentions(20),
    listIgHashtagCandidates(20),
  ]);

  return (
    <div className="ig-admin ig-inbox" data-admin="true">
      <header className="ig-admin__hdr">
        <h1>void --news / ig inbox</h1>
        <p className="ig-admin__meta">
          {dms.filter((d) => d.priority === "press").length} press DM ·{" "}
          {dms.filter((d) => d.priority === "inbox").length} general DM ·{" "}
          {comments.length} comments awaiting reply ·{" "}
          {mentions.length} new mentions ·{" "}
          {hashtags.length} engagement opportunities
        </p>
      </header>

      <section className="ig-admin__section">
        <h2>Press DMs</h2>
        {dms.filter((d) => d.priority === "press").length === 0 ? (
          <p className="ig-admin__empty">No press DMs in the queue.</p>
        ) : (
          dms
            .filter((d) => d.priority === "press")
            .map((d) => (
              <div key={d.id} className="ig-inbox__dm ig-inbox__dm--press">
                <div className="ig-inbox__dm-hdr">
                  <strong>@{d.ig_username ?? "unknown"}</strong>
                  <span>{new Date(d.created_at).toLocaleString()}</span>
                  {d.first_touch_sent && (
                    <span className="ig-inbox__tag">first-touch sent</span>
                  )}
                </div>
                <p className="ig-inbox__dm-text">{d.text}</p>
                {d.matched_keywords && d.matched_keywords.length > 0 && (
                  <p className="ig-inbox__hint">
                    keywords: {d.matched_keywords.join(", ")}
                  </p>
                )}
              </div>
            ))
        )}
      </section>

      <section className="ig-admin__section">
        <h2>Comments needing reply</h2>
        {comments.length === 0 ? (
          <p className="ig-admin__empty">Inbox zero on comments.</p>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="ig-inbox__comment">
              <div className="ig-inbox__dm-hdr">
                <strong>@{c.ig_username ?? "unknown"}</strong>
                <span className="ig-inbox__tag" data-score={Math.round(c.score)}>
                  score {Math.round(c.score)}
                </span>
                <span>{new Date(c.created_at).toLocaleString()}</span>
                <a
                  href={`https://www.instagram.com/p/${c.ig_media_id}`}
                  target="_blank"
                  rel="noopener"
                >
                  open post →
                </a>
              </div>
              <p className="ig-inbox__dm-text">{c.text}</p>
              {c.reply_drafted && (
                <p className="ig-inbox__draft">draft: {c.reply_drafted}</p>
              )}
            </div>
          ))
        )}
      </section>

      <section className="ig-admin__section">
        <h2>General DMs</h2>
        {dms.filter((d) => d.priority === "inbox").length === 0 ? (
          <p className="ig-admin__empty">No general DMs.</p>
        ) : (
          dms
            .filter((d) => d.priority === "inbox")
            .map((d) => (
              <div key={d.id} className="ig-inbox__dm">
                <div className="ig-inbox__dm-hdr">
                  <strong>@{d.ig_username ?? "unknown"}</strong>
                  <span>{new Date(d.created_at).toLocaleString()}</span>
                </div>
                <p className="ig-inbox__dm-text">{d.text}</p>
              </div>
            ))
        )}
      </section>

      <section className="ig-admin__section">
        <h2>Mentions</h2>
        {mentions.length === 0 ? (
          <p className="ig-admin__empty">No new mentions.</p>
        ) : (
          mentions.map((m) => (
            <div key={m.id} className="ig-inbox__mention">
              <div className="ig-inbox__dm-hdr">
                <strong>@{m.ig_username ?? "unknown"}</strong>
                <span>{new Date(m.created_at).toLocaleString()}</span>
                {m.permalink && (
                  <a href={m.permalink} target="_blank" rel="noopener">
                    open →
                  </a>
                )}
              </div>
              {m.caption && <p className="ig-inbox__dm-text">{m.caption}</p>}
            </div>
          ))
        )}
      </section>

      <section className="ig-admin__section">
        <h2>Engagement opportunities (hashtag pulls)</h2>
        {hashtags.length === 0 ? (
          <p className="ig-admin__empty">
            Nothing surfacing. The listener runs daily at 14:00 UTC.
          </p>
        ) : (
          hashtags.map((h) => (
            <div key={h.id} className="ig-inbox__candidate">
              <div className="ig-inbox__dm-hdr">
                <span className="ig-inbox__tag" data-hashtag>
                  #{h.hashtag}
                </span>
                <strong>@{h.ig_username ?? "unknown"}</strong>
                <span>engagement {Math.round(h.engagement_score)}</span>
                {h.permalink && (
                  <a href={h.permalink} target="_blank" rel="noopener">
                    open →
                  </a>
                )}
              </div>
              {h.caption && (
                <p className="ig-inbox__dm-text">{h.caption.slice(0, 240)}</p>
              )}
            </div>
          ))
        )}
      </section>
    </div>
  );
}
