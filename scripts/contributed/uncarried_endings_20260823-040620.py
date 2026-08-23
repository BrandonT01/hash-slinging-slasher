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

# Walk up to the repository rather than counting parents: a fixed count is right in
# contrib/ and wrong once `submit` files this under scripts/contributed/, where it
# resolves to a scripts/scripts that has never existed. scripts/README.md.
ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = ["fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
          "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2"]

# Sound is a separate pass with a separate vocabulary (CLAUDE.md §5), and its ending list is
# capped the same way: `data/sound.suffixes.txt` carries 2,890 endings, and 485,837 of 615,194
# published sound names -- 79% -- end in something it cannot express.
SOUND_TABLES = ["fnv1a_xsounds", "fnv1a_xsounds_v2",
                "fnv1a_soundbanks_aliases", "fnv1a_soundbanks_aliases_v2"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--top", type=int, default=3000,
                        help="how many of the commonest uncarried endings to carry")
    parser.add_argument("--min-core", type=int, default=8,
                        help="ignore cores shorter than this; short cores are noise")
    parser.add_argument("--sound-pass", action="store_true",
                        help="measure the SOUND tables against data/sound.suffixes.txt instead. "
                             "This is the sound half of the same gap and it is larger: 79% of "
                             "published sound names end in something the sound list cannot say")
    parser.add_argument("--sounds", action="store_true",
                        help="keep dotted (sound) endings. Off by default: sounds are a separate "
                             "pass with a separate vocabulary, and at three segments they "
                             "otherwise crowd out every ending the other four types use")
    parser.add_argument("--segments", type=int, default=1,
                        help="how many trailing underscore segments count as the ending. "
                             "1 measures 178,016 uncarried endings over 620,830 names; "
                             "2 measures 471,768 over 1,610,162, and its commonest are "
                             "animation transitions (_to_walk, _to_sprint, _offset_additive)")
    parser.add_argument("--game", default=None,
                        help="take the cores only from names this game is known to use. "
                             "Two-segment endings are numerous enough that the published "
                             "core list makes the plan unrunnable; this aims it instead")
    parser.add_argument("--published-only", action="store_true",
                        help="skip the confirmed names. CLAUDE.md §6 says to measure the "
                             "confirmed corpus too, not only the published tables -- the two "
                             "differ in exactly the ways that matter")
    args = parser.parse_args()

    import snapshot

    ending_list = "sound.suffixes.txt" if args.sound_pass else "suffixes.txt"
    carried = {line.strip() for line in (ROOT / "data" / ending_list)
               .read_text(encoding="utf-8").splitlines() if line.strip()}
    names = snapshot.table_names(*(SOUND_TABLES if args.sound_pass else TABLES))
    if not args.published_only:
        # The snowball: everything this machine and every merged submission has confirmed is a
        # new core and a new ending for the next pass. CLAUDE.md §7.
        names = names + snapshot.confirmed_names()

    def split(name):
        """A name as (core, ending), where the ending is the last N underscore segments."""
        pieces = name.split("_")
        if len(pieces) <= args.segments:
            return None, None
        return "_".join(pieces[:-args.segments]), "_" + "_".join(pieces[-args.segments:])

    counted = collections.Counter()
    for name in names:
        _, ending = split(name)
        if not ending or ending in carried:
            continue
        # Sound names carry a dotted tail and go in their own pass with their own vocabulary.
        # CLAUDE.md §5: a sound ending tried against a model id can only ever be a coincidence,
        # never a match -- and at three segments they otherwise dominate the ranking.
        if not (args.sounds or args.sound_pass) and "." in ending:
            continue
        counted[ending] += 1

    # The cores. Restricted to one game's own names when asked, because the two-segment
    # ending vocabulary is large enough that the published core list makes the plan unrunnable.
    core_source = names
    if args.game:
        core_source = []
        folder = ROOT / "all_names" / args.game.lower()
        for path in sorted(folder.glob("*.txt")) if folder.exists() else []:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                _, _, value = line.strip().partition(",")
                if value:
                    core_source.append(value)
        core_source += snapshot.confirmed_names()

    cores = set()
    for name in core_source:
        core, _ = split(name)
        if core and len(core) >= args.min_core:
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
