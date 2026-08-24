"""Does widening the lists destroy the cores it is meant to decorate?

`typed_cross.py` calls `decorations()` twice with the SAME (depth, begins, ends): once on our
names, where the result becomes the plan's `begin:`/`end:` columns, and once on the external
names, where the result is used to STRIP them down to cores. Those two uses pull in opposite
directions -- widening our lists adds reach, widening their stripping removes middle -- and the
method has no way to ask for one without the other.

METHODS.md §18 says the ceiling is unfound: *"the cores shrink as the lists widen ... so the two
move against each other and there is a width past which it stops. Nobody has found it yet."*

This prints the curve.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import typed_cross

SOURCE = os.path.join("borrowed", "bo3_assetlist.txt")


def load():
    external = {}
    with open(SOURCE, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            kind, _, name = line.partition(",")
            name = name.strip().strip('"').replace("\\", "/").lower()
            kind = kind.strip().lower()
            if name and kind in typed_cross.TYPES:
                external.setdefault(kind, set()).add(name)
    return external


def main():
    external = load()
    settings = [(3, 250, 1200), (4, 1500, 8000), (5, 4000, 25000), (6, 8000, 50000)]

    for kind, table in sorted(typed_cross.TYPES.items()):
        theirs = external.get(kind)
        if not theirs:
            continue
        mine = typed_cross.ours(kind, table)
        print("\n%s -- ours %s, theirs %s" %
              (kind, format(len(mine), ","), format(len(theirs), ",")))
        print("  %-22s %8s %8s %10s" % ("their stripping", "begins", "ends", "cores"))

        for depth, begins, ends in settings:
            their_h, their_t = typed_cross.decorations(theirs, depth, begins, ends)
            cores = typed_cross.cores(theirs, their_h, their_t) - mine
            our_h, our_t = typed_cross.decorations(mine, depth, begins, ends)
            print("  depth %d %5d x %-7d %8d %8d %10s   -> %s candidates" % (
                depth, begins, ends, len(our_h), len(our_t), format(len(cores), ","),
                format(len(our_h) * len(cores) * len(our_t), ",")))


if __name__ == "__main__":
    main()
