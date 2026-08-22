"""Which relations between asset names actually hold, measured rather than guessed.

    python scripts/seams.py                      every relation, strongest first
    python scripts/seams.py --pair material image    one pair, every reduction
    python scripts/seams.py --min-shared 500     hide relations too weak to build on
    python scripts/seams.py --top 40             how many rows to print

Reconnaissance, not a method. It prints numbers, never candidates.

## What this is for

The highest-yield methods in this project are **derivations**: a confirmed material implies an
image name, an image implies its other channels. Measured on the run record, they return a name
every few hundred candidates, against every few million for a blind search -- three orders of
magnitude, and it is not close.

Every derivation that exists was found by somebody noticing a relation by eye, one at a time, and
by 2026-08-22 nobody had found a new one for two days while yield per candidate fell 6.8x in a
single day. That is the real bottleneck here: not compute, not candidates, but **how many
relations anybody has thought to look for.** So this looks for all of them at once.

## How it measures

A name is a **core** wearing decorations: a directory, a leading segment, a trailing segment,
numbers. Two asset types are related when the same core turns up in both wearing each type's own
decorations -- `mc/mtl_wpn_ak47_c` and `i_wpn_ak47_c` are one idea spelled twice.

Which decorations to strip is the whole question, and it is not the same for every pair. So this
does not fix one answer: it strips them **every way**, on each side independently, and reports
which combination lands. That is the part that finds something. `cross_type.py --measure` measures
one reduction -- strip a directory, a leading and a trailing token -- applied to both sides at
once, so a relation that needs a *different* reduction on each side is invisible to it, and the
material-image seam is exactly that shape.

## Reading the output

    shared      cores present in both types under these reductions. Evidence the relation holds
    of B        what share of B's cores that is -- how much of B this relation explains
    only in A   cores A has and B has not. **This is the headroom**: what a derivation built on
                this relation would actually produce

**Read `shared` and `only in A` together.** Large `shared` with near-zero `only in A` is a real
relation that has already been mined out -- true, and worth nothing. Large `only in A` with
near-zero `shared` is not a relation at all, just two reductions that throw away enough to
collide.

## `only in A` is not a yield estimate, and treating it as one wastes passes

This is the most important thing on this page and it was learned the hard way on the day this was
written. The two strongest seams here were both taken through to a run:

    material `no head` -> image `no ends`     75,964 shared (59.98% of image), 181,466 only in A
    material `no ends` -> xmodel `no tail`    15,270 shared (15.57% of xmodel), 125,134 only in A

Both are five times stronger than the figures `cross_type.py --measure` records for the same
pairs, because it applies one reduction to both sides and these seams want a different one on
each. Both relations are real: **85.9%** of the material-image shared cores reconstruct an actual
published image name when spelled with image's own decorations.

Both returned **0 matched ids** -- not zero new, zero matched -- across 113 million and 78 million
candidates, on each of the two games. See METHODS.md.

A core one type has and another has not is overwhelmingly a core the second type **never had**,
not one nobody has named. `only in A` counts the first and cannot tell it from the second. So
this tool ranks *relations*, and nothing here ranks *yield*. What ranks yield is running it, and
`scripts/seam_stems.py --write-plan` plus `confirm_plan` makes that minutes rather than a night.

**Run the seam. Do not reason about the headroom.**

A row that survives that test is a derivation worth writing into `scripts/derive_closure.py`,
which then re-runs it after every pass for free.
"""
import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

TABLES = {
    "xmodel": "fnv1a_xmodels",
    "material": "fnv1a_xmaterials",
    "image": "fnv1a_ximages",
    "xanim": "fnv1a_xanims",
    "sound_alias": "fnv1a_soundbanks_aliases",
}

# A directory is part of what the engine hashes, so it is structure rather than noise.
MAX_DIRECTORY = 6

# A core shorter than this collides for reasons that have nothing to do with a relation. Three
# characters of shared tail will match across any two large name sets and mean nothing.
SHORTEST_CORE = 6


def split_directory(name):
    """`mc/mtl_wpn_ak47` -> (`mc/`, `mtl_wpn_ak47`). Empty directory when there is none."""
    head, sep, rest = name.partition("/")
    if sep and len(head) <= MAX_DIRECTORY and "_" not in head:
        return head + "/", rest
    return "", name


# ---------------------------------------------------------------------------------------------
# The reductions: a name down to what might be shared with another type.
#
# Each is applied to one side of a pair independently of the other, which is the point. A
# reduction is only allowed to *remove* -- a rule that adds is a generator, and measuring with one
# measures the generator rather than the relation.
# ---------------------------------------------------------------------------------------------


def r_whole(name):
    return name


def r_no_directory(name):
    return split_directory(name)[1]


def r_no_head(name):
    """Without the leading segment: `mtl_wpn_ak47` -> `wpn_ak47`. Directory dropped with it."""
    parts = r_no_directory(name).split("_")
    return "_".join(parts[1:]) if len(parts) > 2 else ""


def r_no_tail(name):
    parts = r_no_directory(name).split("_")
    return "_".join(parts[:-1]) if len(parts) > 2 else ""


def r_no_ends(name):
    parts = r_no_directory(name).split("_")
    return "_".join(parts[1:-1]) if len(parts) > 3 else ""


