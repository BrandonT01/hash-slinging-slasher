"""Offer each prefix the words that have actually followed *it*, not the words that are common.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/continuations.py | ./bin/windows/confirm_list.exe - --label "per-prefix continuations"

## What it does that the general search does not

The general search recombines a beginning, a stem and an ending, and the three lists are global:
every stem is offered the same 700 beginnings and the same 4,800 endings. That is the right shape
for a first pass and it has a specific blind spot. `i_c_t8_mp_spe_` and `mc/` get offered
identical vocabulary, when what actually follows them in real names has almost nothing in common.

So this measures, for every prefix that occurs in known names, which tokens follow it *there* --
and offers each prefix only those. The same total number of candidates buys names in the families
the game really has rather than in the cross product of every family with every other.

This is the strongest single finding in the published work on the equivalent problem: on Black
Ops 4, replacing a generic 256-word extension with per-prefix continuations returned 2.4x the
names for less than half the search. It has never been tried in this repository.

## Directory prefixes get the whole vocabulary

There are twelve material directories -- `mc/ wc/ clt/ splm/ vd/ mcs/ ei/ cltp/ vdd/ el/ mcp/
ec/` -- and a handful more elsewhere. They head a small share of known names and a large share of
recoverable ones, and there are few enough of them that handing each the entire vocabulary is
affordable where it would not be for anything longer. They are treated separately for that
reason.

## Options

    --depth N        how many continuation tokens to append (default 1; 2 is the interesting one)
    --cap N          most continuations offered to an ordinary prefix (default 64)
    --min-seen N     ignore a prefix seen fewer than this many times (default 3)
    --endings FILE   also append each measured ending (default: none -- see below)
    --count          print how many candidates this would produce and stop

Reads the tables, the merged submissions and this machine's findings. Writes candidates to
standard output, one per line.
"""
import collections
import os
import sys

import settings
import snapshot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The tables that are Black Ops 4 and Cold War. The `_v2` files are MW2022/BO6 and teach the
# wrong conventions -- see docs/HASHES.md for which file is which game.
THIS_ERA = [
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_xsounds",
    "fnv1a_soundbanks_aliases",
    "fnv1a_strings",
] + ["fnv1a_%s_xsounds" % language for language in (
    "english french german italian spanish americanspanish brazilianportugese "
    "russian polish japanese korean chinese"
).split()]


def split(name):
    """A name as its tokens, keeping the marks so it can be put back together exactly.

    Both `_` and `/` separate, because a directory is as much a segment boundary as an
    underscore -- and the engine hashes the slash, so it cannot simply be dropped.
    """
    tokens, current = [], ""
    for character in name:
        if character in "_/":
            tokens.append(current + character)
            current = ""
        else:
            current += character
    if current:
        tokens.append(current)
    return tokens


def measure(names, min_seen):
    """{prefix: Counter of the tokens seen straight after it}, over every position in every name."""
    following = collections.defaultdict(collections.Counter)

    for name in names:
        tokens = split(name)
        prefix = ""
        for token in tokens:
            following[prefix][token] += 1
            prefix += token

    return {
        prefix: counter
        for prefix, counter in following.items()
        if prefix and sum(counter.values()) >= min_seen
    }


def directories(names):
    """The leading `xxx/` directories, which get the whole vocabulary rather than a capped list."""
    found = collections.Counter()
    for name in names:
        head, sep, _ = name.partition("/")
        if sep and head and "_" not in head and len(head) <= 6:
            found[head + "/"] += 1
    return found


def main(argv):
    depth = int(argv[argv.index("--depth") + 1]) if "--depth" in argv else 1
    cap = int(argv[argv.index("--cap") + 1]) if "--cap" in argv else 64
    min_seen = int(argv[argv.index("--min-seen") + 1]) if "--min-seen" in argv else 3
    counting = "--count" in argv

    # Off by default, and the reason is arithmetic rather than taste. Writing every candidate
    # out with every one of the 4,800 measured endings multiplies six million lines by 4,801 --
    # thirty billion lines, over a terabyte of text, to ask a question the Rust engine answers
    # for nothing. `Meet` peels endings off the wanted ids instead of appending them to
    # candidates, so an ending costs a share of one pass rather than a pass of its own. Generate
    # the interesting stems here; let the general search dress them.
    endings_file = argv[argv.index("--endings") + 1] if "--endings" in argv else "none"

    endings = []
    if endings_file != "none":
        with open(endings_file, encoding="utf-8") as handle:
            endings = [line.strip() for line in handle if line.strip()]

    print("reading known names", file=sys.stderr)
    names = snapshot.table_names(*THIS_ERA) + snapshot.confirmed_names()
    names = [name.strip().lower().replace("\\", "/") for name in names if name.strip()]
    print("%d known names" % len(names), file=sys.stderr)

    following = measure(names, min_seen)
    dirs = directories(names)
    vocabulary = collections.Counter()
    for counter in following.values():
        vocabulary.update(counter)

    print(
        "%d prefixes with a measured continuation, %d distinct tokens, %d directories"
        % (len(following), len(vocabulary), len(dirs)),
        file=sys.stderr,
    )

    whole = [token for token, _ in vocabulary.most_common()]
    produced = 0
    out = sys.stdout

    def emit(candidate):
        nonlocal produced
        produced += 1
        if not counting:
            out.write(candidate)
            out.write("\n")

    def extend(prefix, choices, left):
        """prefix + up to `left` continuation tokens, each also tried with every ending."""
        for token in choices:
            candidate = prefix + token
            emit(candidate)

            for ending in endings:
                emit(candidate + ending)

            if left > 1:
                # A token that has followed *this* longer prefix, if any has; the prefix's own
                # list otherwise. This is where a two-word middle nobody has seen comes from.
                deeper = following.get(candidate)
                deeper = [t for t, _ in deeper.most_common(cap)] if deeper else choices[: cap // 4]
                extend(candidate, deeper, left - 1)

    # Directories first and exhaustively: few of them, and they head the families this search
    # recovers most of.
    for directory, _ in dirs.most_common():
        extend(directory, whole, depth)

    for prefix, counter in following.items():
        if prefix in dirs:
            continue
        extend(prefix, [token for token, _ in counter.most_common(cap)], depth)

    print("%d candidates" % produced, file=sys.stderr)
    if counting:
        print(
            "run again without --count to write them, or pipe straight into confirm_list",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main(sys.argv[1:])
