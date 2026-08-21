"""Black Ops 4 SAB sound names, rebuilt from the path structure its own known names carry.

A method, not a report. Pipe it into `confirm_list`, and it must be `--no-fold`:

    python scripts/sabpaths.py | ./bin/windows/confirm_list.exe - --no-fold \
        --label "SAB directory and basename recombination" --script scripts/sabpaths.py

## The problem it solves

`sound_asset` in Black Ops 4 is the largest unnamed ground in either game -- 70,876 of 79,263 --
and the general sound pass reaches almost none of it. The reason is structural, not incidental:
a general pass composes `beginning + stem + ending`, and its beginnings are the 700 measured in
`data/sound.prefixes.txt`. A Black Ops 4 sound name is a *deep path* --
`amb\environment\wind\gusts\gust_leaves\...`, five and six segments -- and no 700-entry beginning
list can express one. METHODS.md records the consequence: a dedicated sound pass returns ~169.

## What it learns first

Every sound-shaped name in every table, plus everything confirmed here, is hashed *unfolded* and
kept only if it reproduces an id the Black Ops 4 snapshot actually holds in `sound_asset`. That
is 8,446 names, and they are the only description of the convention that exists. Measured on them:

* **2,267 distinct directories**, **7,689 distinct basenames**, path depth 3-6 segments.
* Six tails cover 8,409 of them: `ln100` 6,761, `ll100` 932, `sn100` 346, `sl100` 181,
  `pn100` 169, `pl100` 20 -- each `.pc.snd`.
* Fifteen top-level heads: `wpn` 1,572, `zmb` 1,474, `fly` 1,391, `amb` 1,214, `prj` 538,
  `mpl` 443, `veh` 391, `uin` 303, `phy` 237, `exp`, `pfx`, `chr`, `blk`, `dst`, `mus`.

The names average 3.7 per directory, so a directory known to exist is a directory whose other
members are overwhelmingly unnamed. That is the ground this reaches.

## Where the extra directories come from

`bo2_sab.csv` and `bo3_sab.csv` hold 400,815 Black Ops 2 and 3 SAB audio paths. Nothing in this
repository has ever used them, because they are SDBM-hashed and so are not "our games" for
exclusion -- but their *names* are Treyarch sound paths from the two titles Black Ops 4 descends
from, and the tail scheme is visibly the same counter: BO2 `.SN65.pc.snd`, BO3 `.SN85.pc.snd`,
BO4 `.sn100.pc.snd`.

Measured before building this: BO3 shares **9.18%** of its stems with known Black Ops 4 / Cold War
sound stems, BO2 **1.35%**. For comparison the seams METHODS.md records as dead measured 0.7%,
0.1% and 0. Offered verbatim the transfer is weak -- 1,721,304 candidates for 3 new names, 1 per
573,768 -- and every one that landed was a *directory* match
(`amb\environment\wind\snowy\wind_snow_l.sl100.pc.snd`). So this takes their directories, not
their stems.

## How it generates

1. **Numbering.** Every known basename ending in digits, walked across the range its own family
   uses, in the padded and unpadded forms the game mixes, under its own directory.
2. **Recombination.** Every directory crossed with the basenames seen under the *same top-level
   head*. Restricting to the head is what keeps this from being a blind cross product: a `wpn`
   basename under an `amb` directory is not a name the game would have.
3. **Borrowed directories.** The Black Ops 2 and 3 directories whose head is one of the fifteen,
   crossed with Black Ops 4 basenames under that head.

Each of the three is crossed with the six measured tails. Nothing is invented: every directory,
basename and tail was a real Treyarch sound name.
"""
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import settings
import snapshot

BS = chr(92)

# Measured on the names that reproduce a Black Ops 4 sound_asset id: these six cover 8,409 of 8,446.
TAILS = (
    "ln100.pc.snd",
    "ll100.pc.snd",
    "sn100.pc.snd",
    "sl100.pc.snd",
    "pn100.pc.snd",
    "pl100.pc.snd",
)

# A basename's trailing number, which is what step 1 walks.
TRAILING = re.compile(r"^(.*?)(\d+)$")

# The leading language directory Black Ops 2 and 3 SAB paths carry and Black Ops 4 does not.
LANG_HEAD = re.compile(r"^(?:[a-z]{2}|devraw[\\/][a-z]+)[\\/]", re.I)


def sab_stem(name):
    """A Black Ops 2/3 SAB path reduced to the part Black Ops 4 would recognise."""
    n = name.replace("/", BS)
    n = LANG_HEAD.sub("", n)
    cut = n.find(".")
    return (n[:cut] if cut > 0 else n).lower()


