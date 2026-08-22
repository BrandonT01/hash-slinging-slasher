"""Offer each suffix the words that have actually *preceded* it. The mirror of `continuations.py`.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/precedents.py | bin\\windows\\confirm_list.exe - \\
        --label "per-suffix precedents" --script scripts/precedents.py

## Why this exists

`continuations.py` takes a prefix and offers it the tokens measured to follow *that* prefix rather
than the tokens that are globally common. Its own docstring calls that the strongest single
finding in the published work on this problem: 2.4x the names for less than half the search.

It only ever looks forward. Nothing here has ever asked the same question backwards -- given a
suffix that real names end with, which tokens actually come *before* it? -- and there is no reason
for that beyond the order somebody wrote the first one in.

The same asymmetry was found and fixed in `tails.py` on 2026-08-22: it replaced a name's last *k*
characters and nothing replaced the first, purely because the hash's invertibility had drawn
attention to the end. Adding the mirror took nine lines and returned **692 names on Cold War in a
single pass**, the best of that day. **Check the mirror of anything that works.**

## What it does

For every suffix occurring in known names -- a trailing run of underscore-separated segments -- it
counts which single token appears immediately before it, across the whole corpus. Then it offers
each suffix exactly those tokens, and nothing else.

That is a much smaller and much better-aimed space than a global beginning list. `_barrel_c` is
preceded by weapon names; `_lod3` by model names; the two share almost no vocabulary, and a global
list offers both to both.

## Why it is a generator and not a plan

Every suffix has its *own* list of precedents, so this is not a cross product -- pairing each
suffix with only its own precedents is the whole point, and a plan would cross every suffix with
every precedent and destroy it. That is the distinction `splice.py` measured the hard way: freely
recombining pieces of different names returns 1 name per 13.7 billion candidates.

So it goes through `confirm_list` at generator speed, and the aim is what buys the names rather
than the volume.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

# How many segments a suffix may run to. Longer suffixes are more specific and their precedent
# lists are shorter and better aimed; past this they are so specific that only the name they came
# from has them.
LONGEST_SUFFIX = 5

# A suffix seen fewer times than this has too few precedents to be measuring a convention.
LEAST_SEEN = 2

# Most precedents to offer one suffix. The distribution is very long-tailed and the tail is where
# the collisions are, not the names.
MOST_PRECEDENTS = 400


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def split(name):
    """(directory, segments). The directory travels with the front, since the engine hashes it."""
    head, sep, rest = name.partition("/")
    if sep and len(head) <= 6 and "_" not in head:
        return head + "/", rest.split("_")
    return "", name.split("_")


def measure(names):
    """{suffix: Counter(token that came immediately before it)}.

    Counted across every name and every suffix length, so a token that precedes `_barrel_c` in one
    family and `_lod3` in another is credited to each separately -- which is exactly the
    information a global beginning list throws away.
    """
    before = collections.defaultdict(collections.Counter)

    for name in names:
        _, parts = split(name)
        if len(parts) < 3:
            continue

        for length in range(1, min(LONGEST_SUFFIX, len(parts) - 1) + 1):
            suffix = "_" + "_".join(parts[-length:])
            before[suffix][parts[-length - 1]] += 1

    return before


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--most", type=int, default=MOST_PRECEDENTS)
    parser.add_argument("--count", action="store_true", help="count candidates and stop")
    options = parser.parse_args(argv)

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    before = measure(names)
    print("distinct suffixes: %s" % format(len(before), ","), file=sys.stderr)

    # Each name, with its leading token replaced by every token measured to precede the rest of
    # it. The name itself is skipped -- it is already known and is not a candidate.
    written = 0
    out = sys.stdout
    batch = []

    for name in names:
        directory, parts = split(name)
        if len(parts) < 3:
            continue

        for length in range(1, min(LONGEST_SUFFIX, len(parts) - 1) + 1):
            suffix = "_" + "_".join(parts[-length:])
            head = "_".join(parts[: -length - 1])
            counted = before.get(suffix)
            if not counted or sum(counted.values()) < LEAST_SEEN:
                continue

            for token, _ in counted.most_common(options.most):
                if token == parts[-length - 1]:
                    continue
                candidate = directory + (head + "_" if head else "") + token + suffix
                written += 1
                if not options.count:
                    batch.append(candidate)

            if len(batch) >= 65536:
                out.write("\n".join(batch) + "\n")
                batch.clear()

    if batch and not options.count:
        out.write("\n".join(batch) + "\n")

    print("%s candidates" % format(written, ","), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
