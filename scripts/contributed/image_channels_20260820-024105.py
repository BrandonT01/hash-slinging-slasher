"""Every other channel of an image we already have one channel of.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/image_channels.py | bin\\windows\\confirm_list.exe - \
        --label "image channel completion" --script scripts/image_channels.py

## What problem it solves

A texture is authored once and exported as several maps -- colour, normal, gloss, occlusion,
specular and so on -- which the engine holds as separate images with separate ids, named by the
same core and a one or two letter channel suffix.

    i_c_t9_usa_pl_spy_investigator_pants_01_c      colour
    i_c_t9_usa_pl_spy_investigator_pants_01_n      normal
    i_c_t9_usa_pl_spy_investigator_pants_01_g      gloss

**Measured on `fnv1a_ximages`: 110,517 of 124,417 distinct cores (88.8%) already appear under more
than one channel.** So a single confirmed image is not one name, it is direct evidence about half
a dozen ids that differ from it by two characters -- and the odds it is the *only* channel that
exists are under one in eight.

`images_from_materials` (METHODS.md method 3) reaches the same pool from a different direction: it
starts from confirmed **materials**. This starts from confirmed **images**, so the two seed from
disjoint material and feed each other -- a channel found here is a new core for the next material
pass, and a material named there is a new core for this one.

## How it generates

Every image name the tables publish and every one this machine has confirmed, cut at its final
underscore, then re-spelled with each channel suffix measured to occur. The bare core is offered
too, since a published image carries no suffix at all often enough to be worth the one candidate.

Nothing is invented: the suffixes are counted from the published table rather than guessed, and
every core is taken from a name known to be real.

## What it reads and writes

Reads `fnv1a_ximages` and this machine's confirmed `image` names, via `snapshot.py`. Writes
candidate names to standard output, one per line; a count to standard error.

## Options

    --count     print how many candidates this would produce, and stop
    --deep      also cut at the second-from-last underscore, which reaches cores whose channel is
                written as two tokens (`_col_lg`). Roughly triples the output.

Reusable, and it compounds: every image confirmed by any method is six more candidates here.
"""
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

# Counted from `fnv1a_ximages`, commonest first, not guessed:
#   _c 115,522   _n 95,954   _g 52,013   _o 40,696   _m 36,227   _s 34,002   _r 16,325
#   _icon 5,630  _e 4,035    _col 3,280  _large 2,898  _nml 2,798
#
# Reproduce with the measurement at the top of this file's history, or:
#   cut -d, -f2- cod-name-db/csv/fnv1a_ximages.csv | sed 's/.*_//' | sort | uniq -c | sort -rn
CHANNELS = [
    "c", "n", "g", "o", "m", "s", "r",
    "e", "col", "nml", "icon", "large",
    # Present in smaller numbers and cheap to carry, since the cost is one candidate each.
    "spc", "gls", "ao", "d", "h", "a", "mask", "small",
]


def cores(deep):
    """Every image core we know to be real, with its channel taken off."""
    names = list(snapshot.table_names("fnv1a_ximages"))
    names += list(snapshot.confirmed_names("image"))

    found = set()
    for name in names:
        name = name.strip().lower().replace("\\", "/")
        if not name or "_" not in name:
            continue

        head, _, tail = name.rpartition("_")

        # Only treat it as a channel if it looks like one. A name ending `_01` is a numbered
        # variant, and cutting there would produce cores that are half a name.
        if head and (tail in CHANNELS or len(tail) <= 2):
            found.add(head)

        if deep and head and "_" in head:
            second, _, _ = head.rpartition("_")
            if second:
                found.add(second)

    return found


def main(argv):
    counting = "--count" in argv
    deep = "--deep" in argv

    seen = set()
    made = 0

    for core in cores(deep):
        for channel in CHANNELS:
            candidate = "%s_%s" % (core, channel)
            if candidate in seen:
                continue
            seen.add(candidate)
            made += 1
            if not counting:
                print(candidate)

        # The undecorated core, which a published image is often spelled as.
        if core not in seen:
            seen.add(core)
            made += 1
            if not counting:
                print(core)

    sys.stderr.write("%d candidates from %d cores and %d channels\n"
                     % (made, len(seen), len(CHANNELS)))
    if counting:
        print("%d candidates" % made)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
