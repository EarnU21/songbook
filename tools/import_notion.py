#!/usr/bin/env python3
"""Pull songs out of the public Notion page into songs/<slug>.txt.

    python3 tools/import_notion.py "Evening Rise" "Om Tare"   # just these
    python3 tools/import_notion.py --all                      # every song
    python3 tools/import_notion.py --list                     # titles only

Existing files are left alone unless --force is given, so hand corrections survive a second run.

Notion has a chord line above each lyric line, lined up with spaces in a proportional font. Where the
chords are spaced out, each one is moved into the lyric line as [C] at the word (or syllable) it sits over.
That position is an estimate: read every imported song once. Where the chords are just listed ("Em Bm G A"),
there is nothing to estimate from, so they stay as a row of their own above the words.
"""
import json, re, sys, unicodedata, urllib.request
from pathlib import Path

PAGE = '8fc8b761-febd-4ab6-a904-1c72eaaa3cf7'
API = 'https://nikschreiner.notion.site/api/v3/loadPageChunk'
OUT = Path(__file__).resolve().parent.parent / 'songs'

CHORD = re.compile(r'^\(?[A-Ha-h](?:is|es)?[#b♯♭]?(?:maj|min|dim|aug|sus|add|m|M|\+|°|ø|\d|[#b+-]\d)*(?:/[A-Ha-h](?:is|es)?[#b♯♭]?)?\)?$')
PARTS = re.compile(r'^(\(?)([A-Ha-h])(is|es)?([#b♯♭]?)(.*?)(?:/([A-Ha-h])(is|es)?([#b♯♭]?))?(\)?)$')
FILLER = {'|', '&', '-', '/', '%', '2x', 'x2', '3x', 'x3', '4x', 'x4'}
VOWELS = set('aeiouyäöüáéíóúàèìòùâêîôû')


def fetch():
    blocks, cursor, n = {}, {'stack': []}, 0
    while True:
        body = json.dumps({'pageId': PAGE, 'limit': 100, 'cursor': cursor, 'chunkNumber': n, 'verticalColumns': False}).encode()
        req = urllib.request.Request(API, data=body, headers={'content-type': 'application/json', 'user-agent': 'Mozilla/5.0'})
        j = json.load(urllib.request.urlopen(req, timeout=60))
        for k, b in j['recordMap'].get('block', {}).items():
            v = b.get('value', {})
            blocks[k] = v.get('value', v) if 'id' not in v else v
        cursor, n = j.get('cursor', {}), n + 1
        if not cursor.get('stack'):
            break
    # what sits inside a closed toggle ("Meaning") is not part of the page load: ask for it by id
    for _ in range(3):
        missing = [c for b in blocks.values() if b.get('type') == 'toggle' or b.get('parent_id') in blocks and blocks[b['parent_id']].get('type') == 'toggle'
                   for c in b.get('content', []) if c not in blocks]
        if not missing: break
        for i in range(0, len(missing), 100):
            body = json.dumps({'requests': [{'pointer': {'table': 'block', 'id': x}, 'version': -1} for x in missing[i:i + 100]]}).encode()
            req = urllib.request.Request(API.replace('loadPageChunk', 'syncRecordValuesMain'), data=body, headers={'content-type': 'application/json', 'user-agent': 'Mozilla/5.0'})
            for k, b in json.load(urllib.request.urlopen(req, timeout=60))['recordMap'].get('block', {}).items():
                v = b.get('value', {})
                blocks[k] = v.get('value', v) if 'id' not in v else v
    return blocks


def title_of(b):
    return ''.join(x[0] for x in (b.get('properties') or {}).get('title', []))


def links_of(b):
    return [a[1] for x in (b.get('properties') or {}).get('title', []) if len(x) > 1 for a in x[1] if a[0] == 'a']


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def is_chord_line(line):
    toks = line.split()
    return bool(toks) and any(CHORD.match(t) for t in toks) and all(CHORD.match(t) or t.lower() in FILLER for t in toks)


