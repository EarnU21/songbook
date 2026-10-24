#!/usr/bin/env python3
"""Turn songs/*.txt into songs.js, and write sw.js so the whole book works offline.

    python3 tools/build.py

Run it after adding or changing a song. A song file looks like this:

    title: Evening Rise
    key: Am                  the key the chords are written in
    capo: 3                  optional: the chords are shapes, played with a capo on this fret
    note: version by ...     optional, shown under the title
    link: Spotify | https://...
    audio: audio/evening-rise.mp3 | live in the circle     a recording; the label is optional, and there may be several

    # Verse                  optional heading; a blank line starts a new block
    [Am]Evening [E]rise, [G]spirit [A]come
    > a remark for the players
    % a comment, not shown

    === Meaning              free text from here on, shown folded up
    ...

Chords go in square brackets right before the syllable they land on (Nathan Vanderpool's format).
The offline worker is his too: tools/build_offline.py in his Secret Songbook did this job.
"""
import hashlib, json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHELL = ['index.html', 'app.js', 'songs.js', 'manifest.webmanifest', 'assets/fonts.css']


def fold(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()


def parse(path):
    song = {'slug': path.stem, 'title': path.stem, 'key': '', 'capo': 0, 'links': [], 'audio': [], 'sections': [], 'texts': []}
    lines = path.read_text(encoding='utf-8').splitlines()
    i = 0
    while i < len(lines) and lines[i].strip():   # the header, up to the first blank line
        m = re.match(r'^(\w+):\s*(.*)$', lines[i])
        if m:
            k, v = m.group(1).lower(), m.group(2).strip()
            if k == 'link':
                label, _, url = v.rpartition('|')
                song['links'].append({'label': label.strip() or 'Link', 'url': url.strip()})
            elif k == 'audio':
                src, _, label = v.partition('|')
                song['audio'].append({'src': src.strip(), 'label': label.strip()})
            elif k == 'capo':
                song['capo'] = int(v or 0)
            else:
                song[k] = v
        i += 1
    sec, text = None, None
    for line in lines[i:]:
        if line.startswith('==='):
            title = line.strip('= ').strip()
            text = {'title': title, 'body': []} if title else None
            if text: song['texts'].append(text)
            sec = None
        elif text is not None:
            text['body'].append(line)
        elif line.startswith('%'):
            continue
        elif not line.strip():
            sec = None
        else:
            if line.startswith('#') or sec is None:
                sec = {'caption': line.lstrip('# ').strip() if line.startswith('#') else '', 'lines': []}
                song['sections'].append(sec)
                if line.startswith('#'): continue
            sec['lines'].append({'note': line[1:].strip()} if line.startswith('>') else line.rstrip())
    for t in song['texts']:
        t['body'] = '\n'.join(t['body']).strip()
    words = ' '.join(re.sub(r'\[[^\]]*\]', '', l) for s in song['sections'] for l in s['lines'] if isinstance(l, str))
    song['find'] = fold(' '.join([song['title'], song.get('note', ''), words]))   # the note too: a search for "taize" finds the Taizé chants
    return song


SW = r'''/* Mantra Collection offline worker, made by tools/build.py: don't edit by hand.
   From Nathan Vanderpool's Secret Songbook. Saves every file below on the first visit and answers from that
   copy when there's no signal. The page and the songs ask the network first, so an update shows as soon as
   someone is online. Recordings are saved the first time they are played. */
const FILES = __FILES__;
const CACHE = 'mantra-collection', AUDIO = 'mantra-collection-audio';
const scopeURL = new URL('./', self.location).href;
const keyFor = (path, rev) => scopeURL + path + '?rev=' + rev;
const REV = Object.fromEntries(FILES);
const FRESH = /\.html$|^songs\.js$|^app\.js$/;

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    for (const [path, rev] of FILES) {   // one at a time: gentle on a phone connection, and only what's new
      const key = keyFor(path, rev);
      if (await cache.match(key)) continue;
      try { const r = await fetch(scopeURL + path, { cache: 'reload' }); if (r.ok) await cache.put(key, r); } catch (err) {}
    }
    self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const cache = await caches.open(CACHE), keep = new Set(FILES.map(([p, r]) => keyFor(p, r)));
    for (const req of await cache.keys()) if (!keep.has(req.url)) await cache.delete(req);   // older versions
    await self.clients.claim();
  })());
});

/* the audio player asks for byte ranges; answer those from the saved copy too */
async function ranged(req, res) {
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.get('range') || '');
  if (!m) return res;
  const buf = await res.arrayBuffer(), size = buf.byteLength;
  const start = m[1] ? +m[1] : Math.max(0, size - +m[2]), end = m[1] && m[2] ? Math.min(+m[2], size - 1) : size - 1;
  return new Response(buf.slice(start, end + 1), { status: 206, headers: {
    'Content-Type': res.headers.get('Content-Type') || 'audio/mpeg', 'Content-Range': `bytes ${start}-${end}/${size}`,
    'Content-Length': String(end - start + 1), 'Accept-Ranges': 'bytes' } });
}

/* a recording: the saved copy if there is one; otherwise fetch the whole file once, keep it, and answer from it */
async function recording(req) {
  const cache = await caches.open(AUDIO), url = req.url;
  let hit = await cache.match(url);
  if (!hit) {
    const full = await fetch(url);
    if (!full.ok || full.status === 206) return full;
    await cache.put(url, full.clone());
    hit = full;
  }
  return req.headers.has('range') ? ranged(req, hit) : hit;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || !req.url.startsWith(scopeURL)) return;
  const path = new URL(req.url).pathname.slice(new URL(scopeURL).pathname.length) || 'index.html';
  if (path.startsWith('audio/')) { e.respondWith(recording(req).catch(() => fetch(req))); return; }
  const rev = REV[path]; if (!rev) return;
  const key = keyFor(path, rev);
  if (FRESH.test(path)) {   // the network first (so updates show), the saved copy without signal
    e.respondWith(fetch(req.url, { cache: 'no-cache' }).catch(async () => (await caches.match(key)) || Response.error()));
    return;
  }
  e.respondWith((async () => (await caches.match(key)) || fetch(req))());
});
'''


def single_file(songs):
    """dist/mantra-collection.html: the whole book in one file, to pass on or keep on a device.
    Words, chords, transposing and search; no recordings, no fonts, no offline worker."""
    html = (ROOT / 'index.html').read_text(encoding='utf-8')
    html = re.sub(r'<link rel="(stylesheet|manifest|icon|apple-touch-icon)"[^>]*>\n', '', html)
    html = re.sub(r'<script>\n/\* Offline:.*?</script>\n', '', html, flags=re.S)
    lean = [{**s, 'audio': []} for s in songs]
    inline = lambda code: '<script>\n' + code.replace('</', '<\\/') + '\n</script>'
    data = 'window.SINGLE_FILE = true;\nwindow.SONGS = ' + json.dumps(lean, ensure_ascii=False, separators=(',', ':')) + ';'
    for tag, code in (('<script src="songs.js"></script>', data), ('<script src="app.js"></script>', (ROOT / 'app.js').read_text(encoding='utf-8'))):
        assert tag in html
        html = html.replace(tag, inline(code))
    assert '<script src=' not in html and 'serviceWorker' not in html and '<link rel=' not in html
    (ROOT / 'dist').mkdir(exist_ok=True)
    out = ROOT / 'dist' / 'mantra-collection.html'
    out.write_text(html, encoding='utf-8')
    return out


def main():
    songs = sorted((parse(p) for p in (ROOT / 'songs').glob('*.txt')), key=lambda s: fold(s['title']))
    (ROOT / 'songs.js').write_text('/* Made by tools/build.py from songs/*.txt: don\'t edit by hand. */\nwindow.SONGS = '
                                   + json.dumps(songs, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    files = SHELL + sorted(str(p.relative_to(ROOT)) for d in ('assets/fonts', 'assets/icons') for p in (ROOT / d).glob('*') if p.suffix != '.txt')
    revs = [[f, hashlib.sha1((ROOT / f).read_bytes()).hexdigest()[:10]] for f in files if (ROOT / f).exists()]
    (ROOT / 'sw.js').write_text(SW.replace('__FILES__', json.dumps(revs)), encoding='utf-8')
    print(f'{len(songs)} songs, {(ROOT / "songs.js").stat().st_size / 1024:.0f} KB; {len(revs)} files saved for offline use')
    out = single_file(songs)
    print(f'{out.relative_to(ROOT)}: the whole book in one file, {out.stat().st_size / 1024:.0f} KB')
    for s in songs:
        if not s['key']: print('  no key:', s['slug'])


if __name__ == '__main__':
    main()
