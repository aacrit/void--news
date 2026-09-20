"""One row per History event: script, anchor, plot, episode, and what to review.

Regenerates docs/data/history-episodes.csv, which is the source for the shared
episode sheet. Run from the repo root:

    python3 pipeline/history/episode_report.py

Everything here is READ from the repo (the event YAML, the committed script, the
audio manifest, git history), so the report cannot drift from what actually
shipped. The "what to review" column is derived by comparing the commit that
ADDED each script against the commits that added each validator rule, so an
episode written before a rule existed says so rather than looking clean.
"""
import sys, json, glob, os, pathlib, subprocess, csv, io
sys.path.insert(0, 'pipeline')
import yaml
from history.script_format import parse_script, validate_script, estimated_minutes, NARRATOR_WPM, MUSIC_MINUTES
from history.casting import cast

ROOT = pathlib.Path('.')
manifest = json.loads((ROOT/'frontend/public/data/history-audio.json').read_text())['episodes']

# Milestones in this session, oldest first. A script committed BEFORE a
# milestone was written without that rule.
MILESTONES = [
    ("b47a4fa", "per-voice length budget (H-07)"),
    ("ede4cf8", "H-11 paraphrase rule"),
    ("dde3c93", "H-11 secondhand + impersonated voice"),
    ("a96450c", "unnamed-witness disclosure rule"),
    ("82274ca", "institutional-voice convention"),
]
def commit_time(sha):
    try:
        return int(subprocess.run(['git','show','-s','--format=%ct',sha],capture_output=True,text=True).stdout.strip())
    except Exception:
        return 0
MS = [(commit_time(s), label) for s, label in MILESTONES]

def added_time(path):
    out = subprocess.run(['git','log','--diff-filter=A','--format=%ct','--','path'.replace('path',path)],
                         capture_output=True,text=True).stdout.split()
    return int(out[-1]) if out else None

rows = []
for ypath in sorted(glob.glob('data/history/events/*.yaml')):
    slug = os.path.basename(ypath)[:-5]
    ev = yaml.safe_load(pathlib.Path(ypath).read_text())
    c = cast(ev)
    nar = c['narrator']
    wpm = NARRATOR_WPM.get(nar, 145)
    ceiling = int((15.0 - MUSIC_MINUTES) * wpm)
    spath = ROOT/f'data/history/scripts/{slug}.txt'
    ep = manifest.get(slug)

    row = {
        'Event': ev.get('title') or slug,
        'Slug': slug,
        'Era': ev.get('era',''),
        'Region': (ev.get('regions') or [''])[0] if isinstance(ev.get('regions'),list) else '',
        'Severity': ev.get('severity',''),
        'Category': ev.get('category',''),
        'Script': 'written' if spath.exists() else 'NOT WRITTEN',
        'Episode': 'rendered' if ep else ('' if not spath.exists() else 'queued'),
        'Anchor (narrator)': nar,
        'Why this anchor': c.get('why',''),
        'Doc voice M': c.get('document_m',''),
        'Doc voice F': c.get('document_f',''),
        'Anchor wpm': wpm,
        'Word ceiling': ceiling,
    }

    if spath.exists():
        sc = parse_script(spath.read_text(), slug)
        mins, rate, who = estimated_minutes(sc, ev)
        findings = validate_script(sc, ev)
        persp = [s for s in sc.segments if s.kind == 'PERSPECTIVE']
        kinds = [s.kind for s in sc.segments]
        opens = [l.text for s in sc.segments if s.kind=='OPEN' for l in s.lines]
        closes = [l.text for s in sc.segments if s.kind=='CLOSE' for l in s.lines]
        voices = sorted({l.speaker for s in sc.segments for l in s.lines})
        at = added_time(f'data/history/scripts/{slug}.txt')
        missing = [lab for t, lab in MS if at and at < t]
        row.update({
            'Words': sc.words,
            'Est. minutes': round(mins, 2),
            'Gate': 'clean' if not findings else '; '.join(f'{f.level} {f.id}' for f in findings),
            'Perspectives': len(persp),
            'Perspective titles': ' | '.join((s.title or '') for s in persp),
            'Scenes': kinds.count('SCENE'),
            'Rests': kinds.count('REST'),
            'Documents read aloud': kinds.count('DOCUMENT'),
            'Voices in script': '+'.join(voices),
            'Cold open (the misconception it refuses)': ' '.join(opens),
            'Close (last beat)': ' '.join(closes),
            'Written before these rules existed': '; '.join(missing) if missing else 'none (has every current rule)',
        })
    if ep:
        row.update({
            'Rendered minutes': round(ep['durationSeconds']/60, 2),
            'Drift vs estimate (min)': round(ep['durationSeconds']/60 - row.get('Est. minutes', 0), 2) if row.get('Est. minutes') else '',
            'Chapters': len(ep.get('chapters') or []),
            'File MB': round(ep['bytes']/1048576, 1),
            'Listen': f"https://news.voidvision.org/audio/history/{slug}.mp3",
        })
    # One actionable column, most urgent first.
    flags = []
    if ep and ep['durationSeconds']/60 > 15.0:
        flags.append(f"OVER the 15 min format ceiling at {ep['durationSeconds']/60:.2f} (audio gate allows 15.5): re-cut the script or accept")
    if spath.exists():
        if row.get('Gate','clean') != 'clean':
            flags.append(f"gate: {row['Gate']}")
        if 'H-11' in row.get('Written before these rules existed',''):
            flags.append("predates H-11: check any read-aloud quote the record marks attributed, paraphrased, secondhand or written in someone else's voice")
        if 'unnamed-witness' in row.get('Written before these rules existed',''):
            flags.append("predates the unnamed-witness rule: check any quote from a speaker the record does not name says so aloud")
        if 'per-voice' in row.get('Written before these rules existed',''):
            flags.append("predates the per-voice budget: its length was sized against one average rate, not its own anchor")
        if 'institutional' in row.get('Written before these rules existed',''):
            flags.append("predates the institutional-voice convention: a report or agency may be read in the F voice")
    else:
        flags.append("script not written yet")
    row['What to review'] = ' // '.join(flags) if flags else 'nothing outstanding'
    row['Event page'] = f"https://news.voidvision.org/history/{slug}/"
    rows.append(row)

