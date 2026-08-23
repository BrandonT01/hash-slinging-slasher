"""Black Ops 4 sound files, spelled the way Black Ops 4 spells them, with their tails replaced.

    python contrib/sab_tails.py --length 3 --write-plan plans/sabtails3.txt
    bin/linux/confirm_plan plans/sabtails3.txt --size
    bin/linux/confirm_plan plans/sabtails3.txt

## The observation this is built on

`docs/HASHES.md` records that the twelve per-language sound tables and the legacy
`fnv1a_xsounds.csv` overlap in **exactly zero rows**, and reads that as two disjoint vocabularies.
It is also true that every one of those rows is stored under its *folded* hash -- forward slashes
-- because that is how the table spells it.

Black Ops 4's `sound_asset` ids are the hash of the name with its **backslashes left alone**
(AGENTS.md section 6). So a recording that both games hold is, from Black Ops 4's point of view,
completely unnamed: the table has the string, and the id nobody can match is the unfolded hash of
the same string with `\\` in it.

Measured before writing this, over all 2,301,143 names in the non-`_v2` tables:

    names whose UNFOLDED backslash hash is a BO4 sound_asset id : 8,574
    names whose FOLDED hash is a BO4 sound_asset id             :     3

and hashing the 923,354 sound-table names verbatim in backslash spelling against the *unnamed*
Black Ops 4 ids returns **18 names for no generation at all**.

## What this method does with it

Those 8,574 known Black Ops 4 sound files end in six tails and almost nothing else:

    .ln100.pc.snd 6,874   .ll100.pc.snd 945   .sn100.pc.snd 346
    .sl100.pc.snd   183   .pn100.pc.snd 169   .pl100.pc.snd  20

Cold War's own sound corpus wears different ones (`.ln75.pc.all.snd`, `.rn75.pc.<lang>.snd`), so
its 384,608 distinct **base paths** -- the name with its extension tail cut off -- are a
vocabulary of real recordings that Black Ops 4 has never been asked about in its own spelling.

So: take every base path in the corpus, cut its last *k* characters off, and let the engine
multiply what is left by every *k*-character string over the measured alphabet followed by each of
the six tails. That is `scripts/tails.py` (method 17) aimed at the one pool it has never been able
to reach, because `tails.py` folds and does not read the sound tables.

`k = 0` is the verbatim cross product and is contained in every larger `k`, so the 18 free names
above come out of the same pass.

## Why a plan and not a generator

It is a cross product, and AGENTS.md section 7 is explicit about those: a Python generator emits a
million candidates a second and the engine covers a hundred trillion in an hour. `--size` first.

## Measured, 2026-08-23

`k=3`: 153,103 stems x 303,918 endings, 46,530,910,657 candidates against 178,214 unnamed
Black Ops 4 ids -- **0 matched**. The 37-character alphabet and six tails were exhaustive at this
length, so the miss is not a size problem: the base-path vocabulary itself (drawn from the shared,
cross-title sound tables) does not share stems with Black Ops 4's own SAB paths closely enough for
a k=3 tail swap to bridge them. Confirmed BO4 `sound_asset` names actually recovered so far are
headed `vox/`, `zmb/`, `fly/`, `wpn/`, `amb/`, `blk/` -- game-specific zombies, Blackout and
emote content -- which is a different vocabulary than the Cold War-heavy base paths this script
draws stems from. Do not scale `--length` up from here; it costs 37x more candidates per step for
the same wrong stems. The next thing worth trying is building the stem list from confirmed BO4
`sound_asset` names and their directories specifically, once there are enough of them to be a
vocabulary rather than a handful of examples.
"""
import argparse
import collections
import glob
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import settings  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The extension tails Black Ops 4's own sound_asset names actually wear, measured off the 8,574
# table names whose unfolded hash lands in that pool. Ordered by how many carry each.
TAILS = (
    ".ln100.pc.snd",
    ".ll100.pc.snd",
    ".sn100.pc.snd",
    ".sl100.pc.snd",
    ".pn100.pc.snd",
    ".pl100.pc.snd",
)

