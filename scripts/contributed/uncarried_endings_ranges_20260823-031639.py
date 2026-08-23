"""Plan disjoint rank bands of endings the committed suffix list cannot express.

    python contrib/uncarried_endings_ranges.py --skip 3000 --top 3000
    bin/windows/confirm_plan.exe plans/uncarried-endings-3001-6000.txt

The first 3,000 uncarried endings were spent on 2026-08-23 and returned 110 Black Ops 4
and 136 Cold War names. The original generator could only widen that plan, which repeats
all of the spent ground. This version carries a rank offset so later passes are disjoint:
`--skip 3000 --top 3000` means ranks 3,001 through 6,000 and asks none of the first pass's
questions again.

Endings are ranked by how many published names wear them. Stems are every published name
with its final underscore segment removed. Both are seeded entirely from names already
known to be real.
"""

import argparse
import collections
import pathlib
import sys


def repository_root():
    """Find the repository from contrib/ or scripts/contributed/ after submission."""
    for parent in pathlib.Path(__file__).resolve().parents:
        if (parent / "scripts" / "snapshot.py").is_file():
            return parent
    raise SystemExit("could not find scripts/snapshot.py above this generator")


ROOT = repository_root()
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = [
    "fnv1a_xmaterials",
    "fnv1a_xmaterials_v2",
    "fnv1a_ximages",
    "fnv1a_ximages_v2",
    "fnv1a_xmodels",
    "fnv1a_xanims",
    "fnv1a_xanims_v2",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip", type=int, default=3000,
                        help="number of commonest uncarried endings already spent")
    parser.add_argument("--top", type=int, default=3000,
                        help="number of endings to carry after the skipped band")
    parser.add_argument("--min-core", type=int, default=8,
                        help="ignore cores shorter than this; short cores are noise")
    parser.add_argument("--audit", action="store_true",
                        help="print the selected ending band without writing a plan")
    args = parser.parse_args()

    if args.skip < 0 or args.top < 1:
        parser.error("--skip must be non-negative and --top must be positive")

    import snapshot

    carried = {
        line.strip()
        for line in (ROOT / "data" / "suffixes.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
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

    ranked = counted.most_common()
    selected = ranked[args.skip:args.skip + args.top]
    first_rank = args.skip + 1
    last_rank = args.skip + len(selected)

    print(f"{len(carried)} carried endings, {len(names)} published names", file=sys.stderr)
    print(f"{len(counted)} uncarried endings heading {sum(counted.values())} names",
          file=sys.stderr)
    print(f"selected ranks {first_rank:,}-{last_rank:,}: {len(selected)} endings",
          file=sys.stderr)

    if args.audit:
        for rank, (ending, count) in enumerate(selected, start=first_rank):
            print(f"{rank:7}  {count:6}  {ending}")
        return

    if not selected:
        raise SystemExit("the selected rank band is empty")

    tag = f"{first_rank}-{last_rank}"
    endings_path = ROOT / "contrib" / f"uncarried_ends_{tag}.txt"
    cores_path = ROOT / "contrib" / f"ending_cores_{tag}.txt"
    plan_path = ROOT / "plans" / f"uncarried-endings-{tag}.txt"

    endings_path.write_text(
        "\n".join(ending for ending, _ in selected) + "\n", encoding="utf-8"
    )
    cores_path.write_text("\n".join(sorted(cores)) + "\n", encoding="utf-8")
    plan_path.write_text(
        "\n".join([
            f"label: uncarried endings ranks {tag} over published cores",
            "describe: a disjoint rank band of real endings the committed suffix list cannot express",
            f"stem: @contrib/{cores_path.name}",
            f"end: @contrib/{endings_path.name}",
            "bare: yes",
            "fold: yes",
            "",
        ]),
        encoding="utf-8",
    )

    candidates = len(selected) * len(cores)
    print(f"{len(selected)} endings x {len(cores):,} cores -> {candidates:,} candidates",
          file=sys.stderr)
    print(plan_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
