# Deployment auf Infomaniak (music.nikschreiner.de)

Wie bei `intern.nikschreiner.de`: ein Push auf `main` löst die GitHub-Action „Deploy to Infomaniak“ aus, die das Songbook
baut, prüft und per SFTP kopiert. Anders als dort gibt es keinen `public/`-Ordner, keine Datenbank und keine `config.php`:
das Songbook besteht nur aus statischen Dateien, die direkt im Document Root der Website liegen.

Auf dem Server liegen danach: `index.html`, `app.js`, `songs.js`, `sw.js`, `manifest.webmanifest`, `.htaccess`,
`mantra-collection.html` (das ganze Buch in einer Datei, zum Weitergeben), `assets/` und `audio/`.

## Einmalig
1. **Website bei Infomaniak** anlegen: im Manager beim Webhosting eine neue Website für `music.nikschreiner.de` hinzufügen
   (eigener DNS-Eintrag, eigener Ordner). Der Forward von `nikschreiner.de` auf Notion darf die Subdomain nicht mit abfangen.
2. **SSL-Zertifikat** (Let's Encrypt) für die Website aktivieren und HTTPS erzwingen. Ohne HTTPS gibt es keinen
   Offline-Betrieb und kein „Zum Homescreen“.
3. **GitHub-Repo** anlegen (privat genügt) und dieses Verzeichnis dorthin pushen.
4. **GitHub-Secrets** im Repo (Settings → Secrets and variables → Actions): `SFTP_HOST`, `SFTP_USERNAME`, `SFTP_PASSWORD`
   (dieselben wie bei der Akte) und `SFTP_TARGET_PATH`: der volle Pfad des Document Root der neuen Website,
   z. B. `/home/clients/…/sites/music.nikschreiner.de`.
5. **Erster Lauf**: Reiter Actions → „Deploy to Infomaniak“ → Run workflow, mit Haken bei „Auch alle Aufnahmen hochladen“.
   Das dauert wegen der Aufnahmen (184 MB) einige Minuten.
6. **Prüfen**: `https://music.nikschreiner.de` am Handy öffnen, einen Song aufrufen, Flugmodus an, Seite neu laden.

## Danach jedes Mal
Song in `songs/` ändern oder hinzufügen, `python3 tools/build.py`, committen, `git push`. Die Action löscht nie etwas auf dem
Server. Aufnahmen gehen nur mit, wenn sich in `audio/` etwas geändert hat.

Ohne GitHub geht es auch von Hand: `tools/deploy.sh` (siehe README).

## Sicherheit
- Der SFTP-Zugang von Infomaniak reicht auf das ganze Hosting, also auch auf die Akte. Wer Schreibzugriff auf dieses Repo
  oder seine Secrets hat, kann dort Dateien ablegen. Darum: 2FA für den GitHub-Account, niemanden als Mitarbeiter einladen,
  der nicht auch an die Akte dürfte. Sauberer wäre ein eigener FTP-Benutzer nur für den Ordner von `music`.
- Das Songbook selbst enthält keine Zugangsdaten und nichts Vertrauliches.
