"""Names one final character away from a name already known to be real, solved backwards.

    python scripts/final_byte.py | bin\windows\confirm_list.exe - ^
        --label "final byte solved backwards" --script scripts/final_byte.py

    python scripts/final_byte.py --targets           the solved names with the ids they answer
    python scripts/final_byte.py --game BLKOPS04     hunt the other game

A method, and the cheapest one measured here by a wide margin.

## The structure

FNV-1a is `h = (h ^ byte) * prime`, so for two names differing **only in their last character**:

    h(A) - h(B) = ((h_prefix ^ a) - (h_prefix ^ b)) * prime

The XOR only touches the low eight bits, so that first term is an integer between -255 and 255 --
the difference between the two hashes is always an **exact small multiple of the prime**:

    p9_example_model_name_1  vs  _2  ->  -3 x prime      vs  _3  ->  -2 x prime
                                 _a  -> -80 x prime      vs  _0  ->  -1 x prime

Which is why two such names look like nearly the same hash: a few times 1.1e12 apart in a space
of 1.8e19. That observation is what this was built from.

**It holds for the final byte and no other.** Change a byte further in and the difference is
carried through more XOR steps; XOR does not commute with the multiply, so it scatters. Measured
one position further in, the multiplier is already 7.1e18 -- which is to say random. Worth knowing
before anybody tries to generalise it.

## Why it is solved rather than searched

The relation inverts. The prime is odd, so it has an inverse mod 2^64, and

    u = (h(prefix) ^ byte) * prime      =>      byte = (u * prime_inverse) ^ h(prefix)

So an unnamed id does not need candidates built and hashed against it. Take every known name's
prefix, ask whether `u * prime_inverse` differs from one of them in the low eight bits only, and
the answer *is the character*. Two hundred and fifty-six lookups per id, no strings.

Measured on Black Ops 4, 2026-08-22: **2,523 candidates, 138 confirmed -- one name per 18.** The
best figure in this repository by a distance; the next is image siblings at one per 394. Sweeping
the same ground the obvious way took 35,068,642 candidates for 75 names, so solving it backwards
is roughly fourteen thousand times cheaper for more coverage -- it tests all 256 bytes, including
the ones no measured alphabet would carry.

## Two things that will bite whoever changes this

**Hash the solved name back before believing it.** The solve gives the byte the *hash* wants; the
game hashes a **normalised** name, lower cased with backslashes folded. A solved byte that is
uppercase or a backslash describes a string that cannot survive normalisation and will never hash
to that id. Without the check this reported 11,003 solutions where 63 were real.

**Most of what it finds may already be claimed.** Its 138 on Black Ops 4 came back as 3 new to the
community, because a brute sweep of the same ground an hour earlier had already claimed them. That
is the `found` against `landed` distinction `methods_report.py` prints, and it is the normal case
rather than a fault.

It is in `scripts/derive_closure.py`, so it re-runs after any pass that confirms anything. That is
where its value now is: it costs seconds and it refills every time the corpus grows.
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
            if not character.isprintable() or character.isspace():
                continue

            # Hashed back before it is believed, and this is not belt and braces.
            #
            # The solve gives the byte the *hash* wants. The game hashes a **normalised** name --
            # lower cased, backslashes folded to forward slashes -- so a solved byte that is
            # uppercase, or a backslash, describes a string that does not survive normalisation
            # and will never hash to this id. Without this check the run reported 11,003 solutions
            # where 63 were real, and `confirm_list` quietly matched 0.6% of what it was handed.
            name = prefix + character
            if snapshot.fnv1a(name) == value:
                found[name] = value

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
