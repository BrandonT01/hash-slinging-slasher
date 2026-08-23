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

# Walk up to the repository rather than counting parents. scripts/README.md.
_root = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_root, "scripts", "snapshot.py")):
    if _root == os.path.dirname(_root):
        break
    _root = os.path.dirname(_root)
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


def affixes(longest):
    """Every affix up to `longest` characters: 36 at one, 1,332 at two, 47,988 at three."""
    out, current = [], [""]
    for _ in range(longest):
        current = [held + letter for held in current for letter in ALPHABET]
        out.extend(current)
    return out


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
    longest = int(argv[argv.index("--affix") + 1]) if "--affix" in argv else 2
    # `--plan` sizes the run and stops. Without it the only way to see the plan was to let the
    # generator write every candidate first, which is the run.
    one_side = "--one-side" in argv

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
    every = affixes(longest)
    one = affixes(1)

    # The full cross product by default: every affix up to `--affix` characters on the left
    # against every one on the right, so `aa_core_a`, `a_core_aa` and `aa_core_aa` are all reached
    # rather than only the one-character corners. At two characters that is 1,776,889 per core, so
    # the budget below trims how many cores get swept -- depth first, breadth with what is left,
    # which is how `affix_sweep` sizes itself too.
    #
    # `--one-side` is the opposite trade: long affixes one side at a time, both sides only at one
    # character, 3,961 per core. An hour then reaches every core the family has, shallowly.
    heads, tails = (one, one) if one_side else (every, every)
    per_core = 1 + 2 * len(every) + len(heads) * len(tails)

    print("%s %ss carrying `%s`, recombined into %d cores"
          % (kind, kind, keyword, len(cores)), file=sys.stderr)
    print("%d candidates per core, %d in total" % (per_core, per_core * len(cores)),
          file=sys.stderr)

    if per_core * len(cores) > budget:
        keep = max(1, budget // per_core)
        print("over the %.1f hour budget: sweeping the first %d cores of %d"
              % (hours, keep, len(cores)), file=sys.stderr)
        cores = cores[:keep]

    if "--plan" in argv:
        return 0

    out = sys.stdout
    for core in cores:
        out.write(core + "\n")
        for affix in every:
            out.write(affix + "_" + core + "\n")
            out.write(core + "_" + affix + "\n")
        for head in heads:
            opened = head + "_" + core + "_"
            for tail in tails:
                out.write(opened + tail + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
