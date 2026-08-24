r"""Build strings worn as cores, under the decorations our own names carry.

    python contrib/harvest_decorated.py --strings logs/harvest_all.txt \
        --write-plan plans/harvest_dec.txt
    bin\windows\confirm_plan.exe plans/harvest_dec.txt --size
    bin\windows\confirm_plan.exe plans/harvest_dec.txt

`contrib/harvest_bo4.py` reads names out of the installed build and asks the game about them
verbatim. Verbatim is only half of it: a string in a script or a UI table is usually the *core*
of an asset name rather than the whole of it, so `loot_ui_icon_stickers_skate_4_large` is a
candidate, and so are `i_loot_ui_icon_stickers_skate_4_large`, `mc/mtl_...` and `..._c`.

This is the one shape METHODS.md says should work. Every previous decoration cross here has taken
its stems from the corpus it was searching, and every one of them is bounded by that corpus:

> Recombining a corpus with itself is bounded by that corpus. Every name Cold War's own bodies and
> Cold War's own variants can compose lies inside the region Cold War's vocabulary already covers
> -- and that region is, by definition, the named one. The unnamed assets are unnamed *because*
> they are outside it.

and the note on the capped beginning list says the same thing from the other side: *"the cap
matters when the stems come from **outside** it."* These stems are from outside it. They were
never in any table, they were read off the disk, and the game's own decorations are exactly what
turns one into an asset name.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rows(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return [line.strip() for line in handle if line.strip()]


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strings", required=True, help="the harvested string list")
    parser.add_argument("--begins", default=os.path.join(ROOT, "data", "prefixes.txt"))
    parser.add_argument("--ends", default=os.path.join(ROOT, "data", "suffixes.txt"))
    parser.add_argument("--shortest", type=int, default=6)
    parser.add_argument("--write-plan", required=True)
    options = parser.parse_args(argv)

    begins, ends = rows(options.begins), rows(options.ends)
    stems = sorted({
        row.lower().replace("\\", "/") for row in rows(options.strings)
        if len(row) >= options.shortest
    })
    print("begins: %s   stems: %s   ends: %s"
          % (format(len(begins), ","), format(len(stems), ","), format(len(ends), ",")),
          file=sys.stderr)

    base = os.path.splitext(options.write_plan)[0]
    with open("%s.stems.txt" % base, "w", encoding="utf-8") as handle:
        handle.write("\n".join(stems) + "\n")

    with open(options.write_plan, "w", encoding="utf-8") as handle:
        handle.write(
            "# Written by contrib/harvest_decorated.py. Regenerate rather than editing.\n"
            "#\n"
            "# Strings read out of the installed build, worn under the beginnings and endings\n"
            "# the corpus measures. The stems come from outside the corpus, which is the whole\n"
            "# reason to expect anything -- see METHODS.md, 'Aim at the unnamed distribution'.\n"
            "\n"
            "label: build strings under measured decorations\n"
            "begin: @data/prefixes.txt\n"
            "stem:  @%s.stems.txt\n"
            "end:   @data/suffixes.txt\n"
            "bare:  no\n" % base
        )
    print("\nwrote %s\nabout %s candidates."
          % (options.write_plan, format(len(begins) * len(stems) * len(ends), ",")),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
