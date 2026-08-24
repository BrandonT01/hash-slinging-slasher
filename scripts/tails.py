"""Every name that is a known name with its last few characters replaced, as a runnable plan.

    python scripts/tails.py --length 2 --write-plan plans/tails2.txt
    bin\\windows\\confirm_plan.exe plans/tails2.txt --size
    bin\\windows\\confirm_plan.exe plans/tails2.txt

The generalisation of `scripts/final_byte.py` past the one character that can be solved.

## Why this is a plan and not a solve

`final_byte.py` inverts the hash for a name's **final** character: the difference between two such
names is an exact small multiple of the prime, so the character falls straight out of the id. One
name per 18 candidates, the best figure in the project.

The obvious next question is how far that extends. Measured, on hashes of names differing in their
last *k* characters -- shared leading hex digits, against 0.03 for two unrelated names:

    k=1   mean 4.26      k=3   mean 0.11
    k=2   mean 1.41      k=4   mean 0.07

**It dies at three.** One character is strongly visible in the hash, two is faint, and from three
the pair is indistinguishable from any two unrelated names. XOR does not commute with the multiply,
so each further step scatters what the last one left. There is no proximity to exploit and no
solve to extend -- which is worth writing down, because "extend the solve to longer tails" is the
obvious next idea and it does not exist.

## What does work

The engine already peels. `confirm_plan` takes beginnings, stems and endings and multiplies them,
choosing whichever direction is cheaper -- so the question "is this id a known name with its last
*k* characters replaced" is just a plan whose stems are known names cut short by *k* and whose
endings are every *k*-character string. No proximity needed; it asks all of them.

The alphabet is measured off the corpus rather than assumed, because a fixed `a-z0-9_` would spend
a third of the pass on characters no name in either game ends with.

Sizes, against 922k known names and the 37 characters names actually end in:

    k=1        37 endings         34 M candidates    seconds
    k=2     1,369 endings        1.3 B candidates    seconds
    k=3    50,653 endings       46.7 B candidates    about a minute
    k=4   1.87 M endings        1.73 T candidates    about half an hour

`k=2` subsumes `k=1`, `k=3` subsumes `k=2`, and so on -- a name differing in only its last
character is also a name differing in its last two. So run the longest you are willing to pay for
and it covers everything below it. `--size` first; that is what it is for.
"""
import argparse
import collections
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

# How many of the measured ending characters to carry. The tail of that distribution is long and
# thin, and the cost is `alphabet ** length`, so this is the knob that decides whether a plan is
# seconds or hours.
ALPHABET = 37

# How many name fronts a character has to block before a head run pays the widening for it.
HEAD_FLOOR = 50000

# A stem shorter than this is not a name with its tail replaced, it is a fragment, and it collides
# with everything.
SHORTEST_STEM = 4


