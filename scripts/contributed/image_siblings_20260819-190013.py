"""Every image a confirmed material implies, from the strongest measured cross-type seam.

    python contrib/image_siblings.py | confirm_list - --label "image siblings of confirmed materials" \
        --script contrib/image_siblings.py

**What problem it solves.** `cross_type.py --measure` puts material and image at 15,770 shared
cores -- 12.8% of image's, far above any other pair and roughly sixty times the model/image pair.
So a material this project has just confirmed is direct evidence about an image nobody has named.
This takes every confirmed material, reduces it to its core, and spells that core the way images
are spelled.

**Reads** the confirmed names for the game being ground, from `findings/<game>/` and every merged
submission (via `scripts/snapshot.confirmed_names`). **Writes** candidate image names to standard
output, one per line, for `confirm_list` to confirm.

**Reusable.** It is worth re-running after any pass that gains materials, and yields nothing on
unchanged input -- like `images_from_materials`, which does the same thing for one hard-coded
decoration set. This differs in taking its decorations from what images are *measured* to wear
rather than from a list written by hand, and in following whichever game is being ground.

**Measured**, Black Ops 4, 2026-08-19: see the run notes in the submission this shipped with.
"""
import os
import sys

# Find `scripts/` wherever this file has been filed. A contributed script is written in
# `contrib/` or `scripts/`, and `submit` files it under `scripts/contributed/` -- so a path
# built from a fixed number of parent directories is right in one of those and wrong in the
# others. Every script in the library was broken this way at once. Walk up instead.
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

# Image's seven commonest trailing tokens, measured with `cross_type.py --measure`: _c 63,750,
# _n 53,011, _g 28,424, _o 22,460, _m 20,142, _s 18,637, _r 9,350. Plus the bare core, because a
# published image carries no suffix at all often enough to be worth the one extra candidate.
SUFFIXES = ["", "_c", "_n", "_g", "_o", "_m", "_s", "_r"]

# What images put on the front, same measurement: i_ heads 227,486 of them and nothing else comes
# close. `mtl_` is included because a material's own prefix survives into some image names.
PREFIXES = ["i_", "", "mtl_"]

# What a material wears that an image does not, stripped to reach the core.
STRIP = ["mtl_", "i_"]


def core(name):
    """A material name reduced to the part an image would share with it."""
    directory, _, rest = name.rpartition("/")

    for lead in STRIP:
        if rest.startswith(lead):
            rest = rest[len(lead):]
            break

    return directory, rest


def main():
    materials = snapshot.confirmed_names("material")
    print("%d confirmed materials to work from" % len(materials), file=sys.stderr)

    seen = set()
    produced = 0

    for name in materials:
        name = name.strip().lower().replace("\\", "/")
        if not name:
            continue

        directory, stem = core(name)
        if len(stem) < 3:
            continue

        # Both with the material's directory and without it: images mostly carry none at all
        # (308,711 of 308,755 published ones), but the handful that do keep the material's.
        for where in ({"", directory + "/" if directory else ""}):
            for prefix in PREFIXES:
                for suffix in SUFFIXES:
                    candidate = where + prefix + stem + suffix
                    if candidate not in seen:
                        seen.add(candidate)
                        produced += 1
                        sys.stdout.write(candidate + "\n")

    print("%d candidates" % produced, file=sys.stderr)


if __name__ == "__main__":
    main()
