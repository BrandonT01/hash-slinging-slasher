r"""The third of the corpus `heads` cannot see: name fronts that contain a directory slash.

    python contrib/heads_slash.py --length 4 --write-plan plans/heads4_slash.txt
    bin\windows\confirm_plan.exe plans/heads4_slash.txt --size
    bin\windows\confirm_plan.exe plans/heads4_slash.txt

## The gap

`scripts/tails.py --head` replaces a known name's first k characters with every k-character
string over an alphabet it measures off the corpus. That measurement is `alphabet_of`, and it
counts `name[-4:]` -- the characters names **end** in -- because the file was written for tails
and the head flag was added later as "the same cross product with the lists swapped".

Names do not begin the way they end. Measured 2026-08-24 over 958,424 published and confirmed
names:

    characters names end in, top 37     _e0lnar1tocsdim2gphw34byku6f5v7x89zjq   (alnum and _)
    characters names begin with         the same, plus  /  *  [  $

    names whose first 3 characters all lie inside the tail alphabet     65.3%
    names whose first 4 characters all lie inside the tail alphabet     64.1%
    names whose first 5 characters all lie inside the tail alphabet     62.2%

    blocked in the first four positions:   /  340,786 names    *  3,410    [  354    $  87

**One character costs 35.9% of the corpus.** `/` is the directory separator, and METHODS records
that material names are paths under twelve directories -- `mc/` alone heads 496,666 published
names. Every one of them, and every `wc/ clt/ splm/ vd/ mcs/ ei/ cltp/ vdd/ el/ mcp/ ec/ mcdp/`
name, has a slash inside its first four characters, so no `heads` run has ever been able to spell
one. `heads` returned 692 in a single pass on Cold War -- the best of that day -- while blind to a
third of the ground it was aimed at.

## Why the complement rather than the fix

The obvious repair is to widen the alphabet and re-run, and that is what `scripts/tails.py` now
does. But a run over the widened alphabet redoes everything the narrow one already covered: at
k=4 that is 1,874,161 of 2,085,136 beginnings, 90% of the work, for ground already swept.

So this writes the **complement** -- only those k-character beginnings carrying at least one
character the tail-measured alphabet lacks. At k=4 that is 210,975 beginnings against 2,085,136,
so the ground `heads` has never reached costs 10% of a full re-run.

Note `--head` semantics: the k-character strings are the *beginnings* and the stems are known
names with their heads cut off, so `bare: no` -- a bare stem would be a truncation, which is a
different method.
"""
import argparse
import collections
import itertools
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)
SHORTEST_STEM = 4


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {n.strip().lower().replace("\\", "/") for n in names if n.strip()}


def alphabets(names, size, floor):
    """The characters names end in, and the ones they begin with that those miss."""
    tail, head = collections.Counter(), collections.Counter()
    for name in names:
        for character in name[-4:]:
            tail[character] += 1
        for character in name[:4]:
            head[character] += 1
    carried = [c for c, _ in tail.most_common(size)]
    missing = [c for c, n in head.most_common() if c not in carried and n >= floor]
    return carried, missing


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--length", type=int, default=4)
    parser.add_argument("--alphabet", type=int, default=37, help="size of the tail-measured half")
    parser.add_argument("--floor", type=int, default=50000,
                        help="how many name fronts a missing character must block to be carried")
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    names = known_names()
    carried, missing = alphabets(names, options.alphabet, options.floor)
    print("known names: %s" % format(len(names), ","), file=sys.stderr)
    print("tail-measured: %s" % "".join(carried), file=sys.stderr)
    print("begins with, and the tail alphabet lacks: %s" % "".join(missing), file=sys.stderr)

    whole = carried + missing
    carried_set = set(carried)
    begins = [
        "".join(row)
        for row in itertools.product(whole, repeat=options.length)
        if not set(row) <= carried_set
    ]
    stems = sorted(
        {n[options.length :] for n in names if len(n) - options.length >= SHORTEST_STEM}
    )
    print(
        "beginnings carrying an uncarried character: %s of %s   stems: %s"
        % (
            format(len(begins), ","),
            format(len(whole) ** options.length, ","),
            format(len(stems), ","),
        ),
        file=sys.stderr,
    )

    base = os.path.splitext(options.write_plan)[0]
    for suffix, rows in (("begins", begins), ("stems", stems)):
        with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
            handle.write("\n".join(rows) + "\n")

    with open(options.write_plan, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by contrib/heads_slash.py. Regenerate rather than editing.\n"
            "#\n"
            "# Every known name with its first %d characters replaced, over the beginnings the\n"
            "# tail-measured alphabet cannot spell -- the %s that names start with and never end\n"
            "# with. 35.9%% of the corpus begins inside this set and no heads run has reached it.\n"
            "\n"
            "label: heads of length %d, slash-bearing beginnings\n"
            "begin: @%s.begins.txt\n"
            "stem:  @%s.stems.txt\n"
            "bare:  no\n"
            % (options.length, "".join(missing), options.length, base, base)
        )
    print(
        "\nwrote %s\nabout %s candidates."
        % (options.write_plan, format(len(begins) * len(stems), ",")),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
