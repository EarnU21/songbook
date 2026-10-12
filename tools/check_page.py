#!/usr/bin/env python3
"""Write check.html: every song from the Notion page as it was typed there (in Notion's font, tabs and all),
next to the same song in the songbook. For reading the chord positions against the original.

    python3 tools/check_page.py

The page is a snapshot of Notion at the time it was made. It ticks off songs in the browser it is opened in.
"""
import html, json, re
from pathlib import Path
from import_notion import fetch, is_chord_line, one_key, slug, songs_on_page, source

ROOT = Path(__file__).resolve().parent.parent


def main():
    blocks = fetch()
    by_title = {}
    for p in (ROOT / 'songs').glob('*.txt'):
        m = re.match(r'title:\s*(.*)', p.read_text(encoding='utf-8'))
        if m: by_title[m.group(1).strip().lower()] = p.stem
    songs = []
    for title, body in songs_on_page(blocks):
        head, lines, texts, todo = source(title, body, blocks)
        t = title.strip()
        name = by_title.get(t.lower()) or by_title.get(re.sub(r'\s*\+\d+$', '', t).lower()) or slug(t)
        rows = [[1 if is_chord_line(one_key(l.rstrip(), None)[0]) else 0, l.rstrip()] for l in lines]
        while rows and not rows[-1][1]: rows.pop()
        if not (ROOT / 'songs' / (name + '.txt')).exists(): continue
        songs.append({'slug': name, 'title': t, 'tabs': any('\t' in l for _, l in rows), 'chords': any(c for c, _ in rows), 'rows': rows})
    page = PAGE.replace('__SONGS__', json.dumps(songs, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))
    (ROOT / 'check.html').write_text(page, encoding='utf-8')
    print(f'check.html: {len(songs)} songs, {sum(s["tabs"] for s in songs)} of them typed with tabs')


PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Check the chords | Mantra Collection</title>
<style>
  :root { --window: #fff; --side: #f6f6f6; --ink: #1d1d1f; --soft: #6e6e73; --line: rgba(0,0,0,.1); --hover: rgba(0,0,0,.05); --accent: #0f7a66; --chord: #0f6b5c;
    --ui: -apple-system, BlinkMacSystemFont, system-ui, "Helvetica Neue", Helvetica, Arial, sans-serif; color-scheme: light dark; }
  @media (prefers-color-scheme: dark) { :root { --window: #1e1e1e; --side: #282828; --ink: #f5f5f7; --soft: #a1a1a6; --line: rgba(255,255,255,.13); --hover: rgba(255,255,255,.07); --accent: #2bb39a; --chord: #6fd0b8; } }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body { margin: 0; display: grid; grid-template-columns: 17rem 1fr; font: 13px/1.4 var(--ui); color: var(--ink); background: var(--window); }
  nav { background: var(--side); border-right: .5px solid var(--line); overflow-y: auto; padding: 10px 8px 20px; }
  nav p { margin: 2px 8px 8px; color: var(--soft); }
  nav label { display: flex; align-items: center; gap: 6px; margin: 0 8px 8px; }
  nav a { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 6px; color: inherit; text-decoration: none; }
  nav a:hover { background: var(--hover); }
  nav a.on { background: var(--accent); color: #fff; }
  nav a.done span:first-child { opacity: .45; text-decoration: line-through; }
  nav a span:first-child { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  nav a small { flex: none; padding: 0 5px; border-radius: 4px; background: var(--hover); font-size: 10px; }
  main { display: grid; grid-template-rows: auto 1fr; min-width: 0; min-height: 0; }
  header { display: flex; align-items: center; gap: 10px; padding: 8px 14px; border-bottom: .5px solid var(--line); background: var(--side); }
  header h1 { flex: 1; margin: 0; font-size: 15px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  button { height: 28px; padding: 0 12px; border: 0; border-radius: 6px; background: var(--window); box-shadow: 0 0 0 .5px rgba(0,0,0,.14), 0 .5px 1.5px rgba(0,0,0,.16); font: 500 13px/1 var(--ui); color: inherit; }
  button.primary { background: var(--accent); color: #fff; }
  .panes { display: grid; grid-template-columns: 1fr 1fr; min-height: 0; }
  .pane { min-width: 0; min-height: 0; display: grid; grid-template-rows: auto 1fr; }
  .pane + .pane { border-left: .5px solid var(--line); }
  .pane h2 { margin: 0; padding: 6px 14px; font-size: 11px; font-weight: 600; letter-spacing: .03em; text-transform: uppercase; color: var(--soft); border-bottom: .5px solid var(--line); }
  /* the left pane is set the way Notion sets a text block on the desktop: its font and size, spaces kept, a tab every 8 spaces */
  #src { overflow: auto; padding: 16px 20px; font: 16px/1.5 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI Variable Display", "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif; white-space: pre; tab-size: 8; }
  #src div { min-height: 1.5em; }
  #src .c { color: var(--chord); font-weight: 600; }
  iframe { width: 100%; height: 100%; border: 0; background: var(--window); }
  @media (max-width: 900px) { body { grid-template-columns: 1fr; } nav { max-height: 30vh; } .panes { grid-template-columns: 1fr; grid-template-rows: 1fr 1fr; } .pane + .pane { border-left: 0; border-top: .5px solid var(--line); } }
</style>
</head>
<body>
<nav>
  <p id="left"></p>
  <label><input type="checkbox" id="hide"> Hide the ones I've checked</label>
  <div id="list"></div>
</nav>
<main>
  <header>
    <h1 id="title"></h1>
    <button id="prev">Previous</button>
    <button id="next">Next</button>
    <button id="ok" class="primary">Looks right</button>
  </header>
  <div class="panes">
    <section class="pane"><h2>As typed in Notion (desktop)</h2><div id="src"></div></section>
    <section class="pane"><h2>In the songbook</h2><iframe id="book" title="The song in the songbook"></iframe></section>
  </div>
</main>
<script>
const SONGS = __SONGS__;
const esc = s => s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
let done = {}; try { done = JSON.parse(localStorage.getItem('mc-check') || '{}'); } catch (e) {}
let at = 0;
const $ = id => document.getElementById(id);
function list() {
  const hide = $('hide').checked;
  $('list').innerHTML = SONGS.map((s, i) => hide && done[s.slug] && i !== at ? '' :
    `<a href="#${s.slug}" class="${i === at ? 'on' : ''}${done[s.slug] ? ' done' : ''}"><span>${esc(s.title)}</span>${s.tabs ? '<small>tabs</small>' : ''}${s.chords ? '' : '<small>no chords</small>'}</a>`).join('');
  $('left').textContent = `${SONGS.filter(s => !done[s.slug]).length} of ${SONGS.length} songs left to check`;
  document.querySelector('nav a.on')?.scrollIntoView({ block: 'nearest' });
}
function show() {
  const s = SONGS[at];
  $('title').textContent = s.title;
  $('src').innerHTML = s.rows.map(([c, l]) => `<div${c ? ' class="c"' : ''}>${esc(l)}</div>`).join('');
  $('src').scrollTop = 0;
  $('book').src = 'index.html#/' + s.slug;
  $('ok').textContent = done[s.slug] ? 'Checked ✓ (undo)' : 'Looks right';
  list();
}
function go(i) { at = Math.max(0, Math.min(SONGS.length - 1, i)); history.replaceState(null, '', '#' + SONGS[at].slug); show(); }
$('prev').onclick = () => go(at - 1);
$('next').onclick = () => go(at + 1);
$('ok').onclick = () => { const k = SONGS[at].slug; if (done[k]) delete done[k]; else done[k] = 1; try { localStorage.setItem('mc-check', JSON.stringify(done)); } catch (e) {} if (done[k] && at < SONGS.length - 1) go(at + 1); else show(); };
$('hide').onchange = list;
addEventListener('hashchange', () => { const i = SONGS.findIndex(s => s.slug === location.hash.slice(1)); if (i >= 0 && i !== at) { at = i; show(); } });
addEventListener('keydown', e => { if (e.target.tagName === 'INPUT') return; if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); go(at + 1); } if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); go(at - 1); } });
at = Math.max(0, SONGS.findIndex(s => s.slug === location.hash.slice(1)));
show();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()
