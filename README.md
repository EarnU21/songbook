# Mantra Collection | Nik & Friends

A songbook for the phone: search, words and chords, transposing, capo, and it works without signal.
The chord format, the transposing code and the offline worker come from Nathan Vanderpool's
[Secret Songbook](https://github.com/NathanVanderpool/nathanvanderpool.com).

## Adding or changing a song

1. Add or edit a file in `songs/`. The format is described at the top of `tools/build.py`;
   chords go in square brackets right before the syllable they land on: `[Am]Evening [E]rise`.
2. Run the build:

   ```bash
   python3 tools/build.py
   ```

`songs.js` and `sw.js` are made by the build. Don't edit them by hand.

## Looking at it

```bash
python3 -m http.server 8765
```

Then open http://localhost:8765. Opening `index.html` straight from the disk shows the songs too,
but the offline copy and "add to home screen" only work from a server.

## Adding a song from a chord sheet

Copy a sheet with the chords on their own line above the words (the way chord sites show them), then:

```bash
pbpaste | python3 tools/import_text.py "Make Room" "Community Music"
```

The second name is optional and is shown under the title. Then run the build.

## Bringing songs over from Notion

```bash
python3 tools/import_notion.py --list
python3 tools/import_notion.py "Evening Rise"
python3 tools/import_notion.py --all
```

Files that already exist are kept (add `--force` to overwrite). The importer estimates where each chord
sits, and guesses the key from the first chord, so read every imported song once. Recordings, images and
videos are not downloaded; the importer leaves a `% audio still in Notion: ...` line where one belongs.
