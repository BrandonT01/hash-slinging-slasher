"""The beginnings the committed lists cannot express, and the vocabulary of the names that use them.

    python scripts/uncarried.py                 report which beginnings are unreachable
    python scripts/uncarried.py --write-plan plans/uncarried.txt

Writes lists and a plan; `confirm_plan` runs it. Not a generator that prints names -- the whole
point is that this shape is a cross product, and a cross product belongs in the engine rather than
on a pipe. See `src/bin/confirm_plan.rs`.

## The idea

The general search builds every candidate as **beginning + stem + ending**, with the beginnings
taken from `data/prefixes.txt`. A beginning that file does not hold is a beginning the search
cannot produce -- so every unnamed asset whose name starts that way is unreachable by it, however
long it runs, and nothing in a run says so.

`scripts/reach.py` reports this as a *ceiling*: what share of known names the lists could rebuild
at all. It prints the commonest offenders. This takes the same measurement further and turns it
into something runnable: every beginning for which **no cut at all** is carried, ranked by how
many published names sit under it.

Measured 2026-08-22 over 1,460,816 published names: **208 such beginnings head 12,311 names**
between them. Among them a whole family of weapon optics -- `reflex_`, `acog_`, `holo_`,
`dualoptic_`, `mms_` -- that no pass in this repository has ever been able to build a single name
from.

## Why the published names are the seed and not the prize

Every name under these beginnings is already published, so rebuilding one finds nothing. They are
here for two other reasons: they prove the beginning is real rather than a scraping artefact, and
their cores are the vocabulary an *unnamed* sibling would share. The find is the sibling.

## What it returned

First run, 2026-08-22, 135,737,598,880 candidates a side: **5 new on Cold War, 2 on Black Ops 4**,
in about two and a half minutes each. Thin per candidate, and it is ground nothing else in the
repository reaches at all -- which is the only reason it is worth anything. It reopens whenever
`derive_lists.py` changes what the beginning list carries, and whenever the published tables gain
a family the list has no cut of.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seams
import snapshot

ROOT = snapshot.ROOT

TABLES = ("fnv1a_xmodels", "fnv1a_xmaterials", "fnv1a_ximages", "fnv1a_xanims")

# A beginning heading fewer names than this is not a family, it is a handful of oddities -- and
# each one carried costs the whole stems-by-endings cross product again.
LEAST_NAMES = 20

# The longest leading run worth testing against the list. Beyond this a "beginning" is most of the
# name, and finding it uncarried says nothing.
LONGEST = 40

# Cores shorter than this collide with everything and mean nothing as stems.
SHORTEST_CORE = 4


def carried_beginnings():
    path = os.path.join(ROOT, "data", "prefixes.txt")
    with open(path, encoding="utf-8", errors="replace") as handle:
        return {line.strip() for line in handle if line.strip()}


def published():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    return names


def uncarried(names, carried):
    """Beginnings for which no cut at all is in the list, by how many names they head.

    "No cut at all" is the strict test and the right one. A list holding `mc/` can build every
    `mc/...` name whatever follows, so a name is only genuinely unreachable when *nothing* it
    starts with is carried.
    """
    counted = collections.Counter()

    for name in names:
        name = name.strip().lower().replace("\\", "/")
        if not name:
            continue

        if any(name[:cut] in carried for cut in range(1, min(len(name), LONGEST) + 1)):
            continue

        head = name.split("_")[0] + "_" if "_" in name else name
        # A leading `*` is a sound-alias artefact rather than a beginning an asset name wears.
        if head.startswith("*"):
            continue
        counted[head] += 1

    return counted


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--least", type=int, default=LEAST_NAMES, help="fewest names a beginning must head")
    parser.add_argument("--write-plan", metavar="PATH", help="write the lists and a confirm_plan plan")
    options = parser.parse_args(argv)

    carried = carried_beginnings()
    print("beginnings the list carries: %s" % format(len(carried), ","), file=sys.stderr)

    names = published()
    print("published names measured: %s" % format(len(names), ","), file=sys.stderr)

    counted = uncarried(names, carried)
    wanted = [head for head, count in counted.most_common() if count >= options.least]
    covered = sum(counted[head] for head in wanted)

    print(
        "\n%s beginnings no cut of which is carried, heading %s published names.\n"
        % (format(len(wanted), ","), format(covered, ",")),
        file=sys.stderr,
    )
    for head in wanted[:20]:
        print("  %-40s %s names" % (head, format(counted[head], ",")), file=sys.stderr)

    if not options.write_plan:
        for head in wanted:
            print(head)
        print(
            "\nThat is the beginning list. Run again with --write-plan to write the stems and a\n"
            "plan `confirm_plan` can run -- the stems are six figures of lines and belong beside\n"
            "the plan as working data, never in a pull request.",
            file=sys.stderr,
        )
        return 0

    # The stems: what the names under these beginnings are made of, plus everything this machine
    # has confirmed. Reduced several ways, because which decoration an unnamed sibling wears is
    # exactly what is not known.
    reductions = dict(seams.REDUCTIONS)
    heads = tuple(wanted)
    family = [
        name.strip().lower().replace("\\", "/")
        for name in names
        if name.strip().lower().startswith(heads)
    ]

    stems = set()
    for name in family:
        for label in ("no head", "no ends", "no tail"):
            core = reductions[label](name)
            if len(core) >= SHORTEST_CORE:
                stems.add(core)

    for name in snapshot.confirmed_names():
        name = name.strip().lower().replace("\\", "/")
        for label in ("no head", "no ends"):
            core = reductions[label](name)
            if len(core) >= SHORTEST_CORE:
                stems.add(core)

    stems = sorted(stems)

    plan_path = os.path.join(ROOT, options.write_plan)
    base = os.path.splitext(plan_path)[0]
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)

    begins_path = base + ".beginnings.txt"
    stems_path = base + ".stems.txt"
    open(begins_path, "w", encoding="utf-8", newline="\n").write("\n".join(wanted) + "\n")
    open(stems_path, "w", encoding="utf-8", newline="\n").write("\n".join(stems) + "\n")

    relative = lambda path: os.path.relpath(path, ROOT).replace("\\", "/")

    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by scripts/uncarried.py. Regenerate rather than editing.\n"
            "#\n"
            "# %s beginnings for which `data/prefixes.txt` carries no cut at all, heading %s\n"
            "# published names. The general search builds beginning + stem + ending, so it cannot\n"
            "# produce a single name starting any of these ways -- however long it runs.\n\n"
            % (format(len(wanted), ","), format(covered, ","))
        )
        handle.write("label: uncarried beginnings\n")
        handle.write(
            "describe: the %d leading segments no cut of which `data/prefixes.txt` carries, "
            "against cores from the published names that use them and from everything this "
            "machine has confirmed\n\n" % len(wanted)
        )
        handle.write("begin: @%s\n\n" % relative(begins_path))
        handle.write("stem: @%s\n\n" % relative(stems_path))
        handle.write("end: @data/suffixes.txt\n\n")
        handle.write("bare: no\nfold: yes\n")

    print(
        "\nwrote %s\n      %s (%s beginnings)\n      %s (%s stems)\n\n"
        "    bin\\windows\\confirm_plan.exe %s --size"
        % (
            relative(plan_path),
            relative(begins_path),
            format(len(wanted), ","),
            relative(stems_path),
            format(len(stems), ","),
            options.write_plan,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
