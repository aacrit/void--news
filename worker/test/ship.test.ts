/**
 * Ship board abuse gates (rev 85 WS-D, audit 5 H1/H2, Sec L5, P1-8).
 *
 * Every write is keyed on the server's salted IP hash, so the client's
 * `fingerprint` buys nothing. These tests drive the real Worker fetch handler
 * against an in-memory D1 built from schema.sql plus migrations/.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import worker, { LIMITS, coarseDevice, type Env } from "../src/index";
import { makeD1 } from "./d1-stub";

const SALT = "a-test-salt-that-is-long-enough-0123456789";
let env: Env;
let raw: ReturnType<typeof makeD1>["raw"];

function seedRequests(n: number): string[] {
  const ids: string[] = [];
  const stmt = raw.prepare(
    `INSERT INTO ship_requests (id,title,description,status,votes,ip_hash,created_at,updated_at)
     VALUES (?,?,?,?,?,?,?,?)`,
  );
  for (let i = 0; i < n; i++) {
    const id = `req-${String(i).padStart(4, "0")}`;
    stmt.run(id, `t${i}`, `d${i}`, "submitted", 0, "seed", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z");
    ids.push(id);
  }
  return ids;
}

async function call(
  path: string,
  opts: { method?: string; body?: unknown; ip?: string } = {},
): Promise<Response> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.ip) headers["CF-Connecting-IP"] = opts.ip;
  const req = new Request(`https://void-api.example${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });
  return worker.fetch(req, env);
}

const vote = (request_id: string, ip: string, fingerprint = "fp") =>
  call("/api/ship/vote", { method: "POST", body: { request_id, fingerprint }, ip });

beforeEach(() => {
  const db = makeD1();
  raw = db.raw;
  env = { DB: db.d1, ALLOWED_ORIGINS: "https://news.voidvision.org", IP_SALT: SALT };
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("votes", () => {
  it("refuses the 31st vote from one IP within the hour", async () => {
    const ids = seedRequests(LIMITS.votesPerIp + 1);
    for (let i = 0; i < LIMITS.votesPerIp; i++) {
      const r = await vote(ids[i], "198.51.100.7", `fp-${i}`);
      expect(r.status).toBe(200);
    }
    const r31 = await vote(ids[LIMITS.votesPerIp], "198.51.100.7", "fp-new");
    expect(r31.status).toBe(429);
    const row = raw.prepare("SELECT votes FROM ship_requests WHERE id = ?").get(ids[LIMITS.votesPerIp]) as {
      votes: number;
    };
    expect(row.votes).toBe(0);
  });

  it("counts one vote per IP however many fingerprints it rotates", async () => {
    const [id] = seedRequests(1);
    for (let i = 0; i < 25; i++) {
      const r = await vote(id, "203.0.113.9", `rotating-${i}-${Math.random()}`);
      expect(r.status).toBe(200);
      expect(((await r.json()) as { votes: number }).votes).toBe(1);
    }
    const n = raw.prepare("SELECT COUNT(*) AS n FROM ship_votes WHERE request_id = ?").get(id) as { n: number };
    expect(n.n).toBe(1);
  });

  it("stores the ip hash, never the client fingerprint", async () => {
    const [id] = seedRequests(1);
    await vote(id, "203.0.113.10", "client-chosen-string");
    const row = raw.prepare("SELECT fingerprint, ip_hash FROM ship_votes").get() as {
      fingerprint: string;
      ip_hash: string;
    };
    expect(row.ip_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(row.fingerprint).toBe(row.ip_hash);
    expect(JSON.stringify(row)).not.toContain("203.0.113.10");
  });

  it("counts distinct IPs separately", async () => {
    const [id] = seedRequests(1);
    await vote(id, "192.0.2.1");
    const r = await vote(id, "192.0.2.2");
    expect(((await r.json()) as { votes: number }).votes).toBe(2);
  });

  it("checks the parent exists before inserting", async () => {
    const r = await vote("no-such-request", "192.0.2.3");
    expect(r.status).toBe(404);
    const n = raw.prepare("SELECT COUNT(*) AS n FROM ship_votes").get() as { n: number };
    expect(n.n).toBe(0);
  });
});

describe("replies", () => {
  it("caps replies per IP, not per fingerprint", async () => {
    const [id] = seedRequests(1);
    for (let i = 0; i < LIMITS.repliesPerIp; i++) {
      const r = await call("/api/ship/reply", {
        method: "POST",
        body: { request_id: id, body: `reply ${i}`, fingerprint: `fp-${i}` },
        ip: "198.51.100.20",
      });
      expect(r.status).toBe(201);
    }
    const over = await call("/api/ship/reply", {
      method: "POST",
      body: { request_id: id, body: "one more", fingerprint: "fresh" },
      ip: "198.51.100.20",
    });
    expect(over.status).toBe(429);
    // Another reader is not locked out by the first one's flood.
    const other = await call("/api/ship/reply", {
      method: "POST",
      body: { request_id: id, body: "hello" },
      ip: "198.51.100.21",
    });
    expect(other.status).toBe(201);
  });

  it("returns 404 for a missing parent", async () => {
    const r = await call("/api/ship/reply", {
      method: "POST",
      body: { request_id: "nope", body: "x" },
      ip: "198.51.100.22",
    });
    expect(r.status).toBe(404);
  });
});

describe("submits", () => {
  const submit = (ip: string, device_info?: string) =>
    call("/api/ship/requests", {
      method: "POST",
      body: { title: "A title", description: "A description", category: "bug", device_info },
      ip,
    });

  it("caps submits per IP while another IP still gets through", async () => {
    for (let i = 0; i < LIMITS.submitsPerIp; i++) expect((await submit("198.51.100.30")).status).toBe(201);
    expect((await submit("198.51.100.30")).status).toBe(429);
    expect((await submit("198.51.100.31")).status).toBe(201);
  });

  it("stores a coarse device class and drops a full user agent", async () => {
    await submit("198.51.100.40", "mobile safari");
    await submit(
      "198.51.100.41",
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Version/17.4 Mobile Safari/604.1",
    );
    const rows = raw.prepare("SELECT device_info FROM ship_requests ORDER BY created_at").all() as {
      device_info: string | null;
    }[];
    expect(rows.map((r) => r.device_info).sort()).toEqual([null, "mobile safari"].sort());
    expect(coarseDevice("desktop firefox")).toBe("desktop firefox");
    expect(coarseDevice("Mozilla/5.0")).toBeNull();
  });
});

describe("salt and errors", () => {
  for (const bad of ["", "void-news-dev-salt-change-me", "short"]) {
    it(`refuses writes with 503 when IP_SALT is ${JSON.stringify(bad)}`, async () => {
      env.IP_SALT = bad;
      const [id] = seedRequests(1);
      const r = await vote(id, "192.0.2.50");
      expect(r.status).toBe(503);
      expect(console.error).toHaveBeenCalled();
      const n = raw.prepare("SELECT COUNT(*) AS n FROM ship_votes").get() as { n: number };
      expect(n.n).toBe(0);
      // Reads still work.
      expect((await call("/api/ship/requests")).status).toBe(200);
    });
  }

  it("never echoes the error detail in a 500", async () => {
    env.DB = {
      prepare() {
        throw new Error("SQLITE secret internals");
      },
    } as unknown as D1Database;
    const r = await call("/api/ship/stats");
    expect(r.status).toBe(500);
    const text = await r.text();
    expect(text).not.toContain("SQLITE");
    expect(JSON.parse(text)).toEqual({ error: "Server error." });
  });
});

describe("listing", () => {
  it("bounds GET /api/ship/requests", async () => {
    seedRequests(LIMITS.listLimit + 5);
    const r = await call("/api/ship/requests");
    const rows = (await r.json()) as unknown[];
    expect(rows.length).toBe(LIMITS.listLimit);
    expect(JSON.stringify(rows[0])).not.toContain("ip_hash");
  });
});
