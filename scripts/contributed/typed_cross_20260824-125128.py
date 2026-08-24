r"""An external corpus crossed **type by type**, each side wearing its own type's decorations.

    python contrib/typed_cross.py --write-plans plans/typed
    bin\windows\confirm_plan.exe plans/typed.image.txt --size

Every cross this project has run pools its stems and asks one set of beginnings and endings about
all of them. That is wrong twice over, and METHODS.md says so in the section on measuring
conventions:

> Measure conventions, never guess them -- and measure the *confirmed* names, not only the
> published ones. The tables hold no xmodel with a directory on it; confirmed xmodels are full of
> them (`splm/`, `clt/`, `cltp/`).

`snapshot.confirmed_names(kind=...)` exists for exactly this, and its docstring is blunt about the
cost of skipping it: *"mixing types silently destroys exactly the measurement being taken."* An
image wears `i_` and `_c`; a material wears `mc/mtl_`; an xanim wears neither. Pooling them spends
almost every candidate asking a question no name of that type could answer.

**What makes this runnable is a typed external corpus, and Black Ops 3's shipped manifests are
one.** `zone_source/all/assetlist/*.csv` is a `type,name` row per asset -- 29,496 image, 18,091
xanim, 8,703 material, 4,141 xmodel -- given away free and with no community content in it, where
`zone/` has every asset in the game but only as strings that have to be harvested and carry no
type at all. See `scripts/harvest_bo3_assetlist.py`.

So each type is its own plan:

  * **cores** -- that type's names in the external corpus, with *its own* measured decorations
    stripped off, so what is left is the thing being borrowed rather than Black Ops 3's spelling
    of it;
  * **beginnings and endings** -- measured on *our* names of the same type, published and
    confirmed.
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

import snapshot

# The wanted types, and the published table each one's convention is measured from.
TYPES = {
    "image": "fnv1a_ximages",
    "material": "fnv1a_xmaterials",
    "xmodel": "fnv1a_xmodels",
    "xanim": "fnv1a_xanims",
}
SHORTEST_CORE = 4


def ours(kind, table):
    """Our names of one type: the published table, plus what this project confirmed as that type."""
    names = {n.strip().lower().replace("\\", "/") for n in snapshot.table_names(table) if n.strip()}
    names |= {
        n.strip().lower().replace("\\", "/")
        for n in snapshot.confirmed_names(kind=kind)
        if n.strip()
    }
    return names


def decorations(names, depth, begins, ends):
    """The beginnings and endings this type actually wears, commonest first."""
    heads, tails = collections.Counter(), collections.Counter()
    for name in names:
        slash = name.rfind("/")
        if 0 < slash < 12:
            heads[name[: slash + 1]] += 1
        body = name[slash + 1 :]
        tokens = body.split("_")
        for index in range(1, min(depth, len(tokens) - 1) + 1):
            heads[name[: slash + 1] + "_".join(tokens[:index]) + "_"] += 1
            tails["_" + "_".join(tokens[-index:])] += 1
    return (
        [head for head, _ in heads.most_common(begins)],
        [tail for tail, _ in tails.most_common(ends)],
    )


def cores(names, heads, tails):
    """A name with its own type's longest matching decorations taken off both ends."""
    heads = sorted(heads, key=len, reverse=True)
    tails = sorted(tails, key=len, reverse=True)
    out = set()
    for name in names:
        body = name
        for head in heads:
            if body.startswith(head) and len(body) - len(head) >= SHORTEST_CORE:
                body = body[len(head) :]
                break
        for tail in tails:
            if body.endswith(tail) and len(body) - len(tail) >= SHORTEST_CORE:
                body = body[: len(body) - len(tail)]
                break
        if len(body) >= SHORTEST_CORE:
            out.add(body)
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default=os.path.join("borrowed", "bo3_assetlist.txt"),
                        help="a `type,name` manifest, or use --typed-source for one already split")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--begins", type=int, default=250)
    parser.add_argument("--ends", type=int, default=1200)
    parser.add_argument("--write-plans", required=True, metavar="PREFIX")
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
            "%s carries no `type,name` rows for %s.\n"
            "Regenerate it with `python scripts/harvest_bo3_assetlist.py --typed`."
            % (options.source, ", ".join(sorted(TYPES)))
        )

    for kind, table in TYPES.items():
        theirs = external.get(kind)
        if not theirs:
            continue

        mine = ours(kind, table)
        heads, tails = decorations(mine, options.depth, options.begins, options.ends)

        # Strip *their* spelling using *their* own decorations, so what crosses is the borrowed
        # thing rather than Black Ops 3's way of writing it.
        their_heads, their_tails = decorations(theirs, options.depth, options.begins, options.ends)
        stems = sorted(cores(theirs, their_heads, their_tails) - mine)

        base = "%s.%s" % (options.write_plans, kind)
        for suffix, values in (("begins", heads), ("stems", stems), ("ends", tails)):
            with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
                handle.write("\n".join(values) + "\n")

        with open("%s.txt" % base, "w", encoding="utf-8") as handle:
            handle.write(
                "# Written by contrib/typed_cross.py. Regenerate rather than editing.\n"
                "#\n"
                "# %s cores from an external corpus, under the beginnings and endings OUR %s\n"
                "# names are measured to wear. Types are never mixed: an image wears `i_` and\n"
                "# `_c`, a material wears `mc/mtl_`, and pooling them spends almost every\n"
                "# candidate on a question no name of that type could answer.\n"
                "\n"
                "label: %s cores borrowed, %s decorations measured\n"
                "begin: @%s.begins.txt\n"
                "stem:  @%s.stems.txt\n"
                "end:   @%s.ends.txt\n"
                "bare:  no\n" % (kind, kind, kind, kind, base, base, base)
            )

        print(
            "%-9s ours %s   theirs %s -> %s core(s)   %s begin x %s end   %s candidates"
            % (
                kind,
                format(len(mine), ","),
                format(len(theirs), ","),
                format(len(stems), ","),
                format(len(heads), ","),
                format(len(tails), ","),
                format(len(heads) * len(stems) * len(tails), ","),
            ),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
