r"""Asset names read straight out of the older titles' `.iwd` archives, which are ZIP files.

    python contrib/harvest_iwd.py --out contrib/iwd_names.txt

Every other harvest here has had to fight a container: Oodle block chains for Black Ops 4, BLTE
frames for CASC, a 4 KB-window zlib whose header byte is 0x48 for Black Ops 3's zones, AES-256-CTR
for Cold War's. `.iwd` is none of those. It is a **ZIP file with the extension changed**, so its
central directory is a plain list of every path inside it, and Python's own `zipfile` reads it.

Steam ships them with Call of Duty 1, 2, 4, World at War, Modern Warfare 2 and 3, Modern Warfare
Remastered and Black Ops:

    Call of Duty Black Ops      47 .iwd    5.76 GB

`.ipak` and `.ff` from the same builds are already covered -- `bo2_ipak` is in cod-name-db and
`contrib/harvest_bo3.py` reads zones -- but nothing here has ever opened an `.iwd`, and it is the
cheapest external vocabulary on the disk: no decompression at all, because a name is metadata
rather than payload.

Three spellings of every entry, for the same reason `harvest_bo3_tools.py` prints three: the path,
the path without its extension, and the bare basename.


**Writes into `borrowed/`, never `contrib/`.** `submit` carries everything in `contrib/`
into the pull request, and a harvest is tens of thousands of scraped strings -- working
data that regenerates from the build in minutes and would otherwise sit in every
contributor's clone for ever. `borrowed/` is gitignored and `submit` does not read it.
The rule is the one `contrib/` exists for: carry the thing that *finds* names, not the
corpus it was built from.
"""
import argparse
import os
import sys
import zipfile

STEAM = r"C:\Program Files (x86)\Steam\steamapps\common"
SEPARATORS = set("_/")
# Folders a player writes to. Anything under one of these is community content, not shipped.
USER_CONTENT = {"mods", "usermaps", "workshop", "raw", "downloaded"}


def keep(text):
    if len(text) < 6 or len(text) > 160:
        return False
    if not any(character in SEPARATORS for character in text):
        return False
    return sum(character.isalpha() for character in text) >= 3


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=STEAM)
    parser.add_argument("--out", default=os.path.join("borrowed", "iwd_names.txt"))
    options = parser.parse_args(argv)

    names = set()
    archives = 0

    for folder, _, entries in os.walk(options.root):
        # Never walk into a folder a player writes to. `mods/` and `usermaps/` are where custom
        # and community content lands, and community content is the one thing that must not enter
        # a candidate list: it looks exactly like an official name, it can never be in either game
        # we search, and it is different on every contributor's disk -- so a method seeded from it
        # is not reproducible and its fingerprint means nothing. Measured on the Black Ops 3 tools
        # beside this: one modder's folder alone contributed 1,216 names, all of them Black Ops 6
        # weapon ports spelled `t10_...`, which METHODS records as dead against these two titles.
        if any(part in USER_CONTENT for part in os.path.relpath(folder, options.root).lower().split(os.sep)):
            continue
        for entry in entries:
            if not entry.lower().endswith(".iwd"):
                continue
            path = os.path.join(folder, entry)
            try:
                with zipfile.ZipFile(path) as archive:
                    inside = archive.namelist()
            except (zipfile.BadZipFile, OSError):
                continue
            archives += 1
            before = len(names)
            for item in inside:
                text = item.replace("\\", "/").lower().strip("/")
                stem, _ = os.path.splitext(text)
                for spelling in (text, stem, os.path.basename(stem)):
                    if keep(spelling):
                        names.add(spelling)
            print("  %-56s %6d entries  +%s"
                  % (os.path.relpath(path, options.root)[:56], len(inside), len(names) - before),
                  flush=True)

    with open(options.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(names)) + "\n")
    print("\n%s archive(s) -> %s name(s) in %s"
          % (archives, format(len(names), ","), options.out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
