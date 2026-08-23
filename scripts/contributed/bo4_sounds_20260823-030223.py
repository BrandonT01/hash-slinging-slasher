"""Black Ops 4 sound files, rebuilt from the vocabulary Black Ops 4 itself uses.

    python contrib/bo4_sounds.py       write the three lists plans/bo4_snd.txt multiplies

## The vocabulary this starts from, and why it was not obvious

`sound_asset` in Black Ops 4 is the largest opportunity in either title -- 70,878 unnamed of
79,263. `all_names/blkops04/sound_asset.txt` holds only **172** names, which is far too thin to
seed anything, and it is easy to conclude from that the ground has no seed corpus.

It has one. The named ids are in the published tables; they are simply not filed under Black Ops 4
anywhere, because these sounds live in SAB files the loader never opens and the pool had to be
added at index 170 with its ids injected. Hashing every name in `fnv1a_xsounds`, `fnv1a_xsounds_v2`,
`bo3_sab` and `bo2_sab` **without folding backslashes** and keeping what lands in the pool recovers
**5,977 distinct names** -- 35x the seed corpus anybody has been working from.

    hashed unfolded, landing in BO4 sound_asset:  7,470
    hashed folded,   landing in BO4 sound_asset:      11

That ratio is the `--no-fold` rule from CLAUDE.md §5 re-confirmed from the other direction, and it
is why this must run `fold: no`.

## What the corpus is shaped like

    depth        3 seg 495   4 seg 1,522   5 seg 2,108   6 seg 1,474   7 seg 355
    directories  fly wpn amb zmb prj mpl veh uin phy exp chr pfx
    tails        .ln100.pc.snd (3,393)  .ll100.pc.snd  .sn100.pc.snd  .sl100.pc.snd  .pn100.pc.snd
    numbered     4,270 of 5,977 basenames end in _NN

That last line is the method. Sounds come in numbered takes, the game ships a run of them, and the
tables have caught only some of each run. Peeling the number off a known sound and letting the
engine put every index back on is a cross product of a few thousand stems against a few hundred
endings -- which is why this is a plan and not a generator printing names.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
KNOWN = ROOT / "contrib" / "bo4_snd_known.txt"

NUMBERED = re.compile(r"^(.*?)(\d+)$")


def recover():
    """Rebuild the seed corpus: every published name whose unfolded hash lands in the pool.

    This is the step that makes the method reproducible. Without it the next contributor sees
    the 172 names in all_names/ and concludes there is nothing to seed from.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    import snapshot                                          # noqa: E402  (path set above)

    snap = snapshot.read(str(ROOT / "snapshots" / "blkops04.ids"))
    index = snap.pools.index("sound_asset")
    records = snap.records.items() if isinstance(snap.records, dict) else snap.records
    wanted = {identifier for identifier, pool in records if pool == index}

    pool = snapshot.table_names("fnv1a_xsounds", "fnv1a_xsounds_v2", "bo3_sab", "bo2_sab")
    pool += snapshot.confirmed_names()
    found = sorted({name for name in pool if snapshot.fnv1a_nofold(name) in wanted})

    KNOWN.write_text(chr(10).join(found) + chr(10), encoding="utf-8")
    print(f"{len(found)} seed names -> contrib/bo4_snd_known.txt", file=sys.stderr)


def main():
    if "--recover" in sys.argv or not KNOWN.exists():
        recover()

    names = [line.strip().lower() for line in KNOWN.read_text(encoding="utf-8").splitlines()
             if line.strip()]

    dirs, stems, tails, widths = set(), set(), set(), set()

    for name in names:
        dot = name.find(".")
        if dot == -1:
            continue
        core, tail = name[:dot], name[dot:]
        tails.add(tail)

        pieces = core.split("\\")
        for cut in range(1, len(pieces)):
            dirs.add("\\".join(pieces[:cut]) + "\\")

        stems.add(core)                 # the whole path, to wear a different tail
        stems.add(pieces[-1])           # the basename, to wear a different directory

        # The numbered take: keep everything up to the digits, remember how wide they were.
        match = NUMBERED.match(pieces[-1])
        if match and match.group(1):
            stems.add(match.group(1))
            stems.add("\\".join(pieces[:-1] + [match.group(1)]))
            widths.add(len(match.group(2)))

    # Endings: a bare tail, and every numbered take wearing every tail. The widths are measured
    # off the corpus rather than assumed -- a run written _000 does not answer to _00.
    ends = set(tails)
    for width in sorted(widths) or {2}:
        for index in range(100 if width <= 2 else 200):
            number = str(index).zfill(width)
            for tail in tails:
                ends.add(number + tail)

    for filename, values in (("bo4_snd_dirs.txt", dirs),
                             ("bo4_snd_stems.txt", stems),
                             ("bo4_snd_ends.txt", ends)):
        (ROOT / "contrib" / filename).write_text(
            chr(10).join(sorted(values)) + chr(10), encoding="utf-8")
        print(f"{len(values):>8} -> contrib/{filename}", file=sys.stderr)


if __name__ == "__main__":
    main()
