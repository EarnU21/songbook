/* Mantra Collection. The chord format, the music helpers (parsing, transposing, spelling) and the
   home-screen/offline pieces come from Nathan Vanderpool's Secret Songbook
   (github.com/NathanVanderpool/nathanvanderpool.com). One page shows every song from songs.js. */
const SONGS = window.SONGS || [];
let SONG = null, SONG_KEY = 0, MINOR = false;
const state = { shift: 0, capo: 0 };
const prefs = { chords: true, size: 1.2 };

/* ---------- Music helpers ---------- */
const KEY_NAMES = ['C','D♭','D','E♭','E','F','F♯','G','A♭','A','B♭','B'];
const MINOR_NAMES = ['Cm','C♯m','Dm','E♭m','Em','Fm','F♯m','Gm','G♯m','Am','B♭m','Bm'];
const LETTERS = 'CDEFGAB', NATURAL = [0,2,4,5,7,9,11];
const LETTER = { C:0, D:2, E:4, F:5, G:7, A:9, B:11 };
const ACC = { 0:'', 1:'♯', 2:'𝄪', 11:'♭', 10:'𝄫' };
const STEP = [0,1,1,2,2,3,4,4,5,5,6,6];                 // letter steps above a root, by semitone
const mod = n => ((n % 12) + 12) % 12;
const mod7 = n => ((n % 7) + 7) % 7;

