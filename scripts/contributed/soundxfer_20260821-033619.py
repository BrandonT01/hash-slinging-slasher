"""Cold War sound stems, respelled the way Black Ops 4 spells sounds.

A method, not a report. Pipe it into `confirm_list`, and it must be `--no-fold`:

    python scripts/soundxfer.py | ./bin/windows/confirm_list.exe - --no-fold \
        --label "cross-game sound stem transfer" --script scripts/soundxfer.py

## The problem it solves

`sound_asset` is the largest unnamed ground in either game -- 70,878 of Black Ops 4's 79,263 are
unnamed -- and it is the one pool where the seed corpus is too thin to grind. Only 8,403 Black
Ops 4 sound names are known, against 860,676 sound names known for Cold War. Every other method
here recombines a game's own vocabulary, and Black Ops 4's sound vocabulary is 10.6% of a game.

The two titles share Treyarch's sound scheme exactly -- `wpn\`, `zmb\`, `fly\`, `amb\`,
`prj\`, `veh\`, `uin\` head both games -- so Cold War's 97,168 distinct stems are the richest
description of what a Black Ops 4 sound name looks like that exists anywhere.

## Why the tables cannot already do this

Two conventions differ at once, and each alone would be enough to hide the seam:

* **The tail.** Cold War writes `.ln75.pc.all.snd` and `.rn75.pc.<lang>.snd`; Black Ops 4 writes
  `.ln100.pc.snd` and five siblings. A stem shared by both games carries a different tail in each.
* **The fold.** Black Ops 4's SAB sound names keep their literal backslashes and the id is the
  hash of exactly that, where every table stores forward slashes. Measured: of 860,676 table
  names, 0 match a Black Ops 4 sound id hashed the usual folded way.

So a stem the two games genuinely share still hashes to two unrelated ids, and no table lookup in
either direction will ever connect them. This strips Cold War's tail, respells the stem with
backslashes and offers it Black Ops 4's own six tails.

## How it generates

1. Every stem in the sound tables and in everything confirmed so far, cut at its first dot.
2. Each stem crossed with the six measured Black Ops 4 tails.
3. Each stem whose basename ends in digits re-numbered across the range those families use,
   in both the padded and unpadded forms the game mixes, and crossed with the tails again.

Nothing is invented: every stem was a real name in one of the two games and every tail was
measured on a confirmed Black Ops 4 sound.

## What it is spent by

Measured 2026-08-20, against 70,860 unnamed ids: step 2 reaches 25 ids from 583,008 candidates,
step 3 a further 18 from 11,147,520. That is the whole of it -- **this seam is worth about 45
names and no more**, because the stems the two games share are mostly already named and Black
Ops 4's remaining sounds are content Cold War never shipped. It is recorded as a method because
the measurement is the useful part: it says the cross-game route into `sound_asset` is closed, so
the next person grinds Black Ops 4's own vocabulary instead of re-deriving this.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snapshot

BS = chr(92)

# Measured on the 8,403 confirmed Black Ops 4 sound names: these six cover 8,368 of them.
TAILS = (
    "ln100.pc.snd",
    "ll100.pc.snd",
    "sn100.pc.snd",
    "sl100.pc.snd",
    "pn100.pc.snd",
    "pl100.pc.snd",
)

# Confirmed numbered sound families run to the low thirties; past that they stop existing.
NUMBERS = 32

TRAILING_DIGITS = re.compile(r"^(.*?)(\d+)$")

SOUND_TABLES = [
    "fnv1a_xsounds",
    "fnv1a_americanspanish_xsounds",
    "fnv1a_brazilianportugese_xsounds",
    "fnv1a_chinese_xsounds",
    "fnv1a_english_xsounds",
    "fnv1a_french_xsounds",
    "fnv1a_german_xsounds",
    "fnv1a_italian_xsounds",
    "fnv1a_japanese_xsounds",
    "fnv1a_korean_xsounds",
    "fnv1a_polish_xsounds",
    "fnv1a_russian_xsounds",
    "fnv1a_spanish_xsounds",
]


def stems():
    """Every sound name either game knows, cut at its first dot and spelled Black Ops 4's way."""
    seen = set()

    sources = snapshot.table_names(*SOUND_TABLES)
    sources += snapshot.confirmed_names("sound_asset")
    sources += snapshot.confirmed_names("sound_alias")

    for name in sources:
        stem = name.partition(".")[0].strip().lower().replace("/", BS)
        if stem and stem not in seen:
            seen.add(stem)
            yield stem


def main():
    out = sys.stdout
    roots = set()

    for stem in stems():
        for tail in TAILS:
            out.write(stem + "." + tail + "\n")

        match = TRAILING_DIGITS.match(stem)
        if match:
            roots.add(match.group(1))

    for root in roots:
        for index in range(NUMBERS):
            for form in ("%d" % index, "%02d" % index):
                base = root + form
                for tail in TAILS:
                    out.write(base + "." + tail + "\n")


if __name__ == "__main__":
    main()
