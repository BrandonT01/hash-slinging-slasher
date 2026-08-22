"""Turns a seam `scripts/seams.py` measured into the three lists a plan needs.

    python scripts/seam_stems.py --from material --from-reduce "no head" \
                                 --to image --to-reduce "no ends"

    python scripts/seam_stems.py --from material --from-reduce "no head" \
                                 --to image --to-reduce "no ends" --write-plan plans/mat_img.txt

Reconnaissance and plumbing, not a method by itself. It prints stems; `confirm_plan` searches them.

## The loop this closes

`seams.py` measures which relations between asset types hold, and reports two numbers per
relation: `shared`, the evidence it is real, and `only in A`, what a derivation built on it would
produce. A strong row is a method waiting to be written -- and until now writing it meant a fresh
Python generator every time, which is why only a handful of the relations that hold have ever
been mined.

This writes it instead. Given the pair and the two reductions, it emits:

  - **the stems**: cores that type A has under its reduction and type B does not under its. Those
    are exactly the names B is missing if the relation holds.
  - **the beginnings and endings**: the leading and trailing segments B is *measured* to wear,
    commonest first, so the cores get spelled the way B spells things rather than the way A does.

`--write-plan` puts all three into a plan file, which `confirm_plan` then runs at engine speed.
That is the whole path from "this relation looks real" to "these names are confirmed", and none
of it needs a new generator.

## The measured seam this was built for

`seams.py` on 2026-08-22 put `material` reduced by `no head` against `image` reduced by
`no ends` at **75,964 shared cores -- 59.98% of image's**, with **181,466 cores only in material**.
The established figure for this pair, from `cross_type.py --measure`, is 15,770 at 12.44%: it
applies one reduction to both sides, and this seam wants a different one on each. Five times the
seam nobody could see.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seams

# How many of the target type's decorations to offer. The cost is a product, so this is the knob
# that decides whether a plan is minutes or hours: the tail is long and thin, and the first dozen
# of each carry most of the corpus.
DECORATIONS = 24


def decorations(names):
    """The leading and trailing segments a type wears, commonest first.

    Measured off the type itself rather than assumed, because the whole point of spelling a core
    "the way B spells things" is that B's conventions are not A's -- and a leading token guessed
    from the other side of the seam is the one part of this that cannot be checked afterwards.
    """
    import collections

    heads, tails = collections.Counter(), collections.Counter()
    for name in names:
        directory, bare = seams.split_directory(name)
        parts = bare.split("_")
        if len(parts) > 2:
            heads[directory + parts[0] + "_"] += 1
            tails["_" + parts[-1]] += 1
    return heads, tails


def main(argv):
    reductions = {label: reduce for label, reduce in seams.REDUCTIONS}

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", required=True, choices=sorted(seams.TABLES))
    parser.add_argument("--to", dest="target", required=True, choices=sorted(seams.TABLES))
    parser.add_argument("--from-reduce", default="no head", choices=sorted(reductions))
    parser.add_argument("--to-reduce", default="no ends", choices=sorted(reductions))
    parser.add_argument("--decorations", type=int, default=DECORATIONS)
    parser.add_argument("--write-plan", metavar="PATH", help="write a confirm_plan plan file")
    parser.add_argument("--limit", type=int, help="cap how many stems are emitted")
    options = parser.parse_args(argv)

    print("loading names...", file=sys.stderr)
    source = seams.load(options.source)
    target = seams.load(options.target)

    source_cores = seams.cores(source, reductions[options.from_reduce])
    target_cores = seams.cores(target, reductions[options.to_reduce])

    shared = source_cores & target_cores
    only_here = sorted(source_cores - target_cores)

    print(
        "  %s under `%s`: %s cores\n  %s under `%s`: %s cores\n  shared: %s   only in %s: %s"
        % (
            options.source,
            options.from_reduce,
            format(len(source_cores), ","),
            options.target,
            options.to_reduce,
            format(len(target_cores), ","),
            format(len(shared), ","),
            options.source,
            format(len(only_here), ","),
        ),
        file=sys.stderr,
    )

    if not shared:
        print(
            "\nNothing is shared, so this is not a seam and the stems below mean nothing.\n"
            "Run `python scripts/seams.py --pair %s %s` and pick a pair of reductions that does\n"
            "share something." % (options.source, options.target),
            file=sys.stderr,
        )
        return 1

    if options.limit:
        only_here = only_here[: options.limit]

    heads, tails = decorations(target)
    beginnings = [head for head, _ in heads.most_common(options.decorations)]
    endings = [tail for tail, _ in tails.most_common(options.decorations)]

    if not options.write_plan:
        for core in only_here:
            print(core)
        print(
            "\n%s stems on standard output. The beginnings and endings %s wears are:\n  %s\n  %s\n\n"
            "Run again with --write-plan to put all three into a plan `confirm_plan` can run."
            % (
                format(len(only_here), ","),
                options.target,
                " ".join(beginnings[:12]),
                " ".join(endings[:12]),
            ),
            file=sys.stderr,
        )
        return 0

    plan_path = os.path.join(seams.snapshot.ROOT, options.write_plan)
    stems_path = os.path.splitext(plan_path)[0] + ".stems.txt"
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)

    with open(stems_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(only_here) + "\n")

    relative = os.path.relpath(stems_path, seams.snapshot.ROOT).replace("\\", "/")
    label = "%s cores spelled as %s (%s / %s)" % (
        options.source,
        options.target,
        options.from_reduce,
        options.to_reduce,
    )

    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by scripts/seam_stems.py from a seam scripts/seams.py measured.\n"
            "#\n"
            "# %s under `%s` shares %s cores with %s under `%s`, which is %.2f%% of %s.\n"
            "# The %s stems below are the cores %s has and %s has not -- if the relation holds,\n"
            "# they are names %s is missing.\n\n"
            % (
                options.source,
                options.from_reduce,
                format(len(shared), ","),
                options.target,
                options.to_reduce,
                100.0 * len(shared) / max(len(target_cores), 1),
                options.target,
                format(len(only_here), ","),
                options.source,
                options.target,
                options.target,
            )
        )
        handle.write("label: %s\n" % label)
        handle.write(
            "describe: cores present in %s under `%s` and absent from %s under `%s`, spelled with "
            "the %d commonest leading and trailing segments %s is measured to wear\n\n"
            % (
                options.source,
                options.from_reduce,
                options.target,
                options.to_reduce,
                options.decorations,
                options.target,
            )
        )
        for beginning in beginnings:
            handle.write("begin: %s\n" % beginning)
        handle.write("\nstem: @%s\n\n" % relative)
        for ending in endings:
            handle.write("end: %s\n" % ending)
        handle.write("\nbare: yes\nfold: yes\n")

    candidates = len(only_here) * (len(beginnings) + 1) * (len(endings) + 1)
    print(
        "\nwrote %s\n      %s (%s stems)\n\n"
        "about %s candidates. Size it before committing an hour:\n\n"
        "    bin\\windows\\confirm_plan.exe %s --size"
        % (
            os.path.relpath(plan_path, seams.snapshot.ROOT),
            relative,
            format(len(only_here), ","),
            format(candidates, ","),
            options.write_plan,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
