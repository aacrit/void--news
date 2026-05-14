import { headers } from "next/headers";
import { listIgPostsForReview, listIgPostsPosted, type IgPostRow } from "../../lib/supabase-server";
import "../../styles/ig-render.css";
import "./admin.css";
import { ReviewCard } from "./ReviewCard";
import { PostedRow } from "./PostedRow";

/* ---------------------------------------------------------------------------
   /admin/ig — manual approval surface for the IG automation stack.

   Auth: HTTP Basic. Credentials in env vars IG_ADMIN_USER and
   IG_ADMIN_PASSWORD. No session cookie; browser re-auths each request.

   The page is intentionally not in the static export — it requires the
   service-role Supabase key, which only the dev server (or a server runtime)
   can supply. Run `npm run dev` and visit http://localhost:3000/admin/ig.

   Operationally: when the daily generator/capture/caption cron finishes,
   the IG admin gets one or two draft posts. Open this page, scrub each
   slide on the right, edit the caption inline if needed, and click
   Approve to flip state=approved. The publisher cron ships approved rows
   on the next Mon/Thu 13:30 UTC window.
   --------------------------------------------------------------------------- */

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

export default async function AdminIgPage() {
  const h = await headers();
  if (!authOk(h.get("authorization"))) {
    return (
      <div className="ig-admin-unauth">
        <h1>/admin/ig</h1>
        <p>
          This surface requires HTTP Basic credentials. Set IG_ADMIN_USER and
          IG_ADMIN_PASSWORD in <code>.env.local</code> and re-authenticate.
        </p>
      </div>
    );
  }

  const [pending, posted] = await Promise.all([
    listIgPostsForReview(),
    listIgPostsPosted(20),
  ]);

  return (
    <div className="ig-admin" data-admin="true">
      <header className="ig-admin__hdr">
        <h1>void --news / ig review</h1>
        <p className="ig-admin__meta">
          {pending.length} pending · {posted.length} recently posted
        </p>
      </header>

      <section className="ig-admin__section">
        <h2>Pending</h2>
        {pending.length === 0 ? (
          <p className="ig-admin__empty">
            Nothing to review. The generator runs daily at 12:00 UTC.
          </p>
        ) : (
          pending.map((row: IgPostRow) => <ReviewCard key={row.id} row={row} />)
        )}
      </section>

      <section className="ig-admin__section">
        <h2>Recently posted</h2>
        {posted.length === 0 ? (
          <p className="ig-admin__empty">No posts published yet.</p>
        ) : (
          posted.map((row: IgPostRow) => <PostedRow key={row.id} row={row} />)
        )}
      </section>
    </div>
  );
}
