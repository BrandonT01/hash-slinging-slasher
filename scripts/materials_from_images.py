"""Material names built from the cores of image names — the material/image seam, run backwards.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/materials_from_images.py | bin\\windows\\confirm_list.exe - ^
        --label "materials from image cores" --script scripts/materials_from_images.py

## The gap this fills

`images_from_materials` (method 3) runs material -> image: take a confirmed material, strip it to a
core, and offer that core as an image under each channel suffix. **The reverse direction has never
been run**, and it is the same seam — the strongest measured relationship between any two asset
types in this project.

The asymmetry that makes it worth running: there are far more published image names than there are
confirmed materials to seed the forward direction with, so the reverse has a much larger corpus to
work from. And the two compound — every material this finds is a new seed for the forward
direction, and every image that finds is a new seed for this one.

## How it generates

For each image name: drop its directory, drop a leading `i_`, drop one trailing channel suffix
(`_c _n _g _o _m _s _r _a _d _h`). What is left is the core.

Each core is then offered as a material under **all twelve** directories, in **both** spellings:

    mc/mtl_<core>      the prefixed form
    mc/<core>          the bare form

Both are needed. Measured over 329,846 published and confirmed material names: **67.4%** carry the
`mtl_` prefix and **32.6% do not**, so emitting only the prefixed form silently gives up a third of
the space. All twelve directories are carried for the same reason `AGENTS.md` §6 gives: ranking
them by popularity keeps `mc/` and `wc/` and discards the naming of everything under the other ten.

## What it reads and writes

Reads the community image tables and this machine's confirmed image names, via `snapshot.py`.
Writes candidates to standard output, one per line; sizing to standard error.

## What it returned, and why the estimate was wrong

**Measured, 2026-08-20: 7 names in Cold War, 10 in Black Ops 4**, from 4.57M candidates each. The
seam is real and close to spent.

Beforehand it estimated 158 for Black Ops 4 -- 1 per 14,456 candidates, against `token_edits` at
1 per 94,000 -- and returned 10. The estimate excluded only names in the *published tables*. A real
run also drops the ids **already claimed** by merged submissions and open pull requests (9,583 of
them on the day), which `wanted_for_search` does and a hand-rolled estimate does not.

Estimate against the claimed set, not the tables, or expect to be out by an order of magnitude.

## Options

    --count          print how many candidates this would produce, and stop
    --prefixed-only  emit only `mtl_<core>` (the 67.4% form)
    --bare-only      emit only `<core>`
    --dirs a,b,c     restrict to these directories

Reusable: it reopens whenever new image names are confirmed, which is every time the image pools
gain anything.
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

BACKSLASH = chr(92)

# One trailing channel suffix is dropped to reach the core. Ordered longest-first is unnecessary
# here because every one is two characters, but the loop stops at the first match either way.
CHANNELS = ("_c", "_n", "_g", "_o", "_m", "_s", "_r", "_a", "_d", "_h")

# All twelve. `mc/` heads 299,387 of the names measured here and `ec/` heads 21; ranking by
# popularity keeps the first two and gives up the naming of everything under the rest.
DIRECTORIES = (
    "mc/", "wc/", "clt/", "splm/", "vd/", "mcs/",
    "ei/", "cltp/", "vdd/", "el/", "mcp/", "ec/",
)


def core_of(name):
    """The part of an image name a material is likely to share.

    Directory, `i_` prefix and one channel suffix removed. Everything else is kept: the core is
    the evidence, and trimming it further invents names rather than recombining real ones.
    """
    text = name.strip().lower().replace(BACKSLASH, "/")
    text = text.rsplit("/", 1)[-1]

    if text.startswith("i_"):
        text = text[2:]

    for channel in CHANNELS:
        if text.endswith(channel) and len(text) > len(channel):
            return text[: -len(channel)]

    return text


def cores():
    names = set(snapshot.table_names("fnv1a_ximages"))
    names |= set(snapshot.confirmed_names("image"))

    out = set()
    for name in names:
        core = core_of(name)
        if core:
            out.add(core)

    return out, len(names)


def main():
    argv = sys.argv[1:]

    # Mutually exclusive by construction: honouring both leaves nothing to emit, and a generator
    # that prints nothing and exits 0 reads downstream as a spent method rather than a bad
    # invocation -- `confirm_list` records a run that found nothing and looks perfectly healthy.
    if "--prefixed-only" in argv and "--bare-only" in argv:
        print(
            "--prefixed-only and --bare-only cannot both be given; they leave no form to emit.",
            file=sys.stderr,
        )
        return 2

    prefixed = "--bare-only" not in argv
    bare = "--prefixed-only" not in argv

    directories = DIRECTORIES
    if "--dirs" in argv:
        at = argv.index("--dirs") + 1
        if at >= len(argv) or argv[at].startswith("-"):
            print("--dirs needs a comma separated list, e.g. --dirs mc,wc", file=sys.stderr)
            return 2

        wanted = [d for d in argv[at].split(",") if d]
        if not wanted:
            print("--dirs was given nothing to use", file=sys.stderr)
            return 2

        directories = tuple(d if d.endswith("/") else d + "/" for d in wanted)

    found, source_names = cores()

    forms = (1 if prefixed else 0) + (1 if bare else 0)
    total = len(found) * len(directories) * forms

    print(
        "%d image names -> %d distinct cores; %d directories x %d form(s) = %d candidates"
        % (source_names, len(found), len(directories), forms, total),
        file=sys.stderr,
    )

    if "--count" in argv:
        return 0

    out = sys.stdout
    for core in found:
        for directory in directories:
            if prefixed:
                out.write(directory + "mtl_" + core + "\n")
            if bare:
                out.write(directory + core + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
