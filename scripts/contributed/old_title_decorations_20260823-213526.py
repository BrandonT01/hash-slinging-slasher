"""Decorations borrowed from the older titles, worn by the names we already hold.

    python contrib/old_title_decorations.py --write-plan plans/olddec.txt
    bin\\windows\\confirm_plan.exe plans/olddec.txt --size
    bin\\windows\\confirm_plan.exe plans/olddec.txt

## Why the older titles, when their names are recorded dead

METHODS.md is clear that older-title *names* do not transfer. Hashed verbatim, all eight `_v2`
tables and the Black Ops 2 and 3 corpora return zero or near it; `cross_era` managed 61 names for
34.5 trillion candidates; Black Ops 3's SAB paths respelled as Black Ops 4 returned 0 in 3.06
billion. The vocabulary of those games describes their assets, not ours.

**A decoration is not vocabulary.** `_desc`, `_rwd`, `.gsc`, `_lod1` are engine conventions rather
than content, and an engine convention is exactly the kind of thing a sequel keeps while renaming
everything it is applied to. So the question this asks is not "is this old name one of ours" but
"is this old *convention* one ours uses, on a name of ours we already hold".

That is the same relation as `contrib/wrapper_decorations.py` -- a string that turns one whole
known name into another -- measured on a corpus we are not searching and applied to one we are.
It is the only cheap source of decorations left once our own corpus has been measured out: ours
yields 51,557 distinct wrappers, the older titles yield **452,978**, of which 3,070 occur ten times
or more and are absent from `data/suffixes.txt`.

Measured 2026-08-23 over 1,774,385 strings from `borrowed/` (Black Ops 1 and 3 builds, the Black
Ops 2 ipak list, and both respellings). The commonest uncarried ones:

    .wav              13,550        _desc          2,445
    .sn100.pc.snd      5,997        _rwd           1,774
    _00.sn100.pc.snd   3,598        .gsc           1,430
    _d.ln100.pc.snd    2,747

Several are plainly sound-file conventions and cannot land on the five types this searches; they
are carried anyway because the cost of an ending that matches nothing is a few million candidates
and the cost of hand-picking is a bias about what this era kept.

Run `borrowed/` through `scripts/contributed/borrow_old_titles_20260821-085126.py` first if it is
empty -- this reads that folder, not the hash tables, because the Black Ops 2 and 3 corpora are
SDBM-hashed and so are not "our games" for exclusion.
"""
import argparse
import collections
import io
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

BORROWED = (
    "bo1_build.txt",
    "bo1_respelled.txt",
    "bo2_ipak.txt",
    "bo3_build.txt",
    "bo3_respelled.txt",
)

LONGEST = 24
SHORTEST_BASE = 4


def known_names():
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def borrowed_names():
    """Every plausible name string in `borrowed/`. These are build scrapes, so most lines are junk.

    The length window and the space test do the filtering: a decoration measured off junk needs a
    junk *base* to have been in the corpus too, which is rare enough that the counts stay clean.
    """
    names = set()
    folder = os.path.join(_root, "borrowed")
    for filename in BORROWED:
        path = os.path.join(folder, filename)
        if not os.path.isfile(path):
            continue
        with io.open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip().lower().replace("\\", "/")
                if 6 <= len(line) <= 120 and " " not in line:
                    names.add(line)
    if not names:
        raise SystemExit(
            "borrowed/ is empty. Fill it with\n"
            "    python scripts/contributed/borrow_old_titles_20260821-085126.py"
        )
    return names


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min", type=int, default=10, help="fewest instances to carry")
    parser.add_argument("--write-plan", metavar="PATH", required=True)
    options = parser.parse_args(argv)

    old = borrowed_names()
    ours = known_names()
    print(
        "older-title strings: %s   names we hold: %s"
        % (format(len(old), ","), format(len(ours), ",")),
        file=sys.stderr,
    )

    with open(os.path.join(_root, "data", "suffixes.txt"), encoding="utf-8") as handle:
        carried = {line.strip().lower() for line in handle if line.strip()}

    counted = collections.Counter()
    for name in old:
        for length in range(1, min(LONGEST, len(name) - SHORTEST_BASE) + 1):
            if name[:-length] in old:
                counted[name[-length:]] += 1

    decorations = sorted(
        (
            decoration
            for decoration, count in counted.items()
            if count >= options.min and decoration not in carried
        ),
        key=lambda decoration: (-counted[decoration], decoration),
    )
    print(
        "decorations in the older titles: %s   uncarried at >=%d: %s"
        % (format(len(counted), ","), options.min, format(len(decorations), ",")),
        file=sys.stderr,
    )
    for decoration in decorations[:10]:
        print("    %-24s %6d" % (decoration, counted[decoration]), file=sys.stderr)

    base = os.path.splitext(options.write_plan)[0]
    stem_path, end_path = base + ".stems.txt", base + ".endings.txt"
    for path, rows in ((stem_path, sorted(ours)), (end_path, decorations)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(rows) + "\n")

    def relative(path):
        return os.path.relpath(path, _root).replace("\\", "/")

    with open(options.write_plan, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Written by contrib/old_title_decorations.py. Regenerate rather than editing.\n"
            "#\n"
            "# Endings measured to wrap one whole older-title name into another, kept where\n"
            "# data/suffixes.txt cannot express them, against every name we hold. The names of\n"
            "# those games are recorded dead; their conventions are a separate question.\n"
            "\n"
            "label: older-title decorations\n"
            "describe: endings measured as whole-name decorations in the Black Ops 1-3 build corpora and absent from the carried suffix list, worn by the names this era already holds\n"
            "\n"
            "stem: @%s\n"
            "\n"
            "end: @%s\n"
            "\n"
            "# Decorations are in the `end` column and there is no `begin` line, so `bare: yes`\n"
            "# supplies the empty opening. Without it the plan builds nothing.\n"
            "bare: yes\n"
            "fold: yes\n" % (relative(stem_path), relative(end_path))
        )

    print(
        "wrote %s\n      %s (%s stems)\n      %s (%s decorations)\n\nabout %s candidates."
        % (
            options.write_plan,
            stem_path,
            format(len(ours), ","),
            end_path,
            format(len(decorations), ","),
            format(len(ours) * len(decorations), ","),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
