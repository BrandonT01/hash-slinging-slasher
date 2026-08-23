"""Which uncarried beginnings are re-decorations of a vocabulary we already hold.

    python contrib/redecorations.py                  rank every uncarried beginning
    python contrib/redecorations.py --write NAME     write that beginning's stem cores

## The measurement this exists to make

`scripts/uncarried.py` finds beginnings the committed list cannot express, and the plan it writes
pairs each with cores taken from the published names that already use it. Run that way over 208
beginnings on 2026-08-22 it returned **5 names** -- because for a beginning whose namespace we
have already seen, its own cores are exactly the ones that are already named.

`mcdp/` on 2026-08-23 returned **2,846** from the same starting point, and the difference was one
number measured first:

    all 692 published `mcdp/` cores also occur under some other beginning   (692 of 692)

That makes `mcdp/` a **re-decoration**: not a namespace with a vocabulary of its own, but the
general material vocabulary wearing a different directory. For a re-decoration the right stem
list is the whole corpus, not the beginning's own cores -- which is why one returned 2,846 and
the other 5.

So the question worth asking of every uncarried beginning is not "how many names does it head"
but **"how much of its vocabulary is borrowed"**. This ranks them by exactly that, so a plan gets
aimed at the ones where the corpus is already holding the answer.

A beginning that scores low is the opposite case and a genuine dead end for this shape: it has
its own private vocabulary, so crossing it with the corpus buys nothing.
"""

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

TABLES = [
    "cod-name-db/csv/fnv1a_xmaterials.csv", "cod-name-db/csv/fnv1a_xmaterials_v2.csv",
    "cod-name-db/csv/fnv1a_ximages.csv", "cod-name-db/csv/fnv1a_ximages_v2.csv",
    "cod-name-db/csv/fnv1a_xmodels.csv",
    "cod-name-db/csv/fnv1a_xanims.csv", "cod-name-db/csv/fnv1a_xanims_v2.csv",
]


def published_names():
    for relative in TABLES:
        path = ROOT / relative
        if not path.exists():
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                _, _, name = line.strip().partition(",")
                if name:
                    yield name


def carried_prefixes():
    path = ROOT / "data" / "prefixes.txt"
    with path.open(encoding="utf-8", errors="replace") as handle:
        return {line.strip() for line in handle if line.strip()}


def leading_segment(name):
    """The beginning a name measures as having: its first `/` or `_` delimited piece."""
    cut = len(name)
    for delimiter in ("/", "_"):
        position = name.find(delimiter)
        if position != -1:
            cut = min(cut, position + 1)
    return name[:cut] if cut < len(name) else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", metavar="BEGINNING",
                        help="write the stem cores for this beginning and stop")
    parser.add_argument("--out", default="contrib/redecoration_cores.txt")
    parser.add_argument("--top", type=int, default=30, help="how many rows to print")
    parser.add_argument("--min-names", type=int, default=20,
                        help="ignore beginnings heading fewer published names than this")
    parser.add_argument("--write-lists", action="store_true",
                        help="write every uncarried beginning and the whole held vocabulary, "
                             "for a plan that crosses the two")
    args = parser.parse_args()

    carried = carried_prefixes()
    prefix_lengths = sorted({len(prefix) for prefix in carried}, reverse=True)

    names = list(published_names())
    print(f"{len(names)} published names, {len(carried)} carried beginnings", file=sys.stderr)

    # The vocabulary we already hold: every name with its longest carried beginning removed.
    vocabulary = set()
    for name in names:
        for length in prefix_lengths:
            if length < len(name) and name[:length] in carried:
                vocabulary.add(name[length:])
                break

    # Group the names whose own leading segment no cut of is carried.
    by_beginning = collections.defaultdict(list)
    for name in names:
        beginning = leading_segment(name)
        if not beginning:
            continue
        if any(beginning[:n] in carried for n in range(1, len(beginning) + 1)):
            continue
        by_beginning[beginning].append(name)

    if args.write_lists:
        begins = sorted(b for b, group in by_beginning.items() if len(group) >= 5)
        newline = chr(10)
        (ROOT / 'contrib' / 'uncarried_begins.txt').write_text(
            newline.join(begins) + newline, encoding='utf-8')
        (ROOT / 'contrib' / 'held_vocab.txt').write_text(
            newline.join(sorted(vocabulary)) + newline, encoding='utf-8')
        print(f'{len(begins)} beginnings, {len(vocabulary)} vocabulary cores', file=sys.stderr)
        return
        return

    if args.write:
        beginning = args.write
        cores = {name[len(beginning):] for name in by_beginning.get(beginning, [])}
        # The stems worth trying are the vocabulary we hold, minus what this beginning already
        # wears -- those are named already and would only be excluded downstream anyway.
        stems = sorted(vocabulary - cores)
        destination = ROOT / args.out
        with destination.open("w", encoding="utf-8") as handle:
            for stem in stems:
                handle.write(stem + "\n")
        print(f"{len(stems)} cores -> {args.out}", file=sys.stderr)
        return

    rows = []
    for beginning, group in by_beginning.items():
        if len(group) < args.min_names:
            continue
        cores = {name[len(beginning):] for name in group}
        borrowed = sum(1 for core in cores if core in vocabulary)
        rows.append((borrowed / len(cores), len(group), len(cores), borrowed, beginning))

    rows.sort(reverse=True)
    print(f"\n{'beginning':<34} {'names':>7} {'cores':>7} {'borrowed':>9} {'share':>7}")
    for share, count, cores, borrowed, beginning in rows[:args.top]:
        print(f"  {beginning:<32} {count:>7} {cores:>7} {borrowed:>9} {share:>6.0%}")
    print(f"\n{len(rows)} uncarried beginnings heading {args.min_names}+ names.")
    print("A high share means the corpus already holds its vocabulary: cross it with the whole")
    print("corpus. A low share means it has a private vocabulary and this shape will not reach it.")


if __name__ == "__main__":
    main()
