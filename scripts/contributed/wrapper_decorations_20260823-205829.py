"""Decorations that wrap a *whole* name, measured rather than listed.

    python contrib/wrapper_decorations.py --write-plan plans/wrappers.txt
    bin\\windows\\confirm_plan.exe plans/wrappers.txt --size
    bin\\windows\\confirm_plan.exe plans/wrappers.txt

## What this asks that nothing else does

Every beginning-list method here crosses a beginning with a **core** -- a name with something
trimmed off it. `uncarried.py` cuts at a segment boundary, `redecorations.py` ranks a beginning by
how much of its vocabulary is borrowed, `mcdp/` won by being crossed with the whole material
vocabulary rather than its own.

This asks the narrower question those all step over: **which strings turn one entire known name
into another entire known name.** `[korea15]` + `i_c_t8_zmb_ofc_hero_dempsey_jacket1_c` is a real
image, and so is the name without it. Nothing is trimmed; the base name is carried whole.

That makes the borrowed share `redecorations.py` ranks by **100% by construction** -- every
instance counted is, by definition, a name we already hold wearing this decoration. The dead end
recorded in METHODS.md for uncarried beginnings ("0 on Black Ops 4 and 7 on Cold War in 945 M
candidates") is the opposite case: beginnings crossed with a vocabulary that was never theirs. The
note closing it says to rank by borrowed share first, and this is that ranking taken to its limit.

## Measured on 2026-08-23, over 1,521,504 known names

4,893 distinct strings wrap one known name into another. 309 of them are absent from
`data/prefixes.txt` at three instances or more, so no general pass can build them:

    mcdp/mtl_          385     the one already mined -- 2,846 names on 2026-08-23
    [korea15]          151     a regional build variant. 151 of 151 base names are known
    paintjob_          132
    mc/mtl_menu_        77
    mc/mtl_wpn_t9_      70
    [japanese]          39     39 of 39 base names known
    img_trim_           31
    ui_icon_mtx_tier_   30

`[korea15]`, `[japanese]` and `[safe]` are worth calling out because they are invisible to every
character-level method in the project as well: `[` occurs in no name's last four characters, so the
alphabet `tails.py` measures cannot spell them from either end.

The cost is one beginning list against the corpus -- 309 x 1.5 M, about 470 M candidates, seconds
of engine time. `--min` moves the threshold; `--suffix` measures the mirror, decorations that wrap
a name at the *end*, which is a much longer list (8,059 boundary-anchored at fifteen instances) and
overlaps the uncarried-endings methods already run.
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

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

# A decoration longer than this is a name in its own right rather than a wrapper, and the count of
# base names that could wear it falls to one or two.
LONGEST = 20

# Below this a decoration is a coincidence of two names sharing a tail, not a convention.
SHORTEST_BASE = 4


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def carried(filename):
    path = os.path.join(_root, "data", filename)
    with open(path, encoding="utf-8") as handle:
        return {line.strip().lower() for line in handle if line.strip()}


def measure(names, suffix):
    """{decoration: how many known names it wraps into another known name}."""
    counted = collections.Counter()
    for name in names:
        for length in range(1, min(LONGEST, len(name) - SHORTEST_BASE) + 1):
            base = name[:-length] if suffix else name[length:]
            if base in names:
                counted[name[-length:] if suffix else name[:length]] += 1
    return counted


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min", type=int, default=3, help="fewest instances to carry")
    parser.add_argument(
        "--suffix",
        action="store_true",
        help="measure decorations that wrap the END of a name instead of the front",
    )
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    already = carried("suffixes.txt" if options.suffix else "prefixes.txt")
    counted = measure(names, options.suffix)
    decorations = sorted(
        (
            decoration
            for decoration, count in counted.items()
            if count >= options.min and decoration not in already
        ),
        key=lambda decoration: (-counted[decoration], decoration),
    )

    print(
        "%s decorations found: %s   uncarried at >=%d instances: %s"
        % (
            "suffix" if options.suffix else "prefix",
            format(len(counted), ","),
            options.min,
            format(len(decorations), ","),
        ),
        file=sys.stderr,
    )
    for decoration in decorations[:12]:
        print("    %-24s %6d" % (decoration, counted[decoration]), file=sys.stderr)

    if not decorations:
        raise SystemExit("nothing uncarried at this threshold; lower --min")

    base = os.path.splitext(options.write_plan)[0]
    side = "endings" if options.suffix else "beginnings"
    stem_path, dec_path = base + ".stems.txt", "%s.%s.txt" % (base, side)
    for path, rows in ((stem_path, sorted(names)), (dec_path, decorations)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(rows) + "\n")

    def relative(path):
        return os.path.relpath(path, _root).replace("\\", "/")

    with open(options.write_plan, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by contrib/wrapper_decorations.py%s. Regenerate rather than editing.\n"
            "#\n"
            "# Decorations measured to turn one WHOLE known name into another whole known name,\n"
            "# kept only where data/%s cannot express them, against every name we hold.\n"
            "# Borrowed share is 100%% by construction -- see this script's docstring.\n"
            "\n"
            "label: wrapper decorations, %s side\n"
            "describe: strings measured to wrap one entire known name into another entire known name and absent from the carried list, against the whole corpus uncut\n"
            "\n"
            "stem: @%s\n"
            "\n"
            "%s: @%s\n"
            "\n"
            "bare: %s\n"
            "fold: yes\n"
            % (
                " --suffix" if options.suffix else "",
                "suffixes.txt" if options.suffix else "prefixes.txt",
                "suffix" if options.suffix else "prefix",
                relative(stem_path),
                "end" if options.suffix else "begin",
                relative(dec_path),
                # `bare` flips meaning between the two sides, and getting it wrong does not fail
                # loudly. With the decorations in the `begin` column they are the only opening the
                # plan has, so the bare stem must stay out. With them in the `end` column there is
                # no `begin` line at all, and `bare: yes` is what supplies the empty one.
                "yes" if options.suffix else "no",
            )
        )

    print(
        "wrote %s\n      %s (%s stems)\n      %s (%s decorations)\n\nabout %s candidates."
        % (
            options.write_plan,
            stem_path,
            format(len(names), ","),
            dec_path,
            format(len(decorations), ","),
            format(len(names) * len(decorations), ","),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
