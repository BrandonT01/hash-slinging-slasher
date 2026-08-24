"""The mirror of the typed cross: borrow their DECORATIONS, keep our cores.

`typed_cross.py` takes external cores and dresses them in the beginnings and endings our names are
measured to wear. The mirror -- our cores wearing *their* decorations -- has never been tried, and
METHODS.md §1248 records that checking the mirror of a working method is how the best single pass
of the project was found.

There is a reason to expect it to reach something. Our decoration lists are measured on names we
already know, so a decoration our games use is in the list *if the names using it have been found*.
A decoration used in Black Ops 4 only on assets nobody has named yet is invisible to that
measurement -- and visible in Black Ops 3, which is Black Ops 4's direct predecessor on the same
engine from the same studio.

That is the same logic that makes `uncarried.py` productive, pointed at an external corpus.

This prints the measurement. It generates no candidates.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import typed_cross

SOURCE = os.path.join("borrowed", "bo3_assetlist.txt")


def load():
    external = collections.defaultdict(set)
    with open(SOURCE, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            kind, _, name = line.partition(",")
            name = name.strip().strip('"').replace("\\", "/").lower()
            kind = kind.strip().lower()
            if name and kind in typed_cross.TYPES:
                external[kind].add(name)
    return external


def main():
    external = load()

    for kind, table in sorted(typed_cross.TYPES.items()):
        theirs = external.get(kind)
        if not theirs:
            continue
        mine = typed_cross.ours(kind, table)

        # Wide, so "not carried" means genuinely absent rather than ranked off the end.
        our_h, our_t = typed_cross.decorations(mine, 4, 20000, 60000)
        their_h, their_t = typed_cross.decorations(theirs, 4, 20000, 60000)

        ours_t, ours_h = set(our_t), set(our_h)
        new_tails = [t for t in their_t if t not in ours_t]
        new_heads = [h for h in their_h if h not in ours_h]

        # The control: of their endings that we DO carry, how many? If the two corpora shared no
        # vocabulary at all, borrowing decorations across would be meaningless.
        shared = len(their_t) - len(new_tails)

        print("\n%s -- ours %s, theirs %s" %
              (kind, format(len(mine), ","), format(len(theirs), ",")))
        print("  their endings %s, of which we already carry %s (%.1f%%) and %s are new" % (
            format(len(their_t), ","), format(shared, ","),
            100.0 * shared / max(len(their_t), 1), format(len(new_tails), ",")))
        print("  their beginnings %s, %s new" %
              (format(len(their_h), ","), format(len(new_heads), ",")))
        print("  sample new endings:    %s" % ", ".join(new_tails[:12]))
        print("  sample new beginnings: %s" % ", ".join(new_heads[:8]))


if __name__ == "__main__":
    main()
