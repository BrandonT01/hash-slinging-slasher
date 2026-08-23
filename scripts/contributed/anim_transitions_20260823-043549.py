"""The animation transition grid, filled in where the tables never showed it.

    python contrib/anim_transitions.py --audit     the grammar, measured
    python contrib/anim_transitions.py             write the plan's two lists

## The grammar

`xanim` is the least-named of the five types in both games -- 67.2% in Black Ops 4, 63.9% in
Cold War -- and unlike the other four it has an obvious productive grammar. A transition
animation is named for the state it leaves and the state it enters:

    <core>_<from>_to_<to>        wpn_t9_ak47_sprint_to_walk

Measured against `fnv1a_xanims` and `fnv1a_xanims_v2` on 2026-08-23:

    6,146 published names match the pattern
    1,445 distinct cores, 101 distinct `from` states, 129 distinct `to` states

1,445 x 101 x 129 is 18.8 million combinations, and the tables hold 6,146 of them -- **0.03% of
the grid**. Most of the rest are nonsense, but a weapon that has `sprint_to_walk` almost certainly
has `walk_to_sprint`, and the cost of asking is one candidate.

This is why it is a plan and not a generator printing names: the grid IS a cross product, and
`confirm_plan` multiplies it at the engine's speed instead of Python's.

## What makes it different from the sweeps that came before it

`contrib/uncarried_endings.py` reached `_sprint_to_walk` as a **literal ending lifted from the
tables** -- it can only ever ask about a transition somebody has already seen somewhere. This
composes the two state vocabularies, so it reaches transitions that appear in **no** table: the
pairing is generated, not observed. That is the difference between copying a name and knowing the
rule that made it.
"""

import argparse
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

PATTERN = re.compile(r"^(.*?)_([a-z0-9]+)_to_([a-z0-9]+)$")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--states", type=int, default=140,
                        help="how many of each state vocabulary to carry")
    parser.add_argument("--wide-cores", action="store_true", default=True,
                        help="take cores from every anim name, not only from ones already "
                             "seen wearing a transition")
    args = parser.parse_args()

    import snapshot

    names = snapshot.table_names("fnv1a_xanims", "fnv1a_xanims_v2")
    names += snapshot.confirmed_names("xanim")

    left, right = collections.Counter(), collections.Counter()
    cores = set()
    for name in names:
        match = PATTERN.match(name.strip().lower())
        if match:
            cores.add(match.group(1))
            left[match.group(2)] += 1
            right[match.group(3)] += 1

    if args.audit:
        print(f"{len(names)} anim names, {sum(left.values())} match <core>_<from>_to_<to>")
        print(f"{len(cores)} cores, {len(left)} from-states, {len(right)} to-states")
        print(f"grid: {len(cores) * len(left) * len(right):,} combinations")
        print("from:", " ".join(t for t, _ in left.most_common(20)))
        print("to:  ", " ".join(t for t, _ in right.most_common(20)))
        return

    # Widen the cores. A core that has never been seen wearing a transition is still a core
    # that could wear one -- the three trailing segments come off any anim name.
    if args.wide_cores:
        for name in names:
            pieces = name.strip().lower().split("_")
            if len(pieces) > 3:
                cores.add("_".join(pieces[:-3]))
                cores.add("_".join(pieces[:-2]))

    froms = [state for state, _ in left.most_common(args.states)]
    tos = [state for state, _ in right.most_common(args.states)]
    endings = [f"_{a}_to_{b}" for a in froms for b in tos]

    (ROOT / "contrib" / "anim_cores.txt").write_text(
        chr(10).join(sorted(c for c in cores if len(c) >= 6)) + chr(10), encoding="utf-8")
    (ROOT / "contrib" / "anim_transitions.txt").write_text(
        chr(10).join(endings) + chr(10), encoding="utf-8")
    kept = sum(1 for c in cores if len(c) >= 6)
    print(f"{kept} cores x {len(endings)} transitions = {kept * len(endings):,} candidates",
          file=sys.stderr)


if __name__ == "__main__":
    main()
