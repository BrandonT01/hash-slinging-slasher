"""Zombies-flavoured xmodel names, recombined from every zombies name already known to be real.

    python contrib/zombie_models.py | bin/windows/confirm_list.exe - ^
        --label "zombie xmodels" --script contrib/zombie_models.py --game BLKOPS04

Black Ops 4's model pool is 61,139 names of which 20,922 are unnamed, and the zombies content is
a family in its own right: it has its own directories, its own character and prop vocabulary, and
its own suffixes. This takes the part of the corpus that already says `zombie` -- published names
from the tables, plus everything this project has confirmed in either game -- cuts it at the marks
a name is built from, and puts the pieces back together against the model beginnings and endings
`derive_lists.py` measured.

Seeded, as everything here is: no candidate contains a token that no real name contains. What it
reaches that a general pass does not is the *cross product* of one family -- every zombies stem
against every model beginning and ending, rather than whatever share of that the global ceiling
happens to afford.
"""
import os
import re
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_root, "scripts"))

import settings  # noqa: E402

WANTED = re.compile(r"zombie|zmb|_zm_|^zm_|/zm_")

# Model beginnings, kept short deliberately. The published model vocabulary heads its names with
# these; a zombies model is a model first.
OPENINGS = [
    "", "p9_", "p8_", "p7_", "p6_", "c_", "t9_", "vm_", "wm_", "attach_", "veh_", "ai_",
    "p9_zmb_", "p8_zmb_", "c_zmb_", "zmb_", "zm_", "p9_zombie_", "c_zombie_", "zombie_",
    "clt/", "splm/", "cltp/", "mc/",
]

# The endings a model family varies. Measured ones come from the committed list; the numbered and
# lod tails are the ones no table can show, because a mesh entry hides them behind its own hash.
TAILS = ["", "_lod0", "_lod1", "_lod2", "_lod3", "_body", "_head", "_hat", "_arms", "_legs",
         "_torso", "_hands", "_fx", "_dead", "_gib", "_world", "_view", "_dmg", "_variant"]
for number in range(0, 13):
    TAILS.append("_%02d" % number)
    TAILS.append("_%d" % number)


def measured(name):
    """The committed endings, which are what the general search itself carries."""
    path = os.path.join(_root, "data", name)
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def corpus():
    """Every name already known to be real, from the tables and from what has been confirmed."""
    # Models only. A zombies *sound* path shares the word and none of the shape, and seeding from
    # it produced 795,105 stems -- 74 billion candidates, which is a week of generating for a pool
    # of 20,922 unnamed ids.
    tables = settings.tables_csv()
    for entry in ("fnv1a_xmodels.csv",):
        with open(os.path.join(tables, entry), encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if "," in line:
                    yield line.strip().split(",", 1)[1].lower().replace(chr(92), "/")

    found = settings.path("findings", "findings")
    for here, _, files in os.walk(found):
        for name in files:
            if not name.startswith("xmodel") or not name.endswith(".txt"):
                continue
            with open(os.path.join(here, name), encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if "," in line:
                        yield line.strip().split(",", 1)[1].lower().replace(chr(92), "/")


def stems_of(name):
    """Every piece of a name that could be a name in its own right, cut at the marks."""
    base = name.rpartition("/")[2]
    parts = base.split("_")

    for start in range(len(parts)):
        for end in range(start + 1, len(parts) + 1):
            piece = "_".join(parts[start:end])
            if len(piece) >= 3:
                yield piece


def main():
    seen_stems = set()
    for name in corpus():
        if not WANTED.search(name):
            continue
        for stem in stems_of(name):
            seen_stems.add(stem)

    # Only the pieces that carry the family. A bare `_01` or `head` is every model in the game and
    # would spend the run on candidates the general search already covers.
    stems = sorted(stem for stem in seen_stems
                   if WANTED.search(stem) and stem.count("_") <= 5)
    print("zombies stems: %d" % len(stems), file=sys.stderr)

    # One trailing segment only, and the commonest of those: an ending is nearly free to the
    # search but not to this pipe, which has to write every candidate out as text.
    endings = TAILS + [item for item in measured("suffixes.txt") if item.count("_") == 1][:400]
    endings = list(dict.fromkeys(endings))
    print("endings: %d, openings: %d" % (len(endings), len(OPENINGS)), file=sys.stderr)
    print("candidates: %d" % (len(stems) * len(endings) * len(OPENINGS)), file=sys.stderr)

    out = sys.stdout
    for stem in stems:
        for opening in OPENINGS:
            head = opening + stem
            for ending in endings:
                out.write(head + ending + "\n")


if __name__ == "__main__":
    main()
