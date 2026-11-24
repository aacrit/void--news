/* The service worker keeps a busy reader off the edge's 429 page.

   On 2026-10-03 thirteen quick page views made ~330 requests and 27 came back
   429; the reader saw Cloudflare's error page several times. The worker sent
   EVERY non-asset request past the HTTP cache ('reload') and handed a 429
   straight to the screen. This runs public/sw.js against a fake edge and
   asserts: a 429 retries once; a navigation still refused shows the cached
   page, or the self-retrying busy page, never the edge's; data does not
   bypass the HTTP cache; a partial (206) response is never cached.

   Run: node test/sw.test.mjs */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import vm from "node:vm";

const SRC = readFileSync(resolve(import.meta.dirname, "../public/sw.js"), "utf8");
let failures = 0;
function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

const ORIGIN = "https://news.voidvision.org";

/* A worker instance against a scripted edge. `edge` is a list of statuses
   answered in order; `cached` is what the Cache API already holds. */
function boot(edge, cached = {}) {
  const calls = [];
  const puts = [];
  const queue = [...edge];
  const listeners = {};
  const store = new Map(Object.entries(cached));
  const cache = {
    put: async (req, res) => { puts.push([typeof req === "string" ? req : req.url, res.status]); },
    addAll: async () => {},
  };
  const ctx = {
    URL, Response, Headers, Number, Math, Promise, console,
    setTimeout: (fn) => setTimeout(fn, 0),
    self: { location: { origin: ORIGIN }, addEventListener: (t, f) => { listeners[t] = f; },
      skipWaiting: () => {}, clients: { claim: () => {} } },
    caches: {
      open: async () => cache,
      match: async (req) => store.get(typeof req === "string" ? req : req.url) ?? undefined,
      keys: async () => [],
      delete: async () => true,
    },
    fetch: async (req, init) => {
      calls.push({ url: req.url, cache: init?.cache });
      const status = queue.length ? queue.shift() : 200;
      const headers = status === 429 ? { "Retry-After": "1" } : {};
      const r = new Response(status === 206 || status === 304 ? null : `edge ${status}`, { status, headers });
      Object.defineProperty(r, "type", { value: "basic" });
      return r;
    },
  };
  ctx.self.addEventListener = (t, f) => { listeners[t] = f; };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  async function request(path, { mode = "no-cors", destination = "" } = {}) {
    let p;
    listeners.fetch({ request: { url: ORIGIN + path, method: "GET", mode, destination },
      respondWith: (x) => { p = x; } });
    const res = await p;
    await new Promise((r) => setTimeout(r, 5));
    return { res, body: res ? await res.clone().text() : "" };
  }
  return { request, calls, puts };
}

const nav = { mode: "navigate", destination: "document" };

/* A 429 is retried once, and the retry's answer is what the reader gets. */
{
  const w = boot([429, 200]);
  const { res } = await w.request("/weekly/", nav);
  check("429 then 200: reader gets the page", res.status === 200, String(res.status));
  check("429 then 200: exactly one retry", w.calls.length === 2, String(w.calls.length));
}

/* Still refused, nothing cached: the busy page, not the edge's. */
{
  const w = boot([429, 429]);
  const { res, body } = await w.request("/sources/", nav);
  check("refused twice: busy page served", res.status === 503 && body.includes("One moment."), `${res.status} ${body.slice(0, 40)}`);
  check("busy page retries itself", /http-equiv="refresh"/.test(body));
  check("busy page carries no dash", !/[–—]/.test(body));
}

/* Still refused, page cached from an earlier visit: the cached copy. */
{
  const w = boot([429, 429], { [`${ORIGIN}/history/`]: new Response("cached history", { status: 200 }) });
  const { body } = await w.request("/history/", nav);
  check("refused twice with a cached copy: the copy is served", body === "cached history", body);
}

/* A navigation revalidates, it does not re-download. */
{
  const w = boot([200]);
  await w.request("/", nav);
  check("navigation uses a conditional request", w.calls[0]?.cache === "no-cache", String(w.calls[0]?.cache));
}

/* Data and RSC payloads leave the HTTP cache alone. */
{
  const w = boot([200, 200]);
  await w.request("/data/brief.json");
  await w.request("/weekly/index.txt?_rsc=abc");
  check("data does not bypass the HTTP cache", w.calls.every((c) => c.cache === undefined), JSON.stringify(w.calls));
}

/* Audio range responses are never handed to Cache.put (it throws on 206). */
{
  const w = boot([206]);
  await w.request("/audio/history/partition.mp3");
  check("a 206 is not cached", !w.puts.some(([, s]) => s === 206), JSON.stringify(w.puts));
}

/* An asset already in the cache costs no request at all. */
{
  const w = boot([], { [`${ORIGIN}/logos/cnn-com.png`]: new Response("png", { status: 200 }) });
  await w.request("/logos/cnn-com.png");
  check("a cached asset makes no request", w.calls.length === 0, String(w.calls.length));
}

/* A refused image is not retried: ~900 logos on /sources, doubled, keep the limit tripped. */
{
  const w = boot([429]);
  await w.request("/logos/cnn-com.png", { destination: "image" });
  check("a refused image is not retried", w.calls.length === 1, String(w.calls.length));
}

/* An asset refused twice is not cached. */
{
  const w = boot([429, 429]);
  const { res } = await w.request("/_next/static/chunks/a.js");
  check("asset 429 retried once", w.calls.length === 2, String(w.calls.length));
  check("a refused asset is not cached", res.status === 429 && w.puts.length === 0, JSON.stringify(w.puts));
}

if (failures) {
  console.log(`\n${failures} service-worker check(s) failed`);
  process.exit(1);
}
console.log("PASS  service worker: 429 retried once, busy page or cached copy, HTTP cache honoured, no 206 cached");
