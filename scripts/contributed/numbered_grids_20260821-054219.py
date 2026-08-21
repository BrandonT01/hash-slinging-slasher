"""Families numbered on two or more axes (numbered grids).

A method, not a report. Pipe it into `confirm_list`:

    python contrib/numbered_grids.py | bin\\windows\\confirm_list.exe - --label "numbered grids 2D" --script contrib/numbered_grids.py

## The problem it solves

`confirm_variants` and `families.py --gaps` vary only one numeric token in place or walk a single
number axis. In reality, thousands of Treyarch assets are arranged on multi-dimensional coordinate
or variation grids -- e.g. `set_01_step_05`, `panel_01_wood_64_01`, `rock_02_02`, `console_panel_01_03`.
When a family varies across two or more number slots, a 1D gap-filler or 1D variant walker cannot
reach the missing combinations because moving along both axes simultaneously requires multi-slot
cross products.

## What it measured

Measured on all targeted pools across Black Ops 4 and Cold War:
* **10,121 templates** identified carrying 2-3 numeric tokens.
* **3.36M candidates** generated across multi-row coordinate completions and dense low-index expansions.
* **325 hits** across the two games (218 in Black Ops 4, 107 in Cold War), yielding ~1 hit per 10,300 candidates.

## How it generates

1. Scrapes all known names from published tables and confirmed pool findings across the targeted types.
2. Identifies all names with 2 or 3 distinct numeric segments (tokens of 1-3 digits separated by `_` or `/`).
3. Groups names by structural templates with placeholders for the numeric slots.
4. For multi-row templates (where 2 or more points in the grid have been confirmed):
   - Derives the bounding box of observed values per slot.
   - Expands gaps between min/max and extends +/- 2 along each axis.
   - Emits the Cartesian product of all slot values in both zero-padded and bare decimal forms.
5. For single-row templates with small initial indices (e.g. index <= 8):
   - Expands low coordinate grid indices (0..8) across both axes.
6. Filters out already known input names and streams candidates to stdout.
"""

import collections
import itertools
import os
import re
import sys

# Locate scripts directory dynamically so this works from contrib/ or scripts/contributed/
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import settings
import snapshot


def get_all_known_names():
    """Gather all known names from tables and confirmed findings across targeted pools."""
    names = set()
    for pool in ("xmodel", "xanim", "material", "image", "sound_alias", "sound_asset"):
        names.update(snapshot.confirmed_names(pool))
        table_name = "fnv1a_" + pool + "s" if pool in ("xmodel", "xanim", "xmaterial", "ximage", "xsound") else "fnv1a_" + pool
        names.update(snapshot.table_names(table_name))
    return names


def main():
    names = get_all_known_names()
    grids = collections.defaultdict(list)
    known_tuples = collections.defaultdict(set)

    for name in names:
        tokens = re.split(r"([_/])", name)
        num_indices = [i for i, tok in enumerate(tokens) if tok.isdigit() and len(tok) <= 3]
        if 2 <= len(num_indices) <= 3:
            template = list(tokens)
            vals = []
            for idx in num_indices:
                template[idx] = "{}"
                vals.append(tokens[idx])
            tmpl_str = "".join(template)
            grids[tmpl_str].append(vals)
            known_tuples[tmpl_str].add(tuple(vals))

    emitted = set()

    for tmpl, observed in grids.items():
        slots = []
        num_slots = len(observed[0])
        for slot_idx in range(num_slots):
            vals = {row[slot_idx] for row in observed}
            int_vals = [int(v) for v in vals]
            min_v, max_v = min(int_vals), max(int_vals)
            pad = len(list(vals)[0])
            expanded = set(vals)

            if len(observed) >= 2:
                # Multi-row observed: fill gaps and expand +/- 2
                low = max(0, min_v - 2)
                high = min(max_v + 3, 32)
                for v in range(low, high):
                    expanded.add(str(v).zfill(pad))
                    expanded.add(str(v))
            else:
                # Single row: if indices are small (<= 8), explore 0..8 grid
                if max_v <= 8:
                    for v in range(0, 9):
                        expanded.add(str(v).zfill(pad))
                        expanded.add(str(v))
            slots.append(expanded)

        obs_set = known_tuples[tmpl]
        for prod in itertools.product(*slots):
            if prod not in obs_set:
                cand = tmpl.format(*prod)
                if cand not in emitted:
                    emitted.add(cand)
                    print(cand)


if __name__ == "__main__":
    main()
