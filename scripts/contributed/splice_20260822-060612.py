"""The head of one real name joined to the tail of another, as a runnable plan.

    python scripts/splice.py --write-plan plans/splice.txt
    bin\\windows\\confirm_plan.exe plans/splice.txt --size
    bin\\windows\\confirm_plan.exe plans/splice.txt

`METHODS.md` has listed `compound_splice.py` under *Candidates worth building* since the file
existed, and nobody built it -- because as a generator it is hopeless. Six million heads against
six million tails is 4.2e13 candidates, and a Python generator emits about a million a second, so
printing them would take a year and a half.

As a **plan** it is the shape the engine was built for: heads are the stems, tails are the
endings, and `run_best` multiplies them. That is the whole reason this could be written today and
not last week.

## The idea

Asset names are built from a small vocabulary of segments in conventional orders. A name this
project has never seen is very often a head it has seen wearing a tail it has seen -- from a
*different* name. `p9_zmb_zombie_head_01` and `p9_ally_soldier_body_03` between them offer
`p9_zmb_zombie_body_03`, which neither contains.

This differs from the methods already here, and the distinction is what stops it being a fifth
name for something:

  - `slotswap` substitutes **one token in place**, keeping both sides. This replaces an entire
    tail.
  - `token_edits` changes a name's **length** by one token. This keeps both pieces whole.
  - `tails.py` replaces the last *k* **characters** with arbitrary ones. This replaces a whole
    suffix with one known to be real, which is a much smaller and much better-aimed space.
  - `continuations` offers a prefix the tokens measured to follow **it**. This offers every head
    every tail, so a rare pairing is reached for the same price as a common one.

## Cutting at underscores only

A head is a name cut at an underscore, and so is a tail. Cutting anywhere else produces fragments
that are not segments, and the whole premise is that real names are assembled from real segments.
Directories come along with the head, since `mc/` is part of what the engine hashes.

## Sizing

Both lists are capped by how often a piece is *observed*, commonest first, because the cost is a
product and the tail of that distribution is very long. `--heads` and `--tails` set the caps;
`--size` before committing the time.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

# A head shorter than this is a prefix every name shares and carries no information; a tail
# shorter than this collides with everything.
SHORTEST = 3


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def pieces(names):
    """Every head and tail a name offers, cut at its underscores, counted by how often seen.

    Counted rather than collected, because the lists have to be capped and popularity is the only
    ordering that is not arbitrary. A piece seen in a thousand names is a piece the game's naming
    convention actually uses.
    """
    heads = collections.Counter()
    tails = collections.Counter()

    for name in names:
        at = -1
        while True:
            at = name.find("_", at + 1)
            if at == -1:
                break
            head, tail = name[: at + 1], name[at:]
            if len(head) >= SHORTEST:
                heads[head] += 1
            if len(tail) >= SHORTEST:
                tails[tail] += 1

    return heads, tails


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--heads", type=int, default=400000, help="how many heads to carry")
    parser.add_argument("--tails", type=int, default=120000, help="how many tails to carry")
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    heads, tails = pieces(names)
    print(
        "distinct heads: %s   distinct tails: %s"
        % (format(len(heads), ","), format(len(tails), ",")),
        file=sys.stderr,
    )

    head_list = [piece for piece, _ in heads.most_common(options.heads)]
    tail_list = [piece for piece, _ in tails.most_common(options.tails)]

    plan_path = os.path.join(ROOT, options.write_plan)
    base = os.path.splitext(plan_path)[0]
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)

    heads_path = base + ".heads.txt"
    tails_path = base + ".tails.txt"
    open(heads_path, "w", encoding="utf-8", newline="\n").write("\n".join(head_list) + "\n")
    open(tails_path, "w", encoding="utf-8", newline="\n").write("\n".join(tail_list) + "\n")

    relative = lambda path: os.path.relpath(path, ROOT).replace("\\", "/")

    with open(plan_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by scripts/splice.py. Regenerate rather than editing.\n"
            "#\n"
            "# The head of one real name joined to the tail of another, both cut at underscores.\n"
            "# %s heads of %s seen, %s tails of %s -- capped by how often each piece is observed,\n"
            "# because the cost is a product and the tail of that distribution is very long.\n\n"
            % (
                format(len(head_list), ","),
                format(len(heads), ","),
                format(len(tail_list), ","),
                format(len(tails), ","),
            )
        )
        handle.write("label: head of one name, tail of another\n")
        handle.write(
            "describe: every name cut at each underscore into a head and a tail, then the "
            "%s commonest heads crossed with the %s commonest tails -- so a head wears tails that "
            "belong to other names entirely\n\n"
            % (format(len(head_list), ","), format(len(tail_list), ","))
        )
        handle.write("stem: @%s\n\n" % relative(heads_path))
        handle.write("end: @%s\n\n" % relative(tails_path))
        # `bare: yes` is the empty beginning, which is what a stem-and-ending plan needs. With no
        # `begin:` lines and `bare: no` the engine has no column to iterate and tests nothing.
        handle.write("bare: yes\nfold: yes\n")

    print(
        "\nwrote %s\n      %s (%s heads)\n      %s (%s tails)\n\n"
        "about %s candidates.\n\n    bin\\windows\\confirm_plan.exe %s --size"
        % (
            relative(plan_path),
            relative(heads_path),
            format(len(head_list), ","),
            relative(tails_path),
            format(len(tail_list), ","),
            format(len(head_list) * len(tail_list), ","),
            options.write_plan,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
