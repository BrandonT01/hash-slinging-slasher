"""The material directories a game actually uses, against the ones the library carries.

    python contrib/mcdp_cores.py                 write the stem cores for the mcdp/ plan
    python contrib/mcdp_cores.py --audit         just report which directories are uncarried
    python contrib/mcdp_cores.py --game BLKOPS04 audit a different title

## What this found, and why it is not `scripts/uncarried.py` under a new name

`uncarried.py` reports leading *segments* the committed beginning list cannot express, and the
plan it writes pairs each such beginning with cores taken from the published names that already
use it. Run that way on 2026-08-22 across 208 beginnings it returned 5 names, because for a
directory the interesting cores are precisely the ones that have *not* been seen under it yet.

This is the other half of that idea, and it rests on one measurement:

    all 692 published `mcdp/` cores also occur under some other material directory   (692 of 692)

`mcdp/` is not a namespace with a vocabulary of its own. It is a **re-decoration of the general
material vocabulary** -- the same cores, wearing a different directory. So the stem list that
reaches new `mcdp/` names is not mcdp's own 692 cores; it is every material core there is.

## Why nothing here could emit one

CLAUDE.md §6 fixes twelve material directories -- `mc/ wc/ clt/ splm/ vd/ mcs/ ei/ cltp/ vdd/ el/
mcp/ ec/` -- and they are hardcoded in `scripts/derive_lists.py` and
`scripts/materials_from_images.py`. Measured against Cold War's own known names on 2026-08-23:

    mc/     2766      mcdp/    820      ei/   526      wc/  193      clt/ 131
    splm/    95       vd/       89      cltp/  55      mcs/  12      el/   12
    vdd/     10       mcp/       0      ec/     0

`mcdp/` is the **second largest material directory in Cold War**, ahead of every carried
directory except `mc/` -- and two directories that are carried do not occur in the game at all.
`data/prefixes.txt` holds no cut of `mcdp/`, so no generator in this repository could produce
one of these names.

Directories are close to a materials-only phenomenon: the same audit over images, xmodels and
xanims in both titles turns up only a handful of one-off directories, so this seam is materials
and stops there.
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The twelve CLAUDE.md §6 fixes, and which the library hardcodes.
CARRIED = ["mc/", "wc/", "clt/", "splm/", "vd/", "mcs/", "ei/", "cltp/", "vdd/", "el/",
           "mcp/", "ec/"]

TABLES = ["cod-name-db/csv/fnv1a_xmaterials.csv", "cod-name-db/csv/fnv1a_xmaterials_v2.csv"]


def published_names():
    """Every material name in the published tables, directory included."""
    for relative in TABLES:
        path = ROOT / relative
        if not path.exists():
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                _, _, name = line.strip().partition(",")
                if "/" in name:
                    yield name


def core_of(name):
    """A material name with its directory and any `mtl_` decoration removed."""
    core = name.split("/", 1)[1]
    return core[4:] if core.startswith("mtl_") else core


def game_directories(game):
    """How often each directory heads a name the game is actually known to use."""
    path = ROOT / "all_names" / game.lower() / "material.txt"
    counts = {}
    if not path.exists():
        return counts
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            _, _, name = line.strip().partition(",")
            if "/" in name:
                directory = name.split("/", 1)[0] + "/"
                counts[directory] = counts.get(directory, 0) + 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true",
                        help="report which directories are uncarried, and write nothing")
    parser.add_argument("--game", default="BLKOPSCW", help="which title to audit")
    parser.add_argument("--out", default="contrib/mcdp_cores.txt",
                        help="where to write the stem cores")
    args = parser.parse_args()

    counts = game_directories(args.game)
    if args.audit or not counts:
        print(f"material directories {args.game} is known to use:")
        for directory, count in sorted(counts.items(), key=lambda pair: -pair[1]):
            mark = "  carried" if directory in CARRIED else "  UNCARRIED -- nothing can emit this"
            print(f"  {directory:<12} {count:>6}{mark}")
        missing = [d for d in CARRIED if d not in counts]
        if missing:
            print(f"\ncarried but absent from {args.game}: {', '.join(missing)}")
        if args.audit:
            return

    # The stems: every core the published material vocabulary holds, from directories other than
    # the one being hunted. All 692 published mcdp/ cores occur here, which is the measurement
    # this method rests on.
    cores = {core_of(name) for name in published_names() if not name.startswith("mcdp/")}
    destination = ROOT / args.out
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for core in sorted(cores):
            handle.write(core + "\n")
    print(f"{len(cores)} cores -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