def known_bo4_sab():
    """Every name that actually reproduces a Black Ops 4 `sound_asset` id, hashed unfolded."""
    snaps = [snapshot.read(p) for p in snapshot.snapshots()]
    bo4 = [s for s in snaps if s.game == "BLKOPS04"]
    if not bo4:
        raise SystemExit("no BLKOPS04 snapshot -- run snapshot.py first")
    snap = bo4[0]
    ids = {a for a, p in snap.records if snap.pool_name(p) == "sound_asset"}

    names = []
    for path in sorted(glob.glob(os.path.join(settings.tables_csv(), "*.csv"))):
        base = os.path.splitext(os.path.basename(path))[0]
        if "sound" in base or "sab" in base:
            names.extend(snapshot.table_names(base))
    names.extend(snapshot.confirmed_names("sound_asset"))

    out = {}
    for n in names:
        nb = n.replace("/", BS)
        key = snapshot.fnv1a_nofold(nb) & snapshot.ID_MASK
        if key in ids:
            out[key] = nb
    return list(out.values())


def split(name):
    """`dir`, `basename`, `tail` of a Black Ops 4 SAB name."""
    cut = name.find(".")
    stem, tail = (name[:cut], name[cut + 1:]) if cut > 0 else (name, "")
    parts = stem.split(BS)
    return BS.join(parts[:-1]), parts[-1], tail


def main():
    report = "--report" in sys.argv

    known = known_bo4_sab()
    dirs_by_head = collections.defaultdict(set)
    bases_by_head = collections.defaultdict(set)
    families = collections.defaultdict(set)      # (dir, prefix) -> numbers seen

    for name in known:
        d, b, _ = split(name)
        if not d:
            continue
        head = d.split(BS)[0]
        dirs_by_head[head].add(d)
        bases_by_head[head].add(b)
        m = TRAILING.match(b)
        if m:
            families[(d, m.group(1))].add(int(m.group(2)))

    heads = set(dirs_by_head)

    # Black Ops 2 and 3 directories, kept only where the head is one Black Ops 4 uses.
    borrowed = collections.defaultdict(set)
    for table in ("bo2_sab", "bo3_sab"):
        for n in snapshot.table_names(table):
            stem = sab_stem(n)
            parts = stem.split(BS)
            if len(parts) < 2:
                continue
            d = BS.join(parts[:-1])
            head = parts[0]
            if head in heads and d not in dirs_by_head[head]:
                borrowed[head].add(d)

    if report:
        step2 = sum(len(dirs_by_head[h]) * len(bases_by_head[h]) for h in heads)
        step3 = sum(len(borrowed[h]) * len(bases_by_head[h]) for h in heads)
        print("known BLKOPS04 SAB names: %d" % len(known))
        print("heads: %d   directories: %d   basenames: %d"
              % (len(heads), sum(len(v) for v in dirs_by_head.values()),
                 sum(len(v) for v in bases_by_head.values())))
        print("borrowed BO2/BO3 directories under those heads: %d"
              % sum(len(v) for v in borrowed.values()))
        print("step 2 pairs: %d  -> %d candidates" % (step2, step2 * len(TAILS)))
        print("step 3 pairs: %d  -> %d candidates" % (step3, step3 * len(TAILS)))
        for h in sorted(heads, key=lambda x: -len(dirs_by_head[x]) * len(bases_by_head[x])):
            print("   %-8s dirs %5d  bases %5d  borrowed %5d  pairs %9d"
                  % (h, len(dirs_by_head[h]), len(bases_by_head[h]), len(borrowed[h]),
                     len(dirs_by_head[h]) * len(bases_by_head[h])))
        return

    seen = set()
    out = sys.stdout

    def emit(stem):
        if stem in seen:
            return
        seen.add(stem)
        for tail in TAILS:
            out.write(stem + "." + tail + "\n")

    # 1. numbering, walked over the range each family actually uses
    for (d, prefix), numbers in families.items():
        lo, hi = min(numbers), max(numbers)
        width = max(len(str(n)) for n in numbers)
        for i in range(max(0, lo - 2), hi + 6):
            emit("%s%s%s%0*d" % (d, BS, prefix, width, i))
            if width > 1:
                emit("%s%s%s%d" % (d, BS, prefix, i))

    # 2. every directory crossed with the basenames of its own head
    for head in sorted(heads):
        for d in sorted(dirs_by_head[head]):
            for b in sorted(bases_by_head[head]):
                emit(d + BS + b)

    # 3. the borrowed Black Ops 2 and 3 directories, same crossing
    for head in sorted(borrowed):
        for d in sorted(borrowed[head]):
            for b in sorted(bases_by_head[head]):
                emit(d + BS + b)


if __name__ == "__main__":
    main()
