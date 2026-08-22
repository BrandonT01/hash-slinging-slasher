"""The Black Ops 3 build vocabulary reduced to cores, so the engine can redecorate it.

    python contrib/bo3_cores.py --out contrib/bo3_cores.txt
    bin\\windows\\confirm_plan.exe plans/bo3_build.txt --size
    bin\\windows\\confirm_plan.exe plans/bo3_build.txt

Run `contrib/harvest_bo3.py` first -- this reads what that writes.

**What problem it solves.** `contrib/harvest_bo3.py` produces Black Ops 3's names as the build
spells them: `i_attach_t7_ar_xr2_barrel_01_o` carries an image beginning and a map suffix already.
Handing that to `confirm_plan` as a stem asks about `i_i_attach_t7_ar_xr2_barrel_01_o_c`, which is
not a name in any title. A plan multiplies its stems by beginnings and endings **literally**, so
the stems have to be the part that stays the same when a title redecorates it.

So this strips what Black Ops 3 put on -- the twelve material directories, the image and material
beginnings, the map suffix, the `_lodNNN` tail the build appends -- and emits the core. Then it
emits that core again with every generation tag this era uses, because the tag is the thing that
moves when an asset is carried forward (see method 17: `t7_` heads 18,379 published image names
*for our era*, so these games really do inherit them).

The point of doing it this way rather than in Python: `plans/bo3_build.txt` puts all 700 measured
beginnings and 4,629 measured endings around every core through the compiled peeling engine. §7's
arithmetic is that every invented method ever run here has tested 10.2 billion candidates between
them, against 103 trillion for one general pass -- so a generator that prints a few decorations of
its own is asking a ten-thousandth of the question this asks.

**Reads** `borrowed/bo3_build.txt`. **Writes** one core per line, for a plan's `stem:` to read.
"""
import argparse
import os
import re
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)

# Material names are paths, and there are twelve directories rather than one. See AGENTS.md.
DIRECTORIES = ("mc/", "wc/", "clt/", "splm/", "vd/", "mcs/",
               "ei/", "cltp/", "vdd/", "el/", "mcp/", "ec/")

# What an image or material puts on the front, longest first so `i_mtl_` wins over `i_`.
OPENINGS = ("i_mtl_", "i_c_", "mtl_", "i_", "c_")

# The map suffix an image ends in. Stripped one deep only: `_base_r` is a core plus `_r`, but
# `_r_c` is not a thing, so taking more than one invents cores the build never had.
SUFFIXES = ("_c", "_n", "_g", "_o", "_m", "_s", "_r", "_a", "_d",
            "_e", "_h", "_l", "_t", "_v", "_x", "_nml", "_spc", "_msk")

# The build appends a mesh-ish tail to model names. It is hashed from the mesh, so it is the one
# thing here that can never be reconstructed -- see the `xmodelmesh` row in AGENTS.md.
LOD = re.compile(r"_lod[0-9a-f]*$")

# Any generation tag as a whole token, and what these two games spell theirs.
TAG = re.compile(r"(?<![a-z0-9])t[0-9](?=_)")
TAGS = ("t8", "t9")


def core(name):
    """One build name reduced to the part another title would keep."""
    for directory in DIRECTORIES:
        if name.startswith(directory):
            name = name[len(directory):]
            break

    for opening in OPENINGS:
        if name.startswith(opening):
            name = name[len(opening):]
            break

    name = LOD.sub("", name)

    for suffix in SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix) + 3:
            name = name[:-len(suffix)]
            break

    return name


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=os.path.join(_root, "borrowed", "bo3_build.txt"))
    parser.add_argument("--out", default=os.path.join(_root, "contrib", "bo3_cores.txt"))
    parser.add_argument("--min", type=int, default=6, help="shortest core worth asking about")
    args = parser.parse_args(argv)

    if not os.path.exists(args.source):
        raise SystemExit(
            "%s is not here. Run `python contrib/harvest_bo3.py` first." % args.source
        )

    cores = set()
    read = 0

    with open(args.source, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            name = line.strip().lower()
            if not name:
                continue
            read += 1

            stem = core(name)
            if len(stem) < args.min:
                continue
            cores.add(stem)

            # And the same core as this era would tag it.
            if TAG.search(stem):
                for tag in TAGS:
                    cores.add(TAG.sub(tag, stem))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        for stem in sorted(cores):
            handle.write(stem + "\n")

    print("%d build name(s) -> %d core(s) -> %s" % (read, len(cores), args.out), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
