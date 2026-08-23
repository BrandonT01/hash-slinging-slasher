"""Black Ops 3's SAB sound names, respelled the way Black Ops 4 spells its own.

    python contrib/bo3_sab_to_bo4.py        write the three lists plans/bo3_snd.txt multiplies

## Why this ground

`sound_asset` in Black Ops 4 is the single largest opportunity in either title -- **70,878
unnamed of 79,263, 10.6% named**. Its ids were injected from the SAB files, because Black Ops 4's
loader never opens them, and its names keep their backslashes: the id is the hash of exactly that,
so this must run `--no-fold`.

Black Ops 4 is Black Ops 3's direct sequel on the same audio pipeline, and the two name sounds
identically. Measured 2026-08-23:

    Black Ops 4 known    zmb  fly  blk  wpn  amb  vox        tails  ln100 ll100 sl100 rn75 rr75
    Black Ops 3 SAB      wpn  fly  zmb  prj  mpl  amb  mus  vox
                                                              tails  SN100 SN85 LN100 LL100 SL100 PN100

Same directories, same dotted-tail grammar. The two differences are mechanical:

  * Black Ops 3 writes the tail in upper case (`.SN85.pc.snd`), Black Ops 4 in lower (`.ll100.pc.snd`).
  * Black Ops 3 puts a language directory at the front of voice paths (`ru\vox\...`, `en\vox\...`);
    Black Ops 4's known names carry no such directory and put the language in the tail instead
    (`.rr75.pc.en.snd`).

So the transfer is: take Black Ops 3's path, drop its language directory, lower case it, strip its
tail, and let the engine put every Black Ops 4 tail back on.

`data/sound.suffixes.txt` holds **no dotted tail at all** (0 of 2,890), so the committed sound
lists cannot express one of these endings -- the tails here are measured off the corpora instead.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The language directories Black Ops 3 puts in front of voice paths and Black Ops 4 does not.
LANGUAGES = {"en", "ru", "fr", "de", "it", "es", "pt", "pl", "ja", "ko", "zh", "cz", "ar"}


def rows(relative, comma_separated):
    path = ROOT / relative
    if not path.exists():
        print(f"  missing: {relative}", file=sys.stderr)
        return
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            yield line.split(",", 1)[1] if comma_separated and "," in line else line


def split_tail(name):
    """A sound name as (core, dotted tail). The tail is everything from the first dot."""
    dot = name.find(".")
    return (name, "") if dot == -1 else (name[:dot], name[dot:])


def main():
    cores, tails, directories = set(), set(), set()

    # Black Ops 3's SAB table: full paths, in exactly the shape Black Ops 4 uses.
    for name in rows("cod-name-db/csv/bo3_sab.csv", True):
        core, tail = split_tail(name.lower())
        if not core:
            continue
        if tail:
            tails.add(tail)
        pieces = core.split("\\")
        if len(pieces) > 1 and pieces[0] in LANGUAGES:
            pieces = pieces[1:]          # Black Ops 4 puts the language in the tail, not the path
        if not pieces:
            continue
        cores.add("\\".join(pieces))
        cores.add(pieces[-1])            # the basename alone, to wear a Black Ops 4 directory
        for cut in range(1, len(pieces)):
            directories.add("\\".join(pieces[:cut]) + "\\")

    # Black Ops 3's wider SAB dump: basenames only, no directories.
    for name in rows("borrowed/bo3_sab.txt", False):
        core, tail = split_tail(name.lower())
        if core:
            cores.add(core)
        if tail:
            tails.add(tail)

    # Black Ops 4's own known sound names, for the tails and directories it actually uses.
    for name in rows("all_names/blkops04/sound_asset.txt", True):
        core, tail = split_tail(name.lower())
        if tail:
            tails.add(tail)
        pieces = core.split("\\")
        for cut in range(1, len(pieces)):
            directories.add("\\".join(pieces[:cut]) + "\\")

    # A tail has to look like one: dots, alphanumerics, ending in .snd. The corpora carry a few
    # malformed rows where a stray dot put a whole path into the tail.
    tails = {t for t in tails
             if t.endswith(".snd") and "\\" not in t and t.count(".") <= 4 and len(t) <= 24}

    for name, values in (("bo3_snd_cores.txt", cores),
                         ("bo3_snd_tails.txt", tails),
                         ("bo3_snd_dirs.txt", directories)):
        destination = ROOT / "contrib" / name
        destination.write_text(chr(10).join(sorted(values)) + chr(10), encoding="utf-8")
        print(f"{len(values):>8} -> contrib/{name}", file=sys.stderr)


if __name__ == "__main__":
    main()
