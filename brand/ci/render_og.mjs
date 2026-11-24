/* ---------------------------------------------------------------------------
   Renders the site-wide share card to frontend/public/og-image.png.

       node brand/ci/render_og.mjs

   WHY A SCRIPT. og-image.png used to be drawn by brand/og_render.py: Pillow,
   Windows font paths, and a card whose layout existed nowhere else. It said
   "AN EXPERIMENTAL NEWSROOM" over a dark ground while every section card was
   paper, and it carried "1,016 SOURCES", a number that goes stale the day a
   source is added. The file is now rendered from the SAME composer every other
   card uses (frontend/app/lib/ogCard.tsx), so the brand cannot drift between
   the site card and a section card, and it is never hand-edited again.

   The composer is TSX inside the Next app, so this transpiles it with the
   TypeScript compiler (already a dependency) into a temp ESM module beside
   frontend/node_modules, imports it, and writes the PNG. Nothing is cached:
   re-run it after any change to the composer and commit the result.
   --------------------------------------------------------------------------- */

import { mkdirSync, readFileSync, rmSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { createRequire } from "module";

const HERE = dirname(fileURLToPath(import.meta.url));
const FRONTEND = join(HERE, "..", "..", "frontend");
const SRC = join(FRONTEND, "app", "lib", "ogCard.tsx");
const OUT = join(FRONTEND, "public", "og-image.png");
const TMP = join(FRONTEND, ".og-render");

const require = createRequire(join(FRONTEND, "package.json"));
const ts = require("typescript");

const js = ts.transpileModule(readFileSync(SRC, "utf8"), {
  compilerOptions: {
    jsx: ts.JsxEmit.ReactJSX,
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ESNext,
  },
}).outputText
  // Node resolves the app's bare "next/og" only through the bundler; the
  // package ships the same module at next/og.js.
  .replace(/from "next\/og"/g, 'from "next/og.js"');

mkdirSync(TMP, { recursive: true });
const mod = join(TMP, "ogCard.mjs");
writeFileSync(mod, js);

try {
  const { voidCard, SITE_TITLE, SITE_TAGLINE } = await import(pathToFileURL(mod).href);
  const res = await voidCard({ title: SITE_TITLE, tagline: SITE_TAGLINE });
  const png = Buffer.from(await res.arrayBuffer());
  writeFileSync(OUT, png);
  console.log(`og-image.png  ${png.length} bytes  "${SITE_TITLE}" / "${SITE_TAGLINE}"`);
} finally {
  rmSync(TMP, { recursive: true, force: true });
}
