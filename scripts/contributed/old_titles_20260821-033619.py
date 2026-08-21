"""Black Ops 2's own asset names, respelled as Black Ops 4 and Cold War spell theirs.

A method, not a report. Pipe it into `confirm_list`:

    python scripts/old_titles.py | ./bin/windows/confirm_list.exe - \
        --label "older-title vocabulary" --script scripts/old_titles.py

## The problem it solves

Every method here recombines vocabulary, and all of them draw on the same vocabulary: the
published tables for these two games, plus what this project has confirmed. That corpus is large
and it is thoroughly picked over -- which is why `reach.py` reports 84-96% and yields keep falling.
The way to move it is not another recombination rule, it is **a source of real names nobody has
read**.

There are exactly three such tables in cod-name-db, and until 2026-08-21 nothing in this
repository touched any of them:

| table | what it holds | why it was invisible |
|---|---|---|
| `bo2_ipak.csv` | **24,565 Black Ops 2 image names** | keyed by native ipak entry ids, which are *not a hash of the name* -- so every hash-based step here skips the file entirely |
| `bo2_sab.csv` | 370,081 Black Ops 2 SAB audio paths | SDBM-hashed, so likewise invisible |
| `bo3_sab.csv` | 30,734 Black Ops 3 SAB audio paths | SDBM-hashed |

They are invisible to the *exclusion* logic for a good reason -- their keys mean nothing to these
games -- and the mistake was letting that carry over to the *seeding* logic, where the keys do not
matter and only the names do. Treyarch reuses its texture library across titles, so a Black Ops 2
image name is a real name in the family we are hunting.

## What it is measured at

Against all 360,461 unnamed ids in the five wanted types, both games, 2026-08-21:

| source | candidates | new names |
|---|---|---|
| `bo2_ipak` image names | 1,038,336 | **53** |
| `bo2_sab` basenames | 9,476,256 | 3 |
| `bo3_sab` basenames | 1,697,952 | 0 |

**1 new name per 19,591 candidates** for the ipak half. For scale, METHODS.md ranks `token_edits`
the best measured method in the project at 1 per 94,000, and a blind `affix_sweep` at 1 per
532,000,000. This is the densest seam anybody here has measured, and it is dense for the obvious
reason: 24,565 names is a very small corpus, and it had never been asked once.

48 of the 53 were Black Ops 4 images and 12 Cold War, on names that read exactly like shared
Treyarch library art -- `i_stone_floor_granite_tile01_cream_n`,
`i_decal_signage_stripe_yellow_rect_n`, `i_p6_monitor_back_small_n`.

The Black Ops 2 SAB half is thin by comparison and the Black Ops 3 half is empty; both are kept
because they cost nothing beside the ipak half, and because their basenames land on `sound_alias`
rather than on images, which nothing else reaches from this direction.

## How it generates

An image is its material's core with a beginning and a map suffix, so each borrowed core is
offered:

1. the six beginnings an image carries (`i_`, bare, `i_mtl_`, `mtl_`, `c_`, `i_c_`) crossed with
   the map suffixes a Treyarch image uses (`_c`, `_n`, `_g`, `_o`, `_m`, `_s`, `_r` and the rest);
2. the twelve material directories crossed with the `mtl_` and bare spellings, since a name that
   is an image here was often a material there;
3. SAB basenames bare, which is the shape a `sound_alias` has.

## What it is spent by

Its own size -- there are only 24,565 ipak names and one pass asks all of them. Re-running it
unchanged will return nothing. **The wider version of this method is `[paths] borrowed` in
`config.toml`**, which feeds a folder of names into the general search as stems and so applies all
700 measured beginnings and 4,800 endings through the peeling engine, rather than the short lists
this script can afford in Python. That mechanism ships on every clone and was empty on all of
them; `scripts/borrow_old_titles.py` fills it from these same three tables.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snapshot

BS = chr(92)

# The beginnings an image carries, as `images_from_materials` measured them.
OPENINGS = ("i_", "", "i_mtl_", "mtl_", "c_", "i_c_")

# The map suffixes a Treyarch image name ends in.
ENDINGS = ("", "_c", "_n", "_g", "_o", "_m", "_s", "_r", "_a", "_d",
           "_e", "_h", "_l", "_t", "_v", "_x", "_nml", "_spc", "_msk")

# Material names are paths, and there are twelve directories rather than one. See AGENTS.md.
DIRECTORIES = ("mc/", "wc/", "clt/", "splm/", "vd/", "mcs/",
               "ei/", "cltp/", "vdd/", "el/", "mcp/", "ec/")


def cores():
    """Every borrowed name reduced to the part another title would share."""
    out = set()

    for raw in snapshot.table_names("bo2_ipak"):
        core = raw.strip().lower()
        # `$white`, `~-gdefaultvehicle` and friends are engine built-ins, not content.
        if core and not core.startswith("$") and not core.startswith("~"):
            out.add(core)

    return out


def sab_basenames():
    """The last path segment of every Black Ops 2 and 3 SAB name, which is the alias-shaped part."""
    out = set()

    for table in ("bo2_sab", "bo3_sab"):
        for raw in snapshot.table_names(table):
            stem = raw.replace("/", BS)
            cut = stem.find(".")
            if cut > 0:
                stem = stem[:cut]
            base = stem.split(BS)[-1].strip().lower()
            if base:
                out.add(base)

    return out


def main():
    out = sys.stdout
    seen = set()

    def emit(name):
        if name not in seen:
            seen.add(name)
            out.write(name + "\n")

    for core in cores():
        for opening in OPENINGS:
            for ending in ENDINGS:
                emit(opening + core + ending)
        for directory in DIRECTORIES:
            emit(directory + "mtl_" + core)
            emit(directory + core)

    for base in sab_basenames():
        emit(base)


if __name__ == "__main__":
    main()
