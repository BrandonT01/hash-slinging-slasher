"""Every short prefix and suffix, exhaustively, around names already known to be real.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/affix_sweep.py --type model --hours 1 | bin\\windows\\confirm_list.exe - \\
        --label "affix sweep" --script scripts/affix_sweep.py

It emits, for each stem, every combination of a short leading and trailing token:

    a_modelname_a      a_modelname_b      ...   z_modelname_9
    b_modelname_a      ...
    aa_modelname_a     aa_modelname_b     ...
    aba_modelname_a    ...

## What problem it solves

Every other method here recombines *measured* vocabulary: a token has to have been seen somewhere
before it can be offered. That is the seeding principle and it is right, but it has one blind spot
-- an affix that appears on exactly one asset in the game is real and is measured nowhere, because
a frequency-ranked list of 4,800 endings cannot hold a token used once.

Short affixes are exactly where that happens. Measured across the four general tables: **341
distinct leading tokens of one to three characters, and 2,044 trailing ones.** The common ones
(`i_`, `mtl_`, `_c`, `_n`, `_01`) are carried by every list. The long tail is not, and the tail is
most of the distinct values.

Enumerating them is cheap in a way enumerating words is not. Thirty-six characters over three
positions is 46,656 possibilities -- a rounding error next to the 2^63 space that makes word
composition hopeless. This is the one place where brute force is the *right* tool, because the
space is genuinely small.

## The limit is time, and it is enforced rather than suggested

`METHODS.md` calls unconstrained character sweeps a last resort, and it is right about long ones.
The protection here is that the run is **sized before it starts**:

    candidates = stems x (L + 1) x 36^L        for a combined affix length of L

which grows so fast that L is decided for you rather than chosen. Measured on this machine,
`confirm_list` fed by a Python generator sustains **6.1 x 10^5 candidates/s** end to end, so an
hour is about 2.2 billion candidates. The script solves for the largest L that fits the budget you
give it and prints the plan before emitting a single line. There is no flag to force a longer one,
because a sweep that takes a fortnight is not a method, it is a mistake nobody notices for a
fortnight.

## What it reads and writes

Reads the community table for the chosen type and this machine's confirmed names, via
`snapshot.py`. Writes candidates to standard output, one per line; the plan and sizing to standard
error.

## Options

    --type NAME     model, material, image, anim, sound_asset or sound_alias (default: model)
    --hours H       time budget, which decides the affix length (default 1.0)
    --stems N       how many stems to sweep (default: as many as the budget allows at L>=2)
    --alphabet S    characters to sweep (default: a-z0-9, measured -- see below)
    --plan          print the plan and stop, emitting nothing

## Why this alphabet

Measured from the short affixes real names actually carry, most frequent first:

    i m t l p 0 c 1 n 9 8 2 g 7 s o e u r a 3 v d 4 6 w b 5 h f k x z y * j q . $ -

Everything after `y` occurs rarely enough to be noise, so the default is `a-z0-9`. The rare ones
are available with `--alphabet` for somebody who has a reason.
"""
import os
import string
import sys

# Find `scripts/` wherever this file has been filed -- see scripts/README.md.
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

# Measured end to end on this machine: a Python generator piped into `confirm_list`.
#
# **Measure it on a long run, not a short one.** A three-million candidate calibration gave
# 6.08 x 10^5/s, and a five-hundred-million one gave 1.2 x 10^6/s -- the difference is entirely
# `confirm_list`'s startup, which loads a snapshot and eight million table hashes before the first
# candidate is tested. On a short run that fixed cost is most of the wall clock; on a real one it
# is noise. Budgeting from the short figure made every plan twice as pessimistic as it needed to
# be, which costs stems rather than safety, but it is still wrong.
#
# Reproduce with a run long enough to amortise it:
#   python scripts/affix_sweep.py --type model --hours 0.25 | confirm_list - --label calib
RATE = 1_200_000

