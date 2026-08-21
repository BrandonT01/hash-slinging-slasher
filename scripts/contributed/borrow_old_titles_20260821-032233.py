"""Fills the `[paths] borrowed` folder with the three older-title tables nothing else here reads.

    python scripts/borrow_old_titles.py            writes borrowed/ and says what to add to config
    python scripts/borrow_old_titles.py --where X  writes somewhere else

Infrastructure, not a generator. It writes a folder of `.txt` names; the *general* search picks
them up as stems and applies all 700 measured beginnings and 4,800 endings to them through the
peeling engine.

## Why this exists

`config.toml` has shipped a `[paths] borrowed` key on every clone since the beginning --
"names borrowed from another title, used as candidates but never measured for conventions" -- and
`confirm_cw` prints `borrowed from the earlier game: 0` at the top of every pass. It has been zero
on every machine, because nothing ever said what to put in it.

`scripts/old_titles.py` measured what is worth putting in it: Black Ops 2's 24,565 ipak image
names return **1 new name per 19,591 candidates**, against 1 per 94,000 for the best method
METHODS.md ranks. That script can only afford a short ending list in Python. This mechanism gets
the same vocabulary the full lists and the peeling engine, which is where the rest of the seam is.

Reads the tables and nothing else. Writes only inside the folder it is given.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snapshot

BS = chr(92)
DEFAULT = "borrowed"

# The three tables whose keys are meaningless to these two games -- ipak entry ids and SDBM -- and
# whose *names* are therefore skipped by every hash-driven step in the repository. See
# docs/HASHES.md for why each is keyed the way it is.
TABLES = ("bo2_ipak", "bo2_sab", "bo3_sab")


def clean(name):
    """Lowercased, with the engine built-ins dropped."""
    name = name.strip().lower()
    if not name or name.startswith("$") or name.startswith("~"):
        return None
    return name


def main():
    where = DEFAULT
    if "--where" in sys.argv:
        where = sys.argv[sys.argv.index("--where") + 1]

    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), where)
    root = where if os.path.isabs(where) else root
    os.makedirs(root, exist_ok=True)

    total = 0
    for table in TABLES:
        names = set()

        for raw in snapshot.table_names(table):
            name = clean(raw)
            if not name:
                continue

            names.add(name)

            # A SAB name is a path with an encoding tail. The whole path, the path without its
            # tail and the bare basename are three different stems and the search wants all of
            # them: the first two are what a sound id is hashed from, the third is the shape a
            # `sound_alias` has.
            if table.endswith("_sab"):
                stem = name.replace("/", BS)
                cut = stem.find(".")
                if cut > 0:
                    names.add(stem[:cut])
                    names.add(stem[:cut].replace(BS, "/"))
                names.add(stem.split(BS)[-1])

        path = os.path.join(root, table + ".txt")
        with open(path, "w", encoding="utf-8") as handle:
            for name in sorted(names):
                handle.write(name + "\n")

        total += len(names)
        print("%-10s %7d names -> %s" % (table, len(names), path))

    print("\n%d names borrowed in total." % total)
    print("Add this to config.toml if it is not there already:\n")
    print("[paths]")
    print('borrowed = "%s"' % where)


if __name__ == "__main__":
    main()
