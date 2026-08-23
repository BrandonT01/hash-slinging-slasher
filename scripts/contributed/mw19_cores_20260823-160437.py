"""Modern Warfare 2019's name corpus, cut into cores for the all-boundary method.

    python contrib/mw19_cores.py                 write the core list
    python contrib/mw19_cores.py --t9            only the names that mention t9 (Cold War)
    python contrib/mw19_cores.py --min-core 12   longer cores only

## Why cores and not the names themselves

Fed to Cold War verbatim, all 1,167,131 captured Modern Warfare 2019 names resolve **2,107**
Cold War assets, of which **2,027 are `localizeentry`** -- the pool CLAUDE.md §5 calls worthless
because the entry already holds its own unhashed string -- and **zero** are in the five types
this project searches. Measured 2026-08-23. Verbatim is therefore spent, and 66,842 of the names
are already in the published tables, so cod-name-db has ingested this title before.

What is not spent is the vocabulary. Method 25 measured that in every core x ending sweep here
**the core list, not the ending list, is the binding constraint**. Modern Warfare 2019 offers
1.1 M real Call of Duty asset names that are not in the Cold War tables at all -- a core list
from a different title's build, in the naming conventions Cold War shares because Warzone shipped
both. That is new material in the sense §8 means it: not a re-measurement of the same reach.

Composite names Cordycep synthesises for merged assets are dropped. They carry `~` and a decimal
id (`a&b~7125482708783213757`) and are an artefact of the dump rather than anything the game
calls an asset -- 135,725 of them, and every one would be a wasted candidate.
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

import snapshot

SEPS = "_/\\."


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--t9", action="store_true",
                        help="only names mentioning t9, Treyarch's Cold War codename. 174,116 of "
                             "the corpus, and the subset most likely to share vocabulary")
    parser.add_argument("--min-core", type=int, default=8)
    parser.add_argument("--out", default="mw19_cores.txt")
    args = parser.parse_args()

    names, dropped = [], 0
    # Through the shared reader so the gzipped corpus works too: the committed artefact is
    # `modwar19.names.txt.gz` (7.3 MB against 54 MB) and only the capturing machine has the raw.
    for _pool, name in snapshot.name_corpus("modwar19"):
        # Packed-channel entries are several real names joined by `&`, not artefacts.
        for piece in snapshot.unpack(name):
            if args.t9 and "t9" not in piece:
                continue
            names.append(piece.lower())

    print(f"{len(names)} names ({dropped} composites dropped)", file=sys.stderr)

    cores = set()
    for name in names:
        for i, ch in enumerate(name):
            if ch in SEPS and i >= args.min_core:
                cores.add(name[:i])
        # The whole name is a core too: Cold War may wear it with an ending of its own.
        if len(name) >= args.min_core:
            cores.add(name)

    out = ROOT / "contrib" / args.out
    out.write_text("\n".join(sorted(cores)) + "\n", encoding="utf-8")
    print(f"{len(cores)} all-boundary cores -> contrib/{args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
