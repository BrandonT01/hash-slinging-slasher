"""Names unreachable at BOTH ends: an uncarried beginning over an uncarried ending.

    python contrib/double_uncarried.py --game BLKOPS04

## Why this pair and not either half

Both halves are measured productive on 2026-08-23 and neither has been crossed with the other:

    uncarried endings   `contrib/uncarried_endings.py`   6,674 names across both games
    uncarried beginning `mcdp/`                          2,846 names on its own

`data/prefixes.txt` carries 700 beginnings and `data/suffixes.txt` 4,629 endings, and both are
caps rather than measurements -- `derive_lists.py` reports what its ceiling cut every run. A name
wearing an uncarried beginning AND an uncarried ending is unreachable twice over, and no pass in
this repository has ever been able to build one.

The general sweep over all 1,075 uncarried beginnings returned only 7 (see the dead ends table),
but that sweep used **bare stems and no endings at all** -- it asked only for names that are a
beginning plus a whole known core. This asks the other question.

The stems here are **middles**: a published name with its first and its last segment both removed,
so the piece that survives is the part that recombines.
"""

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = ["fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
          "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2"]


def leading(name):
    """The beginning a name measures as having: its first `/` or `_` delimited piece."""
    cut = len(name)
    for delimiter in ("/", "_"):
        position = name.find(delimiter)
        if position != -1:
            cut = min(cut, position + 1)
    return name[:cut] if cut < len(name) else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game", default="BLKOPS04")
    parser.add_argument("--begins", type=int, default=300)
    parser.add_argument("--ends", type=int, default=30000)
    parser.add_argument("--segments", type=int, default=2,
                        help="how many trailing segments count as the ending")
    args = parser.parse_args()

    import snapshot

    prefixes = {line.strip() for line in (ROOT / "data" / "prefixes.txt")
                .read_text(encoding="utf-8").splitlines() if line.strip()}
    suffixes = {line.strip() for line in (ROOT / "data" / "suffixes.txt")
                .read_text(encoding="utf-8").splitlines() if line.strip()}

    names = snapshot.table_names(*TABLES) + snapshot.confirmed_names()

    begin_counts, end_counts = collections.Counter(), collections.Counter()
    middles = set()

    for name in names:
        head = leading(name)
        if head and not any(head[:n] in prefixes for n in range(1, len(head) + 1)):
            begin_counts[head] += 1

        pieces = name.split("_")
        if len(pieces) > args.segments:
            tail = "_" + "_".join(pieces[-args.segments:])
            if tail not in suffixes and "." not in tail:
                end_counts[tail] += 1

        # The middle: first segment and last `segments` segments both removed.
        if head and len(pieces) > args.segments + 1:
            body = name[len(head):]
            body = "_".join(body.split("_")[:-args.segments])
            if len(body) >= 6:
                middles.add(body)

    begins = [b for b, _ in begin_counts.most_common(args.begins)]
    ends = [e for e, _ in end_counts.most_common(args.ends)]

    print(f"{len(begin_counts)} uncarried beginnings, {len(end_counts)} uncarried endings, "
          f"{len(middles)} middles", file=sys.stderr)

    tag = args.game.lower()
    for suffix, values in (("begins", begins), ("mids", sorted(middles)), ("ends", ends)):
        destination = ROOT / "contrib" / f"{tag}_dbl_{suffix}.txt"
        destination.write_text(chr(10).join(values) + chr(10), encoding="utf-8")
        print(f"{len(values):>8} -> contrib/{destination.name}", file=sys.stderr)
    print(f"{len(begins) * len(middles) * len(ends):,} candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
