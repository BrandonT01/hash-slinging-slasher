"""How much reach the 4,800-ending ceiling actually costs, measured on composed endings.

Reconnaissance, not a generator. It prints a number and an argument; it does not emit candidates.

    python scripts/suffix_chains.py

## The question it settles

METHODS.md carried `suffix_chains.py` as a candidate worth building, with this reasoning: endings
compose (`_01` + `_c`), `data/suffixes.txt` is capped at 4,800 *observed* endings, and
`derive_lists.py` reports thousands more measured and dropped past that ceiling — so rare
compositions are structurally absent and no pass can ever express them. The deciding measurement it
asked for was "how many pairwise compositions of the top 50 endings are already published but
missing from `data/suffixes.txt`".

**Measured 2026-08-21**, top 60 carried endings, against the 1,460,804 published names in
`fnv1a_ximages`, `fnv1a_xmaterials`, `fnv1a_xmodels` and `fnv1a_xanims`:

| | |
|---|---|
| compositions of the top 60 not carried | 3,384 |
| of those, actually ending a published name | **1,718** |
| published names they cover | **49,626** |

`_01_snow` ends 349 published names, `_02_b` 288, `_decal_a` 261, `_02_white` 239. The gap is real
and it is large.

## Why it was still not built, which is the useful half

**A missing ending is not the same as an unreachable name.** The general search composes
`beginning + stem + ending`, and the *stem* is an arbitrary piece of a name already known to be
real — so `mc/mtl_foo_01_snow` is reachable as stem `mc/mtl_foo_01` plus the carried ending
`_snow`, with nothing composed at all. The composition only buys anything where the intermediate
stem is *not* independently known, which is a far smaller set than 49,626 and is not measured by
the number above.

`reach.py` measures the thing that actually matters and reports 83.8-95.9% ending coverage per
table, which is consistent with most of this gap already being absorbed by stems. Its own warning
applies here in full: a high share does not predict yield, and **tuning lists until the number is
high is not the work**.

So this is recorded as *measured and declined* rather than built. If somebody does build it, the
honest version has to exclude compositions whose left half is already a known piece — otherwise it
re-finds what a general pass finds anyway, which is the mistake that turned "the best method in
the project, 1 per 810" into 0 new names on 2026-08-20.

Reads `data/suffixes.txt` and the tables. Writes nothing. Needs no game, network or snapshot.
"""
import collections
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

TABLES = ("fnv1a_ximages", "fnv1a_xmaterials", "fnv1a_xmodels", "fnv1a_xanims")

# How many of the carried endings to compose. The candidate note said 50; 60 is used here so the
# figure is not sitting exactly on the boundary it was specified at.
TOP = 60


def carried():
    path = os.path.join(_root, "data", "suffixes.txt")
    with open(path, encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip()}


def tail_counts(names, endings):
    """How many names each ending finishes, looked up by length rather than scanned."""
    by_length = collections.defaultdict(set)
    for ending in endings:
        by_length[len(ending)].add(ending)

    lengths = sorted(by_length)
    counts = collections.Counter()

    for name in names:
        for length in lengths:
            if length <= len(name) and name[-length:] in by_length[length]:
                counts[name[-length:]] += 1

    return counts


def main():
    endings = carried()
    names = []
    for table in TABLES:
        names.extend(name.strip().lower() for name in snapshot.table_names(table))

    print("endings carried: %d   published names measured: %d" % (len(endings), len(names)))

    ranked = [ending for ending, _ in tail_counts(names, endings).most_common(TOP)]

    compositions = {
        left + right
        for left in ranked
        for right in ranked
        if left + right not in endings
    }

    found = tail_counts(names, compositions)
    covered = sum(found.values())

    print("\ncompositions of the top %d endings not carried: %d" % (TOP, len(compositions)))
    print("of those, actually ending a published name:    %d" % len(found))
    print("published names they cover:                    %d" % covered)

    print("\nthe widest of them:")
    for composition, count in found.most_common(12):
        print("   %-26s %d names" % (composition, count))

    print(
        "\nBefore building a generator on this: the general search's *stem* is an arbitrary piece\n"
        "of a real name, so `foo_01_snow` is already reachable as stem `foo_01` + ending `_snow`.\n"
        "Only compositions whose left half is not itself a known piece buy anything. See the\n"
        "docstring, and reach.py, which measures the ceiling that actually binds."
    )


if __name__ == "__main__":
    main()
