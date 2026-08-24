r"""Black Ops 3's official asset names, read from the manifests the tools ship.

    python contrib/harvest_bo3_assetlist.py

Finds the build through the **`TA_TOOLS_PATH`** environment variable the mod tools set, so it
works on anybody's install without a hardcoded path.

## Why only this one path

The obvious version of this script walked the whole Black Ops 3 install, and it was wrong. Most
people using this repository *have* the mod tools -- it is largely why they want these names
unhashed -- and a mod tools tree is a **working directory**, not the shipped game. `model_export/`,
`source_data/`, `texture_assets/` and `share/raw/` are where a modder's own and the community's
assets live, in the thousands.

Measured on the install this was written on, whose owner uses the tools only to release their own
work and so has about the cleanest tree in the community -- a **floor**, not a typical case: one
modder's folder contributed **1,216 names**, and they are the dangerous shape rather than obvious
rubbish:

    t10_ar_coslo723_anim
    wpn_t10_p01_ar_coslo723_barrel_v0_c

`t10` is **Black Ops 6**. Those read exactly like official Treyarch names, they can never be in
either title this project searches, and METHODS.md already records every `_v2` table as measured
dead. On an install with a real mod library that is most of the corpus.

The general rule it cost 867,766 names to learn: **seed only from something every contributor has
identical bytes of.** A method seeded from a user-writable directory gives a different corpus on
every disk, so it cannot be reproduced and its fingerprint -- the whole mechanism that stops two
people grinding the same ground -- means nothing.

`zone_source/all/assetlist/*.csv` passes that test. They are the shipped per-zone manifests, one
`type,name` row per asset, and nobody has a reason to write to them. The other trustworthy path is
`zone/` itself, which `contrib/harvest_bo3.py` already reads.
"""
import argparse
import collections
import glob
import os
import sys

STEAM = r"C:\Program Files (x86)\Steam\steamapps\common\Call of Duty Black Ops III"
SEPARATORS = set("_/")


def tools_root(given):
    if given:
        return given
    from_environment = os.environ.get("TA_TOOLS_PATH", "").strip().rstrip("\\/")
    return from_environment or STEAM


def keep(text):
    if len(text) < 6 or len(text) > 160:
        return False
    if not any(character in SEPARATORS for character in text):
        return False
    return sum(character.isalpha() for character in text) >= 3


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="overrides TA_TOOLS_PATH")
    parser.add_argument("--out", default=os.path.join("borrowed", "bo3_assetlist.txt"))
    options = parser.parse_args(argv)

    root = tools_root(options.root)
    folder = os.path.join(root, "zone_source", "all", "assetlist")
    manifests = sorted(glob.glob(os.path.join(folder, "*.csv")))
    if not manifests:
        raise SystemExit(
            "no manifests under %s\n"
            "Set TA_TOOLS_PATH, or pass --root, pointing at a Black Ops 3 mod tools install."
            % folder
        )

    names = set()
    kinds = collections.Counter()

    for path in manifests:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                kind, _, name = line.partition(",")
                name = name.strip().strip('"').replace("\\", "/").lower()
                if not name:
                    continue
                kinds[kind.strip().lower()] += 1
                for spelling in (name, os.path.splitext(name)[0], os.path.basename(name)):
                    if keep(spelling):
                        names.add(spelling)

    with open(options.out, "w", encoding="utf-8") as handle:
        handle.write("\n".join(sorted(names)) + "\n")

    print("%d manifest(s) under %s" % (len(manifests), folder), file=sys.stderr)
    for kind, count in kinds.most_common(10):
        print("   %8s  %s" % (format(count, ","), kind), file=sys.stderr)
    print("\n%s distinct name(s) -> %s" % (format(len(names), ","), options.out), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
