"""Names one *character* away from a name we already have, where that character changes the length.

    python contrib/char_edits.py --type image | bin\\windows\\confirm_list.exe - \
        --label "character deletion and transposition" --script contrib/char_edits.py

## The gap this fills

`token_edits.py` opens its case by observing that every method in `METHODS.md` substitutes and
none of them changes a name's length, then fixes that at *token* granularity -- a name plus or
minus one whole word. The character granularity underneath it was never filled in, and the two do
not overlap:

  - `final_byte` solves the **last** character, `tails`/`heads` replace the first or last k
    characters. All three are fixed-width substitutions: k characters in, k characters out.
  - `confirm_variants` moves a number in place, `slotswap` and `templates` replace whole tokens.
  - `token_edits` adds or removes a whole token between two underscores.

So a name that is a known name with **one character dropped**, or with **two adjacent characters
in the other order**, is unreachable by all of them however long they run:

    wpn_ak47_scope_01
    wpn_ak47_scope_001    <- an insertion, reachable by nothing (and expensive: alphabet x length)
    wpn_ak47_scope_1      <- a deletion, reachable by nothing, and this file's business
    wpn_ak47_scoep_01     <- a transposition, likewise

Zero-padding is why this is worth a pass rather than a curiosity. A number written `_01` in one
asset and `_1` in its sibling is a one-character deletion and nothing here can spell it, because
every fixed-width method must return a string of the same length it took.

## Why deletion and transposition, and not insertion

Deletion and transposition are **free of an alphabet**: each position of each name yields exactly
one candidate, so the whole corpus costs `names x length` rather than `names x length x |alphabet|`.
That is tens of millions against tens of billions, and it is the entire reason this is cheap enough
to be worth trying before anything expensive. Insertion is the same idea multiplied by 37 and
belongs in a plan if either of these two pays.

## What it does not touch

**The directory is kept whole.** Editing characters inside `mc/` or `vox/scripted/` invents
directories that do not exist -- the same closed-vocabulary argument `token_edits.split` makes --
so edits are confined to everything after the final slash.
"""

import argparse
import os
import sys

# Find `scripts/` wherever this file has been filed -- see scripts/README.md.
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

TYPES = {
    "model": ("fnv1a_xmodels", "xmodel"),
    "material": ("fnv1a_xmaterials", "material"),
    "image": ("fnv1a_ximages", "image"),
    "anim": ("fnv1a_xanims", "xanim"),
}

# Past this the basename is a generated identifier rather than a composed one -- a mesh tail is 26
# base32 characters hashed from the mesh itself -- and editing one produces nothing.
MAX_BASENAME = 96


def corpus(kind):
    table, confirmed = TYPES[kind]
    names = list(snapshot.table_names(table)) + list(snapshot.confirmed_names(confirmed))

    out = set()
    for name in names:
        name = name.strip().lower().replace("\\", "/")
        if name:
            out.add(name)
    return out


def edits(name, deletions, transpositions):
    """Every one-character deletion and adjacent transposition of `name`, leaving its directory
    alone. Deduplicated: repeated characters otherwise yield the same string twice."""
    cut = name.rfind("/") + 1
    head, base = name[:cut], name[cut:]
    if not base or len(base) > MAX_BASENAME:
        return

    seen = set()
    if deletions:
        for i in range(len(base)):
            edited = base[:i] + base[i + 1 :]
            if edited and edited not in seen:
                seen.add(edited)
                yield head + edited
    if transpositions:
        for i in range(len(base) - 1):
            if base[i] == base[i + 1]:
                continue
            edited = base[:i] + base[i + 1] + base[i] + base[i + 2 :]
            if edited not in seen:
                seen.add(edited)
                yield head + edited


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--type", choices=sorted(TYPES), action="append")
    parser.add_argument("--no-deletions", action="store_true")
    parser.add_argument("--no-transpositions", action="store_true")
    parser.add_argument("--size", action="store_true", help="count candidates, emit none")
    args = parser.parse_args(argv)

    kinds = args.type or sorted(TYPES)
    deletions = not args.no_deletions
    transpositions = not args.no_transpositions

    total = 0
    write = sys.stdout.write
    for kind in kinds:
        names = corpus(kind)
        count = 0
        for name in names:
            for candidate in edits(name, deletions, transpositions):
                count += 1
                if not args.size:
                    write(candidate + "\n")
        print(f"{kind}: {len(names)} names, {count} candidates", file=sys.stderr)
        total += count

    print(f"{total} candidates", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
