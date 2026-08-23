"""The endings the committed list cannot express, against the cores that would wear them.

    python contrib/uncarried_endings.py                write the two lists
    python contrib/uncarried_endings.py --audit        just rank the uncarried endings
    python contrib/uncarried_endings.py --top 4000     how many endings to carry

## The gap

`data/suffixes.txt` carries **4,629** endings, and `derive_lists.py` reports what its ceiling
cuts. Measured against the published tables on 2026-08-23, what it cuts is not a tail:

    178,016 distinct uncarried endings, heading 620,830 published names

That is **28% of the published corpus ending in something no generator here can put on a name.**
The commonest are not exotic:

    _thermalmap 16,000   _moving 1,650   _jog 1,559   _swatch 1,370   _xmag 1,167
    _crouch 1,109        _fxsim 1,008    and a large `_NNn` family (_4n .. _51n)

## Why this is worth building rather than re-measuring

CLAUDE.md §8 is explicit that re-running `derive_lists.py` does not reopen ground -- it changes
what a search is *called* without changing what it can *reach*, and the ending list is capped, so
re-measuring cannot lift the cap. This does not re-measure. It takes the endings the cap threw
away and pairs them with the cores that already wear them elsewhere, which is the same shape that
made `mcdp/` return 2,846 on 2026-08-23: real vocabulary the lists structurally cannot express.

The stems are every published name with its own last segment removed, so a core that wears
`_c` in the tables can be asked about wearing `_thermalmap` here.
"""

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = ["fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
          "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--top", type=int, default=3000,
                        help="how many of the commonest uncarried endings to carry")
    parser.add_argument("--min-core", type=int, default=8,
                        help="ignore cores shorter than this; short cores are noise")
    args = parser.parse_args()

    import snapshot

    carried = {line.strip() for line in (ROOT / "data" / "suffixes.txt")
               .read_text(encoding="utf-8").splitlines() if line.strip()}
    names = snapshot.table_names(*TABLES)

    counted = collections.Counter()
    cores = set()
    for name in names:
        cut = name.rfind("_")
        if cut <= 0:
            continue
        ending = name[cut:]
        if ending not in carried:
            counted[ending] += 1
        core = name[:cut]
        if len(core) >= args.min_core:
            cores.add(core)

    print(f"{len(carried)} carried endings, {len(names)} published names", file=sys.stderr)
    print(f"{len(counted)} uncarried endings heading {sum(counted.values())} names",
          file=sys.stderr)

    if args.audit:
        for ending, count in counted.most_common(40):
            print(f"  {count:6}  {ending}")
        return

    endings = [ending for ending, _ in counted.most_common(args.top)]
    (ROOT / "contrib" / "uncarried_ends.txt").write_text(
        chr(10).join(endings) + chr(10), encoding="utf-8")
    (ROOT / "contrib" / "ending_cores.txt").write_text(
        chr(10).join(sorted(cores)) + chr(10), encoding="utf-8")
    print(f"{len(endings)} endings, {len(cores)} cores "
          f"-> {len(endings) * len(cores):,} candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
