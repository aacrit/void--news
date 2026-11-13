/**
 * The press rule, and what an episode is.
 *
 * app/lib/episode.ts is the pure core the whole On Air system rests on. It was
 * written on 2026-09-21 to end a class of defect rather than one instance of
 * it: the provider had a single `brief` slot that all three programmes wrote
 * into, and every surface read it as if it were always the daily edition. Six
 * reader-visible consequences were measured in a browser before the change:
 *
 *   - /onair announced a History documentary as "World Edition, ON AIR, 23 min"
 *   - opening /weekly paused a playing brief mid-sentence and swapped the source
 *   - returning home detached a playing documentary
 *   - Play on a History episode on /audio loaded it and played nothing
 *   - an OS pause left the pill, the tab bar and the wordmark claiming to play
 *   - a tab resume on /weekly swapped in the daily MP3 under Weekly labels
 *
 * Everything here is one of those, reduced to the decision that caused it.
 * There is no browser and no React: that is the point of the module, and the
 * reason these can be asserted at all.
 *
 * Run: node test/episode.test.mjs   (compiles the TS it needs first)
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-episode-"));
let failures = 0;

function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", "app/lib/episode.ts",
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"],
  { cwd: ROOT, stdio: "pipe" });

/* tsc anchors its output at the common root of every file it pulled in, which
   the weekly type re-export moves up to app/. Find the file rather than
   guessing its depth (the same reason chapters.test.mjs does). */
function findEmitted(dir, name) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      const hit = findEmitted(path, name);
      if (hit) return hit;
    } else if (entry.name === name) {
      return path;
    }
  }
  return null;
}

function collect(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name);
    return e.isDirectory() ? collect(path) : path.endsWith(".js") ? [path] : [];
  });
}

const emitted = findEmitted(out, "episode.js");
if (!emitted) {
  console.log("FAIL  tsc emitted no episode.js");
  process.exit(1);
}

/* episode.ts imports ./chapters for the one coercion point, and tsc emits that
   specifier verbatim: extensionless, which Node's ESM resolver will not
   resolve. Add the extension in the emitted output rather than reaching for a
   bundler, so this test keeps depending on nothing but tsc and node. */
for (const file of collect(out)) {
  const before = readFileSync(file, "utf8");
  const after = before.replace(
    /(\bfrom\s+["'])(\.[^"']*?)(["'])/g,
    (m, a, spec, z) => (/\.[cm]?js$/.test(spec) ? m : `${a}${spec}.js${z}`)
  );
  if (after !== before) writeFileSync(file, after);
}

const ep = await import(pathToFileURL(emitted).href);

/* ---- fixtures: one row per programme, shaped like the real exports ----- */

const BRIEF = {
  id: "brief-2026-09-21",
  edition: "world",
  tldr_headline: "Two capitals recall their ambassadors",
  tldr_text: "One paragraph per story.",
  opinion_text: "An op-ed.",
  opinion_lean: "center",
  opinion_start_seconds: 540,
  audio_url: "/audio/world/brief-2026-09-21.mp3?v=42d5b960",
  audio_duration_seconds: 782,
  audio_voice_label: "Two voices",
  audio_chapters: [
    { startTime: 18, title: "Headlines", kind: "headlines" },
    { startTime: 540, title: "Opinion", kind: "opinion" },
  ],
  created_at: "2026-09-21T11:00:00Z",
};

const DIGEST = {
  id: "weekly-2026-09-14",
  week_start: "2026-09-14",
  cover_headline: "The week the ceasefire held",
  cover_text: [{ text: "Eleven days, three capitals." }],
  audio_url: "/audio/weekly/argument-2026-09-14.mp3",
  audio_duration_seconds: 1_402,
  audio_voice_label: "Three anchors",
  audio_chapters: null,
  created_at: "2026-09-14T18:00:00Z",
  /* The weekly row carries this field too. It must never print an edition. */
  edition: "world",
};

const HISTORY = {
  id: "fall-of-constantinople",
  title: "The Fall of Constantinople",
  subtitle: null,
  audioUrl: "/audio/history/fall-of-constantinople.mp3",
  durationSeconds: 903,
  chapters: null,
  publishedAt: "2026-09-12T00:00:00Z",
};

const daily = ep.episodeFromBrief(BRIEF);
const weekly = ep.episodeFromWeekly(DIGEST);
const history = ep.episodeFromHistory(HISTORY);

/* ---- 1. each programme is itself ------------------------------------- */

check("the daily brief is the daily programme", daily.kind === "daily");
check("the daily brief carries its edition", daily.editionLabel === "World");
check("the daily brief keeps its opinion firewall", daily.opinionStartSeconds === 540);
check("the daily brief coerces its chapters once", daily.chapters.length === 2);

check("the weekly digest is the weekly programme", weekly.kind === "weekly");
check("the weekly programme is called The Argument", weekly.programmeLabel === "The Argument");
/* The measured defect: the Argument was datelined "World Edition" because it
   was written into the daily slot. A weekly row that carries an `edition`
   field must still print none. */
