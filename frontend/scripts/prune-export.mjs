#!/usr/bin/env node
/*
 * Post-build: keep the static export inside Cloudflare Pages' file ceiling.
 *
 * Pages refuses a deployment of more than 20,000 files. On 2026-11-18 the
 * export reached 20,086 files, plus the 74 History MP3s the deploy pulls in
 * after the build, and the day's edition never went live. 17,700 of those
 * files were the story archive: Next writes six files per prerendered page
 * (index.html, index.txt and four __next.*.txt segment payloads), and the
 * archive grows by about 25 stories a day.
 *
 * The five .txt files are React Server Component payloads that Next's client
 * router fetches when it navigates to a page WITHOUT a full load. Nothing
 * navigates to /story/ that way: every entry (StoryCard, LeadStory,
 * MobileStoryCard, MoreStories, shared links) is a plain <a href>, so the
 * browser loads index.html, whose payload is inlined. The .txt files under
 * /story/ are never requested, and they go.
 *
 * Then the gate: the export plus the History audio the deploy adds must stay
 * under the ceiling with room to spare. It fails the build here, where it is
 * visible on the branch, instead of at Cloudflare after the data commit.
 */
import { readdirSync, statSync, unlinkSync, existsSync } from "node:fs";
import { join } from "node:path";

const OUT = join(process.cwd(), "out");
const STORY = join(OUT, "story");
const PAGES_FILE_LIMIT = 20_000;
// History episodes are pulled into out/audio/history by the deploy, after
// this script runs. 78 events today; leave room for the catalogue to grow.
const DEPLOY_ADDS = 150;
const FAIL_AT = PAGES_FILE_LIMIT - DEPLOY_ADDS - 1_000;
const WARN_AT = Math.floor(PAGES_FILE_LIMIT * 0.75);

function countFiles(dir) {
  let n = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    n += entry.isDirectory() ? countFiles(p) : 1;
  }
  return n;
}

if (!existsSync(OUT)) {
  console.error("prune-export: no out/ directory; the build did not export.");
  process.exit(1);
}

const before = countFiles(OUT);
let removed = 0;
if (existsSync(STORY)) {
  for (const id of readdirSync(STORY)) {
    const dir = join(STORY, id);
    if (!statSync(dir).isDirectory()) continue;
    for (const f of readdirSync(dir)) {
      if (f.endsWith(".txt") && statSync(join(dir, f)).isFile()) {
        unlinkSync(join(dir, f));
        removed += 1;
      }
    }
  }
}
const after = countFiles(OUT);
const projected = after + DEPLOY_ADDS;

console.log(
  `prune-export: ${before} files, removed ${removed} story RSC payloads, ` +
    `${after} remain (${projected} with History audio; Pages limit ${PAGES_FILE_LIMIT}).`,
);

if (after > FAIL_AT) {
  console.error(
    `prune-export: FAIL. ${after} files exceeds the build budget of ${FAIL_AT}. ` +
      `Cloudflare Pages will refuse this deploy. Reduce what the export writes ` +
      `(the story archive is the largest directory) before merging.`,
  );
  process.exit(1);
}
if (after > WARN_AT) {
  console.warn(
    `prune-export: WARNING. ${after} files is over 75% of the Pages limit.`,
  );
}
