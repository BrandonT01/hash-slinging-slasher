"""`heads`, with the alphabet measured at the end of the name it is actually replacing.

    python contrib/heads_measured_alphabet.py --length 3 --write-plan plans/heads3m.txt
    bin\\windows\\confirm_plan.exe plans/heads3m.txt --size
    bin\\windows\\confirm_plan.exe plans/heads3m.txt

## The bug this exists for

`scripts/tails.py` replaces the last *k* characters of a known name, and its alphabet is measured
rather than assumed -- `alphabet_of` counts the characters of `name[-4:]` across the corpus and
keeps the commonest 37, because a fixed `a-z0-9_` would spend a third of the pass on characters no
name ends with. That is right, and it is the reason the method is cheap.

`--head` was added on 2026-08-22 as the mirror: replace the *first* k characters instead. It
returned 692 names on Cold War, the best single pass in the project. It reuses `alphabet_of`
unchanged -- so it replaces the front of a name with characters measured off the **back**.

Those two distributions are not the same, and the gap is not small. Measured over the 1,521,471
names known here on 2026-08-23:

    alphabet measured from name[-4:]   0123456789_abcdefghijklmnoprstuvwxyz  (and a space)
    alphabet measured from name[:4]    $*/346789[_abcdefghijklmnopqrstuvwxyz

    present only at the head:  $  *  /  [  q
    present only at the tail:  (space)  0  1  2  5

    known names whose first 3 characters the tail alphabet can spell:  1,189,567 / 1,521,471  78.19%
    known names whose first 3 characters the head alphabet can spell:  1,521,146 / 1,521,471  99.98%

**A fifth of the corpus was structurally unreachable and the pass looked perfectly healthy.**
What it could not spell is not a random fifth either. It is every material path -- `mc/` heads
496,666 published names, and `wc/ vd/ ei/ el/ cp/` follow -- every name beginning `*` (`*cp`,
`*na`, `*kg`, `*wz`, `*mp`, `*st`, `*tk`, ...), every name beginning `[`, and every name beginning
`q`. The 977 distinct three-character openings real names use are simply not drawn from the
alphabet real names *close* with.

Two of those matter beyond the arithmetic. Replacing the first three characters of an `mc/...`
material is a **directory swap** -- the same core offered to `wc/`, `vd/`, and the other ten -- and
that is the shape `mcdp/` returned 2,846 names for. And the `*` family is large, regular, and has
never been touched from the front by anything.

## What this changes, and what it does not

Only the alphabet. Same stems, same engine, same `run_best`, same exclusion -- so it is not a
re-measure of the lists (`METHODS.md` records that as a dead end, and rightly: it changes what a
search is called without changing what it can reach). This changes what it can reach: 977 real
openings against the 50,653 strings the tail alphabet's 37 characters can spell, of which a fifth
of the real ones were absent.

`--length 3` is 50,653 beginnings and about 75 B candidates -- four minutes. `--length 2` is 1,369
and seconds. k=3 subsumes k=2 subsumes k=1, as in `tails.py`.
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

ALPHABET = 37
SHORTEST_STEM = 4


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def head_alphabet(names, size, length):
    """The characters real names actually *begin* with, commonest first.

    Counted over `name[:length + 1]` for the same reason `tails.py` counts over `name[-4:]`: a
    three-character head draws on all three positions, and one character of overlap keeps the
    boundary character in the count without letting the middle of the name in.
    """
    counted = collections.Counter()
    for name in names:
        for character in name[: length + 1]:
            counted[character] += 1
    return [character for character, _ in counted.most_common(size)]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--length", type=int, default=3)
    parser.add_argument("--alphabet", type=int, default=ALPHABET)
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    if not 1 <= options.length <= 5:
        raise SystemExit("--length is between 1 and 5")

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    alphabet = head_alphabet(names, options.alphabet, options.length)
    beginnings = ["".join(t) for t in itertools.product(alphabet, repeat=options.length)]
    stems = sorted(
        {name[options.length :] for name in names if len(name) - options.length >= SHORTEST_STEM}
    )

    # What the correction actually buys, printed rather than claimed.
    eligible = [name for name in names if len(name) - options.length >= SHORTEST_STEM]
    spellable = sum(
        1
        for name in eligible
        if all(character in alphabet for character in name[: options.length])
    )
    print(
        "alphabet (%d): %s\nstems: %s   beginnings: %s\nheads this alphabet can spell: %s of %s (%.2f%%)"
        % (
            len(alphabet),
            "".join(alphabet),
            format(len(stems), ","),
            format(len(beginnings), ","),
            format(spellable, ","),
            format(len(eligible), ","),
            100.0 * spellable / max(len(eligible), 1),
        ),
        file=sys.stderr,
    )

    base = os.path.splitext(options.write_plan)[0]
    stem_path, begin_path = base + ".stems.txt", base + ".beginnings.txt"
    for path, rows in ((stem_path, stems), (begin_path, beginnings)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(rows) + "\n")

    def relative(path):
        return os.path.relpath(path, _root).replace("\\", "/")

    with open(options.write_plan, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by contrib/heads_measured_alphabet.py --length %d. Regenerate rather than\n"
            "# editing.\n"
            "#\n"
            "# Every known name with its first %d character(s) replaced, over the %d characters\n"
            "# names are measured to BEGIN with. scripts/tails.py --head measures that alphabet off\n"
            "# the last four characters instead, which cannot spell mc/, wc/, *cp, [ko or q..., and\n"
            "# so could not reach 21.8%% of the corpus. See this script's docstring.\n"
            "\n"
            "label: heads of length %d, head-measured alphabet\n"
            "describe: every known name with its first %d characters replaced, over the %d characters names are measured to begin with rather than to end with\n"
            "\n"
            "stem: @%s\n"
            "\n"
            "begin: @%s\n"
            "\n"
            "bare: no\n"
            "fold: yes\n"
            % (
                options.length,
                options.length,
                len(alphabet),
                options.length,
                options.length,
                len(alphabet),
                relative(stem_path),
                relative(begin_path),
            )
        )

    print(
        "wrote %s\n      %s (%s stems)\n      %s (%s beginnings)\n\nabout %s candidates."
        % (
            options.write_plan,
            stem_path,
            format(len(stems), ","),
            begin_path,
            format(len(beginnings), ","),
            format(len(stems) * len(beginnings), ","),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
