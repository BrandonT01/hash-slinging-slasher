"""Sound files rebuilt from the seed vocabulary that was in the tables all along.

    python contrib/sound_takes.py --game BLKOPS04 --pool sound_asset
    python contrib/sound_takes.py --game BLKOPSCW --pool sound_asset

## The finding this rests on

`all_names/<game>/<pool>.txt` is what every sound method here seeds from, and for the sound pools
it is almost empty. It is not that the names are unknown -- they are in the published tables. They
are simply not filed under either game, because these sounds live in SAB files the loader never
opens, so the pools had to be added by hand and their ids injected.

Hashing every published sound name and keeping what lands in each pool recovers this, 2026-08-23:

    game       pool           ids     all_names   recovered
    BLKOPS04   sound_asset  79,263         172       5,977   (unfolded)
    BLKOPS04   sound_alias  50,043       8,105      17,341
    BLKOPSCW   sound_asset  97,217         148      39,199   (folded)
    BLKOPSCW   sound_alias  50,890      24,733      16,589

**Cold War sound methods have been seeding from 148 names while 39,199 sat in the tables** -- a
265x difference. That is most of why this ground keeps returning little; it was never the method.

The two games hash these differently and it is not a detail:

    BLKOPS04 sound_asset   7,470 hits unfolded, 3 folded      -> fold: no
    BLKOPSCW sound_asset  39,199 hits folded, 31,845 unfolded  -> fold: yes

## The shape, once you can see the corpus

Sounds ship as numbered takes -- `chicken_00`, `chicken_01`, `split_tear_08` -- and the tables have
caught only some of each run. Peeling the number off a known sound and letting the engine put every
index back on is a cross product, so this writes a plan rather than printing names.
"""

import argparse
import collections
import pathlib
import re
import sys

# Walk up to the repository rather than counting parents: a fixed count is right in
# contrib/ and wrong once `submit` files this under scripts/contributed/, where it
# resolves to a scripts/scripts that has never existed. scripts/README.md.
ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

TABLES = ["fnv1a_xsounds", "fnv1a_xsounds_v2", "fnv1a_soundbanks_aliases",
          "fnv1a_soundbanks_aliases_v2", "fnv1a_english_xsounds", "bo3_sab", "bo2_sab"]

NUMBERED = re.compile(r"^(.*?)(\d+)$")


def recover(game, pool, unfolded):
    """Every published name whose hash lands in this game's pool."""
    import snapshot

    snap = snapshot.read(str(ROOT / "snapshots" / f"{game.lower()}.ids"))
    index = snap.pools.index(pool)
    records = snap.records.items() if isinstance(snap.records, dict) else snap.records
    wanted = {identifier for identifier, kind in records if kind == index}

    names = snapshot.table_names(*TABLES) + snapshot.confirmed_names()
    hash_of = snapshot.fnv1a_nofold if unfolded else snapshot.fnv1a
    return sorted({name for name in names if hash_of(name) in wanted}), len(wanted)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game", default="BLKOPS04")
    parser.add_argument("--pool", default="sound_asset")
    parser.add_argument("--prefix", default=None, help="what to call the written lists")
    parser.add_argument("--top-tails", type=int, default=16,
                        help="keep only the commonest dotted tails; 62 of them cover a long "
                             "thin tail that multiplies the plan for nothing")
    parser.add_argument("--takes-only", action="store_true",
                        help="write just the numbered-take shape: path-up-to-the-number against "
                             "every index. This is the aimed half and is thousands of times "
                             "smaller than the full recombination")
    args = parser.parse_args()

    # Black Ops 4 SAB sound names keep their backslashes; every other pool folds.
    unfolded = args.game.upper() == "BLKOPS04" and args.pool == "sound_asset"
    prefix = args.prefix or f"{args.game.lower()}_{args.pool}"

    names, total = recover(args.game, args.pool, unfolded)
    print(f"{len(names)} seed names recovered from {total} ids "
          f"({'unfolded' if unfolded else 'folded'})", file=sys.stderr)
    if not names:
        sys.exit("nothing recovered -- check the pool name and the fold")

    # Keep only the commonest tails. The long thin tail of one-off tails multiplies the whole
    # plan and buys almost nothing: 16 of the 62 cover better than 99% of the corpus.
    counted = collections.Counter()
    for name in names:
        dot = name.lower().find(".")
        if dot != -1:
            counted[name.lower()[dot:]] += 1
    keep = {tail for tail, _ in counted.most_common(args.top_tails)}

    dirs, stems, takes, tails, widths = set(), set(), set(), set(), set()
    for name in (n.lower() for n in names):
        dot = name.find(".")
        core, tail = (name, "") if dot == -1 else (name[:dot], name[dot:])
        if tail:
            if keep and tail not in keep:
                continue
            tails.add(tail)

        pieces = re.split(r"[\/]", core)
        separator = "\\" if "\\" in core else "/"
        for cut in range(1, len(pieces)):
            dirs.add(separator.join(pieces[:cut]) + separator)

        stems.add(core)               # the whole path, to wear a different tail
        stems.add(pieces[-1])         # the basename, to wear a different directory

        match = NUMBERED.match(pieces[-1])
        if match and match.group(1):
            stems.add(match.group(1))
            whole = separator.join(pieces[:-1] + [match.group(1)])
            stems.add(whole)
            takes.add(whole)
            widths.add(len(match.group(2)))

    # A bare tail, plus every take index in the measured widths wearing every measured tail.
    # The widths are measured, not assumed: a run written _000 does not answer to _00.
    ends = set(tails)
    for width in sorted(widths) or {2}:
        for index in range(100 if width <= 2 else 200):
            number = str(index).zfill(width)
            for tail in tails:
                ends.add(number + tail)
    if not tails:                     # aliases carry no dotted tail at all
        ends = {str(i).zfill(w) for w in (sorted(widths) or [2]) for i in range(100)}

    if args.takes_only:
        dirs, stems = set(), takes
        ends = {str(i).zfill(w) + t
                for w in (sorted(widths) or [2]) for i in range(100 if w <= 2 else 200)
                for t in (tails or {""})}

    for suffix, values in (("dirs", dirs), ("stems", stems), ("ends", ends)):
        destination = ROOT / "contrib" / f"{prefix}_{suffix}.txt"
        destination.write_text(chr(10).join(sorted(values)) + chr(10), encoding="utf-8")
        print(f"{len(values):>8} -> contrib/{destination.name}", file=sys.stderr)

    print(f"\nfold: {'no' if unfolded else 'yes'}   game: {args.game}", file=sys.stderr)


if __name__ == "__main__":
    main()