check("the weekly issue prints NO edition", weekly.editionLabel === null,
  String(weekly.editionLabel));
check("the weekly issue leads with its cover line", weekly.subtitle === "Eleven days, three capitals.");
check("a legacy weekly row degrades to no chapters", weekly.chapters.length === 0);

check("a history event is the history programme", history.kind === "history");
check("a history event prints NO edition", history.editionLabel === null);
/* The lock screen used to date a 1453 documentary today, because the metadata
   was built from Date.now() rather than from the episode. */
check("a history event keeps its own published date",
  history.publishedAt === "2026-09-12T00:00:00Z");
check("a history event has no opinion firewall", history.opinionStartSeconds === null);

/* ---- 2. nothing without audio is an episode -------------------------- */

check("a brief with no audio is not an episode", ep.episodeFromBrief({ ...BRIEF, audio_url: null }) === null);
check("a null brief is not an episode", ep.episodeFromBrief(null) === null);
check("a digest with no audio is not an episode", ep.episodeFromWeekly({ ...DIGEST, audio_url: null }) === null);
check("a history payload with no audio is not an episode", ep.episodeFromHistory({ ...HISTORY, audioUrl: "" }) === null);

/* ---- 3. identity: the same audio, however it is referenced ----------- */

check("an episode is itself", ep.sameEpisode(daily, daily));
check("two programmes are never the same episode", !ep.sameEpisode(daily, weekly));
check("nothing is the same as nothing", !ep.sameEpisode(null, null));
check("an episode is not the same as nothing", !ep.sameEpisode(daily, null));

/* The pipeline appends a content hash on every run, and the archive rows carry
   a brief id a later refetch can reissue. Both forms are one episode, which is
   why a play button could lose track of the audio it had just started. */
const rehashed = ep.episodeFromBrief({
  ...BRIEF,
  id: "reissued-id",
  audio_url: "/audio/world/brief-2026-09-21.mp3?v=ffffffff",
});
check("the same file with a new cache-bust is the same episode",
  ep.sameEpisode(daily, rehashed));
check("the same id with a different file is still the same episode",
  ep.sameEpisode(daily, ep.episodeFromBrief({ ...BRIEF, audio_url: "/audio/world/other.mp3" })));
check("stripCacheBust leaves a plain url alone",
  ep.stripCacheBust("/audio/a.mp3") === "/audio/a.mp3");
check("stripCacheBust drops the query",
  ep.stripCacheBust("/audio/a.mp3?v=1&x=2") === "/audio/a.mp3");

/* ---- 4. one press rule ----------------------------------------------- */

/* The measured defect: Play on a History episode LOADED it and played
   nothing, while the same button on an already-loaded issue toggled. One
   rule, so the hub, the pill, the page, the panel and the History hero all
   behave the same. */
check("pressing the loaded episode toggles it",
  ep.decidePress(daily, daily) === "toggle");
check("pressing another programme loads and plays it",
  ep.decidePress(daily, history) === "load-and-play");
check("pressing anything on an empty player loads and plays it",
  ep.decidePress(null, history) === "load-and-play");
check("a reissued id still toggles rather than restarting",
  ep.decidePress(daily, rehashed) === "toggle");

/* ---- 5. a render may offer; it may never seize ----------------------- */

/* The measured defect: opening /weekly paused a playing brief mid-sentence
   and swapped the element's source, with no gesture from the reader. */
check("an idle player may be offered a programme",
  ep.mayTakeOver(null, false, weekly));
check("a PAUSED programme may be replaced by a page that renders",
  ep.mayTakeOver(daily, false, weekly));
check("a PLAYING programme may never be replaced without a press",
  !ep.mayTakeOver(daily, true, weekly));
check("a page never re-offers the episode already loaded",
  !ep.mayTakeOver(weekly, false, weekly));
check("not even a playing episode re-offers itself",
  !ep.mayTakeOver(weekly, true, weekly));

/* ---- 6. the labels the chrome prints -------------------------------- */

check("the three programme labels are the three names",
  ep.PROGRAMME_LABEL.daily === "On Air"
  && ep.PROGRAMME_LABEL.weekly === "The Argument"
  && ep.PROGRAMME_LABEL.history === "History");
check("an unknown edition falls back to World",
  ep.editionLabelFor("atlantis") === "World");
check("a missing edition falls back to World",
  ep.editionLabelFor(null) === "World" && ep.editionLabelFor(undefined) === "World");
check("south-asia is spelled out", ep.editionLabelFor("south-asia") === "South Asia");

/* No programme label may carry a banned dash: these strings are printed in the
   masthead, the pill and the panel. */
for (const [kind, label] of Object.entries(ep.PROGRAMME_LABEL)) {
  check(`${kind}'s label carries no dash`, !/[–—]/.test(label), label);
}

rmSync(out, { recursive: true, force: true });

if (failures) {
  console.log(`\n${failures} episode failure(s)`);
  process.exit(1);
}
console.log("PASS  episode identity, the press rule, and what may seize the player");
