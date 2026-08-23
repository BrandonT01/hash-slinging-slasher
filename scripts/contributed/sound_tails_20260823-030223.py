"""`tails`, applied to the sound corpus nobody could see.

    python contrib/sound_tails.py --game BLKOPSCW
    python contrib/sound_tails.py --game BLKOPS04

Method 17 -- a known name with its last k characters replaced -- is one of the two best
measured here (1,151 names in 21 seconds a game). It seeds from `snapshot.confirmed_names()`,
which for the sound pools means **148 names in Cold War and 172 in Black Ops 4**, because these
sounds live in SAB files the loader never opens and were never filed under either game.

`contrib/sound_takes.py` recovers the real corpus by hashing the published sound tables into the
pool: **39,199 for Cold War, 5,977 for Black Ops 4**. This points method 17 at that instead.

One change to the shape, and it is the whole reason this is a separate script. A sound name is
`core` + `.dotted.tail`, and the tail is a closed vocabulary of about sixteen entries. Replacing
the last k characters of the *whole name* rewrites the tail into nonsense and asks the game about
`....sn` + junk. So the k characters are taken off the **core**, and the tail is put back on
whole: the ending list is `k characters x every measured tail`.

Cold War sound files are already measured closed to numbered takes (36,971 of 39,199 basenames end
in a number; that sweep returned 0) and to directory x basename recombination (0). This asks the
one thing those two cannot: a sound whose name differs from a real one inside the basename.
"""

import argparse
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789_"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--game", default="BLKOPSCW")
    parser.add_argument("--known", default=None, help="the recovered corpus to seed from")
    parser.add_argument("--lengths", default="1,2", help="how many core characters to replace")
    parser.add_argument("--top-tails", type=int, default=16)
    args = parser.parse_args()

    tag = args.game.lower()
    known = pathlib.Path(args.known) if args.known else (
        ROOT / "contrib" / ("cw_snd_known.txt" if tag == "blkopscw" else "bo4_snd_known.txt"))
    if not known.exists():
        sys.exit(f"{known} is missing -- run contrib/sound_takes.py for this game first")

    names = [line.strip().lower() for line in known.read_text(encoding="utf-8").splitlines()
             if line.strip()]

    counted = collections.Counter()
    for name in names:
        dot = name.find(".")
        if dot != -1:
            counted[name[dot:]] += 1
    tails = [tail for tail, _ in counted.most_common(args.top_tails)]

    lengths = [int(piece) for piece in args.lengths.split(",") if piece.strip()]

    stems = set()
    for name in names:
        dot = name.find(".")
        if dot == -1:
            continue
        core = name[:dot]
        for k in lengths:
            if len(core) > k:
                stems.add(core[:-k])

    ends = set()
    for k in lengths:
        run = [""]
        for _ in range(k):
            run = [piece + character for piece in run for character in ALPHABET]
        for piece in run:
            for tail in tails:
                ends.add(piece + tail)

    prefix = f"{tag}_sndtails"
    for suffix, values in (("stems", stems), ("ends", ends)):
        destination = ROOT / "contrib" / f"{prefix}_{suffix}.txt"
        destination.write_text(chr(10).join(sorted(values)) + chr(10), encoding="utf-8")
        print(f"{len(values):>8} -> contrib/{destination.name}", file=sys.stderr)
    print(f"{len(stems) * len(ends):,} candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
