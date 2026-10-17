/* commonsSrcSet: a phone gets a Commons thumbnail, never the whole original,
   and never a thumbnail wider than the file.

   On 2026-10-02 the /history landing loaded 3,997 KB of images at 375px
   against a 2,500 KB budget: 70 of 170 History images were stored as the
   unscaled original (Commons resolves a narrower file to itself), so they got
   no srcset and a 319px card downloaded a 3461px photograph. Commons serves no
   thumbnail at or above a file's own width, so the width must come from data
   (`hero_image_width`, from the Commons API) and every offered step must sit
   below it.

   Run: node test/commons-image.test.mjs */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-commons-"));
let failures = 0;
function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", "app/lib/commonsImage.ts",
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"],
  { cwd: ROOT, stdio: "pipe" });
const { commonsSrcSet } = await import(pathToFileURL(join(out, "commonsImage.js")).href);

const widthsOf = (s) => (s || "").split(", ").map((c) => Number(c.split(" ").pop().slice(0, -1)));

/* An unscaled original with its width: thumbnails below it, the file at its own width. */
const cyrus = "https://upload.wikimedia.org/wikipedia/commons/3/35/Cyrus_Cylinder.jpg?utm_source=commons";
const s1 = commonsSrcSet(cyrus, 3461);
check("original gets thumbnails", !!s1 && s1.includes("/wikipedia/commons/thumb/3/35/Cyrus_Cylinder.jpg/330px-Cyrus_Cylinder.jpg 330w"), s1);
check("original offered at its own width", !!s1 && s1.endsWith(`${cyrus} 3461w`), s1);

/* A 700px file: no 960 or 1280 thumbnail, which Commons would refuse. */
const mongol = "https://upload.wikimedia.org/wikipedia/commons/f/f4/MongolEmpire.jpg";
const s2 = commonsSrcSet(mongol, 700);
check("no step at or above the file's width", JSON.stringify(widthsOf(s2)) === "[330,500,700]", s2);

/* No width: nothing can be offered safely, so nothing is. */
check("original without a width gets no srcset", commonsSrcSet(mongol) === undefined);
/* Narrower than the smallest step: nothing to offer. */
check("original under 330px gets no srcset", commonsSrcSet(mongol, 300) === undefined);
/* A format whose thumbnail Commons renames is left alone. */
check("tiff original left alone",
  commonsSrcSet("https://upload.wikimedia.org/wikipedia/commons/a/ab/Map.tif", 4000) === undefined);

/* A stored thumbnail keeps working, and respects a known width. */
const thumb = "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/35/Cyrus_Cylinder.jpg/1280px-Cyrus_Cylinder.jpg?utm_source=commons";
check("thumbnail steps unchanged", JSON.stringify(widthsOf(commonsSrcSet(thumb))) === "[330,500,960,1280]");
check("thumbnail steps bounded by a known width", JSON.stringify(widthsOf(commonsSrcSet(thumb, 900))) === "[330,500,1280]");
check("another host gets no srcset", commonsSrcSet("https://example.org/a.jpg", 2000) === undefined);

/* The served data: every raster Commons original hero carries its width, so it can shrink. */
const events = JSON.parse(readFileSync(join(ROOT, "public/data/history.json"), "utf8"));
const ORIGINAL = /^https:\/\/upload\.wikimedia\.org\/wikipedia\/[^/]+\/[0-9a-f]\/[0-9a-f]{2}\/[^/?#]+\.(jpe?g|png|gif|webp)(\?|$)/i;
/* Named, not counted: this hero's file is not in data/history/commons_media.json
   (it reaches the row by another route), so no width is known for it. Any
   other bare original fails. */
const KNOWN_BARE = new Set(["armenian-genocide"]);
const bare = events.filter((e) => ORIGINAL.test(e.hero_image_url || "") && !e.hero_image_width
  && !KNOWN_BARE.has(e.slug));
check("served originals carry their width", bare.length === 0, bare.map((e) => e.slug).join(", "));

if (failures) {
  console.log(`\n${failures} commons-image check(s) failed`);
  process.exit(1);
}
console.log("PASS  Commons images: thumbnails below the file's width, originals shrink, served heroes carry widths");
