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
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT

PRIME = 0x100000001B3
MASK = (1 << 64) - 1

# The prime is odd, so it has an inverse mod 2^64 and the hash runs backwards. See src/search.rs.
PRIME_INVERSE = pow(PRIME, -1, 1 << 64)
TOP = 1 << 63

TABLES = (
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_soundbanks_aliases",
)

def known_names():
    """Every name known to be real: published, submitted by anybody, confirmed here."""
    names = []
    for table in TABLES:
        names += snapshot.table_names(table)
    names += snapshot.confirmed_names()
    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def chosen_game(override=None):
    """Which game to hunt: the flag, else what `start` wrote down, else the first snapshot.

    `state/game.txt` is the alternation `start` maintains and the same file every Rust tool reads
    through `config::game()`. Picking by snapshot filename order instead -- which this did for one
    afternoon -- silently hunts Black Ops 4's ids while `confirm_list` confirms against Cold War's,
    and the run looks entirely healthy while asking the wrong question.
    """
    if override:
        return override.lower()

    try:
        with open(os.path.join(ROOT, "state", "game.txt"), encoding="utf-8") as handle:
            written = handle.read().strip().lower()
            if written:
                return written
    except OSError:
        pass

    return None


def unnamed_ids(game=None):
    """The ids that game holds that nothing can name, under both spellings of the top bit.

    Both, because a loader id has bit 63 cleared and the name's own hash may not have. Comparing
    only the masked form would silently miss half of them -- and silently, because the search
    would look entirely healthy.
    """
    game = chosen_game(game)
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


def solve(names, ids):
    """{name: id} for every unnamed id that is a known name with its final character changed.

    Solved rather than searched, which is the whole point. Because

        u = (h(prefix) ^ byte) * prime

    the byte comes straight back out:

        byte = (u * prime_inverse) ^ h(prefix)

    So for an unnamed id there is no candidate to build and nothing to hash. Take every known
    name's prefix -- the name without its last character -- and ask whether `u * prime_inverse`
    differs from any of them in the low eight bits only. Two hundred and fifty-six lookups per id,
    and the answer is the character itself.

    The upper fifty-six bits being zero is a free proof: if they are not, the two hashes are not a
    final-byte pair and the arithmetic simply did not close. That is what makes this exact where
    the sweep it replaces was a guess -- and it tests all 256 bytes, including the ones no measured
    alphabet would carry, for less than the sweep spent on 39.
    """
    prefixes = {}
    for name in names:
        if len(name) >= 2:
            prefixes.setdefault(snapshot.fnv1a(name[:-1]), name[:-1])

    found = {}
    for value in ids:
        scaled = (value * PRIME_INVERSE) & MASK
        for byte in range(256):
            prefix = prefixes.get(scaled ^ byte)
            if prefix is None:
                continue
            character = chr(byte)
            # A name is what the game hashes, and the game hashes printable text. A solved byte
            # outside that is the arithmetic closing by coincidence, which at 256 tries against a
            # million prefixes it occasionally will.
            if character.isprintable() and not character.isspace():
                found[prefix + character] = value

    return found


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--targets", action="store_true", help="print the proven-adjacent ids")
    parser.add_argument("--game", help="hunt this game rather than the configured one")
    options = parser.parse_args(argv)

    names = known_names()
    print("known names: %s" % format(len(names), ","), file=sys.stderr)

    game, ids = unnamed_ids(options.game)
    found = solve(names, ids)
    print(
        "game: %s, unnamed ids hunted: %s, solved: %s"
        % (game, format(len(ids) // 2, ","), format(len(found), ",")),
        file=sys.stderr,
    )

    if options.targets:
        for name, value in sorted(found.items()):
            print("%016x  %s" % (value, name))
        print(
            "\nEach line is solved, not guessed: the arithmetic only closes when the two names\n"
            "differ in exactly their final character. Point an expensive sweep at these families --\n"
            "`scripts/affix_sweep.py` is only worth running aimed, and this says where to aim.",
            file=sys.stderr,
        )
        return 0

    out = sys.stdout
    names_out = sorted(found)
    for at in range(0, len(names_out), 65536):
        out.write("\n".join(names_out[at : at + 65536]) + "\n")

    print("%s candidates" % format(len(names_out), ","), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
