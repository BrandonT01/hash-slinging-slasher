"""All-boundary cores against uncarried endings, aimed at Black Ops 4 `sound_asset`.

    python contrib/bo4_sound_allboundary.py            write the two lists
    python contrib/bo4_sound_allboundary.py --audit    rank the uncarried endings and stop

## Why this pool, and why this is not a dead end already

`sound_asset` in Black Ops 4 is the largest single opportunity in either title: **70,680 unnamed
of 79,263**. METHODS.md records the most expensive negative in the project against it -- 379
billion candidates for zero hits of any kind -- and that negative is real; it was independently
certified at 100.0% reconstruction by `bo4_sound_plumbing_check.py`.

But read what it closed. It swept **numbered takes** (peel the index off a known sound, put every
index back) and **directory x basename recombination** (a known basename under a different known
directory). Both are recombinations *within one segment depth*. Neither is this.

This is method 25 -- cores cut at **every** segment boundary -- crossed with the endings
`data/sound.suffixes.txt` structurally cannot express. A core five segments deep in one path gets
asked about wearing a two-segment ending from another. That relation has never been pointed at
this pool, so the standing negative does not cover it.

## Two things that make this different from the general sound pass

  - **The corpus is recovered, not read.** `all_names/blkops04/sound_asset.txt` holds 178 names.
    The pool's ids were injected from SAB files the loader never opens, so its named half is not
    filed under Black Ops 4 anywhere -- it is recovered by hashing the published tables into the
    pool *unfolded*, which returns **8,583**. That is method 21, and every sound method that
    seeded from `all_names/` was working from 2% of the available vocabulary.

  - **Backslashes, and no folding.** Black Ops 4 sound names keep their backslashes and their id
    is the hash of exactly that. Cores must therefore break at `\\` as well as at `_` and `.`,
    and the plan must run `fold: no`. Mixing Cold War's forward-slash paths into the core list
    contributes nothing here, so the corpus is restricted to what this pool actually holds.
"""

import argparse
import collections
import os
import pathlib
import sys

# Walk up until the repository is found, rather than counting parents. A fixed count is correct
# in contrib/ and wrong once `submit` files this under scripts/contributed/, where it would
# resolve to a scripts/scripts that has never existed. scripts/README.md.
ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

import snapshot

SOUND_TABLES = ["fnv1a_xsounds", "fnv1a_xsounds_v2",
                "fnv1a_soundbanks_aliases", "fnv1a_soundbanks_aliases_v2"]
SOUND_POOL = 170          # added at index 170, ids injected from the SAB files (CLAUDE.md §5)
SEPS = "_\\/."            # backslash first: it is the one that matters for this title


def recover(ids):
    """The named half of the pool, hashed out of the published tables unfolded (method 21)."""
    out = {}
    for name in set(snapshot.table_names(*SOUND_TABLES)) | set(snapshot.confirmed_names()):
        h = snapshot.fnv1a_nofold(name)
        if h in ids or (h & snapshot.ID_MASK) in ids:
            out[h] = name
    seed = ROOT / "all_names" / "blkops04" / "sound_asset.txt"
    if seed.exists():
        for line in seed.read_text(encoding="utf-8", errors="replace").splitlines():
            _, _, value = line.strip().partition(",")
            if value:
                out.setdefault(snapshot.fnv1a_nofold(value), value)
    return sorted({n.lower() for n in out.values()})


def all_boundary_cores(name, min_core):
    for i, ch in enumerate(name):
        if ch in SEPS and i >= min_core:
            yield name[:i]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--top", type=int, default=60000,
                        help="how many of the commonest uncarried endings to carry")
    parser.add_argument("--min-core", type=int, default=10)
    parser.add_argument("--segments", type=int, default=2,
                        help="how many trailing underscore segments count as an ENDING. This "
                             "does not constrain the cores -- that is the point of method 25")
    args = parser.parse_args()

    path = next((p for p in snapshot.snapshots()
                 if "blkops04" in os.path.basename(p).lower()), None)
    if not path:
        raise SystemExit("no Black Ops 4 snapshot found")

    snap = snapshot.read(path)
    ids = {aid for aid, pool in snap.records if pool == SOUND_POOL}
    names = recover(ids)
    print(f"pool {SOUND_POOL}: {len(ids)} ids, {len(names)} recovered, "
          f"{len(ids) - len(names)} unnamed", file=sys.stderr)

    carried = {line.strip() for line in
               (ROOT / "data" / "sound.suffixes.txt").read_text(encoding="utf-8").splitlines()
               if line.strip()}

    # Endings measured off this pool's own names, not off the mixed sound corpus. A Cold War
    # ending cannot help here -- the tails are this title's own (.ln100.pc.snd and friends).
    counted = collections.Counter()
    for name in names:
        pieces = name.split("_")
        if len(pieces) <= args.segments:
            continue
        ending = "_" + "_".join(pieces[-args.segments:])
        if ending not in carried:
            counted[ending] += 1

    print(f"{len(carried)} carried sound endings; {len(counted)} uncarried in this pool "
          f"heading {sum(counted.values())} of its names", file=sys.stderr)

    if args.audit:
        for ending, count in counted.most_common(30):
            print(f"  {count:6}  {ending}")
        return

    cores = set()
    for name in names:
        cores.update(all_boundary_cores(name, args.min_core))

    endings = [e for e, _ in counted.most_common(args.top)]
    (ROOT / "contrib" / "bo4snd_ends.txt").write_text(
        chr(10).join(endings) + chr(10), encoding="utf-8")
    (ROOT / "contrib" / "bo4snd_cores.txt").write_text(
        chr(10).join(sorted(cores)) + chr(10), encoding="utf-8")
    print(f"{len(endings)} endings x {len(cores)} all-boundary cores "
          f"-> {len(endings) * len(cores):,} candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
