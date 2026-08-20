"""Names one token longer or one token shorter than a name we already have.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/token_edits.py --type model | bin\\windows\\confirm_list.exe - \
        --label "token insertion and deletion" --script scripts/token_edits.py

## The gap this fills

Every method in `METHODS.md` **substitutes**, and none of them changes a name's *length*:

  - the general search rebuilds a name as `beginning + stem + ending` -- three parts, and the
    stem is one piece cut from a seed, so nothing is added between two kept pieces
  - `confirm_variants` replaces a number in place
  - `slotswap` (method 10) replaces one token with another measured for that slot
  - `templates` (method 11) replaces several at once

All of those keep the token count exactly as the seed had it. So a name that is a known name plus
one word, or minus one word, is unreachable by all of them however long they run:

    p9_rus_apartment_tower_sign_01
    p9_rus_apartment_tower_sign_01_dirty     <- an ending, reachable
    p9_rus_apartment_stone_tower_sign_01     <- an insertion, reachable by nothing

That second case is common in this game's naming because artists qualify a name as an asset set
grows -- a `wall` becomes a `stone_wall` when a second material shows up -- and both spellings
survive in the build.

Deletion is the same gap from the other side, and it is the cheaper half: dropping a token from a
real name asks whether the unqualified name also exists, which needs no vocabulary at all and
produces only as many candidates as the seed has tokens.

## How it generates

**Deletions** need nothing measured: each token of each known name is dropped in turn.

**Insertions** are seeded, never invented. For each position, the vocabulary offered is the set of
tokens actually observed *at that position* across names sharing the same leading token -- so a
name beginning `p9_` is offered the words that follow `p9_` elsewhere, not the corpus's globally
common words. That keeps this inside the seeding principle and keeps the output small enough to
matter: a global vocabulary at every position would produce more candidates than the general
search and reach less.

## What it reads and writes

Reads the community tables for the chosen type and this machine's confirmed names, via
`snapshot.py`. Writes candidates to standard output, one per line; sizing to standard error.

## Options

    --type NAME      model, material, image, anim or alias (default: model)
    --cap N          most insertion words offered per position (default 12)
    --min-seen N     times a word must appear at a position to be offered (default 8)
    --no-insert      deletions only -- far smaller, and the higher-precision half
    --count          print how many candidates this would produce, and stop

Reusable. Deletions are exhausted after one run against a fixed corpus; insertions reopen
whenever `--cap` or the corpus changes.
"""
import collections
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

TYPES = {
    "model": ("fnv1a_xmodels", "xmodel"),
    "material": ("fnv1a_xmaterials", "material"),
    "image": ("fnv1a_ximages", "image"),
    "anim": ("fnv1a_xanims", "xanim"),
    "alias": ("fnv1a_soundbanks_aliases", "sound_alias"),
}

# Beyond this a name is a generated identifier rather than a composed one, and editing it produces
# vocabulary that means nothing.
MAX_TOKENS = 12


def corpus(kind):
    table, confirmed = TYPES[kind]
    names = list(snapshot.table_names(table)) + list(snapshot.confirmed_names(confirmed))

    out = set()
    for name in names:
        name = name.strip().lower().replace("\\", "/")
        if name:
            out.add(name)
    return out


def split(name):
    """(directory, tokens). The directory is kept whole -- it is a closed vocabulary, and
    inserting words into a path invents directories that do not exist."""
    directory, _, base = name.rpartition("/")
    if directory:
        directory += "/"
    return directory, base.split("_")


def vocabulary(parsed, cap, min_seen):
    """{(leading token, position): [words observed there]}.

    Keyed on the leading token so that `p9_` names offer what follows `p9_`, rather than what is
    common across the whole type. A global list would be the same handful of words everywhere and
    would reach almost nothing.
    """
    seen = collections.defaultdict(collections.Counter)

    for _, tokens in parsed:
        if len(tokens) > MAX_TOKENS:
            continue
        head = tokens[0]
        for position, token in enumerate(tokens):
            seen[(head, position)][token] += 1

    out = {}
    for key, counter in seen.items():
        words = [word for word, count in counter.most_common(cap) if count >= min_seen]
        if words:
            out[key] = words
    return out


def main(argv):
    kind = "model"
    if "--type" in argv:
        kind = argv[argv.index("--type") + 1]
    if kind not in TYPES:
        raise SystemExit("--type must be one of: %s" % ", ".join(sorted(TYPES)))

    cap = int(argv[argv.index("--cap") + 1]) if "--cap" in argv else 12
    min_seen = int(argv[argv.index("--min-seen") + 1]) if "--min-seen" in argv else 8
    counting = "--count" in argv
    inserting = "--no-insert" not in argv

    known = corpus(kind)
    parsed = [split(name) for name in known]
    words = vocabulary(parsed, cap, min_seen) if inserting else {}

    seen = set()
    made = 0

    for directory, tokens in parsed:
        if len(tokens) > MAX_TOKENS or len(tokens) < 2:
            continue

        # Deletions: drop each token in turn.
        for position in range(len(tokens)):
            shorter = tokens[:position] + tokens[position + 1:]
            if not shorter:
                continue
            candidate = directory + "_".join(shorter)
            if candidate not in known and candidate not in seen:
                seen.add(candidate)
                made += 1
                if not counting:
                    print(candidate)

        if not inserting:
            continue

        # Insertions: offer each position the words measured to occur there.
        head = tokens[0]
        for position in range(1, len(tokens) + 1):
            for word in words.get((head, min(position, len(tokens) - 1)), ()):
                longer = tokens[:position] + [word] + tokens[position:]
                candidate = directory + "_".join(longer)
                if candidate not in known and candidate not in seen:
                    seen.add(candidate)
                    made += 1
                    if not counting:
                        print(candidate)

    sys.stderr.write("%s: %d known names, %d candidates\n" % (kind, len(known), made))
    if counting:
        print("%d candidates" % made)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
