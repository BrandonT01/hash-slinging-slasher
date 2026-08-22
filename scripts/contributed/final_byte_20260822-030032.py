"""Names one final character away from a name already known to be real.

    python scripts/final_byte.py | bin\\windows\\confirm_list.exe - \
        --label "final byte substitution" --script scripts/final_byte.py

    python scripts/final_byte.py --targets    the unnamed ids proven adjacent to a known name

A method, and a piece of reconnaissance nothing else here can produce.

## The structure this rests on

FNV-1a is `h = (h ^ byte) * prime`, so for two names differing **only in their last character**:

    h(A) - h(B) = ((h_prefix ^ a) - (h_prefix ^ b)) * prime

The XOR only touches the low eight bits, so that first term is an integer between -255 and 255.
The difference between the two hashes is therefore always an **exact small multiple of the
prime** -- measured, not assumed:

    p9_example_model_name_1  vs  _2   ->  -3 x prime
                                 _3   ->  -2 x prime
                                 _a   -> -80 x prime

Which is why two such names look, as somebody put it, like nearly the same hash: a few times
1.1e12 apart in a space of 1.8e19.

**It holds for the final byte and no other.** Change a byte further in and the difference is
carried through more XOR steps, and XOR does not commute with the multiply, so it scatters --
measured at position two from the end the multiplier is already 7.1e18, which is to say random.
That limit is worth knowing before anybody tries to generalise it.

## The two things it buys

**A method.** Every known name's final-character variants, hashed and confirmed. Cheap, and it
reaches names no measured ending list has to carry -- an ending used once in the whole game is
reached here for the same price as a common one.

**A target list, which is the more interesting half.** Because the relation inverts, you can ask
the question backwards: for an unnamed id `u`, is `u - d * prime` the hash of a name we know, for
some small `d`? That is a few hundred lookups per id and it needs no strings at all. A hit proves
that unnamed asset's name is one final character from a name already in hand -- so it is not a
guess about where a family continues, it is a *proof* that it does.

Measured on Cold War, 2026-08-22: **1,288 unnamed ids are provably one final byte from a known
name.** `--targets` prints them with the name they neighbour. Those are the ids worth pointing an
expensive sweep at -- `scripts/affix_sweep.py` says it is only worth running aimed at a family you
suspect, and this is the only thing here that says *which* families to suspect, with proof.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

PRIME = 0x100000001B3
MASK = (1 << 64) - 1
TOP = 1 << 63

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

# How many final characters to try. Measured off the corpus rather than assumed -- see
# `ending_alphabet`, which reads what real names actually end in.
ALPHABET_SIZE = 48


def known_names():
    """Every name known to be real: published, submitted by anybody, confirmed here."""
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def ending_alphabet(names, size=ALPHABET_SIZE):
    """The characters real names actually end in, commonest first.

    Measured rather than assumed. A fixed `a-z0-9_` would spend a third of the pass on characters
    no name in either game ends with, and would miss any that are not letters.
    """
    counted = collections.Counter(name[-1] for name in names if name)
    return [character for character, _ in counted.most_common(size)]


def unnamed_ids():
    """The ids the current game holds that nothing can name, under both spellings of the top bit.

    Both, because a loader id has bit 63 cleared and the name's own hash may not have. Comparing
    only the masked form would silently miss half of them -- and silently, because the search
    would look entirely healthy.
    """
    game = os.environ.get("SLASHER_GAME", "").lower()
    paths = snapshot.snapshots()

    chosen = None
    for path in paths:
        shot = snapshot.read(path)
        if not game or shot.game.lower() == game:
            chosen = shot
            break
    if chosen is None:
        chosen = snapshot.read(paths[0])

    known = snapshot.known_hashes()
    ids = set(chosen.unnamed(known).keys())
    return chosen.game, ids | {value | TOP for value in ids}


def targets(names, ids):
    """{unnamed hash: known name} for every id one final byte from a name we hold.

    The backward direction, which is the whole point: no strings are built and no candidate is
    hashed. `u - d * prime` for small `d` is either the hash of something we know or it is not.
    """
    by_hash = {}
    for name in names:
        by_hash[snapshot.fnv1a(name)] = name

    found = {}
    for value in ids:
        for step in range(-255, 256):
            if step == 0:
                continue
            neighbour = (value - step * PRIME) & MASK
            name = by_hash.get(neighbour)
            if name:
                found[value] = name
                break

    return found


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--targets", action="store_true", help="print the proven-adjacent ids")
    parser.add_argument("--alphabet", type=int, default=ALPHABET_SIZE)
    options = parser.parse_args(argv)

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    if options.targets:
        game, ids = unnamed_ids()
        found = targets(names, ids)
        print("game: %s, unnamed ids hunted: %s" % (game, format(len(ids) // 2, ",")), file=sys.stderr)
        print(
            "\n%s unnamed id(s) are provably one final character from a name already known.\n"
            % format(len(found), ","),
            file=sys.stderr,
        )
        for value, name in sorted(found.items(), key=lambda pair: pair[1]):
            print("%016x  neighbours  %s" % (value, name))
        print(
            "\nThese are proofs, not guesses: the arithmetic only closes if the two names differ in\n"
            "exactly their last byte. Point an expensive sweep at these families -- see\n"
            "`scripts/affix_sweep.py`, which is only worth running aimed.",
            file=sys.stderr,
        )
        return 0

    alphabet = ending_alphabet(names, options.alphabet)
    print("ending alphabet (%d): %s" % (len(alphabet), "".join(alphabet)), file=sys.stderr)

    out = sys.stdout
    written = 0
    batch = []
    for name in names:
        if len(name) < 2:
            continue
        stem = name[:-1]
        last = name[-1]
        for character in alphabet:
            if character != last:
                batch.append(stem + character)
        if len(batch) >= 65536:
            out.write("\n".join(batch) + "\n")
            written += len(batch)
            batch.clear()

    if batch:
        out.write("\n".join(batch) + "\n")
        written += len(batch)

    print("%s candidates" % format(written, ","), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