def norm_chord(t):
    """The page's spellings, made uniform: "a" is A minor, "Cism" is C#m, "B/e" has its bass note capitalised."""
    m = PARTS.match(t)
    if not m: return t
    op, root, ending, acc, tail, bass, bending, bacc, cl = m.groups()
    acc = {'is': '#', 'es': 'b'}.get(ending, acc)
    if root.islower() and not (tail.startswith('m') and not tail.startswith('maj')): tail = 'm' + tail
    out = op + root.upper() + acc + tail
    if bass: out += '/' + bass.upper() + {'is': '#', 'es': 'b'}.get(bending, bacc)
    return out + cl


ONE = r'\(?[A-Ha-h](?:is|es)?[#b♯♭]?(?:maj|min|dim|aug|sus|add|m|M|\+|°|ø|\d)*\)?'
PAIR = re.compile(rf'({ONE})(\s*[|/]\s*)({ONE})(?!\S)')


def pc(chord):
    m = PARTS.match(norm_chord(chord))
    return ('C D EF G A B'.index(m.group(2).upper()) + {'#': 1, '♯': 1, 'b': -1, '♭': -1}.get(m.group(4), 0)) % 12


def pairs_of(line):
    """The chord pairs of a line that is nothing but pairs: "Am | Cm    C | Eb" or "Dm/Em  G/A"."""
    return PAIR.findall(line) if re.fullmatch(rf'\s*(?:{PAIR.pattern}\s*)+', line) else []


def sure(pairs):
    """Two keys for certain, not a bass note: the halves are set apart, or the second half is a whole chord (G/Am)."""
    return any(sep != '/' or re.search(r'[a-z0-9]', norm_chord(y)[1:].lstrip('#b')) for _, sep, y in pairs)


def one_key(line, gap):
    """The page gives some songs in two keys at once (with and without capo, or low and high).
    Keep the first of each pair, in the same columns. A lone G/A stays what it is, G over an A bass,
    unless the rest of the song shows its pairs are two keys that same distance apart."""
    pairs = pairs_of(line)
    if not pairs or not (sure(pairs) or (gap is not None and all((pc(y) - pc(x)) % 12 == gap for x, _, y in pairs))):
        return line, False
    return PAIR.sub(lambda m: m.group(1).ljust(len(m.group())), line), True


def width(s):
    """Rough width of text in Notion's font, in em. Spaces are narrow, which is why counting characters fails."""
    w = 0
    for c in s:
        if c == ' ': w += .28
        elif c in "iljtfrI.,'’:;!|-()": w += .32
        elif c in 'mwMW': w += .85
        elif c.isupper(): w += .68
        else: w += .55
    return w


def syllable_starts(word):
    """Places inside a word where a chord may land: a consonant that opens a new syllable."""
    out = set()
    for i in range(1, len(word) - 1):
        if not (word[i].isalpha() and word[i].lower() not in VOWELS and word[i + 1].lower() in VOWELS): continue
        if not (word[i - 1].isalpha() or word[i - 1] == '-'): continue
        if not any(c in VOWELS for c in word[:i].lower()): continue   # not inside the opening consonants (Ch-rist)
        j = i
        while j > 0 and word[j - 1].isalpha() and word[j - 1].lower() not in VOWELS: j -= 1
        out.add(j if j > 0 and word[j - 1] == '-' else i)   # after a hyphen the syllable starts right there (Wa-chet)
    return sorted(out)


