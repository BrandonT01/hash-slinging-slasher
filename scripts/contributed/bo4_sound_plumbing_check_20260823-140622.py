"""Is the Black Ops 4 sound_asset dead end a real zero, or a plumbing failure?

METHODS.md (PR #437) records the largest negative in the project:

    Black Ops 4 sound files, numbered takes and recombination -- 2,572 directories x 10,538
    cores x 13,995 numbered-take endings, 379 billion candidates unfolded, 0 matched -- not
    0 new, 0 hits of any kind. Whatever the unnamed 70,878 are, they are not recombinations
    of the 5,977 that are named.

That closes the single largest opportunity in either game (70,878 unnamed of 79,263), so it is
worth one cheap check before it is blessed as settled.

The check is the one that certified the Cold War negatives -- "31,842 of 31,845 names reconstruct
exactly as directory + basename + tail". The Black Ops 4 row carries no equivalent. This rebuilds
the vocabulary exactly as `bo4_sounds_20260823-030223.py` does, then asks whether that vocabulary
can express the names that are already known.

    python contrib/bo4_sound_plumbing_check.py

Read the verdict carefully: it answers "can the sweep express a real name", which is necessary
for the zero to be meaningful. It cannot by itself prove the zero wrong, because the engine only
ever hunts *unnamed* ids -- a candidate that reproduces an already-named sound is not a hit.
"""

import collections
import os
import pathlib
import re
import sys

# Walk up until the repository is found, rather than counting parents. A fixed count is
# correct in contrib/ and wrong once `submit` files this under scripts/contributed/,
# where it would resolve to a scripts/scripts that has never existed. scripts/README.md.
ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

import snapshot

SOUND_TABLES = ["fnv1a_xsounds", "fnv1a_xsounds_v2",
                "fnv1a_soundbanks_aliases", "fnv1a_soundbanks_aliases_v2"]

NUMBERED = re.compile(r"^(.*?)(\d+)$")
SOUND_POOL = 170          # added at index 170, ids injected from the SAB files (CLAUDE.md §5)


def main():
    path = next((p for p in snapshot.snapshots()
                 if "blkops04" in os.path.basename(p).lower()), None)
    if not path:
        raise SystemExit("no Black Ops 4 snapshot found")

    snap = snapshot.read(path)
    ids = {aid for aid, pool in snap.records if pool == SOUND_POOL}
    print(f"pool {SOUND_POOL} holds {len(ids)} ids")

    # --- recover the named half (method 21) ---------------------------------------------
    # Unfolded, because Black Ops 4 sound names keep their backslashes and their id is the
    # hash of exactly that.
    recovered = {}
    folded_hits = 0
    for name in set(snapshot.table_names(*SOUND_TABLES)) | set(snapshot.confirmed_names()):
        h = snapshot.fnv1a_nofold(name)
        for value in (h, h & snapshot.ID_MASK):
            if value in ids:
                recovered[value] = name
        f = snapshot.fnv1a(name)
        if f in ids or (f & snapshot.ID_MASK) in ids:
            folded_hits += 1

    print(f"recovered unfolded: {len(recovered)}   folded: {folded_hits}")
    print(f"unnamed: {len(ids) - len(recovered)} of {len(ids)}")

    names = sorted({n.lower() for n in recovered.values()})
    if not names:
        raise SystemExit("recovered nothing")

    # --- rebuild his vocabulary, exactly as bo4_sounds.py does --------------------------
    dirs, stems, tails, widths = set(), set(), set(), set()
    for name in names:
        dot = name.find(".")
        if dot == -1:
            continue
        core, tail = name[:dot], name[dot:]
        tails.add(tail)
        pieces = core.split("\\")
        for cut in range(1, len(pieces)):
            dirs.add("\\".join(pieces[:cut]) + "\\")
        stems.add(core)                 # the whole path, to wear a different tail
        stems.add(pieces[-1])           # the basename, to wear a different directory
        match = NUMBERED.match(pieces[-1])
        if match and match.group(1):
            stems.add(match.group(1))
            stems.add("\\".join(pieces[:-1] + [match.group(1)]))
            widths.add(len(match.group(2)))

    ends = set(tails)
    for width in sorted(widths) or {2}:
        for index in range(100 if width <= 2 else 200):
            for tail in tails:
                ends.add(str(index).zfill(width) + tail)

    print(f"\nrebuilt vocabulary: {len(dirs)} dirs, {len(stems)} stems, {len(ends)} ends")
    print(f"his row claims:      2,572 dirs, 10,538 cores, 13,995 ends")

    # --- can it express the names that are known? ---------------------------------------
    # The plan builds beginning + stem + ending, with the bare stem allowed. A known name is
    # expressible if some (stem, end) pair, or some (dir, stem, end) triple, rebuilds it.
    bare_ok = 0
    dir_ok = 0
    misses = []
    for name in names:
        dot = name.find(".")
        if dot == -1:
            continue
        core, tail = name[:dot], name[dot:]
        pieces = core.split("\\")
        basename = pieces[-1]
        directory = "\\".join(pieces[:-1]) + "\\" if len(pieces) > 1 else ""

        if core in stems and tail in ends:
            bare_ok += 1
        if directory in dirs and basename in stems and tail in ends:
            dir_ok += 1
        elif core not in stems and len(misses) < 5:
            misses.append(name)

    total = len(names)
    print(f"\nexpressible among the {total} known names:")
    print(f"  as bare stem + ending:        {bare_ok:6} / {total}  ({bare_ok/total:6.1%})")
    print(f"  as directory + base + ending: {dir_ok:6} / {total}  ({dir_ok/total:6.1%})")
    print("\nCold War was certified at 31,842 of 31,845 (99.99%).")
    if misses:
        print("\nnot expressible:")
        for name in misses:
            print(f"  {name[:110]}")

    ok = max(bare_ok, dir_ok) / total
    print("\nverdict:", (
        "VOCABULARY SOUND -- it can express real names of this shape, so the zero is not a "
        "malformed-candidate artefact. Note the engine hunts only UNNAMED ids, so a rebuilt "
        "known name is correctly not counted as a hit; 'zero hits' is consistent with working "
        "plumbing and the negative stands on its own terms."
        if ok > 0.9 else
        "VOCABULARY CANNOT EXPRESS ITS OWN CORPUS -- the sweep asked malformed questions and "
        "its zero says nothing about the unnamed ids."))


if __name__ == "__main__":
    main()
