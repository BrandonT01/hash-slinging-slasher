"""Uncarried endings, crossed with cores cut at EVERY segment boundary.

    python contrib/uncarried_endings_allboundary.py                     write the two lists
    python contrib/uncarried_endings_allboundary.py --audit             rank the uncarried endings
    python contrib/uncarried_endings_allboundary.py --sound-pass        the sound half
    python contrib/uncarried_endings_allboundary.py --top 100000        how many endings to carry

## What this changes, and why it is the whole point

This is method 25 in METHODS.md -- *all-boundary cores* -- rebuilt. It is not a new method. It
is a fix to how every ending sweep in this repository builds its cores, and it was measured as
the single most productive change of 2026-08-23.

Every ending sweep here, `uncarried_endings` included, built its cores by removing **exactly as
many trailing segments as the ending has**. A two-segment ending could therefore only ever be
offered to a name cut two segments from its end. That restriction is arbitrary -- there is no
reason a core sitting five segments deep in one name should not wear a two-segment ending
borrowed from another -- and it was costing most of the yield.

Cutting every known name at *every* segment boundary instead. Measured by GoastcraftHD,
2026-08-23, both games together:

    all-boundary cores x  20,000 endings          602 names
    all-boundary cores x 100,000 endings        2,553 names
    all-boundary cores x 300,000 endings        1,470 names

against **2,065** for the depth-matched sweep at 200,000 endings -- more names on five times
fewer endings. Repeated at the other depths, both games: 1 segment 316, 3 segments 1,523,
4 segments 381. On sound, which breaks at path separators as well as underscores, 839,743 cores
against 100,000 uncarried sound endings returned **1,746 in one pass** -- more than the entire
depth-matched sound sweep (1,385) had returned across six.

The lesson generalises past this method, and is worth carrying to any cross product here:

    The ending list was never the binding constraint. The core list was.

The two multiply. Widening the endings five-fold over the wide core list quadrupled the yield,
where widening them over the narrow core list had gone flat. When a cross product underperforms,
work out which of the three lists is actually restricting it before widening whichever one is
easiest to widen.

## Provenance

The depth-matched ancestor is `scripts/contributed/uncarried_endings_20260823-040620.py`. The
all-boundary change was made after 04:06 on 2026-08-23 and documented in PR #437, but no
submission from 04:06 onward carried a `.py` file, so the code implementing the project's
highest-yield measured change did not exist anywhere. This is that code, rebuilt from the
measurements in #437. CLAUDE.md section 7: always pass `--script`, or the method dies with the
session.

## The gap it is aimed at

`data/suffixes.txt` carries 4,629 endings and `derive_lists.py` reports what its ceiling cuts.
What it cuts is not a tail: 178,016 distinct uncarried endings heading 620,830 published names,
28% of the published corpus ending in something no generator here can put on a name. The sound
half is larger -- `data/sound.suffixes.txt` carries 2,890, and 79% of published sound names end
in something it cannot express. Re-measuring cannot lift a cap; this takes what the cap threw
away.
"""

import argparse
import collections
import pathlib
import sys

# Walk up until the repository is found, rather than counting parents. A fixed count is
# correct in contrib/ and wrong once `submit` files this under scripts/contributed/,
# where it would resolve to a scripts/scripts that has never existed. scripts/README.md.
ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = ["fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
          "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2"]

# Sound is a separate pass with a separate vocabulary (CLAUDE.md section 5), and its ending list
# is capped the same way.
SOUND_TABLES = ["fnv1a_xsounds", "fnv1a_xsounds_v2",
                "fnv1a_soundbanks_aliases", "fnv1a_soundbanks_aliases_v2"]


