#!/usr/bin/env python3
"""Turn a pasted chord sheet (chords on their own line above the words, lined up in a fixed-width font,
the way chord sites show them) into songs/<slug>.txt.

    pbpaste | python3 tools/import_text.py "Make Room" "Community Music"
    python3 tools/import_text.py "Make Room" < sheet.txt

The second name is optional and becomes the note under the title. An existing file is kept unless --force is given.
Then run tools/build.py.
"""
import sys
from import_notion import OUT, sheet, slug


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args: sys.exit(__doc__)
    head = {'title': args[0]}
    if len(args) > 1: head['note'] = args[1]
    lines = [l for l in sys.stdin.read().splitlines() if not l.startswith('```')]
    path = OUT / (slug(args[0]) + '.txt')
    if path.exists() and '--force' not in sys.argv:
        sys.exit(f'{path.name} is already there (add --force to replace it)')
    path.write_text(sheet(head, lines, mono=True), encoding='utf-8')
    print('imported', path.name)


if __name__ == '__main__':
    main()
