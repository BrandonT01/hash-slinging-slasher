"""The same voice line, spoken by every speaker the game has -- the sound grid nothing reaches.

    python contrib/speaker_grids.py | bin/windows/confirm_list.exe - \
        --label "speaker grids" --script contrib/speaker_grids.py

**What problem it solves.** `scripts/reach.py` measures the sound lists against the published
sound tables and puts `xsounds` at **10.6% `named`**: nine tenths of real Cold War sound-file
names carry a beginning the 700-entry sound prefix list cannot express, so no general pass can
ever build them however long it runs. The names it cannot reach are not scattered -- they are
deep, regular voice paths, and the reach report names them itself (`vox/scripted/wolf/vox_`,
449 names; `vox/scripted/bdzr/vox_`, 448; six more of the same shape).

**Why it is not the dead end in METHODS.md.** "Recombining sound file paths, in either game, at
any corpus density" is recorded dead -- directory x basename, 0 new of 400,000. That measurement
transplanted a basename *verbatim* under another directory. For this family that is guaranteed
to fail, because the leaf directory name is **also a token inside the basename**:

    vox/scripted/mpl/abnd/vox_abnd_bb_ctf_start_00.rn75.pc.en.snd
                     ^^^^      ^^^^

Moving that basename under `anbo/` yields `vox/scripted/mpl/anbo/vox_abnd_...`, which is not how
the game spells anything. The axis has to be substituted in *both* places at once. That is a
transformation, not a transplant, and it is why the recorded negative does not cover this ground.

**The structure, measured 2026-08-22** over `fnv1a_xsounds` + `fnv1a_english_xsounds` + everything
confirmed: 69,510 `vox/scripted/` names, **62,965 of which (90.6%) match `<parent>/<key>/vox_<key>_<line>`
exactly**. Grouping them into (parent -> speakers x lines) grids:

    parent dir                     speakers   lines     cells     holes
    vox/scripted/operators               37     753     27861      8417
    vox/scripted/ping                    37     509     18833      4628
    vox/scripted/zm_operators            37     389     14393      3372
    vox/scripted                         37     258      9546       675
    vox/scripted/mpl                     64    1738    111232    102092

`operators`, `ping` and `zm_operators` are grids that are **70% filled already** -- the game
really does record every line for every operator -- so their holes are the highest-confidence
candidates in the pool. Six `mpl` speakers carry an inventory of *exactly* 1,098 lines apiece,
which is what a filled row looks like.

**Reads** every published sound table and every confirmed `sound_asset` name. **Writes** the
holes: for each grid, each speaker crossed with each line the grid knows, spelled with the
speaker token substituted in both the directory and the basename, wearing only the tails that
line has actually been observed with. Names already known are dropped. **Writes backslashes**,
which is the spelling Black Ops 4 hashes and which Cold War folds, so one output serves both.

**Reusable.** It refills whenever a pass confirms a sound name that adds a speaker or a line to
any grid, so it is worth re-running after any pass that gains sounds.
"""
import os
import sys
import collections

# Find `scripts/` wherever this file has been filed -- `contrib/`, `scripts/`, or
# `scripts/contributed/` after `submit` files it. Walk up rather than counting parents.
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

# Every sound table in cod-name-db that holds file paths for these two eras. The language tables
# are included deliberately: a line recorded for one speaker in one language is direct evidence
# of the same line for another speaker, and they are where most of the vox corpus lives.
TABLES = [
    "fnv1a_xsounds",
    "fnv1a_english_xsounds",
    "fnv1a_french_xsounds",
    "fnv1a_german_xsounds",
    "fnv1a_italian_xsounds",
    "fnv1a_spanish_xsounds",
    "fnv1a_americanspanish_xsounds",
    "fnv1a_brazilianportugese_xsounds",
    "fnv1a_russian_xsounds",
    "fnv1a_polish_xsounds",
    "fnv1a_japanese_xsounds",
    "fnv1a_korean_xsounds",
    "fnv1a_chinese_xsounds",
]


def known_sound_names():
    """Every sound file name anybody here can see, folded to forward slashes and lower cased."""
    names = set()

    for name in snapshot.table_names(*TABLES):
        names.add(name.strip().lower().replace("\\", "/"))
    for name in snapshot.confirmed_names("sound_asset"):
        names.add(name.strip().lower().replace("\\", "/"))

    names.discard("")
    return names


def split(name):
    """`a/b/key/vox_key_line.tail` -> (`a/b`, `key`, `line`, `tail`), or None if it is not one.

    The requirement that the leaf directory appear as a token in the basename is the whole
    method: it is what makes the axis substitutable, and it is what the verbatim-transplant
    measurement recorded dead could not have used.
    """
    directory, _, last = name.rpartition("/")
    if not directory or "/" not in directory:
        return None

    core, dot, tail = last.partition(".")
    if not dot:
        return None

    parent, _, key = directory.rpartition("/")
    if not key or not parent:
        return None

    # The line is what is left once the speaker token is taken out of the basename. Anchoring on
    # `_<key>_` rather than a bare substring keeps `ami6` from matching inside another token.
    marker = "_" + key + "_"
    at = core.find(marker)
    if at < 0:
        return None

    line = core[:at] + "_\x00_" + core[at + len(marker):]
    return parent, key, line, tail


def main():
    known = known_sound_names()
    print("%d known sound names" % len(known), file=sys.stderr)

    # parent -> speakers seen, and parent -> line -> tails that line wears anywhere.
    speakers = collections.defaultdict(set)
    lines = collections.defaultdict(lambda: collections.defaultdict(set))
    matched = 0

    for name in known:
        piece = split(name)
        if piece is None:
            continue
        parent, key, line, tail = piece
        matched += 1
        speakers[parent].add(key)
        lines[parent][line].add(tail)

    print(
        "%d names sit in a speaker grid, across %d parent directories"
        % (matched, len(speakers)),
        file=sys.stderr,
    )

    produced = 0
    seen = set()

    for parent in sorted(speakers):
        who = speakers[parent]

        # A grid needs at least two speakers to have an axis at all; one speaker tells us
        # nothing about anybody else and would just re-emit what we already have.
        if len(who) < 2:
            continue

        for line, tails in lines[parent].items():
            for key in who:
                core = line.replace("\x00", key)
                for tail in tails:
                    name = "%s/%s/%s.%s" % (parent, key, core, tail)
                    if name in known or name in seen:
                        continue
                    seen.add(name)
                    produced += 1
                    print(name.replace("/", "\\"))

    print("%d candidates" % produced, file=sys.stderr)


if __name__ == "__main__":
    main()