# 37 characters covers 99.99% of the last four characters of a base path. The cost is
# `alphabet ** length`, so this is the knob that decides whether the plan is minutes or hours.
ALPHABET = 37

# Shorter than this and the stem is a fragment rather than a name with its tail replaced.
SHORTEST_STEM = 6


def base_paths():
    """Every sound-shaped name in the tables, backslashed, with its extension tail removed.

    Every non-`_v2` table is read rather than only the sound ones: the two games share assets, the
    tables are not perfectly sorted by type, and a name without a dotted extension is skipped here
    anyway, so reading widely costs nothing and cannot pull in the wrong shape.
    """
    folder = settings.tables_csv()
    out = set()

    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        if "_v2" in os.path.basename(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                _, _, name = line.partition(",")
                name = name.strip().lower()
                if not name:
                    continue
                name = name.replace("/", "\\")
                segment = name.rsplit("\\", 1)[-1]
                dot = segment.find(".")
                if dot < 0:
                    continue
                out.add(name[:len(name) - (len(segment) - dot)])

    return out


def alphabet_of(bases, size):
    """The characters base paths actually end in, commonest first. Measured, not assumed."""
    counted = collections.Counter()
    for base in bases:
        for character in base[-4:]:
            counted[character] += 1
    return [character for character, _ in counted.most_common(size)]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--length", type=int, default=3, help="characters of the base to replace")
    parser.add_argument("--alphabet", type=int, default=ALPHABET)
    parser.add_argument("--tails", type=int, default=len(TAILS), help="how many tails to carry")
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    if not 0 <= options.length <= 4:
        raise SystemExit("--length is 0 to 4; past that the ending list is larger than the corpus")

    bases = base_paths()
    print("base paths: %s" % format(len(bases), ","), file=sys.stderr)

    alphabet = alphabet_of(bases, options.alphabet)
    tails = TAILS[:options.tails]

    stems = {base[:len(base) - options.length] for base in bases}
    stems = sorted(stem for stem in stems if len(stem) >= SHORTEST_STEM)

    endings = [
        "".join(combination) + tail
        for combination in itertools.product(alphabet, repeat=options.length)
        for tail in tails
    ]

    plan = os.path.abspath(options.write_plan)
    stem_file = os.path.splitext(plan)[0] + ".stems.txt"
    ending_file = os.path.splitext(plan)[0] + ".endings.txt"

    with open(stem_file, "w", encoding="utf-8") as handle:
        handle.write("\n".join(stems) + "\n")
    with open(ending_file, "w", encoding="utf-8") as handle:
        handle.write("\n".join(endings) + "\n")

    relative = lambda path: os.path.relpath(path, ROOT).replace(os.sep, "/")

    with open(plan, "w", encoding="utf-8") as handle:
        handle.write(
            "label: black ops 4 sound tails, k=%d, unfolded\n"
            "describe: sound base paths from the tables, backslash-spelled the way Black Ops 4"
            " spells them, last %d characters replaced, each of the %d measured SAB tails"
            " appended\n\n"
            "stem: @%s\n"
            "end: @%s\n\n"
            "# `bare` is the empty beginning: with no `begin:` line this is what makes the\n"
            "# stem-and-ending product get built at all.\n"
            "bare: yes\n"
            "# Black Ops 4 SAB names keep their backslashes and their ids are the hash of exactly\n"
            "# that. Without this the pass matches nothing while looking perfectly healthy.\n"
            "fold: no\n"
            % (options.length, options.length, len(tails),
               relative(stem_file), relative(ending_file))
        )

    print("stems: %s" % format(len(stems), ","), file=sys.stderr)
    print("endings: %s" % format(len(endings), ","), file=sys.stderr)
    print("candidates: %s" % format(len(stems) * len(endings), ","), file=sys.stderr)
    print(plan)


if __name__ == "__main__":
    main(sys.argv[1:])
