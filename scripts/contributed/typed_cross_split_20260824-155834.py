r"""The typed cross with its two knobs separated -- wide decorations, shallow stripping.

    python contrib/typed_cross_split.py --write-plans plans/tcs
    bin\windows\confirm_plan.exe plans/tcs.xanim.txt --size

## The flaw this fixes

`typed_cross.py` calls `decorations()` twice with the **same** `(depth, begins, ends)`:

    heads, tails             = decorations(mine,   depth, begins, ends)   # the plan's columns
    their_heads, their_tails = decorations(theirs, depth, begins, ends)   # used to STRIP

Those two uses pull in opposite directions. The first is *reach* -- every beginning and ending our
names are measured to wear, and more is strictly better. The second is *stripping* -- the longest
decoration that matches gets cut off the external name, and what survives is the core being
borrowed. Widen it and there is less middle left to borrow.

METHODS.md §18 records the symptom without naming the cause: *"the cores shrink as the lists widen
-- deeper stripping leaves less middle -- so the two move against each other and there is a width
past which it stops. Nobody has found it yet."* The two move against each other **because one flag
drives both**, and no width finds the ceiling because the ceiling is an artefact of the coupling.

Measured on the Black Ops 3 manifests, 2026-08-24 (`contrib/measure_core_collapse.py`):

| type | cores at depth 3, 250x1200 | at depth 6, 8000x50000 | lost |
|---|---|---|---|
| image | 10,121 | 6,206 | -39% |
| material | 4,438 | 2,461 | -45% |
| xmodel | 1,456 | 797 | -45% |
| **xanim** | **2,268** | **883** | **-61%** |

`xanim` is the type METHODS says leads consistently, is the least-named type in both games (68.9%
and 64.0%), and is the one Black Ops 3 ships most of -- and running the widest configuration threw
away 61% of its borrowed vocabulary to buy ending-list reach.

## What this does instead

Two independent sets of knobs. `--depth/--begins/--ends` size **our** decorations, which become the
plan's columns; `--strip-*` size **theirs**, which do the cutting. Defaults keep our side wide and
their side at the narrow depth-3 setting that preserves the most core.

That is not a wider search than the widest one already run. It is the same width pointed at 2.57x
the xanim vocabulary -- and 1,385 of those cores cannot be expressed by the coupled version at any
setting, because widening to reach them is what destroys them.
"""
import argparse
import collections
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

from typed_cross import TYPES, cores, decorations, ours


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=os.path.join("borrowed", "bo3_assetlist.txt"),
                        help="a `type,name` manifest from harvest_bo3_assetlist.py --typed")
    parser.add_argument("--write-plans", required=True, metavar="PREFIX")

    # Our decorations: the plan's columns. Wider is strictly more reach.
    parser.add_argument("--depth", type=int, default=6)
    parser.add_argument("--begins", type=int, default=8000)
    parser.add_argument("--ends", type=int, default=50000)

    # Their decorations: the stripping. Wider is strictly less core, so this stays narrow.
    parser.add_argument("--strip-depth", type=int, default=3)
    parser.add_argument("--strip-begins", type=int, default=250)
    parser.add_argument("--strip-ends", type=int, default=1200)

    parser.add_argument("--kind", help="only this type")
    options = parser.parse_args(argv)

    external = collections.defaultdict(set)
    with open(options.source, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            kind, _, name = line.partition(",")
            name = name.strip().strip('"').replace("\\", "/").lower()
            kind = kind.strip().lower()
            if name and kind in TYPES:
                external[kind].add(name)

    if not external:
        raise SystemExit(
            "%s carries no `type,name` rows.\n"
            "Regenerate it with `python scripts/harvest_bo3_assetlist.py --typed`."
            % options.source
        )

    for kind, table in sorted(TYPES.items()):
        if options.kind and kind != options.kind:
            continue
        theirs = external.get(kind)
        if not theirs:
            continue

        mine = ours(kind, table)
        heads, tails = decorations(mine, options.depth, options.begins, options.ends)

        their_heads, their_tails = decorations(
            theirs, options.strip_depth, options.strip_begins, options.strip_ends)
        stems = sorted(cores(theirs, their_heads, their_tails) - mine)

        base = "%s.%s" % (options.write_plans, kind)
        for suffix, values in (("begins", heads), ("stems", stems), ("ends", tails)):
            with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
                handle.write("\n".join(values) + "\n")

        with open("%s.txt" % base, "w", encoding="utf-8") as handle:
            handle.write(
                "# Written by contrib/typed_cross_split.py. Regenerate rather than editing.\n"
                "#\n"
                "# %s cores from an external corpus, under the beginnings and endings OUR %s\n"
                "# names wear. The two sizings are independent: our decorations are wide\n"
                "# (%d x %d, depth %d) because that is reach, and their stripping is narrow\n"
                "# (%d x %d, depth %d) because that is what preserves the core being borrowed.\n"
                "\n"
                "label: %s cores borrowed wide, stripped shallow\n"
                "begin: @%s.begins.txt\n"
                "stem:  @%s.stems.txt\n"
                "end:   @%s.ends.txt\n"
                "bare:  no\n" % (
                    kind, kind,
                    options.begins, options.ends, options.depth,
                    options.strip_begins, options.strip_ends, options.strip_depth,
                    kind, base, base, base)
            )

        print("%-9s ours %s   theirs %s -> %s core(s)   %s begin x %s end   %s candidates"
              % (kind, format(len(mine), ","), format(len(theirs), ","), format(len(stems), ","),
                 format(len(heads), ","), format(len(tails), ","),
                 format(len(heads) * len(stems) * len(tails), ",")))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
