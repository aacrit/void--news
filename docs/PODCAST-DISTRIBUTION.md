# Podcast distribution

Void's audio ships as three podcast feeds, one per show, all static XML on the
Pages CDN next to the MP3s they point at. Nothing is hosted elsewhere; a
podcast app that polls the feed gets the episode straight from
`news.voidvision.org`.

| Show | Feed | Cadence | Written by |
|---|---|---|---|
| Void News: On Air | https://news.voidvision.org/podcast-world.xml | Daily | `pipeline/main.py`, from `daily_briefs` through the SQLite shim, committed by `pipeline.yml` |
| Void News: The Argument | https://news.voidvision.org/podcast-weekly.xml | Sundays | `weekly-digest.yml`, from `frontend/build-data/weekly-issues.json` |
| Void News: History | https://news.voidvision.org/podcast-history.xml | When an episode is rendered | `render-history-audio.yml` (publish job) and again on every daily run, from `frontend/public/data/history-audio.json` plus `data/history/events/<slug>.yaml` |

All three come from `pipeline/briefing/podcast_feed_generator.py`, and all
three are titled `Void News: <programme>`: On Air, The Argument and History
are programmes of Void News, not brands of their own (the weekly channel was
"Void Weekly: The Argument" under an author of "Void News" until 2026-09-21).
`tests/test_podcast_feed.py` holds the committed XML, JPG and SVG to that and
to everything under "What each feed carries"; run it directly, no key, no
database. The weekly and history feeds need no database:

```
python3 pipeline/briefing/podcast_feed_generator.py --history --weekly
```

The daily feed needs `VOID_SQLITE_PATH` and is skipped, with a message, when
it is unset.

The three addresses are advertised in two places: `<link rel="alternate"
type="application/rss+xml">` in the root layout, so a feed reader pointed at
any page finds them, and the `/listen` page, which shows them to people with
a copy button.

## The dead-enclosure defect, fixed 2026-09-20

`podcast-world.xml` listed nine items. `_write_audio_static` in
`audio_producer.py` keeps only the last two dated MP3s under
`frontend/public/audio/world/`, so seven of the nine enclosures returned 404,
and two items shared one enclosure URL because a re-run of the same slot
writes the same filename. Apple rejects a feed with a dead enclosure outright.

The fix is in the generator, not the retention window: the daily and weekly
feeds now list only rows whose MP3 exists in the working tree, and one item
per enclosure URL, newest first. The window itself is unchanged, so the daily
feed carries two or three episodes at a time. Widening it means widening the
audio kept in git; that is a separate decision.

The history feed is different: its MP3s are gitignored and fetched from a
GitHub Release at deploy, so presence in the working tree is not the test.
The manifest `publish_audio.py` writes is, and every entry in it was uploaded
before it was written.

`podcast-us.xml` pointed at the decommissioned Supabase host. The `us`
edition is no longer generated; the feed and its covers are gone from
`frontend/public/`.

## The stale weekly item, fixed 2026-09-21

The served `podcast-weekly.xml` said "Issue #26: Trump Mocks Banned
Reporters" while `/weekly/` said "Vol. I, No. 1: Greenland's Arctic
Calculus". Two defects. The label: the page computes volume and number from
`WEEKLY_LAUNCH_ISSUE` in `frontend/app/weekly/format.ts`; the feed printed
the raw epoch count. `weekly_parse.issue_label` is now the Python twin and
the item title reads `Vol. I, No. 1: <cover headline>: The Argument, <date>`;
the test asserts the two constants agree. The headline: the XML was committed
by hand from a working tree whose archive still carried the earlier cover,
and the next `weekly-digest` run (audio-only dispatch, 2026-09-21 00:39)
checked out a ref whose workflow did not yet carry the "Generate weekly
podcast feed" step, so it refreshed the archive and left the feed alone. The
feed is derived from `build-data/weekly-issues.json` and is never edited;
`tests/test_podcast_feed.py` now fails whenever the committed XML's first
item is not what the committed archive produces, so the two cannot drift
again in silence.

## What each feed carries

- Channel: title, `<link>` to the section page (`/onair/`, `/weekly/`,
  `/history/`), description, RSS `<image>` and `itunes:image` (the same
  file), `itunes:author` and `itunes:owner` "Void News", category,
  `itunes:explicit` false, `itunes:type` episodic, `podcast:locked` no.
- Item: title, description (the shared editorial sanitiser is applied, so no
  em dashes and no significance words, and every description ends a
  sentence: a History subtitle without a full stop is closed before it is
  joined to the summary, and S-03 fails the build otherwise), `<enclosure>`
  with the absolute URL,
  the byte length and `audio/mpeg`, a GUID with `isPermaLink="false"`,
  `pubDate` in RFC 2822, `itunes:duration`, `itunes:episodeType` full, and
  `<podcast:chapters>` pointing at the JSON sidecar next to the MP3.
- GUIDs: the brief's UUID for On Air, the issue's UUID for The Argument,
  `history:<slug>` for History. They never change. Changing a GUID makes every
  app re-download the episode as new.
- Cache-bust queries (`?v=`) are stripped from enclosure URLs. Some apps treat
  a changed query as a new file.

## Artwork