def merge_mono(chords, lyric):
    """The same for a sheet typed in a fixed-width font, where a chord's column is exactly where it lands."""
    lyric = lyric.rstrip()
    spots, tail, last = {}, [], -1
    for m in re.finditer(r'\S+', chords):
        if not CHORD.match(m.group()): continue
        x, ch = m.start(), norm_chord(m.group())
        cands = [(abs(w.start() - x), w.start()) for w in re.finditer(r'\S+', lyric)]
        cands += [(abs(w.start() + i - x) + .9, w.start() + i) for w in re.finditer(r'\S+', lyric) for i in syllable_starts(w.group())]
        if x < len(lyric) and lyric[x] == '_': cands.append((.5, x))   # over a held note (O_____): right where it stands
        cands = [c for c in cands if c[1] > last]
        if x >= len(lyric) or not cands:
            tail.append(ch); continue
        last = min(cands)[1]; spots[last] = ch
    out = ''.join((f'[{spots[i]}]' if i in spots else '') + c for i, c in enumerate(lyric)).strip()
    return out + ''.join(f' [{c}]' for c in tail)


def merge(chords, lyric):
    lyric = lyric.rstrip()
    found = [(width(chords[:m.start()]), norm_chord(m.group())) for m in re.finditer(r'\S+', chords) if CHORD.match(m.group())]
    words = [(m.start(), m.group()) for m in re.finditer(r'\S+', lyric)]
    spots, tail, last = {}, [], -1
    for x, ch in found:
        if not words or x > width(lyric) + .6:
            tail.append(ch); continue
        wi = min(range(len(words)), key=lambda i: abs(width(lyric[:words[i][0]]) - x))
        pos = words[wi][0]
        if pos <= last:   # that word already has a chord: look inside it, then at the next word
            inner = [words[wi][0] + i for i in syllable_starts(words[wi][1]) if words[wi][0] + i > last]
            inner = [p for p in inner if abs(width(lyric[:p]) - x) < 1.2]
            later = [p for p, _ in words if p > last]
            pos = min(inner, key=lambda p: abs(width(lyric[:p]) - x)) if inner else (later[0] if later else None)
        if pos is None:
            tail.append(ch); continue
        spots[pos] = ch; last = pos
    out = ''.join((f'[{spots[i]}]' if i in spots else '') + c for i, c in enumerate(lyric))
    return out + ''.join(f' [{c}]' for c in tail)


def chord_row(line):
    return ' '.join(f'[{norm_chord(t)}]' if CHORD.match(t) else t for t in line.split())


def convert(title, body, blocks):
    head, lines, texts, todo = {'title': title.strip()}, [], [], []

    def walk(b):
        t, s = b.get('type'), title_of(b).replace(' ', ' ')
        if t == 'toggle':
            inner = [title_of(blocks[c]) for c in b.get('content', []) if c in blocks]
            texts.append((s.strip() or 'Meaning', '\n'.join(inner).strip()))
        elif t in ('audio', 'video', 'file', 'image'):
            todo.append(f'% {t} still in Notion: {s.strip()}')
        elif t in ('text', 'bulleted_list', 'sub_header'):
            for url in links_of(b):
                label = s.strip() if s.strip() and not s.strip().startswith('http') and len(s) < 60 else re.sub(r'^https?://(www\.)?([^/]+).*$', r'\2', url)
                head.setdefault('link', []).append(f'{label} | {url}')
            if links_of(b) and len(s) < 60:
                return   # the line was the link's label
            segs = [x for x in (b.get('properties') or {}).get('title', []) if x[0].strip()]
            if segs and all(len(x) > 1 and any(a[0] == 'a' for a in x[1]) for x in segs):
                return   # the whole line is a link: it lives in the header now
            lines.extend(('# ' + x if t == 'sub_header' else x) for x in s.split('\n'))
        for c in (b.get('content') or []) if t not in ('toggle',) else []:
            if c in blocks: walk(blocks[c])

    for b in body:
        walk(b)
    return sheet(head, lines, texts, todo)


