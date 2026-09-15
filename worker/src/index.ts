/**
 * void-api — Cloudflare Worker fronting D1 for the live user-write path.
 *
 * This is the ONLY live database in the Void News Cloudflare stack. Every READ
 * on the site is static JSON on the CDN; only the ship board / feedback writes
 * need a database. This Worker re-implements the access control, rate limits,
 * and the sync_ship_votes recount that Supabase RLS + Postgres triggers +
 * SECURITY DEFINER functions used to enforce. See ../migration/PORT_NOTES.md.
 *
 * Routes (all under /api/ship):
 *   GET  /api/ship/requests            list requests (privileged cols omitted)
 *   POST /api/ship/requests            submit (forces status/votes; ip rate-limit)
 *   POST /api/ship/vote                {request_id, fingerprint} -> new count
 *   GET  /api/ship/replies?request_id  list replies for a request
 *   POST /api/ship/reply               {request_id, body, fingerprint} rate-limited
 *   GET  /api/ship/stats               counts by status
 *   GET  /api/health                   ok
 */

export interface Env {
  DB: D1Database;
  ALLOWED_ORIGINS: string;
  IP_SALT: string;
}

// ── Public column list (mirrors fetchShipRequests; omits device_info/ip_hash) ──
const REQUEST_PUBLIC_COLS =
  "id,title,description,category,area,edition_context,status,priority,votes," +
  "ceo_response,claude_branch,shipped_commit,shipped_diff_summary,created_at," +
  "triaged_at,shipped_at,updated_at";

const CATEGORIES = new Set(["bug", "feature", "enhancement"]);
const AREAS = new Set(["frontend", "pipeline", "bias", "audio", "design", "other"]);
const EDITIONS = new Set(["world", "us", "europe", "south-asia"]);