Apple and Spotify want a square JPG or PNG between 1400 and 3000 px, RGB,
under 512 KB. Each show has its own: `frontend/public/podcast-cover-world.jpg`
(On Air), `-weekly.jpg` (The Argument) and `-history.jpg` (History), each
3000x3000, rendered 2026-09-21 from the SVG beside it. Every cover reads
"VOID NEWS", the programme's name and its cadence, in the house faces, and
nothing else: no edition name, no source count, no `--` wordmark. Until that
render all three feeds pointed at one cover, and it was a pre-rebrand raster
reading "void --onair", "WORLD BRIEF", "409 sources".

`_cover_for` in the generator has no fallback. A feed whose JPG is missing
raises, because a feed fronting another show's art is a wrong fact on a
directory page. `tests/test_podcast_feed.py` checks each JPG exists, is
square, sits between 1400 and 3000 px and under 512 KB, and that its SVG
twin's text carries none of the retired strings.

To re-render after editing an SVG (Playwright under `frontend/`, and Playfair
Display, IBM Plex Mono and Barlow Condensed installed as system fonts, or
the wordmark falls back to Georgia):

```
cat > /tmp/covers.json <<'EOF'
[{"svg": "/abs/frontend/public/podcast-cover-world.svg",   "out": "/tmp/world.png",   "width": 3000},
 {"svg": "/abs/frontend/public/podcast-cover-weekly.svg",  "out": "/tmp/weekly.png",  "width": 3000},
 {"svg": "/abs/frontend/public/podcast-cover-history.svg", "out": "/tmp/history.png", "width": 3000}]
EOF
node brand/ci/render_svg.mjs /tmp/covers.json
python3 -c "from PIL import Image; [Image.open(f'/tmp/{e}.png').convert('RGB').save(f'frontend/public/podcast-cover-{e}.jpg', quality=85, optimize=True, progressive=True) for e in ('world','weekly','history')]"
python3 tests/test_podcast_feed.py
```

## Validation, before every submission

1. Run an RSS validator on each feed: https://validator.w3.org/feed/ or
   https://podba.se/validate/ (the second checks the iTunes tags).
2. `curl -I` every enclosure and expect 200 with `content-type: audio/mpeg`
   and a `content-length` equal to the `length` attribute:

   ```
   for u in $(grep -o 'enclosure url="[^"]*"' frontend/public/podcast-history.xml \
              | sed 's/enclosure url="//;s/"$//'); do
     printf '%s ' "$u"; curl -sI "$u" | grep -i '^HTTP/'
   done
   ```

3. `curl -I` each `<podcast:chapters>` URL and each `itunes:image` URL.
4. Artwork: square, 1400 to 3000 px, JPG or PNG, under 512 KB.
5. `itunes:owner` email is `PODCAST_EMAIL` (default `void.news.dev@gmail.com`).
   Apple sends its ownership verification to that address and the show is
   not listed until the mail is answered. The inbox must be monitored.
6. One feed per show. Do not submit one feed twice under two names, and do
   not put two shows in one feed.
7. GUIDs never change once published (see above).
8. `itunes:explicit` is `false` on all three. If a script ever needs to carry
   explicit material, the flag goes on the item, not the channel.
9. Categories: On Air is News / Daily News, The Argument is News / News
   Commentary, History is History. Apple lists a show under its first
   category.
10. No em dashes anywhere in the XML: `grep -c $'\u2014' frontend/public/podcast-*.xml`
    should print 0 for each file (the escape is the dash's code point).

## Submission

### Apple Podcasts Connect

1. Sign in at https://podcastsconnect.apple.com with the Apple ID that owns
   the show (it should be the account behind `PODCAST_EMAIL`).
2. Add a show, choose "Add a show with an RSS feed", paste the feed URL.
3. Apple fetches the feed and reports validation errors on the spot. Fix in
   the generator, regenerate, push, retry. Do not hand-edit the XML in the
   repo; the next pipeline run overwrites it.
4. Answer the verification mail sent to `itunes:owner`.
5. Submit for review. Review takes hours to a few days. Once approved the
   show has an Apple Podcasts URL and an ID; record both in this file.
6. Repeat for each of the three shows. Three feeds, three submissions.

### Spotify for Podcasters

1. Sign in at https://podcasters.spotify.com, "Add your podcast", "I have a
   podcast with an RSS feed".
2. Paste the feed URL. Spotify sends a verification code to `itunes:owner`;
   paste it back.
3. Fill in the category and language (they are read from the feed but can be
   overridden), submit. Spotify usually lists within a day.
4. Repeat per show.

### Everyone else

Pocket Casts, Overcast, Castro and most smaller apps index from the Apple
Podcasts directory, so the Apple listing is what makes the show searchable
in them; nothing to submit. Podcast Index (https://podcastindex.org/add) is
a free, optional addition that some open apps read directly. Amazon Music
and YouTube Music each have their own submission form and can wait.

## What remains manual

- Creating the Apple and Spotify accounts and submitting the three feeds.
- Watching the `PODCAST_EMAIL` inbox for the verification mails.
- Deciding whether the daily audio retention window (two dated files) is the
  back catalogue On Air should offer.
- Recording the Apple and Spotify show URLs in this file once listed.
