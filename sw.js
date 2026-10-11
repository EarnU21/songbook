/* Mantra Collection offline worker, made by tools/build.py: don't edit by hand.
   From Nathan Vanderpool's Secret Songbook. Saves every file below on the first visit and answers from that
   copy when there's no signal. The page and the songs ask the network first, so an update shows as soon as
   someone is online. Recordings are saved the first time they are played. */
const FILES = [["index.html", "ef1854108d"], ["app.js", "944eb5b808"], ["songs.js", "1445fbe1ed"], ["manifest.webmanifest", "b2f9113cd3"], ["assets/fonts.css", "d1a4341b93"], ["assets/fonts/atkinson-hyperlegible-latin-400-italic.woff2", "28700b8a79"], ["assets/fonts/atkinson-hyperlegible-latin-400-normal.woff2", "3201099022"], ["assets/fonts/atkinson-hyperlegible-latin-700-normal.woff2", "05dadf003f"], ["assets/fonts/atkinson-hyperlegible-latin-ext-400-italic.woff2", "ce11b2e53b"], ["assets/fonts/atkinson-hyperlegible-latin-ext-400-normal.woff2", "3a54aad037"], ["assets/fonts/atkinson-hyperlegible-latin-ext-700-normal.woff2", "97dbf56ced"], ["assets/icons/apple-touch-icon.png", "988c359f14"], ["assets/icons/icon-192.png", "16ae0769bd"], ["assets/icons/icon-512.png", "4050c1a2e1"], ["assets/icons/icon.svg", "c67e0edeef"]];
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
    e.respondWith(fetch(req).catch(async () => (await caches.match(key)) || Response.error()));
    return;
  }
  e.respondWith((async () => (await caches.match(key)) || fetch(req))());
});