function parsePitch(s) {
  const m = /^([A-G])([#b♯♭]?)/.exec(s);
  if (!m) return null;
  let pc = LETTER[m[1]];
  if (m[2] === '#' || m[2] === '♯') pc++;
  if (m[2] === 'b' || m[2] === '♭') pc--;
  return { pc: mod(pc), len: m[0].length };
}
function parseChord(sym) {
  const [main, bass] = sym.split('/');
  const r = parsePitch(main);
  if (!r) return null;
  return { root: r.pc, quality: main.slice(r.len), bass: bass ? parsePitch(bass)?.pc : null };
}

/* The chords in a song file are what you finger; with "capo: 3" in the file they sound three half steps higher.
   shift moves the sounding key, capo is the fret the reader's capo is on. Untouched, a song reads as written. */
const move = () => (SONG.capo || 0) + state.shift - state.capo;
const PLAIN_FLAT = ['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B'];
const PLAIN_SHARP = ['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','B'];
function noteName(letterIdx, pc) {
  const l = mod7(letterIdx), acc = ACC[mod(pc - NATURAL[l])];
  const name = LETTERS[l] + (acc ?? '?');
  /* Players read B faster than C♭, and F faster than E♯ */
  if (acc === undefined || /^(C♭|F♭|E♯|B♯)$/.test(name) || /𝄪|𝄫/.test(name))
    return (acc === '♯' || acc === '𝄪' ? PLAIN_SHARP : PLAIN_FLAT)[mod(pc)];
  return name;
}
function keyName(pc) { return (MINOR ? MINOR_NAMES : KEY_NAMES)[mod(pc)]; }
/* Spell a note (given in the original key) after transposition, using its
   scale degree in the new key, so borrowed chords keep flats (E♭ in F, B♭ in C). */
function spell(pc) {
  const k = mod(SONG_KEY + move()), kl = LETTERS.indexOf(keyName(k)[0]);
  const deg = mod(pc - SONG_KEY);
  return noteName(kl + STEP[deg], mod(pc + move()));
}
function chordName(sym) {
  const c = parseChord(sym);
  if (!c) return sym;
  return spell(c.root) + c.quality + (c.bass != null ? '/' + spell(c.bass) : '');
}
/* "(Gmaj7)" is an optional chord: it keeps its brackets */
function shown(sym) {
  const m = /^\((.*)\)$/.exec(sym);
  return m ? '(' + chordName(m[1]) + ')' : chordName(sym);
}

/* ---------- Rendering ---------- */
function segments(src) {
  const out = [], re = /\[([^\]]*)\]/g;   // [] (empty) starts a new chordless spot: "[E♭]  []can" puts the word after the chord
  let last = 0, chord = null, m;
  while ((m = re.exec(src))) {
    if (m.index > last || chord !== null) out.push({ chord, text: src.slice(last, m.index) });
    chord = m[1]; last = re.lastIndex;
  }
  out.push({ chord, text: src.slice(last) });
  return out.filter(s => s.chord || s.text);
}
const esc = s => s.replace(/[&<>"]/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]));
const fold = s => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase();

/* One line of the song. Each chord sits over the syllable after it. The words are cut into pieces at the spaces so
   a long line can wrap on a phone; pieces of one word (a chord change inside it) are kept together. */
function lineHTML(src) {
  const segs = segments(src), hasCh = segs.some(s => s.chord);
  const words = src.replace(/\[[^\]]*\]/g, '').replace(/[^\p{L}]/gu, '');
  /* a row of chords with no words ("[Em] [Bm] [G] [A]"): one tight row that belongs to the line under it */
  if (hasCh && !words) return `<div class="line chord-only">${segs.map(s =>
    (s.chord ? `<b class="ch">${esc(shown(s.chord))}</b>` : '') + (s.text.trim() ? `<span class="ch between">${esc(s.text.trim())}</span>` : '')).join('')}</div>`;
  const pieces = [];
  segs.forEach(s => (s.text.match(/\s*\S+\s*|\s+/g) || ['']).forEach((t, i) => pieces.push({ chord: i ? null : s.chord, text: t })));
  let html = '', open = false;
  pieces.forEach((p, i) => {
    const next = pieces[i + 1], glue = next && /\S$/.test(p.text) && /^\S/.test(next.text);
    const seg = `<span class="seg${p.text.trim() ? '' : ' bare'}">${hasCh ? `<b class="ch">${p.chord ? esc(shown(p.chord)) : ''}</b>` : ''}<span class="ly">${esc(p.text) || ' '}</span></span>`;
    if (glue && !open) { html += '<span class="word">'; open = true; }
    html += seg;
    if (!glue && open) { html += '</span>'; open = false; }
  });
  return `<div class="line">${html}</div>`;
}

/* Chords take no room, so the words keep their natural spacing. Where two chords on one row would touch,
   the first one's spot is widened just enough; a chord that would stick out past the right edge gets its full width. */
function spreadChords() {
  if (!prefs.chords) return;
  const box = r => { const g = document.createRange(); g.selectNodeContents(r); return g.getBoundingClientRect(); };
  document.querySelectorAll('#song .line:not(.chord-only)').forEach(line => {
    const chs = [...line.querySelectorAll('.ch')].filter(c => c.textContent);
    chs.forEach(c => { c.parentElement.style.paddingRight = ''; c.parentElement.style.minWidth = ''; });
    const edge = line.getBoundingClientRect().right, gap = parseFloat(getComputedStyle(line).fontSize) * .4;
    chs.forEach((c, i) => {
      const a = box(c), next = chs[i + 1], seg = c.parentElement;
      if (a.right > edge) { seg.style.minWidth = Math.ceil(a.width) + 'px'; return; }
      if (!next) return;
      const b = box(next);
      if (Math.abs(b.top - a.top) < 4 && a.right + gap > b.left) seg.style.paddingRight = Math.ceil(a.right + gap - b.left + parseFloat(getComputedStyle(seg).paddingRight)) + 'px';
    });
  });
}
addEventListener('resize', () => { spreadChords(); });
document.fonts && document.fonts.ready.then(() => { spreadChords(); markStretched(); });

/* A word pulled apart by a wide chord (tan - to under "Em G"): show the hyphen, the way chord charts do.
   Only when it's actually pulled apart. */
function markStretched() {
  document.querySelectorAll('#song .word .seg:not(:last-child)').forEach(sg => {
    sg.classList.remove('stretched');
    if (!prefs.chords) return;
    const r = document.createRange(); r.selectNodeContents(sg.querySelector('.ly'));
    if (sg.getBoundingClientRect().width - r.getBoundingClientRect().width > 1.5) sg.classList.add('stretched');
  });
}
addEventListener('resize', markStretched);
document.fonts && document.fonts.ready.then(markStretched);

function renderSong() {
  document.getElementById('song').innerHTML = SONG.sections.map(sec =>
    `<section class="sec">${sec.caption ? `<h2>${esc(sec.caption)}</h2>` : ''}` +
    sec.lines.map(l => typeof l === 'string' ? lineHTML(l) : `<p class="remark">${esc(l.note)}</p>`).join('') + '</section>').join('')
    || '<p class="remark">The words for this song are not here yet: so far they are a picture, PDF or recording on the Notion page.</p>';
  spreadChords(); markStretched();
}

function renderKey() {
  const hasKey = !!SONG.key;
  document.getElementById('keyGroup').hidden = document.getElementById('capoBox').hidden = !hasKey;
  if (!hasKey) { document.getElementById('facts').textContent = SONG.note || ''; return; }
  const sounding = SONG_KEY + (SONG.capo || 0) + state.shift;
  document.getElementById('keyOut').textContent = keyName(sounding);
  /* Capo: each choice is named by the shapes it gives */
  document.getElementById('capoPick').innerHTML = Array.from({ length: 10 }, (_, n) =>
    `<option value="${n}"${n === state.capo ? ' selected' : ''}>${n ? `Capo ${n}: ${keyName(sounding - n)} shapes` : 'No capo'}</option>`).join('');
  const original = SONG_KEY + (SONG.capo || 0);
  let facts = `Key <b>${keyName(sounding)}</b>` + (state.shift ? ` (original ${keyName(original)})` : '');
  if (state.capo) facts += ` · capo on fret <b>${state.capo}</b>, ${keyName(sounding - state.capo)} shapes`;
  if (SONG.note) facts += ` · ${esc(SONG.note)}`;
  document.getElementById('facts').innerHTML = facts;
}

function renderPage() {
  document.title = SONG.title + ' | Mantra Collection';
  document.getElementById('title').textContent = SONG.title;
  const links = document.getElementById('links');
  links.innerHTML = SONG.links.map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a>`).join(' · ');
  links.hidden = !SONG.links.length;
  /* recordings load only when played; the offline worker keeps each one after its first play */
  document.getElementById('audio').innerHTML = SONG.audio.map(a =>
    `<figure>${a.label ? `<figcaption>${esc(a.label)}</figcaption>` : ''}<audio controls preload="none" src="${esc(a.src)}"></audio></figure>`).join('');
  document.getElementById('texts').innerHTML = SONG.texts.map(t => `<details><summary>${esc(t.title)}</summary><div>${esc(t.body)}</div></details>`).join('');
  const i = SONGS.indexOf(SONG), prev = SONGS[i - 1], next = SONGS[i + 1];
  document.getElementById('foot').innerHTML = (prev ? `<a href="#/${prev.slug}">← ${esc(prev.title)}</a>` : '<span></span>') + (next ? `<a href="#/${next.slug}">${esc(next.title)} →</a>` : '');
  renderKey(); renderSong();
}

/* ---------- The list ---------- */
function renderList() {
  const q = fold(document.getElementById('q').value.trim());
  /* a match in the title comes before a match in the words */
  const hits = q ? [...SONGS.filter(s => fold(s.title).includes(q)), ...SONGS.filter(s => !fold(s.title).includes(q) && s.find.includes(q))] : SONGS;
  let letter = '';
  document.getElementById('list').innerHTML = hits.map(s => {
    const l = fold(s.title)[0]?.toUpperCase() || '';
    const head = !q && l !== letter ? `<li class="letter" aria-hidden="true">${letter = l}</li>` : '';
    return head + `<li><a href="#/${s.slug}"><b>${esc(s.title)}</b><span>${esc(s.key || '')}${s.capo ? ' · capo ' + s.capo : ''}</span></a></li>`;
  }).join('') || '<li class="none">Nothing found. Try fewer letters.</li>';
  document.getElementById('count').textContent = q ? `${hits.length} of ${SONGS.length} songs` : `${SONGS.length} songs`;
}
document.getElementById('q').addEventListener('input', renderList);

/* ---------- What the reader chose, kept on this device ---------- */
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } },
  set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
};
function remember() {
  const changed = state.shift || state.capo !== (SONG.capo || 0);
  store.set('mc-' + SONG.slug, changed ? { shift: state.shift, capo: state.capo } : null);
}
function applyPrefs() {
  document.body.classList.toggle('no-chords', !prefs.chords);
  document.getElementById('chordsBtn').setAttribute('aria-checked', prefs.chords);
  document.documentElement.style.setProperty('--size', prefs.size + 'rem');
  if (SONG) { spreadChords(); markStretched(); }
}
Object.assign(prefs, store.get('mc-prefs') || {});
applyPrefs();

document.getElementById('keyDown').onclick = () => { state.shift = state.shift <= -6 ? 5 : state.shift - 1; remember(); renderKey(); renderSong(); };
document.getElementById('keyUp').onclick = () => { state.shift = state.shift >= 6 ? -5 : state.shift + 1; remember(); renderKey(); renderSong(); };
document.getElementById('capoPick').onchange = e => { state.capo = +e.target.value; remember(); renderKey(); renderSong(); };
document.getElementById('chordsBtn').onclick = () => { prefs.chords = !prefs.chords; store.set('mc-prefs', prefs); applyPrefs(); };
const resize = d => { prefs.size = Math.min(2.2, Math.max(.9, +(prefs.size + d).toFixed(2))); store.set('mc-prefs', prefs); applyPrefs(); };
document.getElementById('smaller').onclick = () => resize(-.1);
document.getElementById('bigger').onclick = () => resize(.1);

/* ---------- Keep the screen on while a song is open ---------- */
let lock = null;
async function stayAwake(on) {
  try {
    if (on && !lock && navigator.wakeLock) { lock = await navigator.wakeLock.request('screen'); lock.addEventListener('release', () => { lock = null; }); }
    if (!on && lock) { await lock.release(); lock = null; }
  } catch (e) {}
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && SONG) stayAwake(true); });

/* ---------- Which page: #/slug is a song, anything else the list ---------- */
let listScroll = 0;
function route() {
  const slug = decodeURIComponent(location.hash.replace(/^#\/?/, ''));
  const song = SONGS.find(s => s.slug === slug);
  if (!SONG && song) listScroll = scrollY;
  SONG = song || null;
  document.getElementById('home').hidden = !!SONG;
  document.getElementById('page').hidden = !SONG;
  stayAwake(!!SONG);
  if (!SONG) { document.title = 'Mantra Collection | Nik & Friends'; document.getElementById('audio').innerHTML = ''; scrollTo(0, listScroll); return; }
  const key = parsePitch(SONG.key || '');
  SONG_KEY = key ? key.pc : 0;
  MINOR = !!key && /^m(?!aj)/.test(SONG.key.slice(key.len));
  const saved = store.get('mc-' + SONG.slug);
  state.shift = saved?.shift || 0;
  state.capo = saved?.capo ?? (SONG.capo || 0);
  renderPage();
  scrollTo(0, 0);
}
addEventListener('hashchange', route);
renderList();
route();

/* "Add to home screen": one tap on Android/Chrome; on iPhone Safari there's no button for it, so show the two steps.
   Hidden when the collection is already open from the home screen, and in browsers that can't do either. */
(() => {
  const box = document.getElementById('install'), btn = document.getElementById('installBtn'), how = document.getElementById('installHow');
  if (window.SINGLE_FILE) return;   // the one-file copy can't be installed
  const installed = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  if (installed) { try { navigator.storage?.persist?.(); } catch (e) {} return; }   // ask the phone to keep the offline copy
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  let prompt = null;
  addEventListener('beforeinstallprompt', e => { e.preventDefault(); prompt = e; box.hidden = false; });
  addEventListener('appinstalled', () => { box.hidden = true; });
  if (ios) box.hidden = false;
  btn.onclick = async () => {
    if (prompt) { prompt.prompt(); const r = await prompt.userChoice; if (r.outcome === 'accepted') box.hidden = true; prompt = null; }
    else { how.hidden = !how.hidden; btn.setAttribute('aria-expanded', !how.hidden); }
  };
})();
