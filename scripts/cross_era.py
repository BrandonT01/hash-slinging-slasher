"""The newer titles' names, reduced to cores and respelled the way our two games spell things.

    python scripts/cross_era.py --write-plan plans/crossera.txt
    bin\\windows\\confirm_plan.exe plans/crossera.txt --size
    bin\\windows\\confirm_plan.exe plans/crossera.txt --game BLKOPS04

`METHODS.md` has listed `cross_era.py` under *Candidates worth building* since the file existed.
This is it.

## Why it is not the dead end that looks like it

The dead-ends table records: *"Names published for the newer titles (`_v2` tables) hashed against
our games -- **0** of 1,175,524 names, against 336,505 unnamed ids."* That measurement is real and
this does not contradict it, because it asked a different question.

Hashing a Modern Warfare name **verbatim** asks whether Cold War holds an asset under Modern
Warfare's exact spelling. It does not, and it never would: the eras decorate names differently.
What survives an engine change is the **core** -- the weapon, the character, the material it is
made of -- and that is what this takes. `mw_ximage_ak47_barrel_col` and `i_wpn_t9_ak47_barrel_c`
are the same idea under two conventions, and only one of them is in our tables.

So: reduce every newer-title name to its core, drop the cores our own corpus already has (those
are not findings), and spell the rest with the beginnings and endings **our** games are measured
to wear.

## Why this shape is worth trying when so much else is dead

Three measurements say recombining our own corpus is finished -- cross-type seams at 0 in 190 M
candidates, `splice.py` at 1 per 13.7 billion. What is measured **live** is importing vocabulary
from *outside*: the Black Ops 1 and 3 build-name methods run at 1 name per 2,405 candidates.

That is the distinction worth holding on to. A method that rearranges what we already have is
working against a corpus that has been rearranged for days. A method that brings in words nobody
here has seen is not.

The `_v2` tables are 81 MB of exactly that, and they are already on disk.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seams
import snapshot

ROOT = snapshot.ROOT

# The newer titles: Vanguard, Modern Warfare II and III, Black Ops 6. Different engine era,
# different naming conventions, a great deal of shared content.
NEWER = (
    "fnv1a_ximages_v2",
    "fnv1a_xmaterials_v2",
    "fnv1a_xanims_v2",
    "fnv1a_xsounds_v2",
    "fnv1a_soundbanks_aliases_v2",
)

# Our two games, which supply the spelling rather than the vocabulary.
OURS = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

# A core shorter than this collides with everything and says nothing about the asset.
SHORTEST_CORE = 6


def cores_of(names, labels=("no head", "no ends", "no directory")):
    """Every core a set of names offers, under several reductions.

    Several rather than one, because which decoration a *foreign* convention puts on a name is
    exactly what is not known -- that is the whole difficulty. Taking three reductions and letting
    the search decide costs three times the stems and removes the guess.
    """
    reductions = dict(seams.REDUCTIONS)
    out = set()
    for name in names:
        for label in labels:
            core = reductions[label](name)
            if len(core) >= SHORTEST_CORE:
                out.add(core)
    return out


def decorations(names, heads_wanted, tails_wanted):
    """The beginnings and endings our games are measured to wear, commonest first."""
    heads, tails = collections.Counter(), collections.Counter()
    for name in names:
        directory, bare = seams.split_directory(name)
        parts = bare.split("_")
        if len(parts) > 2:
            heads[directory + parts[0] + "_"] += 1
            tails["_" + parts[-1]] += 1
    return (
        [head for head, _ in heads.most_common(heads_wanted)],
        [tail for tail, _ in tails.most_common(tails_wanted)],
    )


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--heads", type=int, default=1200)
    parser.add_argument("--tails", type=int, default=6000)
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    theirs = set()
    for table in NEWER:
        theirs.update(
            name.strip().lower().replace("\\", "/")
            for name in snapshot.table_names(table)
            if name.strip()
        )
    print("newer-title names: %s" % format(len(theirs), ","), file=sys.stderr)

    ours = set()
    for table in OURS:
        ours.update(
            name.strip().lower().replace("\\", "/")
            for name in snapshot.table_names(table)
            if name.strip()
        )
    ours.update(
        name.strip().lower().replace("\\", "/")
        for name in snapshot.confirmed_names()
        if name.strip()
    )
    print("our names: %s" % format(len(ours), ","), file=sys.stderr)

    # Cores our corpus already holds are not vocabulary this brings in -- they are what every other
    # method here is already built on, and crossing them again is the recombination measured dead.
    theirs_cores = cores_of(theirs)
    ours_cores = cores_of(ours)
    fresh = sorted(theirs_cores - ours_cores)

    print(
        "cores: theirs %s, ours %s, **new to us %s**"
        % (
            format(len(theirs_cores), ","),
            format(len(ours_cores), ","),
            format(len(fresh), ","),
        ),
        file=sys.stderr,
    )

    heads, tails = decorations(ours, options.heads, options.tails)

    plan_path = os.path.join(ROOT, options.write_plan)
    base = os.path.splitext(plan_path)[0]
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)

    paths = {}
    for what, entries in (("stems", fresh), ("heads", heads), ("tails", tails)):
        paths[what] = base + ".%s.txt" % what
        open(paths[what], "w", encoding="utf-8", newline="\n").write("\n".join(entries) + "\n")

    relative = lambda path: os.path.relpath(path, ROOT).replace("\\", "/")

    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by scripts/cross_era.py. Regenerate rather than editing.\n"
            "#\n"
            "# %s cores that the newer titles' tables hold and ours do not, spelled with the %s\n"
            "# commonest beginnings and %s commonest endings our two games are measured to wear.\n"
            "#\n"
            "# The dead-ends table records those tables as dead *hashed verbatim*. This asks a\n"
            "# different question: not whether Cold War holds a Modern Warfare name, but whether it\n"
            "# holds the same asset under its own convention.\n\n"
            % (
                format(len(fresh), ","),
                format(len(heads), ","),
                format(len(tails), ","),
            )
        )
        handle.write("label: newer-title cores respelled\n")
        handle.write(
            "describe: cores taken from the _v2 tables under three reductions, minus every core "
            "our own corpus already holds, crossed with the beginnings and endings our games "
            "actually wear\n\n"
        )
        handle.write("begin: @%s\n\n" % relative(paths["heads"]))
        handle.write("stem: @%s\n\n" % relative(paths["stems"]))
        handle.write("end: @%s\n\n" % relative(paths["tails"]))
        handle.write("bare: yes\nfold: yes\n")

    total = len(fresh) * (len(heads) + 1) * (len(tails) + 1)
    print(
        "\nwrote %s\n\nabout %s candidates.\n\n    bin\\windows\\confirm_plan.exe %s --size"
        % (relative(plan_path), format(total, ","), options.write_plan),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
