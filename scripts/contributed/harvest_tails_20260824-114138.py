r"""`tails` and `heads`, seeded from harvested build strings instead of from known names.

    python contrib/harvest_tails.py --strings logs/harvest_all.txt --length 3 \
        --write-plan plans/harvest_tails.txt
    python contrib/harvest_tails.py --strings logs/harvest_all.txt --length 3 --head \
        --write-plan plans/harvest_heads.txt

`scripts/tails.py` asks "is this unnamed id a **known name** with its last *k* characters
replaced", and it is one of the two best methods here. Its seed is `known_names()` -- the
published tables plus everything confirmed -- so every stem it has ever used came from the corpus
being searched, and METHODS.md §1473 says exactly what that costs:

> Recombining a corpus with itself is bounded by that corpus. [...] The unnamed assets are unnamed
> *because* they are outside it.

The build harvests break that bound, and they break it in the way that suits this method best.
Of 273,138 strings read out of the Black Ops 4 zones, **145 hashed straight to real asset ids**.
The other 272,993 are the interesting ones: they are strings the game itself carries, in the same
tables and scripts as the ones that *are* asset names, so a great many of them are a channel code,
a variant digit or a language tag away from one. That is precisely the question `tails` asks, and
nothing has ever pointed it at a seed that was not already in the corpus.

`--head` swaps the lists and replaces the first *k* characters instead, with the alphabet
correction from `contrib/heads_slash.py`: names begin with `/` and never end with it, and the
tail-measured alphabet blocks 35.9% of name fronts without it.
"""
import argparse
import collections
import itertools
import os
import sys

ALPHABET = 37
HEAD_FLOOR_SHARE = 0.02
SHORTEST_STEM = 4


def rows(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return [line.strip().lower().replace("\\", "/") for line in handle if line.strip()]


def alphabet_of(names, size, head):
    """Measured off the harvested strings themselves, not off the corpus."""
    counted = collections.Counter()
    for name in names:
        for character in (name[:4] if head else name[-4:]):
            counted[character] += 1
    carried = [character for character, _ in counted.most_common(size)]
    if head:
        floor = HEAD_FLOOR_SHARE * sum(counted.values()) / max(size, 1)
        carried += [
            character for character, seen in counted.most_common()
            if character not in carried and seen >= floor
        ]
    return carried


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strings", required=True, action="append",
                        help="a harvested string list; repeat to pool several builds")
    parser.add_argument("--length", type=int, default=3)
    parser.add_argument("--head", action="store_true", help="replace the first k characters")
    parser.add_argument("--alphabet", type=int, default=ALPHABET)
    parser.add_argument("--write-plan", required=True)
    options = parser.parse_args(argv)

    names = set()
    for path in options.strings:
        names |= set(rows(path))
    print("harvested strings: %s" % format(len(names), ","), file=sys.stderr)

    alphabet = alphabet_of(names, options.alphabet, options.head)
    affixes = ["".join(row) for row in itertools.product(alphabet, repeat=options.length)]
    if options.head:
        stems = sorted({n[options.length:] for n in names
                        if len(n) - options.length >= SHORTEST_STEM})
    else:
        stems = sorted({n[: -options.length] for n in names
                        if len(n) - options.length >= SHORTEST_STEM})

    print("alphabet (%d): %s\nstems: %s   %s: %s"
          % (len(alphabet), "".join(alphabet), format(len(stems), ","),
             "beginnings" if options.head else "endings", format(len(affixes), ",")),
          file=sys.stderr)

    base = os.path.splitext(options.write_plan)[0]
    for suffix, values in (("stems", stems), ("affixes", affixes)):
        with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
            handle.write("\n".join(values) + "\n")

    side = "begin: @%s.affixes.txt\nstem:  @%s.stems.txt" if options.head else \
           "stem:  @%s.stems.txt\nend:   @%s.affixes.txt"
    with open(options.write_plan, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by contrib/harvest_tails.py. Regenerate rather than editing.\n"
            "#\n"
            "# A string read out of a build, with its %s %d character(s) replaced by every\n"
            "# string over the alphabet those strings are measured to use there.\n"
            "\n"
            "label: harvested strings, %s of length %d\n"
            "%s\n"
            # `bare` flips meaning between the two, and getting it wrong does not fail: a tails
            # plan has no `begin:` line, so the empty beginning is the only opening column it has
            # and without it the plan reports billions of candidates and scans none. A heads plan
            # supplies the beginnings itself, and there `bare` would add the headless stem alone,
            # which is a truncation and a different method.
            "bare:  %s\n"
            % (
                "first" if options.head else "last",
                options.length,
                "heads" if options.head else "tails",
                options.length,
                side % (base, base),
                "no" if options.head else "yes",
            )
        )
    print("\nwrote %s\nabout %s candidates."
          % (options.write_plan, format(len(stems) * len(affixes), ",")), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
