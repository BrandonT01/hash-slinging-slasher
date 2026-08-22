"""Black Ops 3's build vocabulary, respelled with Black Ops 4's and Cold War's generation tags.

    python contrib/bo3_respell.py | bin/windows/confirm_list.exe - --game BLKOPS04 \
        --label "black ops 3 build names, respelled" --script contrib/bo3_respell.py

Run `contrib/harvest_bo3.py` first -- this reads what that writes.

**What problem it solves.** `contrib/harvest_bo3.py` opens Black Ops 3's retail build, which is a
vocabulary this project has never had. Running those names *verbatim* is the obvious first use and
it works -- 4 new Black Ops 4 names from the first 73,303, or 1 per 18,326, which is the densest
rate measured here. But verbatim only finds assets Black Ops 4 kept under Black Ops 3's exact
name, and Treyarch renames the generation tag when it carries one forward.

**The tag is real and it is measured.** Counting the published tables for *these* two games:

    tag        ximages    xmaterials    xmodels
    t7_ (BO3)   18,379        22,606        626
    t8_ (BO4)   86,368        76,634     16,017
    t9_ (CW)   151,632       124,615     50,753

Two things follow. Black Ops 4 and Cold War really do carry Black Ops 3 assets forward, because
18,379 `t7_` image names are published *for our era*. And the tag is the thing that moves: an asset
kept from Black Ops 3 into Black Ops 4 is spelled `t8_` where Black Ops 3 spelled it `t7_`. Of the
Black Ops 3 build names harvested, **37% carry a generation tag**, and they are exactly the
weapons, attachments and characters that get carried forward
(`i_attach_t7_ar_xr2_barrel_01_o`, `mc/mtl_attach_t7_ar_xr2_coupler_02`).

So this substitutes the tag rather than recombining anything. Every `t<n>_` in a harvested name is
rewritten to `t8_` and to `t9_`, keeping the rest of the name exactly as the build spells it.

**Writes** the respelled names to standard output for `confirm_list`, and -- unless `--stdout-only`
-- also to `borrowed/bo3_respelled.txt`, which is inside the folder `[paths] borrowed` already
points at. That matters more than the direct run: the general search takes everything in that
folder as **stems** and puts all 700 measured beginnings and 4,629 endings around them through the
compiled peeling engine, which is a far wider question than this script could ask in Python.

**What it is spent by.** Its own size, like every borrowed-vocabulary method: there are only so
many Black Ops 3 names and one pass asks all of them. It refills only when the build harvest does.
"""
import argparse
import os
import re
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)

# Any generation tag, as a whole token: `t7_` in `attach_t7_ar_xr2`, but never the `t7` inside a
# word like `part7_`. The leading boundary is what keeps this from mangling unrelated names.
TAG = re.compile(r"(?<![a-z0-9])t[0-9](?=_)")

# What these two games spell their own generations. Black Ops 4 is t8, Cold War t9; both are
# offered for every source name because a build harvest does not say which title reused what.
TAGS = ("t8", "t9")


def respell(name):
    """Every spelling of one harvested name under this era's generation tags."""
    if not TAG.search(name):
        return ()

    out = []
    for tag in TAGS:
        moved = TAG.sub(tag, name)
        if moved != name:
            out.append(moved)
    return out


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source", default=os.path.join(_root, "borrowed", "bo3_build.txt"),
        help="what contrib/harvest_bo3.py wrote",
    )
    parser.add_argument(
        "--out", default=os.path.join(_root, "borrowed", "bo3_respelled.txt"),
        help="where to leave the names for the general search to use as stems",
    )
    parser.add_argument("--stdout-only", action="store_true", help="do not write the borrowed file")
    args = parser.parse_args(argv)

    if not os.path.exists(args.source):
        raise SystemExit(
            "%s is not here. Run `python contrib/harvest_bo3.py` first -- it reads the Black Ops 3\n"
            "build and writes the names this respells." % args.source
        )

    seen = set()
    read = 0

    with open(args.source, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            name = line.strip().lower()
            if not name:
                continue
            read += 1
            for moved in respell(name):
                if moved not in seen:
                    seen.add(moved)

    print("%d harvested name(s) -> %d respelled" % (read, len(seen)), file=sys.stderr)

    if not args.stdout_only:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            for name in sorted(seen):
                handle.write(name + "\n")
        print("written to %s" % args.out, file=sys.stderr)

    for name in sorted(seen):
        print(name)


if __name__ == "__main__":
    main(sys.argv[1:])
