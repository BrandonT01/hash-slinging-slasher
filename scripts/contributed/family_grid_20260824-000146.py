"""Complete the grids the recovered names are shaped like.

    python contrib/family_grid.py --audit          rank the families, emit nothing
    python contrib/family_grid.py --top 8          how many families to fill
    python contrib/family_grid.py | confirm_list - --label "family grid" --script contrib/family_grid.py

## Why grids

`scripts/unnamed_profile.py` shows that the names this project recovers are a different shape
from the published tables: shorter, flatter, far less numeric, and heavily concentrated in a
handful of families -- `vox_` alone is a third of everything ever found here, against two
hundredths of a percent of the tables.

Those families are not free text. They are grids: `vox_<speaker>_<line>` over hundreds of speaker
codes and thousands of lines, where every speaker records broadly the same lines. The same shape
runs through `p7_`/`p8_`/`p9_`, `wpn_`, `fly_`, `evt_`, `icon_`, `att_`. Most of the grid is
unnamed, so the unseen cells are candidates by construction rather than by guesswork.

## What this is not

It is a cross product over one corpus, which §8 warns is bounded by that corpus -- so it cannot
reach a name whose vocabulary is not already here. That limit is real and it is why this returns
tens rather than thousands.

What makes it worth running anyway is that the bound is not the *named* region. A grid cell is a
line one speaker has and another does not; the vocabulary is shared by construction, and the game
holds the asset either way. That is the one shape where recombining a corpus with itself still
reaches ground it does not already cover.

Measured 2026-08-23 on Cold War: 5.56 M unseen `vox_` cells returned 34 names in twelve seconds,
and 50.3 M cells across every family returned 10 more. A low rate per candidate, and the
candidates cost nothing.
"""

import argparse
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

import snapshot

SOUND_TABLES = ["fnv1a_soundbanks_aliases", "fnv1a_soundbanks_aliases_v2",
                "fnv1a_xsounds", "fnv1a_xsounds_v2"]
ASSET_TABLES = ["fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
                "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2"]


def families(have, min_members, min_axis, min_tails):
    """{head: (axis values, tails)} for every `head_<axis>_<tail>` family worth filling."""
    grouped = collections.defaultdict(list)
    for name in have:
        # Paths and dotted sound tails are a different grammar and are left alone.
        if name.count("_") >= 2 and "/" not in name and "." not in name and "\\" not in name:
            grouped[name.split("_", 1)[0]].append(name)

    out = {}
    for head, names in grouped.items():
        if len(names) < min_members:
            continue
        axis, tails = set(), collections.Counter()
        for name in names:
            parts = name.split("_", 2)
            if len(parts) == 3 and parts[1] and parts[2]:
                axis.add(parts[1])
                tails[parts[2]] += 1
        if len(axis) < min_axis or len(tails) < min_tails:
            continue

        # Only the tails more than one axis value already uses. A tail seen under a single value
        # is not evidence of a grid -- it is one asset that happens to sort here, and pairing it
        # with every other value invents names nothing suggests. `i_` looks enormous by raw
        # product and collapses to almost nothing under this, which is the point: it is not a
        # grid, it is every name beginning `i_`.
        shared = {tail for tail, count in tails.items() if count > 1}
        if len(shared) < min_tails:
            continue
        out[head] = (axis, shared)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--audit", action="store_true", help="rank the families and stop")
    ap.add_argument("--top", type=int, default=8, help="how many families to fill")
    ap.add_argument("--cap", type=int, default=60_000_000, help="most cells to emit in total")
    ap.add_argument("--min-members", type=int, default=200)
    ap.add_argument("--min-axis", type=int, default=3)
    ap.add_argument("--min-tails", type=int, default=20)
    args = ap.parse_args()

    have = {n.lower() for n in snapshot.confirmed_names()}
    have |= {n.lower() for n in snapshot.table_names(*(SOUND_TABLES + ASSET_TABLES))}
    have.discard("")
    print(f"{len(have)} names known", file=sys.stderr)

    found = families(have, args.min_members, args.min_axis, args.min_tails)
    ranked = sorted(found.items(), key=lambda kv: -(len(kv[1][0]) * len(kv[1][1])))

    if args.audit:
        print(f"{len(ranked)} families\n", file=sys.stderr)
        for head, (axis, tails) in ranked[:30]:
            print(f"  {head:14} {len(axis):5} x {len(tails):7} = {len(axis)*len(tails):>12,}")
        return

    emitted = 0
    for head, (axis, tails) in ranked[: args.top]:
        for a in sorted(axis):
            for t in sorted(tails):
                if emitted >= args.cap:
                    print(f"emitted {emitted} (capped)", file=sys.stderr)
                    return
                cell = f"{head}_{a}_{t}"
                if cell not in have:
                    print(cell)
                    emitted += 1
    print(f"emitted {emitted} unseen cells from {min(args.top, len(ranked))} families",
          file=sys.stderr)


if __name__ == "__main__":
    main()
