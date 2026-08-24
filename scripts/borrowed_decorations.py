r"""Decorations measured on a build we are *not* searching, worn by the cores we already hold.

    python contrib/borrowed_decorations.py --source contrib/bo3_tools.txt \
        --write-plan plans/borrowed_dec.txt
    bin\windows\confirm_plan.exe plans/borrowed_dec.txt --size

The mirror of `contrib/harvest_decorated.py`. That one takes stems from outside the corpus and
wears our decorations; this takes **decorations** from outside and wears them on our cores.

Both exist because of the same paragraph in METHODS.md:

> Recombining a corpus with itself is bounded by that corpus. Every name Cold War's own bodies and
> Cold War's own variants can compose lies inside the region Cold War's vocabulary already covers
> -- and that region is, by definition, the named one.

A cross has two halves and only one of them has to come from outside to break that bound. Method
22 (*uncarried endings*) is the largest single method here at 6,674 names, and it works precisely
because `data/suffixes.txt` is capped at 4,629 of the 178,016 endings the corpus holds -- but every
one of those 178,016 was still measured on the corpus. This asks the endings and beginnings a
**different build** uses, which the corpus has never carried at any cap.

`contrib/old_title_decorations.py` had the same idea and drew its wrappers from *whole-name*
relations -- a string that turns one known name into another. This is simpler and reaches further:
every token-prefix and token-suffix any source name carries, ranked by how many carry it, minus
whatever `data/prefixes.txt` and `data/suffixes.txt` already say.
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

ROOT = snapshot.ROOT
TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)


def rows(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return [line.strip().lower().replace("\\", "/") for line in handle if line.strip()]


def affixes(names, depth):
    """Every token-prefix and token-suffix, counted."""
    heads, tails = collections.Counter(), collections.Counter()
    for name in names:
        tokens = name.split("_")
        for index in range(1, min(depth, len(tokens) - 1) + 1):
            heads["_".join(tokens[:index]) + "_"] += 1
            tails["_" + "_".join(tokens[-index:])] += 1
        slash = name.find("/")
        if 0 < slash < 12:
            heads[name[: slash + 1]] += 1
    return heads, tails


def cores(depth):
    """Our own names, cut at every token boundary -- what the borrowed decorations go on."""
    names = set()
    for table in TABLES:
        names |= {n.strip().lower().replace("\\", "/") for n in snapshot.table_names(table) if n.strip()}
    names |= {n.strip().lower().replace("\\", "/") for n in snapshot.confirmed_names() if n.strip()}

    out = set()
    for name in names:
        body = name.split("/")[-1]
        tokens = body.split("_")
        for start in range(0, min(depth, len(tokens))):
            for end in range(len(tokens), max(len(tokens) - depth, start), -1):
                piece = "_".join(tokens[start:end])
                if len(piece) >= 5:
                    out.add(piece)
    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", required=True, help="names harvested from another build")
    parser.add_argument("--depth", type=int, default=3, help="tokens an affix may be long")
    parser.add_argument("--core-depth", type=int, default=2,
                        help="tokens that may be cut off each end of one of our names")
    parser.add_argument("--begins", type=int, default=600, help="how many borrowed beginnings")
    parser.add_argument("--ends", type=int, default=3000, help="how many borrowed endings")
    parser.add_argument("--write-plan", required=True)
    options = parser.parse_args(argv)

    carried_begins = set(rows(os.path.join(ROOT, "data", "prefixes.txt")))
    carried_ends = set(rows(os.path.join(ROOT, "data", "suffixes.txt")))

    heads, tails = affixes(rows(options.source), options.depth)
    begins = [h for h, _ in heads.most_common() if h not in carried_begins][: options.begins]
    ends = [t for t, _ in tails.most_common() if t not in carried_ends][: options.ends]
    stems = sorted(cores(options.core_depth))

    print("borrowed beginnings the corpus does not carry: %s\n"
          "borrowed endings the corpus does not carry:    %s\n"
          "our own cores:                                 %s"
          % (format(len(begins), ","), format(len(ends), ","), format(len(stems), ",")),
          file=sys.stderr)

    base = os.path.splitext(options.write_plan)[0]
    for suffix, values in (("begins", begins), ("stems", stems), ("ends", ends)):
        with open("%s.%s.txt" % (base, suffix), "w", encoding="utf-8") as handle:
            handle.write("\n".join(values) + "\n")

    with open(options.write_plan, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by contrib/borrowed_decorations.py. Regenerate rather than editing.\n"
            "#\n"
            "# Beginnings and endings measured on a build we are not searching, worn by cores cut\n"
            "# from names we already hold. The half that breaks the corpus bound is the wrapper.\n"
            "\n"
            "label: borrowed decorations over held cores\n"
            "begin: @%s.begins.txt\n"
            "stem:  @%s.stems.txt\n"
            "end:   @%s.ends.txt\n"
            "bare:  no\n" % (base, base, base)
        )
    print("\nwrote %s\nabout %s candidates."
          % (options.write_plan, format(len(begins) * len(stems) * len(ends), ",")),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
