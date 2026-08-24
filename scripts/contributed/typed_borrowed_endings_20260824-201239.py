r"""Endings measured on another build, kept type by type, worn by our own cores.

    python contrib/typed_borrowed_endings.py --write-plans plans/tbe
    bin\windows\confirm_plan.exe plans/tbe.xanim.txt --size

## What this is, and what it is not

`scripts/borrowed_decorations.py` already takes decorations from a build we are not searching and
wears them on cores we already hold. It is the right idea and it is **pooled**: one `--source` of
names, one set of beginnings and one set of endings, asked about every asset type at once.

METHODS.md §18 is about exactly that mistake in the other direction, and measured what fixing it
was worth on the same corpus, the same day, against both games:

| | candidates | names |
|---|---|---|
| pooled, untyped | 346 B | **0** |
| typed | 5.5 B | **50** |

*"An image wears `i_` and `_c`; a material wears `mc/mtl_`; an xanim wears neither. Pooling them
spends almost every candidate asking a question no name of that type could answer."* That applies
to a borrowed ending as much as to a borrowed core, and nothing has applied it to one yet.

## Why a borrowed ending reaches somewhere a measured one cannot

Our ending lists are measured on names we already know. So an ending our games use is in the list
**if the names using it have been found**. An ending used in Black Ops 4 only on assets nobody has
named is invisible to that measurement -- and Black Ops 3 is Black Ops 4's direct predecessor, same
studio, same engine, same conventions.

That is the `uncarried.py` argument pointed at an external corpus, and the overlap says the two
vocabularies really are the same grammar (measured 2026-08-24,
`contrib/measure_borrowed_decorations.py`):

| type | their endings | we already carry | new to us |
|---|---|---|---|
| xanim | 19,274 | 6,086 (**31.6%**) | 13,188 |
| xmodel | 8,664 | 1,449 (16.7%) | 7,215 |
| material | 21,991 | 3,182 (14.5%) | 18,809 |
| image | 60,000 | 4,985 (8.3%) | 55,015 |

A third of Black Ops 3's animation endings are ones our corpus independently arrived at, which is
the control: the borrowing is meaningful. The rest is the ground.

**Only the endings are borrowed.** The same measurement says their *beginnings* do not transfer --
`t7_icon_attach_`, `mc/mtl_zmb_t7_`, `attach_t7_loot_` -- because a beginning carries the title tag
and an ending carries the part. So beginnings stay ours.
"""
import argparse
import collections
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

from typed_cross import TYPES, cores, decorations, ours


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=os.path.join("borrowed", "bo3_assetlist.txt"),
                        help="a `type,name` manifest from harvest_bo3_assetlist.py --typed")
    parser.add_argument("--write-plans", required=True, metavar="PREFIX")

    parser.add_argument("--begins", type=int, default=1500, help="our beginnings, per type")
    parser.add_argument("--ends", type=int, default=8000, help="their new endings, per type")

    # Widening `--ends` from 8,000 to 24,000 redoes the first 8,000 -- a third of the work for
    # ground already swept. `--ends-skip 8000` writes the COMPLEMENT instead, which is the same
    # trick `contrib/heads_slash.py` uses against the widened head alphabet.
    parser.add_argument("--ends-skip", type=int, default=0,
                        help="drop this many of the highest-ranked borrowed endings first")
    parser.add_argument("--depth", type=int, default=4, help="tokens a decoration may be long")

    # Our cores are stripped shallowly on purpose: deep stripping is what destroys the middle,
    # measured at -61% on xanim in METHODS §18's note on the coupled flags.
    parser.add_argument("--strip-depth", type=int, default=3)
    parser.add_argument("--strip-begins", type=int, default=250)
    parser.add_argument("--strip-ends", type=int, default=1200)

    parser.add_argument("--kind", help="only this type")
    options = parser.parse_args(argv)

    external = collections.defaultdict(set)
    with open(options.source, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            kind, _, name = line.partition(",")
            name = name.strip().strip('"').replace("\\", "/").lower()
            kind = kind.strip().lower()
            if name and kind in TYPES:
                external[kind].add(name)

    if not external:
        raise SystemExit(
            "%s carries no `type,name` rows.\n"
            "Regenerate it with `python scripts/harvest_bo3_assetlist.py --typed`."
            % options.source
        )

    for kind, table in sorted(TYPES.items()):
        if options.kind and kind != options.kind:
            continue
        theirs = external.get(kind)
        if not theirs:
            continue

        mine = ours(kind, table)

        # Ours: the beginnings we wear, and the cores we hold.
        our_heads, our_tails = decorations(mine, options.depth, options.begins, options.ends)
        strip_h, strip_t = decorations(
            mine, options.strip_depth, options.strip_begins, options.strip_ends)
        stems = sorted(cores(mine, strip_h, strip_t))

        # Theirs: endings measured on their names of the SAME type, minus everything we already
        # carry -- what is left is the ground our own measurement cannot see.
        _, their_tails = decorations(theirs, options.depth, options.begins, 200000)
        carried = set(our_tails)
        borrowed = [t for t in their_tails if t not in carried]
        borrowed = borrowed[options.ends_skip : options.ends_skip + options.ends]

        base = "%s.%s" % (options.write_plans, kind)
        for suffix, values in (
            ("begins", our_heads), ("stems", stems), ("ends", borrowed)
        ):
            with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
                handle.write("\n".join(values) + "\n")

        with open("%s.txt" % base, "w", encoding="utf-8") as handle:
            handle.write(
                "# Written by contrib/typed_borrowed_endings.py. Regenerate rather than editing.\n"
                "#\n"
                "# OUR %s cores and OUR %s beginnings, under the endings Black Ops 3's own\n"
                "# %s names wear and our corpus has never shown. Types are never mixed: an\n"
                "# ending belongs to a part, and a part belongs to a type.\n"
                "\n"
                "label: %s cores under borrowed %s endings\n"
                "begin: @%s.begins.txt\n"
                "stem:  @%s.stems.txt\n"
                "end:   @%s.ends.txt\n"
                "bare:  no\n" % (kind, kind, kind, kind, kind, base, base, base)
            )

        print("%-9s ours %s -> %s core(s)   %s begin x %s borrowed end   %s candidates"
              % (kind, format(len(mine), ","), format(len(stems), ","),
                 format(len(our_heads), ","), format(len(borrowed), ","),
                 format(len(our_heads) * len(stems) * len(borrowed), ",")))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
