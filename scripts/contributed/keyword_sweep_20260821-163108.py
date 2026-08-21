"""Every known name carrying a keyword, recombined with itself and swept with short affixes.

    python contrib/keyword_sweep.py --keyword zombie --type model | ^
        bin\\windows\\confirm_list.exe - --label "keyword sweep: zombie" ^
        --script contrib/keyword_sweep.py --game BLKOPS04

`scripts/affix_sweep.py` sweeps short affixes around a *core*, and it is deliberately blind to
what the core says -- it takes the middle of a name and wraps it. That is the right shape for the
whole corpus and the wrong one for a family: an hour spread across every model core in the game
reaches each of them once, and the affix it can afford gets shorter the more cores there are.

This is the family version, and it does two things that one does not:

  - **the name is recombined with itself.** Every contiguous run of its own tokens that still
    carries the keyword, every one-token deletion, and every adjacent swap. `p9_zmb_zombie_head_01`
    offers `zmb_zombie_head`, `zombie_head_01`, `zmb_zombie_01`, `zombie_zmb_head_01` and so on.
    Real names in a family are each other's rearrangements far more often than they are each
    other's neighbours in a frequency table.
  - **then the affixes go on**, exactly as the sweep does it: every one and two character leading
    and trailing token, so an affix used once in the game is reached even though no measured list
    can hold it.

The two together are the point. An affix sweep alone needs the core to be right; a recombination
alone needs the affix to have been measured. A family is small enough to afford both at once.

Nothing here is unseeded except the affixes: every token in every candidate comes from a name the
game itself holds.
"""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot  # noqa: E402

# What a table is called, and which pool its confirmed names live in.
TYPES = {
    "model": ("fnv1a_xmodels", "xmodel"),
    "material": ("fnv1a_xmaterials", "material"),
    "image": ("fnv1a_ximages", "image"),
    "anim": ("fnv1a_xanims", "xanim"),
}

ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"

# Roughly what `confirm_list` reads and hashes per second, measured on the zombies run:
# 452,317,008 candidates in 299 seconds.
RATE = 1_500_000


def affixes():
    """Every one and two character affix, which is 36 + 1,296 of them."""
    one = list(ALPHABET)
    two = [a + b for a in ALPHABET for b in ALPHABET]
    return one, two


def rearrangements(parts, keyword):
    """The name said in the ways the same family says it elsewhere.

    Contiguous runs, one-token deletions and adjacent swaps -- and only the ones that still carry
    the keyword, since a variant that has dropped it is no longer this family and is the general
    search's job.
    """
    out = []

    for start in range(len(parts)):
        for end in range(start + 1, len(parts) + 1):
            run = parts[start:end]
            if any(keyword in token for token in run):
                out.append("_".join(run))

    for index in range(len(parts)):
        without = parts[:index] + parts[index + 1:]
        if without and any(keyword in token for token in without):
            out.append("_".join(without))

    for index in range(len(parts) - 1):
        swapped = list(parts)
        swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
        out.append("_".join(swapped))

    return out


def seeds(kind, keyword):
    """Every name of this type, in either game, that carries the keyword."""
    table, pool = TYPES[kind]
    seen = set()

    for source in (snapshot.confirmed_names(pool), snapshot.table_names(table)):
        for name in source:
            name = name.strip().lower().replace("\\", "/")
            if keyword not in name:
                continue

            base = name.rpartition("/")[2]
            if base and base not in seen:
                seen.add(base)
                yield base


def main(argv):
    keyword = argv[argv.index("--keyword") + 1].lower() if "--keyword" in argv else "zombie"
    kind = argv[argv.index("--type") + 1] if "--type" in argv else "model"
    hours = float(argv[argv.index("--hours") + 1]) if "--hours" in argv else 1.0

    if kind not in TYPES:
        raise SystemExit("--type must be one of: %s" % ", ".join(sorted(TYPES)))

    budget = int(hours * 3600 * RATE)

    cores = set()
    for base in seeds(kind, keyword):
        cores.add(base)
        for variant in rearrangements(base.split("_"), keyword):
            if variant:
                cores.add(variant)

    cores = sorted(cores)
    one, two = affixes()

    # What one core costs: itself, a leading affix, a trailing affix, and both at one character.
    # Two-character affixes go on one side only -- both sides at two characters is 1.7M per core,
    # which buys length nobody has evidence for at the price of everything else.
    per_core = 1 + 2 * (len(one) + len(two)) + len(one) * len(one)

    print("%s %ss carrying `%s`, recombined into %d cores"
          % (kind, kind, keyword, len(cores)), file=sys.stderr)
    print("%d candidates per core, %d in total" % (per_core, per_core * len(cores)),
          file=sys.stderr)

    if per_core * len(cores) > budget:
        keep = max(1, budget // per_core)
        print("over the %.1f hour budget: sweeping the first %d cores of %d"
              % (hours, keep, len(cores)), file=sys.stderr)
        cores = cores[:keep]

    out = sys.stdout
    for core in cores:
        out.write(core + "\n")
        for head in one + two:
            out.write(head + "_" + core + "\n")
            out.write(core + "_" + head + "\n")
        for head in one:
            for tail in one:
                out.write(head + "_" + core + "_" + tail + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
