"""The tails `tails.py` structurally cannot spell: the ones carrying a punctuation character.

    python contrib/symbol_tails.py --length 3 --write-plan plans/symtails.txt
    bin\\windows\\confirm_plan.exe plans/symtails.txt --size
    bin\\windows\\confirm_plan.exe plans/symtails.txt

`scripts/tails.py` replaces a known name's last *k* characters over the **37** commonest characters
names end in, and 37 is the right knob because the cost is `alphabet ** length`. Measured over the
1,522,215 names known here on 2026-08-23, those 37 spell the last three characters of 99.74% of
them -- so the cap is nearly free, which is exactly why nobody has looked at what it costs.

What it costs is not a random 0.26%. Names end in **49** distinct characters, and the twelve the
cap drops are one rare letter and every punctuation mark in the corpus:

    ranks 38-49:   q  |  .  /  =  <  -  `  ]  $  @  [

`tails` has been run thirteen times and `tails --length 4` and `--length 5` besides, so the ground
those 37 characters reach is thoroughly swept. The ground they cannot reach has never been swept at
all, because no run has ever carried a single one of these characters in an ending.

This writes the **complement**: every *k*-character ending over all 49 observed characters that
carries at least one of the twelve, and no ending that the 37 can already spell. So it is disjoint
from every `tails` run by construction rather than by hoping the exclusion catches it.

    k=2      1,033 endings      1.6 B candidates    seconds
    k=3     70,472 endings    107.0 B candidates    a few minutes

The same argument does not apply at the front. `contrib/heads_measured_alphabet.py` measures the
head alphabet where the head is, and its 37 characters already spell 99.99% of first-three-character
openings -- the punctuation names *begin* with (`*`, `[`, `$`, `/`) is common enough to be inside
the cap there, and so is `q`. It is only at the end that the cap and the punctuation coincide.
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

# What `tails.py` carries, and so what this must not repeat.
CARRIED = 37
SHORTEST_STEM = 4


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def ending_alphabet(names):
    """Every character real names end in, commonest first -- `tails.alphabet_of` without the cap."""
    counted = collections.Counter()
    for name in names:
        for character in name[-4:]:
            counted[character] += 1
    return [character for character, _ in counted.most_common()]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--length", type=int, default=3)
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    names = known_names()
    alphabet = ending_alphabet(names)
    swept, dropped = set(alphabet[:CARRIED]), alphabet[CARRIED:]
    print(
        "known names: %s\nending characters: %d, of which tails.py carries %d\ndropped: %s"
        % (format(len(names), ","), len(alphabet), CARRIED, " ".join(repr(c) for c in dropped)),
        file=sys.stderr,
    )

    # The complement: at least one dropped character, so no ending here is one `tails.py` has run.
    endings = [
        "".join(ending)
        for ending in itertools.product(alphabet, repeat=options.length)
        if any(character not in swept for character in ending)
    ]
    stems = sorted(
        {name[: -options.length] for name in names if len(name) - options.length >= SHORTEST_STEM}
    )

    base = os.path.splitext(options.write_plan)[0]
    stem_path, end_path = base + ".stems.txt", base + ".endings.txt"
    for path, rows in ((stem_path, stems), (end_path, endings)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(rows) + "\n")

    def relative(path):
        return os.path.relpath(path, _root).replace("\\", "/")

    with open(options.write_plan, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by contrib/symbol_tails.py --length %d. Regenerate rather than editing.\n"
            "#\n"
            "# Every %d-character ending over the %d characters names are observed to end in that\n"
            "# carries at least one of the %d characters scripts/tails.py's 37-character cap drops.\n"
            "# Disjoint from every tails run by construction. See this script's docstring.\n"
            "\n"
            "label: tails of length %d over the dropped punctuation\n"
            "describe: known names with their last %d characters replaced by an ending carrying at least one of the punctuation characters the measured 37-character tail alphabet drops\n"
            "\n"
            "stem: @%s\n"
            "\n"
            "end: @%s\n"
            "\n"
            "# No begin line, so `bare: yes` supplies the empty opening column -- without it this\n"
            "# plan builds nothing at all. See METHODS.md on how `bare` flips between the two ends.\n"
            "bare: yes\n"
            "fold: yes\n"
            % (
                options.length,
                options.length,
                len(alphabet),
                len(dropped),
                options.length,
                options.length,
                relative(stem_path),
                relative(end_path),
            )
        )

    print(
        "wrote %s\n      %s (%s stems)\n      %s (%s endings)\n\nabout %s candidates."
        % (
            options.write_plan,
            stem_path,
            format(len(stems), ","),
            end_path,
            format(len(endings), ","),
            format(len(stems) * len(endings), ","),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
