"""Every name we already hold, tried verbatim against the other title -- in both slash spellings.

A method, not a report. Pipe it into `confirm_list`:

    python scripts/cross_game.py | ./bin/windows/confirm_list.exe - \
        --label "whole-name cross-game transfer" --script scripts/cross_game.py

Run it a second time with `--no-fold` to reach the ids that are hashed with their backslashes
intact; the two halves land on different ids and neither is a superset of the other. See below.

## The problem it solves

`confirm_cw` seeds *pieces* across the two games -- it says so at startup, "confirmed in BLKOPSCW
and worth trying here" -- and then recombines them as `beginning + stem + ending`. Nothing tries a
name **whole**. That sounds like it should be covered by the recombination, and mostly it is:
measured below, 38,692 of Black Ops 4's unnamed ids are reachable this way and 38,673 of them had
already been confirmed on this machine by ordinary passes.

The 19 that were left are the point. A whole name needs no beginning in `data/prefixes.txt` and no
ending in `data/suffixes.txt`, so it reaches the names those lists cannot express -- and
`reach.py` measures that gap at 4-16% of every table, with `xsounds` endings the worst at 77.1%.
This is the cheapest possible way to collect what falls through it: no generation at all, just
hashing a list that already exists.

## The two slash spellings, which is why this is not a one-liner

Black Ops 4's SAB sound names keep their literal backslashes and their ids are the hash of exactly
that, where every table stores forward slashes. `AGENTS.md` records it as absolute -- 8,385 of
8,385 known names reproduce unfolded, 0 folded -- but measured over the whole corpus that is true
of the *SAB-injected* ids only. Both spellings return names here, on different ids:

    zmb/ai/hellhounds/step/fly_hellhound_step_08.ln100.pc.snd     folded
    zmb\ai\hellhounds\step\fly_hellhound_step_00.ln100.pc.snd     unfolded

Same family, same directory, adjacent numbers, two conventions. So this emits both spellings of
every path-shaped name and lets `confirm_list` decide which lands. Offering only one silently
halves the method, and it is the half nobody would notice missing.

## What it reaches, measured 2026-08-21

2,469,429 whole names -- every non-`_v2` table plus everything confirmed here -- against Black Ops
4's 212,562 unnamed ids in the five wanted types:

| pool | ids reached |
|---|---|
| `sound_alias` | 12,990 |
| `image` | 12,025 |
| `material` | 8,363 |
| `xmodel` | 3,075 |
| `xanim` | 2,126 |
| `sound_asset` | 113 |

**19 of them were new**, every one a `sound_asset`. That is the shape of this method and it is
worth being honest about: it is a gap-filler, not a producer. It costs a couple of minutes, it
needs no lists, and it collects exactly what the end-first passes structurally cannot.

## What it is spent by

An ordinary general pass on the same game, which reaches the same ids by recombination and will
have taken the vast majority of them already. Run this *after* a general pass rather than instead
of one, and re-run it whenever the other game's confirmed corpus has grown -- that corpus is the
input, so a grown corpus is a genuinely different search.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import settings
import snapshot

BS = chr(92)

# The `_v2` tables are the IW era and use a different offset; their names teach the wrong
# conventions and docs/HASHES.md records reading them for vocabulary as a known dead end. The
# Black Ops 2 and 3 SAB tables are a different era's sound scheme and are handled by sabpaths.py.
def wanted(table):
    return not (table.endswith("_v2") or table.startswith("bo2") or table.startswith("bo3"))


def main():
    names = set()

    for path in sorted(glob.glob(os.path.join(settings.tables_csv(), "*.csv"))):
        table = os.path.splitext(os.path.basename(path))[0]
        if wanted(table):
            names.update(snapshot.table_names(table))

    names.update(snapshot.confirmed_names())

    out = sys.stdout
    for name in names:
        out.write(name + "\n")
        # The same name spelled the other way. Only path-shaped names have a second spelling, and
        # emitting it unconditionally would just double the candidate count for nothing.
        if "/" in name:
            out.write(name.replace("/", BS) + "\n")
        elif BS in name:
            out.write(name.replace(BS, "/") + "\n")


if __name__ == "__main__":
    main()
