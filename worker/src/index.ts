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
 *   POST /api/ship/vote                {request_id} -> new count
 *   GET  /api/ship/replies?request_id  list replies for a request
 *   POST /api/ship/reply               {request_id, body} rate-limited
 *   GET  /api/ship/stats               counts by status
 *   GET  /api/health                   ok
 *
 * Identity (rev 85 WS-D, audit 5 H1/H2): every write is keyed on the SERVER's
 * salted hash of CF-Connecting-IP, never on a client-supplied string. The old
 * `fingerprint` field is accepted and ignored; the legacy NOT NULL
 * `fingerprint` column is filled with the same ip hash so its old
 * UNIQUE(request_id, fingerprint) agrees with the new UNIQUE(request_id,
 * ip_hash) from migrations/0001. Rotating the client fingerprint therefore
 * buys nothing.
 *
 * IP_SALT must be a real secret (`wrangler secret put IP_SALT`). With it
 * missing or still the old placeholder, every write returns 503 and logs why:
 * a guessable salt makes the IPv4 space brute-forceable from the hash.
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

/** The literal that used to be committed in wrangler.toml [vars]. */
export const PLACEHOLDER_SALTS = new Set(["void-news-dev-salt-change-me", "change-me", ""]);
const MIN_SALT_LENGTH = 16;

/** Per-IP and global hourly caps. The globals are backstops only, set far
 *  above any honest day, so one client can no longer lock everyone out. */
export const LIMITS = {
  submitsPerIp: 5,
  submitsGlobal: 1000,
  votesPerIp: 30,
  votesGlobal: 5000,
  repliesPerIp: 15,
  repliesGlobal: 2000,
  /** GET /api/ship/requests page size (Sec L5: it was unbounded). */
  listLimit: 200,
} as const;

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

/** Device classes the feedback form may send; see FeedbackForm.tsx. */
const DEVICE_CLASS_RE =
  /^(mobile|tablet|desktop)(?: (chrome|safari|firefox|edge|opera|samsung|other))?$/;

export function coarseDevice(raw: unknown): string | null {
  if (raw == null) return null;
  const v = String(raw).trim().toLowerCase();
  return DEVICE_CLASS_RE.test(v) ? v : null;
}

/** The salt, or null when it is missing or a known placeholder. */
export function usableSalt(env: Env): string | null {
  const salt = (env.IP_SALT ?? "").trim();
  if (PLACEHOLDER_SALTS.has(salt) || salt.length < MIN_SALT_LENGTH) return null;
  return salt;
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

      // Every write hashes the IP, so every write needs a real salt.
      let salt: string | null = null;
      if (request.method === "POST") {
        salt = usableSalt(env);
        if (salt === null) {
          console.error(
            "void-api: IP_SALT is missing or a placeholder; refusing writes. " +
              "Run `wrangler secret put IP_SALT` with a long random value.",
          );
          return json({ error: "Writes are paused. Try again later." }, 503, cors);
        }
      }

      // ── GET /api/ship/requests ──
      if (path === "/api/ship/requests" && request.method === "GET") {
        const { results } = await env.DB.prepare(
          `SELECT ${REQUEST_PUBLIC_COLS} FROM ship_requests ORDER BY created_at DESC LIMIT ?`,
        )
          .bind(LIMITS.listLimit)
          .all();
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

        const iph = await ipHash(request, salt!);

        // Rate limit: per ip_hash, plus a high global backstop.
        if ((await countLastHour(env, "ship_requests", "ip_hash", iph)) >= LIMITS.submitsPerIp)
          return json({ error: "Too many submissions from here. Try again later." }, 429, cors);
        if ((await countLastHour(env, "ship_requests")) >= LIMITS.submitsGlobal)
          return json({ error: "The board is busy right now. Try again shortly." }, 429, cors);

        const id = uuid();
        const ts = nowIso();
        // Only a coarse device class is stored ("mobile safari"). Anything else,
        // such as a full user agent from an old cached page, is dropped.
        const deviceInfo = coarseDevice(body.device_info);
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

      // ── POST /api/ship/vote (parent check, cap, insert, recount) ──
      if (path === "/api/ship/vote" && request.method === "POST") {
        const body = (await request.json().catch(() => null)) as Record<string, unknown> | null;
        const requestId = String(body?.request_id ?? "");
        if (!requestId) return json({ error: "request_id is required." }, 400, cors);

        // Parent first: a vote on a missing request is a clean 404, never an
        // FK failure surfacing as a 500.
        const parent = await env.DB.prepare(`SELECT 1 AS x FROM ship_requests WHERE id = ?`)
          .bind(requestId)
          .first();
        if (!parent) return json({ error: "Unknown request." }, 404, cors);

        const iph = await ipHash(request, salt!);
        if ((await countLastHour(env, "ship_votes", "ip_hash", iph)) >= LIMITS.votesPerIp)
          return json({ error: "Too many votes from here. Try again later." }, 429, cors);
        if ((await countLastHour(env, "ship_votes")) >= LIMITS.votesGlobal)
          return json({ error: "The board is busy right now. Try again shortly." }, 429, cors);

        // UNIQUE(request_id, ip_hash) makes a repeat from the same IP a no-op,
        // whatever fingerprint the client claims. The legacy fingerprint
        // column carries the ip hash too (see the header).
        try {
          await env.DB.prepare(
            `INSERT INTO ship_votes (id,request_id,fingerprint,ip_hash,created_at) VALUES (?,?,?,?,?)`,
          )
            .bind(uuid(), requestId, iph, iph, nowIso())
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
        if (!requestId || !text)
          return json({ error: "request_id and body are required." }, 400, cors);
        if (text.length > 280) return json({ error: "Reply must be 280 characters or fewer." }, 400, cors);

        // Parent must exist (FK is enforced, but return a clean 404).
        const parent = await env.DB.prepare(`SELECT 1 AS x FROM ship_requests WHERE id = ?`)
          .bind(requestId)
          .first();
        if (!parent) return json({ error: "Unknown request." }, 404, cors);

        const iph = await ipHash(request, salt!);
        if ((await countLastHour(env, "ship_replies", "ip_hash", iph)) >= LIMITS.repliesPerIp)
          return json({ error: "You are replying too fast. Try again later." }, 429, cors);
        if ((await countLastHour(env, "ship_replies")) >= LIMITS.repliesGlobal)
          return json({ error: "The board is busy right now. Try again shortly." }, 429, cors);

        const id = uuid();
        const ts = nowIso();
        await env.DB.prepare(
          `INSERT INTO ship_replies (id,request_id,body,fingerprint,ip_hash,created_at) VALUES (?,?,?,?,?,?)`,
        )
          .bind(id, requestId, text, iph, iph, ts)
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
      // Log the cause for `wrangler tail`; never echo it to the client.
      console.error("void-api: unhandled error", e);
      return json({ error: "Server error." }, 500, cors);
    }
  },
};
