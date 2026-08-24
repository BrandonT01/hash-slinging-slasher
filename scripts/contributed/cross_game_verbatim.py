r"""Every name confirmed in one title, tried verbatim in the other.

    python contrib/cross_game_verbatim.py | bin\windows\confirm_list.exe - \
        --label "cross-game verbatim" --script contrib/cross_game_verbatim.py

METHODS lists this under *Candidates worth building* as `cross_game.py`: "try a name confirmed in
one title verbatim in the other. `confirm_cw` seeds *pieces* across games already, but nothing
tries whole names. Nearly free: no generation, just hashing a list that exists."

It has never been built, and the reason it is worth the two minutes is in CLAUDE.md rather than in
any measurement: Cold War carries a great deal of Black Ops 4's content, so the two corpora are
not independent. Anything *published* is excluded on both games by construction -- the tables are
the exclusion set -- so the only names that can possibly land are the ones this project and its
contributors found themselves and cod-name-db has not caught up with.

That is what this prints: every name in `findings/` and `submissions/`, for both games, with no
recombination of any kind.
"""
import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot


def main():
    seen = set()
    out = sys.stdout
    for raw in snapshot.confirmed_names():
        name = raw.strip()
        if not name:
            continue
        for spelling in (name.lower(), name.lower().replace("\\", "/"), name.lower().replace("/", "\\")):
            if spelling not in seen:
                seen.add(spelling)
                out.write(spelling + "\n")
    print("printed %s spelling(s)" % format(len(seen), ","), file=sys.stderr)


if __name__ == "__main__":
    main()