function corsHeaders(origin: string | null, env: Env): Record<string, string> {
  const allowed = env.ALLOWED_ORIGINS.split(",").map((s) => s.trim());
  const allow = origin && allowed.includes(origin) ? origin : allowed[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(body: unknown, status: number, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

async function ipHash(req: Request, salt: string): Promise<string> {
  const ip = req.headers.get("CF-Connecting-IP") || "0.0.0.0";
  const data = new TextEncoder().encode(`${salt}:${ip}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 64);
}

function uuid(): string {
  return crypto.randomUUID();
}

/** ISO-8601 UTC, second precision (matches CURRENT_TIMESTAMP style). */
function nowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** Rows inserted within the last hour, filtered by an equality column (or global). */
async function countLastHour(
  env: Env,
  table: string,
  col?: string,
  val?: string,
): Promise<number> {
  const since = new Date(Date.now() - 3600_000).toISOString();
  const where = col ? `created_at >= ? AND ${col} = ?` : `created_at >= ?`;
  const stmt = env.DB.prepare(`SELECT COUNT(*) AS n FROM ${table} WHERE ${where}`);
  const bound = col ? stmt.bind(since, val) : stmt.bind(since);
  const row = await bound.first<{ n: number }>();
  return row?.n ?? 0;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = request.headers.get("Origin");
    const cors = corsHeaders(origin, env);
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    try {
      // ── GET /api/health ──
      if (path === "/api/health") return json({ ok: true }, 200, cors);

      // ── GET /api/ship/requests ──
      if (path === "/api/ship/requests" && request.method === "GET") {
        const { results } = await env.DB.prepare(
          `SELECT ${REQUEST_PUBLIC_COLS} FROM ship_requests ORDER BY created_at DESC`,
        ).all();
        return json(results ?? [], 200, cors);
      }

      // ── POST /api/ship/requests (submit) ──
      if (path === "/api/ship/requests" && request.method === "POST") {
        const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;
        if (!body) return json({ error: "Invalid JSON." }, 400, cors);

        const title = String(body.title ?? "").trim();
        const description = String(body.description ?? "").trim();
        const category = String(body.category ?? "feature");
        const area = String(body.area ?? "other");
        const editionRaw = body.edition_context;
        const edition = editionRaw == null ? null : String(editionRaw);

        if (title.length === 0 || title.length > 120)
          return json({ error: "Title must be 1 to 120 characters." }, 400, cors);
        if (description.length === 0 || description.length > 2000)
          return json({ error: "Description must be 1 to 2000 characters." }, 400, cors);
        if (!CATEGORIES.has(category)) return json({ error: "Unknown category." }, 400, cors);
        if (!AREAS.has(area)) return json({ error: "Unknown area." }, 400, cors);
        if (edition !== null && !EDITIONS.has(edition))
          return json({ error: "Unknown edition." }, 400, cors);

        const iph = await ipHash(request, env.IP_SALT);

        // Rate limit (migration 068): >=5/hr per ip_hash, or >=120/hr global.
        if ((await countLastHour(env, "ship_requests", "ip_hash", iph)) >= 5)
          return json({ error: "Too many submissions from here. Try again later." }, 429, cors);
        if ((await countLastHour(env, "ship_requests")) >= 120)
          return json({ error: "The board is busy right now. Try again shortly." }, 429, cors);

        const id = uuid();
        const ts = nowIso();
        const deviceInfo =
          body.device_info == null ? null : String(body.device_info).slice(0, 200);
        // Privileged columns are set server-side; client input for them is ignored.
        await env.DB.prepare(
          `INSERT INTO ship_requests
             (id,title,description,category,area,edition_context,status,votes,
              device_info,ip_hash,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
        )
          .bind(id, title, description, category, area, edition, "submitted", 0, deviceInfo, iph, ts, ts)
          .run();

        const row = await env.DB.prepare(
          `SELECT ${REQUEST_PUBLIC_COLS} FROM ship_requests WHERE id = ?`,
        )
          .bind(id)
          .first();
        return json(row, 201, cors);
      }

      // ── POST /api/ship/vote (insert + recount = sync_ship_votes) ──
      if (path === "/api/ship/vote" && request.method === "POST") {
        const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;
        const requestId = String(body?.request_id ?? "");
        const fingerprint = String(body?.fingerprint ?? "").slice(0, 64);
        if (!requestId || !fingerprint)
          return json({ error: "request_id and fingerprint are required." }, 400, cors);

        // Insert the vote; UNIQUE(request_id,fingerprint) makes a repeat a no-op.
        try {
          await env.DB.prepare(
            `INSERT INTO ship_votes (id,request_id,fingerprint,created_at) VALUES (?,?,?,?)`,
          )
            .bind(uuid(), requestId, fingerprint, nowIso())
            .run();
        } catch (e) {
          const msg = String(e);
          if (!/UNIQUE|constraint/i.test(msg)) throw e;
          // Duplicate vote: fall through and return the current authoritative count.
        }

        // Idempotent recount -> persist -> return (the anti-inflation property).
        await env.DB.prepare(
          `UPDATE ship_requests
             SET votes = (SELECT COUNT(*) FROM ship_votes WHERE request_id = ?)
           WHERE id = ?`,
        )
          .bind(requestId, requestId)
          .run();
        const row = await env.DB.prepare(`SELECT votes FROM ship_requests WHERE id = ?`)
          .bind(requestId)
          .first<{ votes: number }>();
        if (!row) return json({ error: "Unknown request." }, 404, cors);
        return json({ votes: row.votes }, 200, cors);
      }

      // ── GET /api/ship/replies?request_id= ──
      if (path === "/api/ship/replies" && request.method === "GET") {
        const requestId = url.searchParams.get("request_id");
        if (!requestId) return json({ error: "request_id is required." }, 400, cors);
        const { results } = await env.DB.prepare(
          `SELECT id,request_id,body,created_at FROM ship_replies
           WHERE request_id = ? ORDER BY created_at ASC`,
        )
          .bind(requestId)
          .all();
        return json(results ?? [], 200, cors);
      }

      // ── POST /api/ship/reply ──
      if (path === "/api/ship/reply" && request.method === "POST") {
        const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;
        const requestId = String(body?.request_id ?? "");
        const text = String(body?.body ?? "").trim();
        const fingerprint = String(body?.fingerprint ?? "").slice(0, 64);
        if (!requestId || !text || !fingerprint)
          return json({ error: "request_id, body and fingerprint are required." }, 400, cors);
        if (text.length > 280) return json({ error: "Reply must be 280 characters or fewer." }, 400, cors);

        // Rate limit (068 per-fingerprint 15/hr, 070 global 200/hr).
        if ((await countLastHour(env, "ship_replies", "fingerprint", fingerprint)) >= 15)
          return json({ error: "You are replying too fast. Try again later." }, 429, cors);
        if ((await countLastHour(env, "ship_replies")) >= 200)
          return json({ error: "The board is busy right now. Try again shortly." }, 429, cors);

        // Parent must exist (FK is enforced, but return a clean 404).
        const parent = await env.DB.prepare(`SELECT 1 AS x FROM ship_requests WHERE id = ?`)
          .bind(requestId)
          .first();
        if (!parent) return json({ error: "Unknown request." }, 404, cors);

        const id = uuid();
        const ts = nowIso();
        await env.DB.prepare(
          `INSERT INTO ship_replies (id,request_id,body,fingerprint,created_at) VALUES (?,?,?,?,?)`,
        )
          .bind(id, requestId, text, fingerprint, ts)
          .run();
        return json({ id, request_id: requestId, body: text, created_at: ts }, 201, cors);
      }

      // ── GET /api/ship/stats ──
      if (path === "/api/ship/stats" && request.method === "GET") {
        const { results } = await env.DB.prepare(
          `SELECT status, COUNT(*) AS n FROM ship_requests GROUP BY status`,
        ).all<{ status: string; n: number }>();
        const counts: Record<string, number> = {
          submitted: 0, triaged: 0, building: 0, shipped: 0, wontship: 0,
        };
        for (const r of results ?? []) counts[r.status] = r.n;
        return json(counts, 200, cors);
      }

      return json({ error: "Not found." }, 404, cors);
    } catch (e) {
      return json({ error: "Server error.", detail: String(e) }, 500, cors);
    }
  },
};