def known_names():
    """Every name known to be real: published, submitted by anybody, confirmed here."""
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def alphabet_of(names, size, head=False):
    """The characters real names actually end in, commonest first.

    Measured, not assumed. Counted across the last few characters rather than only the last, since
    a two-character tail draws on both positions.

    `head` widens it with the characters names **begin** with that they never end with. Names do
    not begin the way they end, and measured 2026-08-24 over 958,424 names the difference is one
    character and a third of the corpus:

        first 3 characters inside the tail alphabet   65.3%
        first 4 characters inside the tail alphabet   64.1%
        blocked in the first four positions      /  340,786 names   *  3,410   [  354   $  87

    `/` is the directory separator, so every `mc/ wc/ clt/ splm/ vd/ mcs/ ei/ cltp/ vdd/ el/ mcp/
    ec/ mcdp/` name -- `mc/` alone heads 496,666 published names -- was unspellable by every head
    run before this. Carrying it costs `((size + 1) / size) ** length`, 11% at k=4.

    Only characters blocking `HEAD_FLOOR` name fronts are carried, so `*` (a mesh hash marker, and
    unreachable anyway) does not multiply the plan for 3,410 names.
    """
    counted = collections.Counter()
    for name in names:
        for character in name[-4:]:
            counted[character] += 1
    alphabet = [character for character, _ in counted.most_common(size)]

    if head:
        fronts = collections.Counter()
        for name in names:
            for character in name[:4]:
                fronts[character] += 1
        alphabet += [
            character
            for character, seen in fronts.most_common()
            if character not in alphabet and seen >= HEAD_FLOOR
        ]
    return alphabet


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--length", type=int, default=2, help="how many characters to replace")
    parser.add_argument(
        "--head",
        action="store_true",
        help="replace the FIRST k characters instead of the last -- the untried mirror",
    )
    parser.add_argument("--alphabet", type=int, default=ALPHABET)
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    if options.length < 1 or options.length > 5:
        raise SystemExit(
            "--length is between 1 and 5. Past that the ending list is %d entries and the plan\n"
            "is larger than the general search, which reaches more for the same money."
            % (options.alphabet ** 6)
        )

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    alphabet = alphabet_of(names, options.alphabet, head=options.head)
    endings = ["".join(pair) for pair in itertools.product(alphabet, repeat=options.length)]

    # The mirror. `tails` replaces the end because the end is where the hash keeps a resemblance
    # and where `final_byte` could solve; nothing has ever replaced the *beginning*, and there is
    # no reason beyond that history. A head is a beginning in the engine's terms, so the same
    # cross product runs with the lists swapped: stems are names with their heads cut off, and the
    # beginnings are every k-character string.
    if options.head:
        stems = sorted(
            {name[options.length :] for name in names if len(name) - options.length >= SHORTEST_STEM}
        )
    else:
        stems = sorted(
            {name[: -options.length] for name in names if len(name) - options.length >= SHORTEST_STEM}
        )

    print(
        "alphabet (%d): %s\nstems: %s   endings: %s"
        % (len(alphabet), "".join(alphabet), format(len(stems), ","), format(len(endings), ",")),
        file=sys.stderr,
    )

    plan_path = os.path.join(ROOT, options.write_plan)
    base = os.path.splitext(plan_path)[0]
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)

    stems_path = base + ".stems.txt"
    endings_path = base + ".endings.txt"
    open(stems_path, "w", encoding="utf-8", newline="\n").write("\n".join(stems) + "\n")
    open(endings_path, "w", encoding="utf-8", newline="\n").write("\n".join(endings) + "\n")

    relative = lambda path: os.path.relpath(path, ROOT).replace("\\", "/")

    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by scripts/tails.py --length %d. Regenerate rather than editing.\n"
            "#\n"
            "# Every known name cut short by %d character(s), against every %d-character ending\n"
            "# over the %d characters names are measured to end in. Answers \"is this unnamed id a\n"
            "# name we hold with its last %d characters replaced\" -- which cannot be solved the way\n"
            "# scripts/final_byte.py solves one character, because past two the hash keeps nothing\n"
            "# of the resemblance. See that file, and this one's docstring, for the measurement.\n\n"
            % (
                options.length,
                options.length,
                options.length,
                len(alphabet),
                options.length,
            )
        )
        handle.write(
            "label: %s of length %d\n" % ("heads" if options.head else "tails", options.length)
        )
        handle.write(
            "describe: every known name cut short by %d character(s), against every %d-character "
            "ending over the %d characters names are measured to end in\n\n"
            % (options.length, options.length, len(alphabet))
        )
        handle.write("stem: @%s\n\n" % relative(stems_path))
        handle.write(
            "%s: @%s\n\n" % ("begin" if options.head else "end", relative(endings_path))
        )

        # `bare` is the **empty beginning**, and which way this goes depends on the mode.
        #
        # Replacing tails, the k-character strings are endings and there is no `begin:` line at
        # all -- so `bare: yes` is what supplies the single opening column. Without it the engine's
        # opening count is `beginnings + bare` = 0, there is no column to iterate, and the pass
        # tests nothing while reporting billions. That cost a 31.7-billion-candidate run that
        # scanned zero and exited reporting success; `confirm_plan` refuses such a plan now.
        #
        # Replacing heads, those same strings *are* the beginnings, so the column exists. `bare`
        # would then add the headless stem on its own -- a truncation, which is a different method
        # and not one this should be credited with.
        handle.write("bare: %s\nfold: yes\n" % ("no" if options.head else "yes"))

    print(
        "\nwrote %s\n      %s (%s stems)\n      %s (%s endings)\n\n"
        "about %s candidates. Size it before committing the time:\n\n"
        "    bin\\windows\\confirm_plan.exe %s --size"
        % (
            relative(plan_path),
            relative(stems_path),
            format(len(stems), ","),
            relative(endings_path),
            format(len(endings), ","),
            format(len(stems) * len(endings), ","),
            options.write_plan,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
