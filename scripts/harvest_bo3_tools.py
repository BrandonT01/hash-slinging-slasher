r"""Black Ops 3's asset names, taken from the mod tools rather than from the shipped zones.

    python contrib/harvest_bo3_tools.py --out contrib/bo3_tools.txt

`contrib/harvest_bo3.py` reads Black Ops 3's `zone/*.ff`, which is the shipped half of the build:
compressed containers holding whatever the game loads. This reads the **other** half, which Steam
also ships and which nothing here has ever opened.

The Black Ops 3 mod tools install the *source* assets, and a source asset is named by its
filename. Counted 2026-08-24 on this machine:

    32,937  .tif           109.7 GB   source textures
    31,785  .xmodel_bin      2.6 GB   source models
     9,797  .lz4                      packed source data
     2,369  .gdt                      asset definition tables, plain text
     2,254  .techsetdef               technique sets, plain text
     1,713  .map             plain    radiant map sources
     1,574  .efx             plain    effect definitions

**No decompression, no format work, no guessing.** The names are the paths, and the `.gdt` files
are plain text tables whose keys are asset names spelled exactly as the engine wants them.

Why it is worth asking Black Ops 4 about: §1473 of METHODS.md says the thing that finds names is a
vocabulary from **outside** the region the named corpus covers, and cod-name-db has no Black Ops 3
model, material, image or anim table at all -- only `bo3_sab`, which is audio. Black Ops 4 is Black
Ops 3's direct sequel on the same engine, and older-title vocabulary is the densest transfer
measured here.

Three spellings of every path are printed, because which one the engine hashes is not knowable in
advance and asking costs nothing: the path as it sits under the tools root, the path with its
extension dropped, and the bare basename.
"""
import argparse
import os
import re
import sys

BO3 = r"C:\Program Files (x86)\Steam\steamapps\common\Call of Duty Black Ops III"

# The extensions whose *contents* are plain text worth reading, rather than only their names.
TEXT = (".gdt", ".techsetdef", ".map", ".efx", ".csv", ".gsc", ".csc", ".gsh", ".atr", ".vision")
# Inside a .gdt an asset name is a quoted token; the same shape works for the other text formats.
QUOTED = re.compile(r'"([A-Za-z0-9_./\\\-]{6,160})"')
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_/.\-]{5,159}")
SEPARATORS = set("_/")


def keep(text):
    if len(text) < 6 or len(text) > 160:
        return False
    if not any(character in SEPARATORS for character in text):
        return False
    return sum(character.isalpha() for character in text) >= 3


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=BO3)
    parser.add_argument("--out", default="contrib/bo3_tools.txt")
    parser.add_argument("--most-text-mb", type=float, default=64.0,
                        help="skip a text file larger than this; none of the real ones are")
    options = parser.parse_args(argv)

    names = set()
    files = 0
    read = 0

    for folder, _, entries in os.walk(options.root):
        for entry in entries:
            files += 1
            path = os.path.join(folder, entry)
            relative = os.path.relpath(path, options.root).replace("\\", "/").lower()
            stem, extension = os.path.splitext(relative)

            for spelling in (relative, stem, os.path.basename(stem)):
                if keep(spelling):
                    names.add(spelling)

            if extension in TEXT:
                try:
                    if os.path.getsize(path) > options.most_text_mb * (1 << 20):
                        continue
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        body = handle.read()
                except OSError:
                    continue
                read += 1
                for found in QUOTED.findall(body):
                    text = found.replace("\\", "/").lower()
                    if keep(text):
                        names.add(text)
                        base, _ = os.path.splitext(text)
                        if keep(base):
                            names.add(base)
                for found in NAME.findall(body):
                    text = found.lower()
                    if keep(text):
                        names.add(text)

    with open(options.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(names)) + "\n")
    print("%s file(s) walked, %s read as text -> %s name(s) in %s"
          % (format(files, ","), format(read, ","), format(len(names), ","), options.out),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
