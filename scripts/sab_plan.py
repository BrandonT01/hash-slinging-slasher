"""`sabpaths` at plan scale: the whole directory x basename x tail product, not a sample of it.

    python scripts/sab_plan.py --write-plan plans/sab.txt
    bin\\windows\\confirm_plan.exe plans/sab.txt --game BLKOPS04 --size

Not a new idea. `scripts/contributed/sabpaths_20260821-085126.py` had this one, works out the
vocabulary carefully, and already seeds from `bo2_sab` and `bo3_sab`. What it could not do is ask
all of it.

## What is actually being fixed

`sabpaths` is a generator, so it emits candidates through a pipe at about a million a second. Its
run is on record: **36,351,762 candidates, 5 names** -- and it had to cap itself to finish at all.
The full product of the vocabulary it assembles is a hundred times that, and the product including
Black Ops 2's directories is over ten billion.

That is the whole change. Same vocabulary, same convention, same reasoning -- asked completely
rather than sampled, because `confirm_plan` runs a cross product on the engine instead of on a
pipe. Ten billion candidates is about ten seconds there.

`sound_asset` in Black Ops 4 is **70,878 unnamed of 79,263**, the largest single piece of unnamed
ground in either game, and this is the only shape that reaches it: a general pass composes
`beginning + stem + ending` from a 700-entry beginning list, and a Black Ops 4 sound name is a
five- or six-segment path that no such list can express.

## The one thing that must not be got wrong

Black Ops 4 SAB names keep their **backslashes**, and their ids are the hash of exactly that. The
plan sets `fold: no`. Folded, this matches nothing at all while looking perfectly healthy --
8,385 of 8,385 known names reproduce unfolded and 0 folded.
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT

# Everything that might hold a sound path, ours and the older titles'. `sabpaths` established that
# BO2 and BO3 are worth reading: BO3 shares 9.18% of stems with Black Ops 4, BO2 1.35% -- low
# rates against very large tables, which is exactly the trade a plan can afford and a pipe cannot.
SOURCES = (
    "bo2_sab",
    "bo3_sab",
    "bo2_ipak",
    "fnv1a_xsounds",
    "fnv1a_soundbanks_aliases",
    "fnv1a_english_xsounds",
)

# The encoding tails, measured by `sabpaths` across the 8,446 names it recovers: six cover 8,409
# of them. Kept explicit rather than measured again, so the two agree.
TAILS = (
    ".ln100.pc.snd",
    ".ll100.pc.snd",
    ".sn100.pc.snd",
    ".sl100.pc.snd",
    ".pn100.pc.snd",
    ".pl100.pc.snd",
)

# Numbered variants, which the recovered names carry constantly (`chicken_00`, `amb_birds_03`).
MOST_VARIANT = 24


def sab_vocabulary():
    """Directories and basenames from every source, spelled the way Black Ops 4 spells them."""
    directories = collections.Counter()
    basenames = collections.Counter()

    for table in SOURCES:
        for name in snapshot.table_names(table):
            name = name.strip().lower().replace("/", "\\")
            if not name or "\\" not in name:
                continue

            head, _, leaf = name.rpartition("\\")
            directories[head + "\\"] += 1

            # Everything from the first dot is an encoding tail, not part of the name.
            leaf = leaf.split(".")[0]
            # And a trailing `_07` is a variant index, which the tail list puts back.
            leaf = re.sub(r"_\d+$", "", leaf)
            if len(leaf) >= 3:
                basenames[leaf] += 1

    for name in snapshot.confirmed_names("sound_asset"):
        name = name.strip().lower()
        if "\\" not in name:
            continue
        head, _, leaf = name.rpartition("\\")
        directories[head + "\\"] += 1
        leaf = re.sub(r"_\d+$", "", leaf.split(".")[0])
        if len(leaf) >= 3:
            basenames[leaf] += 1

    return directories, basenames


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--directories", type=int, default=40000)
    parser.add_argument("--basenames", type=int, default=200000)
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    directories, basenames = sab_vocabulary()
    print(
        "directories %s, basenames %s"
        % (format(len(directories), ","), format(len(basenames), ",")),
        file=sys.stderr,
    )

    heads = [d for d, _ in directories.most_common(options.directories)]
    stems = [b for b, _ in basenames.most_common(options.basenames)]

    # A basename wears a variant index or none, then an encoding tail.
    tails = list(TAILS) + [
        "_%02d%s" % (index, tail) for index in range(MOST_VARIANT) for tail in TAILS
    ]

    plan_path = os.path.join(ROOT, options.write_plan)
    base = os.path.splitext(plan_path)[0]
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)

    written = {}
    for what, entries in (("dirs", heads), ("names", stems), ("tails", tails)):
        written[what] = base + ".%s.txt" % what
        open(written[what], "w", encoding="utf-8", newline="\n").write("\n".join(entries) + "\n")

    relative = lambda path: os.path.relpath(path, ROOT).replace("\\", "/")

    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by scripts/sab_plan.py. Regenerate rather than editing.\n"
            "#\n"
            "# `sabpaths`' vocabulary asked completely instead of sampled: %s directories x %s\n"
            "# basenames x %s tails. Its own run managed 36,351,762 candidates through a pipe.\n"
            "#\n"
            "# fold: no is not optional. Black Ops 4 SAB names keep their backslashes and their ids\n"
            "# are the hash of exactly that -- 8,385 of 8,385 known names reproduce unfolded, 0\n"
            "# folded. Folded this matches nothing while looking entirely healthy.\n\n"
            % (format(len(heads), ","), format(len(stems), ","), format(len(tails), ","))
        )
        handle.write("label: SAB paths, whole product\n")
        handle.write(
            "describe: every directory seen in any sound table crossed with every basename and "
            "every measured encoding tail, with and without a variant index, hashed unfolded\n\n"
        )
        handle.write("game: BLKOPS04\n\n")
        handle.write("begin: @%s\n\n" % relative(written["dirs"]))
        handle.write("stem: @%s\n\n" % relative(written["names"]))
        handle.write("end: @%s\n\n" % relative(written["tails"]))
        handle.write("bare: no\nfold: no\n")

    total = len(heads) * len(stems) * (len(tails) + 1)
    print(
        "\nwrote %s\n\nabout %s candidates.\n\n    bin\\windows\\confirm_plan.exe %s --size"
        % (relative(plan_path), format(total, ","), options.write_plan),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
