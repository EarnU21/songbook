#!/bin/bash
# Upload the songbook to the web host over SFTP.
#
#   tools/deploy.sh            the page, the songs and the fonts (small, a few seconds)
#   tools/deploy.sh --audio    the recordings in audio/ as well (large)
#
# Where to upload is read from deploy.env next to this repo's README (copy deploy.env.example and fill it in).
# No password is stored: sftp asks for it, or uses your SSH key.
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f deploy.env ] || { echo "deploy.env is missing: copy deploy.env.example to deploy.env and fill it in." >&2; exit 1; }
source deploy.env
: "${SFTP_HOST:?set SFTP_HOST in deploy.env}" "${SFTP_USER:?set SFTP_USER in deploy.env}" "${SFTP_PATH:?set SFTP_PATH in deploy.env}"

python3 tools/build.py

# a leading "-" lets sftp carry on when the folder is already there
commands="cd $SFTP_PATH
put index.html
put app.js
put songs.js
put manifest.webmanifest
-mkdir assets
put -r assets
"
if [ "${1:-}" = "--audio" ]; then
  commands+="-mkdir audio
put -r audio
"
fi
# sw.js goes last: it tells phones that have the book saved to fetch the new files
commands+="put sw.js
bye
"

echo "Uploading to $SFTP_USER@$SFTP_HOST:$SFTP_PATH ..."
sftp -P "${SFTP_PORT:-22}" "$SFTP_USER@$SFTP_HOST" <<< "$commands"
echo "Done."