COLS = ['Event','Slug','Script','Episode','What to review','Era','Region','Severity','Category',
        'Anchor (narrator)','Why this anchor','Doc voice M','Doc voice F','Anchor wpm','Word ceiling',
        'Words','Est. minutes','Rendered minutes','Drift vs estimate (min)','Gate',
        'Perspectives','Perspective titles','Scenes','Rests','Documents read aloud','Voices in script',
        'Cold open (the misconception it refuses)','Close (last beat)',
        'Written before these rules existed','Chapters','File MB','Listen','Event page']

buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=COLS, extrasaction='ignore')
w.writeheader()
# written scripts first, then unwritten; rendered before queued
def key(r):
    return (0 if r['Script']=='written' else 1, 0 if r['Episode']=='rendered' else 1, r['Event'])
for r in sorted(rows, key=key):
    w.writerow(r)
pathlib.Path('docs/data/history-episodes.csv').write_text(buf.getvalue())
print('rows', len(rows))
print('written', sum(1 for r in rows if r['Script']=='written'), 'rendered', sum(1 for r in rows if r['Episode']=='rendered'))

# ---------------------------------------------------------------------------
# A second, narrower file for the shared sheet. The full register above is the
# record; this is the view a person actually scans. The two verbose derived
# columns become tokens, because the same three sentences repeated on 39 rows
# were half the file and nobody reads a sentence they have already read 38
# times. The legend for the tokens lives in the Legend tab / the commit message.
RULE_TOKEN = [
    ('per-voice', 'H07-voice'),
    ('H-11 paraphrase', 'H11-para'),
    ('H-11 secondhand', 'H11-2nd'),
    ('unnamed-witness', 'unnamed'),
    ('institutional', 'inst-voice'),
]

def _tokens(missing: str) -> str:
    return ','.join(tok for needle, tok in RULE_TOKEN if needle in missing)

def _action(r: dict) -> str:
    if r['Script'] != 'written':
        return 'write script'
    if r['Episode'] != 'rendered':
        return 'render'
    rendered = r.get('Rendered minutes') or 0
    if rendered and float(rendered) > 15.0:
        return f'OVER 15 min ({rendered})'
    return ''

def _clip(s: str, n: int) -> str:
    s = (s or '').strip()
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '...'

SHEET = ['Event','Script','Episode','Action','Rules it predates','Anchor','Why this anchor',
         'Words','Est min','Rendered min','Drift','Gate','Shape','Voices',
         'Cold open (what it refuses)','Chapters','Listen','Page','Slug']

sbuf = io.StringIO()
sw = csv.DictWriter(sbuf, fieldnames=SHEET, extrasaction='ignore')
sw.writeheader()
for r in sorted(rows, key=key):
    sw.writerow({
        'Event': r['Event'], 'Script': r['Script'], 'Episode': r.get('Episode',''),
        'Action': _action(r),
        'Rules it predates': _tokens(r.get('Written before these rules existed','')),
        'Anchor': r['Anchor (narrator)'], 'Why this anchor': r['Why this anchor'],
        'Words': r.get('Words',''), 'Est min': r.get('Est. minutes',''),
        'Rendered min': r.get('Rendered minutes',''), 'Drift': r.get('Drift vs estimate (min)',''),
        'Gate': r.get('Gate',''),
        'Shape': (f"{r['Scenes']} scenes, {r['Rests']} rests, {r['Documents read aloud']} docs, "
                  f"{r['Perspectives']} accounts") if r['Script'] == 'written' else '',
        'Voices': r.get('Voices in script',''),
        'Cold open (what it refuses)': _clip(r.get('Cold open (the misconception it refuses)',''), 170),
        'Chapters': r.get('Chapters',''), 'Listen': r.get('Listen',''),
        'Page': r['Event page'], 'Slug': r['Slug'],
    })
pathlib.Path('docs/data/history-episodes-sheet.csv').write_text(sbuf.getvalue())
print('sheet bytes', len(sbuf.getvalue()))
