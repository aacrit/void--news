/* ---------------------------------------------------------------------------
   CF Pages Function — /api/ig/webhook

   Receives Instagram Graph API webhooks for comments, mentions, messages
   (DMs), and media events. Verifies the X-Hub-Signature-256 header against
   META_APP_SECRET. Writes to Supabase via the service-role key.

   Routes that hit this function:
     GET  /api/ig/webhook?hub.mode=subscribe&hub.verify_token=...&hub.challenge=...
       → Returns hub.challenge if hub.verify_token matches META_WEBHOOK_VERIFY_TOKEN.
     POST /api/ig/webhook
       → Body is a Meta webhook payload. We verify the signature, dispatch
         per event type into ig_comments / ig_dms / ig_mentions tables.

   Bindings (configured in Cloudflare Pages → Settings → Environment variables):
     META_APP_SECRET            verifies signatures
     META_WEBHOOK_VERIFY_TOKEN  arbitrary string Aacrit picks; given to Meta
                                during webhook subscription setup
     SUPABASE_URL
     SUPABASE_SERVICE_ROLE_KEY
   --------------------------------------------------------------------------- */

interface Env {
  META_APP_SECRET?: string;
  META_WEBHOOK_VERIFY_TOKEN?: string;
  SUPABASE_URL?: string;
  SUPABASE_SERVICE_ROLE_KEY?: string;
}

interface PagesContext<E> {
  request: Request;
  env: E;
}

type PagesHandler<E> = (ctx: PagesContext<E>) => Promise<Response> | Response;

export const onRequestGet: PagesHandler<Env> = async ({ request, env }) => {
  const url = new URL(request.url);
  const mode = url.searchParams.get("hub.mode");
  const token = url.searchParams.get("hub.verify_token");
  const challenge = url.searchParams.get("hub.challenge");
  if (mode === "subscribe" && token && token === env.META_WEBHOOK_VERIFY_TOKEN) {
    return new Response(challenge ?? "", { status: 200 });
  }
  return new Response("forbidden", { status: 403 });
};

export const onRequestPost: PagesHandler<Env> = async ({ request, env }) => {
  const rawBody = await request.text();
  const sigHeader = request.headers.get("x-hub-signature-256") || "";
  const sigOk = await verifySignature(env.META_APP_SECRET ?? "", rawBody, sigHeader);
  if (!sigOk) {
    return new Response("bad signature", { status: 401 });
  }

  let body: unknown;
  try {
    body = JSON.parse(rawBody);
  } catch {
    return new Response("bad json", { status: 400 });
  }

  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) {
    return new Response("supabase not configured", { status: 500 });
  }

  // Meta wraps everything in { entry: [{ changes: [...] }] }. The contents of
  // changes[].field tells us which event type: "comments", "mentions",
  // "messages", etc.
  const entries = (body as { entry?: Array<{ changes?: Array<{ field: string; value: Record<string, unknown> }> }> }).entry ?? [];

  for (const entry of entries) {
    for (const change of entry.changes ?? []) {
      try {
        await dispatch(change.field, change.value, env);
      } catch (e) {
        console.log(`dispatch error (${change.field}):`, e);
      }
    }
  }

  return new Response("ok", { status: 200 });
};

// ---------------------------------------------------------------------------

async function verifySignature(secret: string, body: string, sigHeader: string): Promise<boolean> {
  if (!secret || !sigHeader.startsWith("sha256=")) return false;
  const expected = sigHeader.slice("sha256=".length);

  const enc = new TextEncoder();
  const keyData = enc.encode(secret);
  const bodyData = enc.encode(body);
  const key = await crypto.subtle.importKey("raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sigBytes = new Uint8Array(await crypto.subtle.sign("HMAC", key, bodyData));
  const actual = Array.from(sigBytes).map((b) => b.toString(16).padStart(2, "0")).join("");

  return timingSafeEqual(actual, expected);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function dispatch(field: string, value: Record<string, unknown>, env: Env): Promise<void> {
  switch (field) {
    case "comments":
      await supaInsert("ig_comments", buildComment(value), env);
      break;
    case "mentions":
      await supaInsert("ig_mentions", buildMention(value), env);
      break;
    case "messages":
    case "message_reactions":
      await supaInsert("ig_dms", buildDm(value), env);
      break;
    default:
      // Quiet drop — Meta sends other event types we don't subscribe to.
      break;
  }
}

function buildComment(value: Record<string, unknown>): Record<string, unknown> {
  return {
    ig_comment_id: pickString(value, "id"),
    ig_media_id: pickString((value.media as Record<string, unknown>) ?? {}, "id") || pickString(value, "media_id"),
    parent_id: pickString(value, "parent_id"),
    ig_user_id: pickString((value.from as Record<string, unknown>) ?? {}, "id") || pickString(value, "user_id"),
    ig_username: pickString((value.from as Record<string, unknown>) ?? {}, "username"),
    text: pickString(value, "text"),
    is_reply: Boolean(pickString(value, "parent_id")),
    signature_ok: true,
    raw: value,
  };
}

function buildMention(value: Record<string, unknown>): Record<string, unknown> {
  return {
    ig_media_id: pickString(value, "media_id") || pickString(value, "id"),
    ig_user_id: pickString(value, "user_id"),
    caption: pickString(value, "caption"),
    permalink: pickString(value, "permalink"),
    raw: value,
  };
}

function buildDm(value: Record<string, unknown>): Record<string, unknown> {
  const msg = (value.message as Record<string, unknown>) ?? {};
  return {
    ig_thread_id: pickString(value, "thread_id"),
    ig_message_id: pickString(msg, "mid") || pickString(value, "id"),
    ig_user_id: pickString((value.sender as Record<string, unknown>) ?? {}, "id"),
    ig_username: pickString((value.sender as Record<string, unknown>) ?? {}, "username"),
    text: pickString(msg, "text"),
    inbound: true,
    raw: value,
  };
}

function pickString(obj: Record<string, unknown>, key: string): string {
  const v = obj[key];
  return typeof v === "string" ? v : "";
}

async function supaInsert(table: string, row: Record<string, unknown>, env: Env): Promise<void> {
  const url = `${env.SUPABASE_URL}/rest/v1/${table}`;
  const r = await fetch(url, {
    method: "POST",
    headers: {
      apikey: env.SUPABASE_SERVICE_ROLE_KEY ?? "",
      Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY ?? ""}`,
      "Content-Type": "application/json",
      Prefer: "resolution=ignore-duplicates,return=minimal",
    },
    body: JSON.stringify(row),
  });
  if (!r.ok) {
    const t = await r.text();
    console.log(`supabase insert ${table} failed`, r.status, t);
  }
}
