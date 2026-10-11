# Veröffentlichen über GitHub Pages (music.nikschreiner.de)

Das Songbook besteht nur aus statischen Dateien. Darum läuft es nicht wie die Akte über Infomaniak, sondern direkt über
GitHub Pages: ein Push auf `main` löst die Action „Deploy to GitHub Pages“ aus, die das Songbook baut, prüft und
veröffentlicht. Es gibt keine Secrets und keinen Zugang zum Infomaniak-Hosting.

Veröffentlicht werden: `index.html`, `app.js`, `songs.js`, `sw.js`, `manifest.webmanifest`, `mantra-collection.html`
(das ganze Buch in einer Datei, zum Weitergeben), `assets/`, `audio/` und `CNAME`.
`songs.js` und `sw.js` liegen nicht im Repo: die Action erzeugt sie aus `songs/*.txt`.

## Einmalig
1. **GitHub-Repo** anlegen, **öffentlich** (Pages ist im kostenlosen Konto nur für öffentliche Repos zu haben), und dieses
   Verzeichnis dorthin pushen. Alles im Repo ist dann für jeden herunterladbar, auch die Aufnahmen und der ganze Verlauf.
2. **Pages einschalten**: im Repo Settings → Pages → Source: „GitHub Actions“.
3. **DNS-Eintrag bei Infomaniak**: in der DNS-Zone von `nikschreiner.de` einen Eintrag vom Typ CNAME anlegen,
   Name `music`, Ziel `<github-name>.github.io.` (bei den bisherigen Repos: `earnu21.github.io.`). Keine Website, kein
   Ordner, kein SSL bei Infomaniak. Der Forward von `nikschreiner.de` auf Notion darf die Subdomain nicht mit abfangen.
4. **Domain eintragen**: Settings → Pages → Custom domain: `music.nikschreiner.de`. GitHub prüft den DNS-Eintrag und
   holt das Zertifikat (das kann bis zu einer Stunde dauern). Danach „Enforce HTTPS“ anhaken. Ohne HTTPS gibt es
   keinen Offline-Betrieb und kein „Zum Homescreen“.
5. **Prüfen**: `https://music.nikschreiner.de` am Handy öffnen, einen Song aufrufen, Flugmodus an, Seite neu laden.

## Danach jedes Mal
- Am Mac: Song in `songs/` ändern oder hinzufügen, committen, `git push`.
- Auf github.com (auch am Handy): Datei in `songs/` öffnen, Stift, ändern, „Commit changes“. Neue Songs über „Add file“.

Nach ein bis zwei Minuten ist die Änderung online. Der Reiter „Actions“ zeigt, ob der Lauf geklappt hat; scheitert der
Build, bleibt die bisherige Seite stehen.

## Grenzen
- Seite höchstens 1 GB, einzelne Dateien höchstens 100 MB. Die Aufnahmen brauchen zurzeit 184 MB.
- Eine Aufnahme, die einmal gepusht wurde, bleibt im Verlauf des öffentlichen Repos, auch wenn die Datei später gelöscht
  wird. Vor dem Pushen überlegen, ob alle Beteiligten einverstanden sind.
