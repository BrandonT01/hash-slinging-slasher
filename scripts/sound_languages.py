"""The same sound, in the eleven languages nobody has named it in yet.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/sound_languages.py | bin\\windows\\confirm_list.exe - \
        --label "sound language and encoding variants" --script scripts/sound_languages.py

## What problem it solves

A Cold War sound file name ends in an encoding tag, a platform, a language and `.snd`:

    vox/scripted/operators/frs1/vox_frs1_promotion_reaction_02.rn75.pc.en.snd
                                                               ^^^^    ^^

Every shipped language is a separate asset with a separate id, and the tables show the game holds
essentially all of them: measured across the twelve per-language tables, `en` has 123,368 names,
`ru` 121,209, `es` 121,207, `fj` 121,155, `fr` 121,115, `ea` 121,097, `bp` 121,083, `ge` 121,082,
`ko` 121,032, `po` 121,011, `it` 120,930, `ms` 112,060. Those numbers being so close is the whole
argument: the languages are near-parallel sets, so a name known in one is direct evidence about
eleven ids that differ from it by two characters.

No other method here reaches that. The general search would have to rediscover the entire path
from its lists to arrive at a name that is already known bar its language code, which is an
enormous amount of work to reproduce something we are holding.

## How it generates

Every sound name the tables publish and every one this machine has confirmed, respelled with each
language code and each encoding tag in turn. The name's own separators are left exactly as found,
which matters: Black Ops 4's SAB names keep their backslashes and their ids are the hash of
precisely that string, so rewriting a separator here would produce a candidate that cannot match.

Nothing is invented -- the codes are measured from the tables rather than guessed, and every stem
is a real name.

## What it reads and writes

Reads the community tables and this machine's confirmed names, via `snapshot.py`. Writes candidate
names to standard output, one per line; a count to standard error.

## Options

    --count         print how many candidates this would produce, and stop
    --game TAG      which game's confirmed names to seed from (default: the configured one)

Reusable. Re-run it after any pass that confirms sound names: each new one is eleven more
candidates.
"""
import os
import sys

# Find `scripts/` wherever this file has been filed -- see scripts/README.md.
_root = os.path.dirname(os.path.abspath(__file__))
while _root != os.path.dirname(_root) and not os.path.isfile(
    os.path.join(_root, "scripts", "snapshot.py")
):
    _root = os.path.dirname(_root)
sys.path.insert(0, os.path.join(_root, "scripts"))

import snapshot

# Measured from the twelve per-language tables, not guessed. `all` is the language-independent
# set (effects, music), which is why it is smaller and why it is still worth trying.
LANGUAGES = ["en", "fr", "ge", "it", "es", "ea", "bp", "ru", "po", "fj", "ko", "ms", "all"]

# The encoding tag. `rn75` dominates at 1,455,282 names, `ln75` has 30,622 and `ln100` 6,898 --
# but a sound present under one tag is often present under another, and the tag is two characters
# of the same string, so trying all three costs nothing worth counting.
ENCODINGS = ["rn75", "ln75", "ln100"]

# Every table that holds sound file names, in either game.
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


def parts_of(name):
    """A sound name split into (stem, encoding, platform, language), or None if it is not one.

    Matched from the right, because the stem itself is full of dots and any split from the left
    lands in the middle of one.

    **Two shapes, and missing the second one made this method blind to the larger game.** Cold War
    names carry a language: `....rn75.pc.en.snd`. Black Ops 4's SAB names do not:
    `fly\\emotes\\teddybear_in.ln100.pc.snd` is stem, encoding, platform. Requiring four pieces
    silently skipped every Black Ops 4 name -- which is where 70,878 of the 79,263 unnamed
    `sound_asset` ids are. The language comes back as None, and the generator then knows to try
    inserting one as well as swapping it.
    """
    if not name.endswith(".snd"):
        return None

    pieces = name[: -len(".snd")].rsplit(".", 3)

    if len(pieces) == 4:
        stem, encoding, platform, language = pieces
    elif len(pieces) == 3:
        stem, encoding, platform = pieces
        language = None
    else:
        return None

    if not stem or not encoding or not platform:
        return None

    return stem, encoding, platform, language


def seeds(game):
    """Every sound name known to be real, from the tables and from what has been confirmed."""
    names = list(snapshot.table_names(*TABLES))
    names += list(snapshot.confirmed_names("sound_asset"))

    out = set()
    for name in names:
        name = name.strip()
        if name:
            # Lower cased, because the hash lower cases; separators left exactly as found.
            out.add(name.lower())

    return out


def candidates(game):
    seen = set()

    for name in seeds(game):
        split = parts_of(name)
        if not split:
            continue

        stem, encoding, platform, language = split

        for other_encoding in ENCODINGS:
            # The language-less shape, which is how Black Ops 4 spells them. Worth trying even
            # from a Cold War seed: the two games share a great deal of content, and a name that
            # exists in both is spelled the other game's way there.
            bare = "%s.%s.%s.snd" % (stem, other_encoding, platform)
            if bare not in seen:
                seen.add(bare)
                yield bare

            for other_language in LANGUAGES:
                if other_language == language and other_encoding == encoding:
                    continue  # the name we already have

                candidate = "%s.%s.%s.%s.snd" % (stem, other_encoding, platform, other_language)
                if candidate not in seen:
                    seen.add(candidate)
                    yield candidate


def main(argv):
    counting = "--count" in argv
    game = None
    if "--game" in argv:
        game = argv[argv.index("--game") + 1]

    made = 0
    for name in candidates(game):
        made += 1
        if not counting:
            print(name)

    sys.stderr.write("%d candidates from %d language codes and %d encodings\n"
                     % (made, len(LANGUAGES), len(ENCODINGS)))
    if counting:
        print("%d candidates" % made)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