TYPES = {
    "model": ("fnv1a_xmodels", "xmodel"),
    "material": ("fnv1a_xmaterials", "material"),
    "image": ("fnv1a_ximages", "image"),
    "anim": ("fnv1a_xanims", "xanim"),
    "sound_asset": ("fnv1a_english_xsounds", "sound_asset"),
    "sound_alias": ("fnv1a_soundbanks_aliases", "sound_alias"),
}

DEFAULT_ALPHABET = string.ascii_lowercase + string.digits

# Which separators a type actually puts between a prefix and the rest, per type.
#
# **A separator, never an alphabet member, and the difference is measured.** In `fnv1a_xmaterials`
# a `/` appears 98,384 times in a short leading affix -- but always in one place, closing a two or
# three letter directory code (`mc/`, `wc/`, `clt/`). It never appears scattered through an affix.
# Putting `/` in the swept alphabet would therefore spend the budget generating `a/b_name_c`, which
# cannot exist, and cost 1.12x at four characters for the privilege. Sweeping the code and
# appending the separator costs nothing extra and reaches every directory, including ones nobody
# has recorded.
#
# Measured, non-alphanumeric characters in short affixes per type:
#   material    '/' x98384   (plus '|' x342, '$' x9, '-' x12 -- noise)
#   model       '*' x4861    (mesh decorations, unreachable anyway)
#   image       '$' x26, '.' x14
#   anim, sound_asset, sound_alias   none at all
#
# `.` is deliberately absent everywhere. Sound names are full of dots, but in long fixed tails
# (`.rn75.pc.en.snd`), never as short random affixes -- and the endings list reaches those at 96.7%
# since the ceiling fix. Sweeping random dots would duplicate that badly and expensively.
SEPARATORS = {
    "model": ["_"],
    "anim": ["_"],
    "material": ["_", "/"],
    "image": ["_", "/"],
    "sound_asset": ["_", "/"],
    "sound_alias": ["_"],
}


def cost(length, alphabet):
    """Candidates per stem for a combined affix length of exactly `length`.

    The prefix takes `p` characters and the suffix the remaining `length - p`, for every split
    including the ones where a side is empty -- so `length + 1` splits, each `|alphabet|^length`
    combinations.
    """
    return (length + 1) * len(alphabet) ** length


def affixes(length, alphabet):
    """Every (prefix, suffix) pair whose lengths add to `length`."""
    from itertools import product

    for split in range(length + 1):
        for head in product(alphabet, repeat=split):
            for tail in product(alphabet, repeat=length - split):
                yield "".join(head), "".join(tail)


def stems_for(kind, limit, contains=None):
    """Stems worth sweeping: what this machine has confirmed first, then the published table.

    `contains` narrows them to one family -- `--contains zombie` sweeps every short affix around
    the zombies cores and nothing else. The sweep is exhaustive in the affix and seeded in the
    stem, so narrowing the stem is the only way to aim it: an hour spread over every model core in
    the game reaches each of them shallowly, and the same hour over one family reaches that family
    with a longer affix than the whole-corpus run could afford.

    Confirmed names come first deliberately. A name this project has just recovered is the one
    most likely to have siblings nobody has looked for, and the published table has already been
    picked over by everybody.
    """
    table, pool = TYPES[kind]

    out, seen = [], set()
    for source in (snapshot.confirmed_names(pool), snapshot.table_names(table)):
        for name in source:
            name = name.strip().lower().replace("\\", "/")

            # The stem is the middle: strip a directory and any affix already on it, so the sweep
            # is not adding a second prefix in front of an existing one.
            base = name.rpartition("/")[2]
            parts = base.split("_")
            if len(parts) < 3:
                continue

            core = "_".join(parts[1:-1])
            if contains and contains not in core:
                continue
            if core and core not in seen:
                seen.add(core)
                out.append(core)
                if len(out) >= limit:
                    return out

    return out


