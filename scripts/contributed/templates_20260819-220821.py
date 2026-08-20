"""Treat a family of known names as a table, and fill in the rows the game never showed you.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/templates.py | ./bin/windows/confirm_list.exe - \
        --label "family column cross product" --script scripts/templates.py

## The problem it solves

`slotswap.py` (METHODS.md method 10) changes exactly **one** token of a known name. That is the
right first cut, and it leaves an obvious gap: this game's longest families vary in several
places at once.

    i_c_t8_mp_spe_firebreak_body1_medic_pouch_small_dotd_exo2_g
    i_c_t8_mp_spe_buffer_body1_r_thigh_l_pouch1_dotd_exo1_c
                  ^^^^^^^^                      ^^^^     ^^^

Who the specialist is, which exo variant it is and which texture channel it is are three
independent choices. A single substitution reaches a name one step from something known; it can
never reach the name that differs in the specialist *and* the channel, and most of the grid is
more than one step from any published corner of it.

## How it generates

Names are bucketed into families by their leading tokens and their token count, so that the
members of a bucket line up column for column. Each column is then measured across the bucket:

    column 5 -> {firebreak, buffer, nomad, ajax, ...}      a small alphabet: a real choice
    column 7 -> {medic, r, l, chest, ...}                  another one
    column 9 -> {c, n, g, m, s, o}                         another one

Columns with a small measured alphabet are the family's **axes**. Columns with a large one are
left alone -- they are the part that identifies the individual asset rather than a choice the
naming scheme offers. Every known name in the bucket is then re-emitted with the full cross
product of the axis alphabets substituted in, which is exactly the grid the family implies and
the game half-published.

Nothing is invented. Every token written into a column was measured in that column, in that
family, in a name known to be real -- the seeding principle, applied to a rectangle instead of a
line.

## What it reads and writes

Reads the community tables, this machine's confirmed findings and the merged submissions, all via
`snapshot.py`. Writes candidate names to standard output, one per line; sizing to standard error.

## Options

    --key N          leading tokens that define a family (default 3)
    --min-members N  ignore a family with fewer known members (default 6)
    --max-axis N     largest column alphabet still treated as an axis (default 8)
    --max-per-name N cap on the cross product applied to one name (default 192)
    --max-axes N     most columns varied at once (default 3)
    --count          print how many candidates this would produce, and stop

## Reusable or one-off

Reusable. It re-measures from the corpus on every run, so it strengthens after any productive
pass.

## What it measured

Recorded in the run note by `confirm_list`; see METHODS.md for the current figures.
"""
import collections
import os
import sys

# Find `scripts/` wherever this file has been filed. A contributed script is written in
# `contrib/` or `scripts/`, and `submit` files it under `scripts/contributed/` -- so a path built
# from a fixed number of parent directories is right in one of those and wrong in the others. This
# has to run *before* `import snapshot`, which is why it is here and not under `__main__`.
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

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

BOUNDARY = "_/"


def split(name):
    """A name as (text, mark) pairs, so that `"".join(t + m)` rebuilds it exactly."""
    tokens, current = [], ""
    for character in name:
        if character in BOUNDARY:
            tokens.append((current, character))
            current = ""
        else:
            current += character
    tokens.append((current, ""))
    return tokens


def main(argv):
    def option(flag, default):
        return int(argv[argv.index(flag) + 1]) if flag in argv else default

    key_length = option("--key", 3)
    min_members = option("--min-members", 6)
    max_axis = option("--max-axis", 8)
    max_per_name = option("--max-per-name", 192)
    max_axes = option("--max-axes", 3)
    counting = "--count" in argv

    print("reading known names", file=sys.stderr)
    names = snapshot.table_names(*THIS_ERA) + snapshot.confirmed_names()
    names = [name.strip().lower().replace("\\", "/") for name in names if name.strip()]
    print("%d known names" % len(names), file=sys.stderr)

    # Bucket into families that line up column for column: same leading tokens, same length.
    families = collections.defaultdict(list)
    for name in names:
        tokens = split(name)
        if len(tokens) <= key_length:
            continue
        key = ("".join(t + m for t, m in tokens[:key_length]), len(tokens))
        families[key].append(tokens)
    print("%d families" % len(families), file=sys.stderr)

    # Measure each column of each family.
    axes_of = {}
    for key, members in families.items():
        if len(members) < min_members:
            continue
        width = key[1]
        columns = [collections.Counter() for _ in range(width)]
        for tokens in members:
            for index, (text, _) in enumerate(tokens):
                columns[index][text] += 1
        axes = [
            (index, [text for text, _ in counter.most_common()])
            for index, counter in enumerate(columns)
            if 2 <= len(counter) <= max_axis
        ]
        # Prefer the widest choices; they are the ones carrying the real grid.
        axes.sort(key=lambda pair: -len(pair[1]))
        if axes:
            axes_of[key] = axes[:max_axes]
    print("%d families with axes" % len(axes_of), file=sys.stderr)

    produced = 0
    batch = []
    out = sys.stdout

    for key, members in families.items():
        axes = axes_of.get(key)
        if not axes:
            continue

        # Trim the cross product to the cap, dropping the narrowest axis first.
        chosen = list(axes)
        while chosen:
            size = 1
            for _, alphabet in chosen:
                size *= len(alphabet)
            if size <= max_per_name:
                break
            chosen.pop()
        if not chosen:
            continue

        for tokens in members:
            texts = [text for text, _ in tokens]
            marks = [mark for _, mark in tokens]

            rows = [texts]
            for index, alphabet in chosen:
                grown = []
                for row in rows:
                    for text in alphabet:
                        if text == row[index]:
                            grown.append(row)
                        else:
                            copy = list(row)
                            copy[index] = text
                            grown.append(copy)
                rows = grown

            for row in rows:
                if row == texts:
                    continue
                produced += 1
                if not counting:
                    batch.append("".join(t + m for t, m in zip(row, marks)))

            if len(batch) >= 65536:
                out.write("\n".join(batch) + "\n")
                batch = []

    if batch and not counting:
        out.write("\n".join(batch) + "\n")

    print("%d candidates" % produced, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
