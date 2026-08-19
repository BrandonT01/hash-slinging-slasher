"""How much of the game the current lists can actually express, measured on names we already know.

    python scripts/reach.py            every pool, both list pairs
    python scripts/reach.py --missing  and the commonest beginnings/endings we do not carry

The general search builds a candidate as `beginning + stem + ending`, drawing the two ends from
`data/prefixes.txt` and `data/suffixes.txt`. Whatever those lists cannot express, no pass can find,
however long it runs -- and nothing in a run says so. A pass that reaches a tenth of the game looks
exactly like a pass that reaches all of it, only with fewer results, which is indistinguishable
from the game simply being nearly finished.

So this measures the ceiling rather than the yield. It takes names cod-name-db already publishes,
which are real names of the kind we are hunting, and asks what share of them the lists could
reconstruct. The unnamed ones are the same shape as the named ones, so the share is a fair estimate
of the best a pass could possibly do.

Reads the tables and `data/`. Needs no game, no network and no snapshot.
"""
import collections
import os
import sys

import snapshot

# Which lists serve which tables, mirroring how the searches choose. A sound pass reads the sound
# pair, everything else reads the general pair -- see `paths::SOUND_SUFFIX_LIST`.
GROUPS = [
    (
        "general",
        "prefixes.txt",
        "suffixes.txt",
        ["fnv1a_xmodels", "fnv1a_xmaterials", "fnv1a_ximages", "fnv1a_xanims"],
    ),
    (
        "sound",
        "sound.prefixes.txt",
        "sound.suffixes.txt",
        ["fnv1a_soundbanks_aliases", "fnv1a_english_xsounds", "fnv1a_xsounds"],
    ),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    path = os.path.join(ROOT, "data", name)
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def endings_of(name):
    """The one, two and three trailing segments a name carries, as the measurement cuts them."""
    base = name.rpartition("/")[2]
    parts = base.split("_")
    out = []

    if len(parts) >= 2:
        out.append("_" + parts[-1])
        out.append("_" + "_".join(parts[-2:]))
    if len(parts) >= 4:
        out.append("_" + "_".join(parts[-3:]))

    return out


def beginnings_of(name):
    """Every beginning the search could actually build this name with.

    Not just the three cuts the measurement counts. A candidate is `beginning + stem + ending`
    and the stem is any piece cut at a mark, so a deep path can be reached by a *short* beginning
    with a long stem just as well as by its whole directory. Counting only the canonical cuts
    said Black Ops 4's sound table was 15.5% reachable when much of the rest is reachable another
    way -- which would have sent someone off to fix a ceiling that was not there.
    """
    out = []
    for index, character in enumerate(name):
        if character in "_/":
            out.append(name[: index + 1])

    return out


def main(argv):
    show_missing = "--missing" in argv

    for title, prefix_file, suffix_file, tables in GROUPS:
        prefixes = set(load(prefix_file))
        endings = set(load(suffix_file))

        print("\n=== %s lists: %d beginnings, %d endings ===" % (title, len(prefixes), len(endings)))
        print("%-28s %9s %9s %9s" % ("table", "names", "beginning", "ending"))

        want_begin = collections.Counter()
        want_end = collections.Counter()

        for table in tables:
            names = snapshot.table_names(table)
            if not names:
                continue

            have_begin = have_end = 0
            for name in names:
                name = name.strip().lower().replace("\\", "/")
                if not name:
                    continue

                bs = beginnings_of(name)
                es = endings_of(name)

                if any(b in prefixes for b in bs):
                    have_begin += 1
                elif bs:
                    want_begin[bs[-1]] += 1

                if any(e in endings for e in es):
                    have_end += 1
                elif es:
                    want_end[es[0]] += 1

            total = max(len(names), 1)
            print("%-28s %9d %8.1f%% %8.1f%%"
                  % (table.replace("fnv1a_", ""), len(names),
                     100.0 * have_begin / total, 100.0 * have_end / total))

        if show_missing:
            print("\n  commonest beginnings not carried:")
            for key, count in want_begin.most_common(8):
                print("    %-42s %d names" % (key, count))
            print("  commonest endings not carried:")
            for key, count in want_end.most_common(8):
                print("    %-42s %d names" % (key, count))

    print("\nA low share is a ceiling, not a yield: it is the most a pass could find even if it")
    print("ran for ever. Raise it by measuring more (`derive_lists.py`) or by a method that does")
    print("not build names end-first at all -- see METHODS.md.")


if __name__ == "__main__":
    main(sys.argv[1:])
