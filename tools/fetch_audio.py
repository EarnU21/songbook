#!/usr/bin/env python3
"""Download the recordings from the Notion page into audio/ and name them in the song files.

    python3 tools/fetch_audio.py

Each recording becomes a line "audio: audio/<file> | <label>" in the song's header, in place of the
"% audio still in Notion" remark. Files that are already in audio/ are not downloaded again.
Voice messages (.ogg) are turned into .m4a with ffmpeg, because iPhones don't play .ogg everywhere.
Then run tools/build.py.
"""
import json, re, shutil, subprocess, urllib.request
from pathlib import Path
from import_notion import API, OUT, PAGE, fetch, slug, title_of

AUDIO = OUT.parent / 'audio'
HEAD = {'content-type': 'application/json', 'user-agent': 'Mozilla/5.0'}


def signed(b):
    body = json.dumps({'urls': [{'url': b['properties']['source'][0][0],
                                 'permissionRecord': {'table': 'block', 'id': b['id'], 'spaceId': b['space_id']}}]}).encode()
    req = urllib.request.Request(API.replace('loadPageChunk', 'getSignedFileUrls'), data=body, headers=HEAD)
    return json.load(urllib.request.urlopen(req, timeout=60))['signedUrls'][0]


def recordings(body, blocks):
    for b in body:
        name = title_of(b).strip()
        if b.get('type') == 'audio' or (b.get('type') == 'video' and name.lower().endswith(('.ogg', '.mp3', '.m4a'))):
            yield b, name
        yield from recordings([blocks[c] for c in b.get('content') or [] if c in blocks], blocks)


def main():
    blocks = fetch()
    AUDIO.mkdir(exist_ok=True)
    songs, cur = [], None
    for bid in blocks[PAGE]['content']:
        b = blocks.get(bid)
        if not b: continue
        if b.get('type') == 'header':
            cur = (title_of(b), []); songs.append(cur)
        elif cur:
            cur[1].append(b)
    total = 0
    for title, body in songs:
        path = OUT / (slug(title) + '.txt')
        found = list(recordings(body, blocks))
        if not found or not path.exists(): continue
        text = path.read_text(encoding='utf-8')
        for n, (b, name) in enumerate(found):
            ext = Path(name).suffix.lower() or '.mp3'
            keep = '.m4a' if ext == '.ogg' and shutil.which('ffmpeg') else ext
            dest = AUDIO / f'{slug(title)}{"-" + str(n + 1) if n else ""}{keep}'
            if not dest.exists():
                raw, part = dest.with_suffix(ext), dest.with_suffix('.part')
                for attempt in range(4):   # a dropped connection must not leave half a file behind
                    try:
                        with urllib.request.urlopen(signed(b), timeout=120) as r, open(part, 'wb') as f:
                            shutil.copyfileobj(r, f)
                        break
                    except OSError:
                        if attempt == 3: raise
                part.rename(raw)
                if keep != ext:
                    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(raw), '-c:a', 'aac', '-b:a', '96k', str(dest)], check=True)
                    raw.unlink()
                print(f'{dest.stat().st_size / 1e6:5.1f} MB  {dest.name}')
            total += dest.stat().st_size
            label = re.sub(r'\.\w+$', '', name)
            label = '' if slug(label) == slug(title) or re.match(r'^(msg|track_|signal-)', label) else label
            line = f'audio: audio/{dest.name}' + (f' | {label}' if label else '')
            text = re.sub(rf'^% (audio|video) still in Notion: {re.escape(name)}[ \t]*\n', '', text, flags=re.M)
            if f'audio: audio/{dest.name}' not in text:
                head, sep, rest = text.partition('\n\n')
                text = head + '\n' + line + sep + rest
        path.write_text(text, encoding='utf-8')
    print(f'{total / 1e6:.0f} MB of recordings in audio/')


if __name__ == '__main__':
    main()
