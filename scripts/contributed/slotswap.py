"""Swap one token of a known name for the tokens measured to occupy that same slot elsewhere.

A method, not a report. Pipe it into `confirm_list`.

    python scripts/slotswap.py | ./bin/windows/confirm_list.exe - \
        --label "sibling token substitution" --script scripts/slotswap.py

## The problem it solves

The median confirmed name has seven or eight underscore-separated segments, and three existing
methods each reach only part of such a name:

* the **general search** recombines `beginning + stem + ending`. It can replace the head or the
  tail of a name, but there is no shape of that rule which alters a token in the *middle* while
  keeping both sides intact.
* **numbers in place** (`confirm_variants`) does change a middle token -- but only when that
  token is a number. `_01` becomes `_02`; `_wood` never becomes `_metal`.
* **per-prefix continuations** grows a prefix rightwards. Everything to the right of the
  insertion point is generated, so a known tail cannot be preserved.

What is left uncovered is the commonest kind of sibling in this game's naming: two names that are
identical except for one non-numeric word in the middle.

    mc/mtl_p8_zm_man_stainglass_tearoom_frame_dirt
    mc/mtl_p8_zm_man_stainglass_tearoom_frame_<?>

## How it generates

For every known name, and every token slot in it, the slot's *local context* is the token before
and the token after. Every name in the corpus votes on what may appear in a given context, so

    (`man_`, `tearoom_`) -> {stainglass, ceiling, window, floor, ...}

and each of those words is then offered to every other name that has the same two neighbours.
The alphabet is measured from real names and applied only where those names say it belongs, so
this stays inside the seeding principle: it recombines material known to be real, and it never
invents a word.

Numbers are folded to `#` when forming a context, so `_01_` and `_07_` are the same neighbour and
a family's vocabulary is shared across all of its members rather than split between them.

## What it reads and writes

Reads the community tables, this machine's confirmed findings and the merged submissions, all
via `snapshot.py`. Writes candidate names to standard output, one per line; progress and sizing
go to standard error.

## Options

    --cap N          most substitutes offered per slot (default 12, by frequency)
    --min-seen N     ignore a context seen fewer than this many times (default 4)
    --min-alt N      ignore a substitute seen fewer than this many times (default 2)
    --max-tokens N   skip names longer than this many tokens (default 16)
    --digits         also substitute purely numeric tokens (default off; method 4 owns those)
    --count          print how many candidates this would produce, and stop

## Reusable or one-off

Reusable. It re-measures from the corpus every time it runs, so it strengthens after any
productive pass -- the same property that makes `derive_lists.py` worth re-running.

## What it measured

Recorded in the run note by `confirm_list`; see METHODS.md for the current figures.
"""
import collections
import os
import sys

import snapshot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The tables that are Black Ops 4 and Cold War. The `_v2` files are MW2022/BO6 and teach the
# wrong conventions -- see docs/HASHES.md for which file is which game.
THIS_ERA = [
    "fnv1a_xmodels",
    "fnv1a_xmaterials",
    "fnv1a_ximages",
    "fnv1a_xanims",
    "fnv1a_xsounds",
    "fnv1a_soundbanks_aliases",
    "fnv1a_strings",
] + ["fnv1a_%s_xsounds" % language for language in (
    "english french german italian spanish americanspanish brazilianportugese "
    "russian polish japanese korean chinese"
).split()]

BOUNDARY = "_/"


def split(name):
    """A name as (text, mark) pairs, so that `"".join(t + m)` rebuilds it exactly.

    Both `_` and `/` separate, because a directory is as much a segment boundary as an
    underscore -- and the engine hashes the slash, so it cannot simply be dropped.
    """
    tokens, current = [], ""
    for character in name:
        if character in BOUNDARY:
            tokens.append((current, character))
            current = ""
        else:
            current += character
    tokens.append((current, ""))
    return tokens


def shape(token):
    """A token with its digits folded, so `_01_` and `_07_` count as the same neighbour."""
    out, in_run = [], False
    for character in token:
        if character.isdigit():
            if not in_run:
                out.append("#")
                in_run = True
        else:
            out.append(character)
            in_run = False
    return "".join(out)


def measure(names, max_tokens):
    """{(before, after): Counter of the tokens seen between them}."""
    alphabet = collections.defaultdict(collections.Counter)

    for name in names:
        tokens = split(name)
        if len(tokens) > max_tokens:
            continue
        texts = [text for text, _ in tokens]
        for index, text in enumerate(texts):
            if not text:
                continue
            before = shape(texts[index - 1]) if index else "^"
            after = shape(texts[index + 1]) if index + 1 < len(texts) else "$"
            alphabet[(before, after)][text] += 1

    return alphabet


def main(argv):
    def option(flag, default):
        return int(argv[argv.index(flag) + 1]) if flag in argv else default

    cap = option("--cap", 12)
    min_seen = option("--min-seen", 4)
    min_alt = option("--min-alt", 2)
    max_tokens = option("--max-tokens", 16)
    digits = "--digits" in argv
    counting = "--count" in argv

    print("reading known names", file=sys.stderr)
    names = snapshot.table_names(*THIS_ERA) + snapshot.confirmed_names()
    names = [name.strip().lower().replace("\\", "/") for name in names if name.strip()]
    print("%d known names" % len(names), file=sys.stderr)

    alphabet = measure(names, max_tokens)
    print("%d slot contexts measured" % len(alphabet), file=sys.stderr)

    # Trim each context to the substitutes worth offering. A context seen a handful of times
    # says nothing, and a substitute seen once is usually a typo or a one-off in somebody's
    # scraped list.
    offers = {}
    for context, counter in alphabet.items():
        if sum(counter.values()) < min_seen:
            continue
        chosen = [text for text, count in counter.most_common(cap) if count >= min_alt]
        if len(chosen) > 1:
            offers[context] = chosen
    print("%d contexts kept" % len(offers), file=sys.stderr)

    produced = 0
    out = sys.stdout
    batch = []

    for name in names:
        tokens = split(name)
        if len(tokens) > max_tokens:
            continue
        texts = [text for text, _ in tokens]
        marks = [mark for _, mark in tokens]

        for index, text in enumerate(texts):
            if not text:
                continue
            # Numbers in place is method 4's job, and it walks ranges this cannot.
            if not digits and text.isdigit():
                continue
            before = shape(texts[index - 1]) if index else "^"
            after = shape(texts[index + 1]) if index + 1 < len(texts) else "$"
            chosen = offers.get((before, after))
            if not chosen:
                continue

            head = "".join(t + m for t, m in zip(texts[:index], marks[:index]))
            tail = "".join(t + m for t, m in zip(texts[index + 1:], marks[index + 1:]))
            mark = marks[index]

            for substitute in chosen:
                if substitute == text:
                    continue
                produced += 1
                if not counting:
                    batch.append(head + substitute + mark + tail)

            if len(batch) >= 65536:
                out.write("\n".join(batch) + "\n")
                batch = []

    if batch and not counting:
        out.write("\n".join(batch) + "\n")

    print("%d candidates" % produced, file=sys.stderr)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1:])