def r_no_head_no_numbers(name):
    return re.sub(r"_?\d+", "", r_no_head(name))


def r_no_ends_no_numbers(name):
    return re.sub(r"_?\d+", "", r_no_ends(name))


def r_no_numbers(name):
    return re.sub(r"_?\d+", "", r_no_directory(name))


def r_no_two_heads(name):
    parts = r_no_directory(name).split("_")
    return "_".join(parts[2:]) if len(parts) > 3 else ""


def r_no_head_no_tail_no_numbers(name):
    return re.sub(r"_?\d+", "", r_no_ends(name))


REDUCTIONS = [
    ("whole", r_whole),
    ("no directory", r_no_directory),
    ("no head", r_no_head),
    ("no tail", r_no_tail),
    ("no ends", r_no_ends),
    ("no two heads", r_no_two_heads),
    ("no numbers", r_no_numbers),
    ("no head, no numbers", r_no_head_no_numbers),
    ("no ends, no numbers", r_no_ends_no_numbers),
]


def load(kind):
    """Every known name of one type: published, submitted by anybody, and confirmed here."""
    names = set(snapshot.table_names(TABLES[kind]))
    names.update(snapshot.confirmed_names(kind))
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def cores(names, reduce):
    """One type's cores under one reduction. Short cores are dropped; they only ever collide."""
    out = set()
    for name in names:
        core = reduce(name)
        if len(core) >= SHORTEST_CORE:
            out.add(core)
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pair", nargs=2, metavar=("FROM", "TO"), help="measure one pair only")
    parser.add_argument("--min-shared", type=int, default=200, help="hide weaker relations")
    parser.add_argument("--top", type=int, default=40, help="how many rows to print")
    parser.add_argument("--types", nargs="+", default=sorted(TABLES), help="which types to cross")
    options = parser.parse_args(argv)

    wanted = sorted(set(options.pair)) if options.pair else options.types
    for kind in wanted:
        if kind not in TABLES:
            raise SystemExit(
                "%s is not an asset type this measures. Pick from: %s"
                % (kind, ", ".join(sorted(TABLES)))
            )

    print("loading names...", file=sys.stderr)
    names = {}
    for kind in wanted:
        names[kind] = load(kind)
        print("  %-12s %s known names" % (kind, format(len(names[kind]), ",")), file=sys.stderr)

    # Every type reduced every way, once. The measurement that follows is then set arithmetic
    # rather than another pass over a third of a million names per combination.
    print("reducing...", file=sys.stderr)
    reduced = {
        (kind, label): cores(names[kind], reduce)
        for kind in wanted
        for label, reduce in REDUCTIONS
    }

    pairs = (
        [tuple(options.pair)]
        if options.pair
        else [(a, b) for a in wanted for b in wanted if a != b]
    )

    rows = []
    for source_kind, target_kind in pairs:
        for source_label, _ in REDUCTIONS:
            source = reduced[(source_kind, source_label)]
            if not source:
                continue
            for target_label, _ in REDUCTIONS:
                target = reduced[(target_kind, target_label)]
                if not target:
                    continue

                shared = len(source & target)
                if shared < options.min_shared:
                    continue

                rows.append(
                    (
                        shared,
                        len(source - target),
                        source_kind,
                        source_label,
                        target_kind,
                        target_label,
                        len(target),
                    )
                )

    # Ranked by what share of the target the relation explains, not by raw hits: a reduction that
    # throws away most of a name collides with everything and would otherwise take every top row.
    rows.sort(key=lambda row: row[0] / max(row[6], 1), reverse=True)

    print(
        "\n%-11s %-19s %-11s %-19s %9s %8s %11s"
        % ("from", "reduced by", "to", "reduced by", "shared", "of B", "only in A")
    )
    for shared, only_in_a, source_kind, source_label, target_kind, target_label, size in rows[
        : options.top
    ]:
        print(
            "%-11s %-19s %-11s %-19s %9s %7.2f%% %11s"
            % (
                source_kind,
                source_label,
                target_kind,
                target_label,
                format(shared, ","),
                100.0 * shared / max(size, 1),
                format(only_in_a, ","),
            )
        )

    if not rows:
        print("  nothing shared %d cores. Lower --min-shared, or the seam is not there."
              % options.min_shared)
        return 0

    print(
        "\n%d relations at or above %d shared cores; showing %d.\n\n"
        "`shared` says the relation is real. `only in A` is NOT a yield estimate: the two strongest\n"
        "rows this has ever produced both matched 0 unnamed ids across 190 million candidates and\n"
        "two games, because a core one type has and another has not is overwhelmingly a core the\n"
        "second type never had. See the note in this file's docstring and in METHODS.md.\n\n"
        "So test a row rather than believing it -- which is now minutes, not a night:\n\n"
        "    python scripts/seam_stems.py --from A --from-reduce R --to B --to-reduce R \\\n"
        "                                 --write-plan plans/a_to_b.txt\n"
        "    bin\\windows\\confirm_plan.exe plans/a_to_b.txt --size\n"
        "    bin\\windows\\confirm_plan.exe plans/a_to_b.txt\n\n"
        "A row that survives that belongs in scripts/derive_closure.py, which re-runs it after\n"
        "every pass for free."
        % (len(rows), options.min_shared, min(len(rows), options.top))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