def sheet(head, lines, texts=(), todo=None, mono=False):
    """Chord lines over lyric lines, turned into a song file. mono: the sheet is lined up in a fixed-width font."""
    todo = todo or []
    out, i, first = [], 0, None
    lead = next((ps[0] for ps in map(pairs_of, lines) if ps and sure(ps)), None)   # the song's first sure pair, if it has two keys
    gap = (pc(lead[2]) - pc(lead[0])) % 12 if lead else None
    while i < len(lines):
        line = lines[i].replace('\t', '    ').rstrip(); i += 1
        if re.fullmatch(r'\s*[A-G]{2,4}(\s+[A-G]{2,4})*', line):   # "GDA": chords written without spaces
            line = ' '.join(line.replace(' ', ''))
        cap = re.match(r'^\s*cap(?:o)?\.?\s*([IVX]+|\d+)\s*$', line, re.I)
        if cap:
            v = cap.group(1).upper()
            head['capo'] = v if v.isdigit() else str({'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}.get(v, 0))
            continue
        sec = re.match(r'^\s*(?:(\d+)\s*x\s*)?\[([^\]]+)\]\s*$', line)
        if sec and not CHORD.match(sec.group(2)):
            out.append('# ' + sec.group(2) + (f' ({sec.group(1)}x)' if sec.group(1) else '')); continue
        aside = re.search(r'\(([^)]*[ :][^)]*)\)\s*$', line)
        probe, two = one_key(line[:aside.start()] if aside else line, gap)
        if two and '% check: two keys in the source (like Dm/Em); the first one was kept' not in todo:
            todo.append('% check: two keys in the source (like Dm/Em); the first one was kept')
        if is_chord_line(probe):
            first = first or next(norm_chord(t) for t in probe.split() if CHORD.match(t))
            nxt = lines[i].rstrip() if i < len(lines) else ''
            spaced = mono or len(probe.split()) == 1 or re.search(r'\S\s{2,}\S', probe) or probe.startswith(' ')
            plain = all(CHORD.match(t) for t in probe.split())
            if nxt.strip() and not is_chord_line(nxt) and spaced and plain:
                out.append((merge_mono if mono else merge)(probe, nxt)); i += 1
            else:
                out.append(chord_row(probe))
                if not plain: out.append('% check: this chord row was not a plain list of chords')
            if aside: out.append('> ' + aside.group(1).strip())
        else:
            out.append(line.strip())

    while out and not out[0]: out.pop(0)
    while out and not out[-1]: out.pop()
    if lead and 'capo' in head and (pc(lead[2]) + int(head['capo'])) % 12 == pc(lead[0]):
        del head['capo']   # the first of each pair was the sounding key, the second the capo shapes
    if first:
        head['key'] = re.match(r'\(?([A-H][#b♯♭]?m?(?!aj))', first).group(1)
        todo.insert(0, '% key guessed from the first chord')
    hdr = [f'{k}: {head[k]}' for k in ('title', 'key', 'capo', 'note') if k in head]
    hdr += [f'link: {l}' for l in head.get('link', [])]
    txt = '\n'.join(hdr + todo) + '\n\n' + re.sub(r'\n{3,}', '\n\n', '\n'.join(out)) + '\n'
    for t, body_text in texts:
        if body_text: txt += f'\n=== {t}\n{body_text}\n'
    return txt


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    blocks = fetch()
    songs, cur = [], None
    for bid in blocks[PAGE]['content']:
        b = blocks.get(bid)
        if not b: continue
        if b.get('type') == 'header':
            cur = (title_of(b), []); songs.append(cur)
        elif cur:
            cur[1].append(b)
    if '--list' in flags:
        print('\n'.join(t for t, _ in songs)); return
    want = {a.lower() for a in args}
    OUT.mkdir(exist_ok=True)
    for title, body in songs:
        if '--all' not in flags and title.strip().lower() not in want: continue
        path = OUT / (slug(title) + '.txt')
        if path.exists() and '--force' not in flags:
            print('kept    ', path.name); continue
        path.write_text(convert(title, body, blocks), encoding='utf-8')
        print('imported', path.name)


if __name__ == '__main__':
    main()
