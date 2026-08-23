"""How much of Modern Warfare 2019's name corpus is Cold War, and where does it already sit?

    python contrib/mw19_overlap.py

Feeding the 1,167,131 captured Modern Warfare 2019 names into Cold War verbatim returned **0
matched** -- not 0 new, 0 hits. That is worth understanding before deciding the corpus is
useless, because there are three quite different explanations and they point at opposite next
moves:

  1. the names hash to Cold War ids that are **already named** -- the tables have them, so they
     are excluded and the corpus is real but spent as a verbatim list
  2. the names hash to **nothing in Cold War at all** -- the two titles share no asset names and
     the corpus is only useful as vocabulary to recombine
  3. the hashing is wrong -- normalisation, mask, or the wrong id space

This separates them. Every captured name is hashed the way Cold War hashes (lower cased,
backslashes folded to forward slashes, FNV-1a 64, compared at 63 bits) and looked up in three
places: the published tables, every id the Cold War snapshot holds, and the unnamed subset.
"""

import collections
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

import snapshot

CAPTURE = ROOT / "snapshots" / "modwar19.names.txt"


def main():
    if not CAPTURE.exists():
        raise SystemExit(f"{CAPTURE} not found -- run snapshot_names against MODWAR19 first")

    path = next((p for p in snapshot.snapshots()
                 if "blkopscw" in os.path.basename(p).lower()), None)
    if not path:
        raise SystemExit("no Cold War snapshot found")

    snap = snapshot.read(path)
    all_ids = {aid for aid, _ in snap.records}
    print(f"Cold War snapshot: {len(all_ids)} distinct ids")

    known = snapshot.known_hashes()
    print(f"published tables:  {len(known)} hashes resolved")

    names = []
    for line in CAPTURE.read_text(encoding="utf-8", errors="replace").splitlines():
        _, _, name = line.partition(",")
        if name:
            names.append(name)
    print(f"captured names:    {len(names)}\n")

    in_game_named = 0        # hashes to an id Cold War holds, and the tables already name it
    in_game_unnamed = 0      # hashes to an id Cold War holds, and nobody has named it  <-- gold
    published_only = 0       # the tables know this name, but Cold War does not hold the asset
    nowhere = 0
    unnamed_examples = []

    for name in names:
        h = snapshot.fnv1a(name)
        masked = h & snapshot.ID_MASK
        in_game = masked in all_ids or h in all_ids
        is_known = h in known or masked in known

        if in_game and is_known:
            in_game_named += 1
        elif in_game:
            in_game_unnamed += 1
            if len(unnamed_examples) < 15:
                unnamed_examples.append(name)
        elif is_known:
            published_only += 1
        else:
            nowhere += 1

    total = len(names)
    def pct(n):
        return f"{n:>9} ({n / total:6.2%})"

    print("of the captured names, hashed the Cold War way:")
    print(f"  in the Cold War game AND already named   {pct(in_game_named)}")
    print(f"  in the Cold War game and UNNAMED         {pct(in_game_unnamed)}")
    print(f"  known to the tables, not in this game    {pct(published_only)}")
    print(f"  nowhere                                  {pct(nowhere)}")

    if unnamed_examples:
        print("\nunnamed Cold War assets these names would resolve:")
        for name in unnamed_examples:
            print(f"  {name[:110]}")

    hit_any = in_game_named + in_game_unnamed
    print(f"\nnames that are genuinely Cold War assets: {hit_any}")
    if hit_any == 0:
        print("\nverdict: the two titles share no asset name verbatim. The corpus cannot be")
        print("used as a candidate list -- its value, if any, is as vocabulary to recombine.")
    elif in_game_unnamed == 0:
        print("\nverdict: the overlap is real but every shared name is already published.")
        print("Verbatim is spent; recombination is where the value would be.")
    else:
        print(f"\nverdict: {in_game_unnamed} unnamed Cold War assets are named outright by this")
        print("corpus. Confirm them.")


if __name__ == "__main__":
    main()
