// IG admin actions — converted from "use server" to client-callable
// stubs because the production CF Pages build requires `output: "export"`,
// which forbids server actions entirely. This file used to call the
// service-role Supabase client server-side; that path now lives only in
// `npm run dev` mode and the stubs below short-circuit production builds.
//
// To restore real mutations: re-add "use server" + the original imports +
// move the `/admin/ig` route off the static-export build (separate
// dev-only Next.js config, or pages-router shim, or a Worker function).
//
// Tracked under the holistic-redesign-2026-05-15 work — IG team should
// fold a proper fix into the IG-automation-stack branch.

const _stub = (label: string) => ({
  ok: false,
  error: `${label} disabled in static build (admin requires npm run dev)`,
});

export async function approveAction(_id: string): Promise<{ ok: boolean; error?: string }> {
  return _stub("approveAction");
}

export async function rejectAction(_id: string): Promise<{ ok: boolean; error?: string }> {
  return _stub("rejectAction");
}

export async function saveCaptionAction(
  _id: string,
  _caption: string,
  _hashtags: string[],
): Promise<{ ok: boolean; error?: string }> {
  return _stub("saveCaptionAction");
}
