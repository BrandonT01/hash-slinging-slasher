"""Uncarried endings made generative: the numbers composed rather than observed.

    python contrib/numeric_endings.py --audit      the patterns, measured
    python contrib/numeric_endings.py              write the plan's two lists

## Why a second pass over ground `uncarried_endings.py` already swept

`contrib/uncarried_endings.py` returned 6,674 names on 2026-08-23 by taking the endings
`data/suffixes.txt` cannot express straight off the published tables. It is limited in exactly
one way: **it can only ask about an ending somebody has already published.** An ending that
carries a number is really a family, and the tables hold whichever members happened to ship.

Measured over two-segment uncarried endings on 2026-08-23:

    88,959 distinct NUMERIC ending patterns, heading 889,050 published names

    _#n_#n      106,797     _v#_g~#   16,339     _v#_s~#   16,288     _#_#      12,360
    _v#_cm       12,168     _#_g~#    11,381     _#_s~#     8,781     _f#ac#_#   6,469
    _#_thermalmap 5,037     _b#_#      4,280     _m#_v#     4,018     _ads_#     3,194

`_#n_#n` alone heads 106,797 names. Every one of those is a two-axis numbered family, and the
tables hold the members that shipped in something somebody has already dumped.

So this replaces each number run with `#` and puts **every index in the measured range** back,
composing family members that appear in no table. It is the numbered-grid idea (METHODS.md
method 4) applied to the ending vocabulary rather than to whole names.

The one caution, learned the same day: `contrib/anim_transitions.py` composed two *word*
vocabularies the same way and returned 1 name a game -- the unobserved pairings were unobserved
because the state machine forbids them. Numbers are different: a family numbered 00..07 in one
map is numbered 00..23 in another, and nothing forbids the index.
"""

import argparse
import collections
import pathlib
import re
import sys

# Walk up to the repository rather than counting parents: a fixed count is right in
# contrib/ and wrong once `submit` files this under scripts/contributed/, where it
# resolves to a scripts/scripts that has never existed. scripts/README.md.
ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = ["fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
          "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2"]

DIGITS = re.compile(r"\d+")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--segments", type=int, default=2)
    parser.add_argument("--patterns", type=int, default=60,
                        help="how many numeric ending patterns to expand")
    parser.add_argument("--limit", type=int, default=48,
                        help="how far to count in each numeric slot")
    parser.add_argument("--game", default=None)
    args = parser.parse_args()

    import snapshot

    carried = {line.strip() for line in (ROOT / "data" / "suffixes.txt")
               .read_text(encoding="utf-8").splitlines() if line.strip()}
    names = snapshot.table_names(*TABLES) + snapshot.confirmed_names()

    patterns = collections.Counter()
    widths = collections.defaultdict(collections.Counter)
    for name in names:
        pieces = name.split("_")
        if len(pieces) <= args.segments:
            continue
        ending = "_" + "_".join(pieces[-args.segments:])
        if ending in carried or "." in ending or not DIGITS.search(ending):
            continue
        shape = DIGITS.sub("#", ending)
        patterns[shape] += 1
        for run in DIGITS.findall(ending):
            widths[shape][len(run)] += 1

    if args.audit:
        print(f"{len(patterns)} numeric patterns heading {sum(patterns.values())} names")
        for shape, count in patterns.most_common(25):
            print(f"  {count:7}  {shape}")
        return

    endings = set()
    for shape, _ in patterns.most_common(args.patterns):
        slots = shape.count("#")
        if slots == 0 or slots > 2:
            continue
        width = widths[shape].most_common(1)[0][0]
        span = range(args.limit if slots == 2 else args.limit * 4)
        if slots == 1:
            for index in span:
                endings.add(shape.replace("#", str(index).zfill(width)))
        else:
            for first in span:
                for second in span:
                    endings.add(shape.replace("#", str(first).zfill(width), 1)
                                .replace("#", str(second).zfill(width), 1))

    # The cores: a published name with the same number of trailing segments removed.
    source = names
    if args.game:
        folder = ROOT / "all_names" / args.game.lower()
        source = []
        for path in sorted(folder.glob("*.txt")) if folder.exists() else []:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                _, _, value = line.strip().partition(",")
                if value:
                    source.append(value)
        source += snapshot.confirmed_names()

    cores = set()
    for name in source:
        pieces = name.split("_")
        if len(pieces) > args.segments:
            core = "_".join(pieces[:-args.segments])
            if len(core) >= 8:
                cores.add(core)

    (ROOT / "contrib" / "num_cores.txt").write_text(
        chr(10).join(sorted(cores)) + chr(10), encoding="utf-8")
    (ROOT / "contrib" / "num_ends.txt").write_text(
        chr(10).join(sorted(endings)) + chr(10), encoding="utf-8")
    print(f"{len(cores)} cores x {len(endings)} composed endings "
          f"= {len(cores) * len(endings):,} candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