def all_boundary_cores(name, min_core, sound):
    """Every prefix of `name` that ends on a segment boundary.

    This is the change. The depth-matched version yielded exactly one core per name -- the one
    sitting `--segments` segments from the end. This yields one per boundary, so a core that is
    five segments deep in one name becomes available to wear a two-segment ending from another.

    Sound names break at path separators and at the dot before their tail as well as at
    underscores, so a sound path contributes cores at every one of those.
    """
    # Black Ops 4 sound names keep their BACKSLASHES and their id is the hash of exactly that
    # (CLAUDE.md section 5), while Cold War sound paths fold to forward slashes. Both separators
    # are listed so this is correct for either game -- without the backslash every Black Ops 4
    # directory boundary is invisible and the core list collapses to the basename.
    seps = "_/" + chr(92) + "." if sound else "_"
    for i, ch in enumerate(name):
        if ch in seps and i >= min_core:
            yield name[:i]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true",
                        help="just rank the uncarried endings and stop")
    parser.add_argument("--top", type=int, default=100000,
                        help="how many of the commonest uncarried endings to carry. 100,000 is "
                             "the measured sweet spot: 20,000 gave 602 names and 300,000 gave "
                             "1,470, against 2,553 here")
    parser.add_argument("--min-core", type=int, default=8,
                        help="ignore cores shorter than this; short cores are noise")
    parser.add_argument("--sound-pass", action="store_true",
                        help="measure the SOUND tables against data/sound.suffixes.txt instead")
    parser.add_argument("--sounds", action="store_true",
                        help="keep dotted (sound) endings in a non-sound pass. Off by default: "
                             "CLAUDE.md section 5, a sound ending tried against a model id can "
                             "only ever be a coincidence")
    parser.add_argument("--segments", type=int, default=2,
                        help="how many trailing segments count as an ENDING when measuring the "
                             "gap. This no longer constrains the cores -- that is the point. "
                             "Yield by depth, both games: 1 seg 316, 2 seg 2,553, 3 seg 1,523, "
                             "4 seg 381")
    parser.add_argument("--game", default=None,
                        help="take the cores only from names this game is known to use")
    parser.add_argument("--confirmed-only", action="store_true",
                        help="cores that exist ONLY in findings/ and the merged submissions -- "
                             "156,178 non-sound and 319,592 sound cores occur nowhere in the "
                             "published tables, so no ending sweep has ever crossed them. "
                             "Measured 746 names, and 583 on the sound side")
    parser.add_argument("--published-only", action="store_true",
                        help="skip the confirmed names entirely")
    args = parser.parse_args()

    import snapshot

    sound = args.sound_pass
    ending_list = "sound.suffixes.txt" if sound else "suffixes.txt"
    carried = {line.strip() for line in (ROOT / "data" / ending_list)
               .read_text(encoding="utf-8").splitlines() if line.strip()}

    published = snapshot.table_names(*(SOUND_TABLES if sound else TABLES))
    confirmed = [] if args.published_only else snapshot.confirmed_names()
    names = published + confirmed

    def ending_of(name):
        """The last N underscore segments of a name, or None if it is too short to have them."""
        pieces = name.split("_")
        if len(pieces) <= args.segments:
            return None
        return "_" + "_".join(pieces[-args.segments:])

    counted = collections.Counter()
    for name in names:
        ending = ending_of(name)
        if not ending or ending in carried:
            continue
        if not (args.sounds or sound) and "." in ending:
            continue
        counted[ending] += 1

    # The cores. Every name cut at every boundary -- this is the change.
    core_source = names
    if args.confirmed_only:
        # New material reopens ground properly; re-measuring the lists never does. The corpus
        # grew ~24,000 names on 2026-08-23 and those cores have never met the ending vocabulary.
        core_source = confirmed
    elif args.game:
        core_source = []
        folder = ROOT / "all_names" / args.game.lower()
        for path in sorted(folder.glob("*.txt")) if folder.exists() else []:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                _, _, value = line.strip().partition(",")
                if value:
                    core_source.append(value)
        core_source += confirmed

    published_cores = set()
    if args.confirmed_only:
        for name in published:
            published_cores.update(all_boundary_cores(name, args.min_core, sound))

    cores = set()
    for name in core_source:
        cores.update(all_boundary_cores(name, args.min_core, sound))
    if args.confirmed_only:
        cores -= published_cores

    print(f"{len(carried)} carried endings, {len(names)} names "
          f"({len(published)} published + {len(confirmed)} confirmed)", file=sys.stderr)
    print(f"{len(counted)} uncarried endings at {args.segments} segment(s), "
          f"heading {sum(counted.values())} names", file=sys.stderr)

    if args.audit:
        for ending, count in counted.most_common(40):
            print(f"  {count:6}  {ending}")
        return

    endings = [ending for ending, _ in counted.most_common(args.top)]
    stem = "sound_" if sound else ""
    ends_path = ROOT / "contrib" / f"ab_{stem}ends.txt"
    cores_path = ROOT / "contrib" / f"ab_{stem}cores.txt"
    ends_path.write_text(chr(10).join(endings) + chr(10), encoding="utf-8")
    cores_path.write_text(chr(10).join(sorted(cores)) + chr(10), encoding="utf-8")
    print(f"{len(endings)} endings x {len(cores)} all-boundary cores "
          f"-> {len(endings) * len(cores):,} candidates", file=sys.stderr)
    print(f"wrote {ends_path.name} and {cores_path.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