def main(argv):
    kind = argv[argv.index("--type") + 1] if "--type" in argv else "model"
    if kind not in TYPES:
        raise SystemExit("--type must be one of: %s" % ", ".join(sorted(TYPES)))

    hours = float(argv[argv.index("--hours") + 1]) if "--hours" in argv else 1.0
    alphabet = argv[argv.index("--alphabet") + 1] if "--alphabet" in argv else DEFAULT_ALPHABET
    budget = int(hours * 3600 * RATE)

    # How long an affix can we afford, and over how many stems? Length first: a longer affix
    # reaches shapes that no number of stems can, and the whole point of this method is the shapes.
    wanted = int(argv[argv.index("--stems") + 1]) if "--stems" in argv else None
    contains = argv[argv.index("--contains") + 1].lower() if "--contains" in argv else None

    # The separator count multiplies everything, so it has to be in the sizing rather than
    # discovered afterwards -- an earlier version sized the run without it, then refused its own
    # plan as over budget, which is a confusing way to be right.
    heads = SEPARATORS.get(kind, ["_"])
    joins = len(heads)

    # Whether the emitter's trailing-only branch fires at all. It is guarded by `join == "_"`, so
    # a type swept under `/` alone emits no trailing-only affix and the sizing must not count one.
    # Read from the same list the emitter loops over, so the two cannot drift.
    emits_trailing = "_" in heads

    def per_stem_at(size):
        """Candidates one stem really produces, which is not `cost` times `joins`.

        Only an affix with a *head* has a separator to vary: the loop below emits head+tail and
        head-only once per separator, and the trailing-only case exactly once, because there is no
        leading separator to put anywhere. Multiplying the whole cost by `joins` counted that last
        case twice for `material`, `image` and `sound_asset` -- the three types with two
        separators -- so every plan for them was over-sized.

        That is not free. The refusal below rejects a plan over budget, and the auto-sizing picks
        the longest affix that still fits, so an inflated count made both decisions early: shorter
        affixes and fewer stems than the hour actually buys.
        """
        total = 0
        for step in range(1, size + 1):
            every = cost(step, alphabet)
            trailing_only = len(alphabet) ** step
            total += (every - trailing_only) * joins
            if emits_trailing:
                total += trailing_only
        return total

    if wanted is None:
        # Spend the budget on the longest affix that still leaves a useful number of stems.
        length, stem_budget = 1, 0
        for candidate in range(1, 6):
            if budget // max(per_stem_at(candidate), 1) < 50:
                break
            length, stem_budget = candidate, budget // per_stem_at(candidate)
        stems = stems_for(kind, stem_budget, contains)
    else:
        stems = stems_for(kind, wanted, contains)
        length = 1
        for candidate in range(1, 6):
            if per_stem_at(candidate) * max(len(stems), 1) > budget:
                break
            length = candidate

    # A leading affix can be closed by any separator its type uses; a trailing one is always `_`,
    # because no measured trailing affix is introduced by a slash.
    per_stem = per_stem_at(length)
    total = per_stem * len(stems)

    sys.stderr.write(
        "affix sweep: %s, alphabet of %d, affixes up to %d character(s) combined\n"
        "  %d stems x %d candidates each = %s candidates\n"
        "  at %s/s that is about %.1f minute(s)\n"
        % (kind, len(alphabet), length, len(stems), per_stem,
           format(total, ","), format(RATE, ","), total / RATE / 60.0)
    )

    if total > budget * 1.05:
        sys.stderr.write("  refusing: that is over the %.1f hour budget. Lower --stems.\n" % hours)
        return 2

    if "--plan" in argv:
        return 0

    for stem in stems:
        for size in range(1, length + 1):
            for head, tail in affixes(size, alphabet):
                for join in heads:
                    if head and tail:
                        print("%s%s%s_%s" % (head, join, stem, tail))
                    elif head:
                        print("%s%s%s" % (head, join, stem))
                    elif join == "_":
                        # A trailing-only affix has no leading separator to vary, so emit it once.
                        print("%s_%s" % (stem, tail))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
