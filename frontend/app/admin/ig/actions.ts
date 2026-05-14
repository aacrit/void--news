"use server";

import {
  approveIgPost as _approve,
  rejectIgPost as _reject,
  updateIgCaption as _updateCaption,
} from "../../lib/supabase-server";

/* Server Actions called from the admin page. Each verifies basic-auth
   before mutating. The page itself is auth-gated, but actions can be
   invoked independently so we re-check the same envelope. */

import { headers } from "next/headers";

async function _verifyAuth(): Promise<boolean> {
  const expectedUser = process.env.IG_ADMIN_USER;
  const expectedPass = process.env.IG_ADMIN_PASSWORD;
  if (!expectedUser || !expectedPass) return false;
  const h = await headers();
  const auth = h.get("authorization");
  if (!auth?.startsWith("Basic ")) return false;
  let decoded: string;
  try {
    decoded = atob(auth.slice(6));
  } catch {
    return false;
  }
  const [u, p] = decoded.split(":", 2);
  return u === expectedUser && p === expectedPass;
}

export async function approveAction(id: string): Promise<{ ok: boolean; error?: string }> {
  if (!(await _verifyAuth())) return { ok: false, error: "unauthorized" };
  const ok = await _approve(id);
  return { ok, error: ok ? undefined : "update failed" };
}

export async function rejectAction(id: string): Promise<{ ok: boolean; error?: string }> {
  if (!(await _verifyAuth())) return { ok: false, error: "unauthorized" };
  const ok = await _reject(id);
  return { ok, error: ok ? undefined : "update failed" };
}

export async function saveCaptionAction(
  id: string,
  caption: string,
  hashtags: string[],
): Promise<{ ok: boolean; error?: string }> {
  if (!(await _verifyAuth())) return { ok: false, error: "unauthorized" };
  const trimmed = (caption ?? "").trim();
  if (!trimmed) return { ok: false, error: "empty caption" };
  if (/[—–]/.test(trimmed)) return { ok: false, error: "remove em/en dashes before saving" };
  const cleanedTags = hashtags.map((h) => h.replace(/^#/, "").trim()).filter(Boolean);
  if (cleanedTags.length < 6 || cleanedTags.length > 8) {
    return { ok: false, error: "need 6 to 8 hashtags" };
  }
  const ok = await _updateCaption(id, trimmed, cleanedTags);
  return { ok, error: ok ? undefined : "update failed" };
}
