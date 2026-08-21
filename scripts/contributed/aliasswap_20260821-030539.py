"""Sound alias names, one token at a time, from the alias vocabulary rather than the path one.

A method, not a report. Pipe it into `confirm_list` -- folded, like everything that is not a
Black Ops 4 sound *file*:

    python scripts/aliasswap.py | ./bin/windows/confirm_list.exe - \
        --label "alias slot substitution" --script scripts/aliasswap.py

## The problem it solves

`sound_alias` is the second largest unnamed ground in the project -- 43,603 unnamed of 50,890 in
Cold War, 23,370 of 50,043 in Black Ops 4 -- and until 2026-08-20 nothing on this machine hunted
it at all, because `config.toml` listed five pools and this was not one of them.

Turning it on is not enough. The sound pass hunts aliases with the vocabulary measured from the
sound *file* tables, and the two are not the same language:

    zmb\ai\blightfather\maggot\flying\maggot_fly_loop_02.ln100.pc.snd   a sound file
    amb_computer_loop_1                                                     an alias

Files are deep paths with dotted tails. Aliases are short underscore-joined names -- half of them
six tokens or fewer, from only 23 distinct leading tokens -- with no slash and no tail anywhere in
them. A beginning or ending measured on one is close to useless against the other. Run against
Cold War with the file vocabulary, the whole sound pass returned **3** aliases.

## Why both games seed one corpus

An alias carries no slash, so there is no fold to get wrong and the id is the plain hash of the
name in either title. That makes the two games' alias corpora a single pool of seed material --
53,956 known names against 39,707 still unnamed -- and it is the reason this is worth running even
though `soundxfer.py` found the *file* route between the games closed.

## How it generates

For every known alias and every token in it, the token's context is its left and right neighbour,
with `^` and `$` at the ends so first and last tokens have one too. Every alias votes on what may
stand in a given context:

    (`amb`, `loop`) -> {computer, fire, water, machine, ...}

and each is offered to every other alias sharing that context. Nothing is invented: every token
written into a slot was measured in that slot, in a name known to be real.

## What it is spent by

Measured 2026-08-20 against 39,707 unnamed ids: slot substitution reaches **318** from 1,844,165
candidates. Two neighbours were tried and are not worth carrying -- *continuations*, offering each
prefix the tokens measured to follow it, reached **3** from 3,311,242, and *truncations*, cutting
a known alias short, reached **0** from 197,726. Aliases are evidently authored as whole names
rather than grown or abbreviated, so the productive move is to vary a word, not the length.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import snapshot

# The alias tables. `fnv1a_strings` is not a sound table but carries about as many alias names as
# the alias table does, and dropping it would throw away half the vocabulary.
TABLES = ("fnv1a_soundbanks_aliases", "fnv1a_strings")


def option(argv, flag, default):
    return int(argv[argv.index(flag) + 1]) if flag in argv else default


def word(argv, flag, default):
    return argv[argv.index(flag) + 1] if flag in argv else default


def context_of(tokens, i, which):
    """The neighbours that define a slot. `^` and `$` so the ends have a context too.

    Keying on one neighbour is looser -- the alphabets are larger and the candidates less certain
    -- but it is the only way to reach a name whose *other* neighbour is itself unknown, which is
    most of a family nobody has named yet.
    """
    left = tokens[i - 1] if i else "^"
    right = tokens[i + 1] if i + 1 < len(tokens) else "$"
    if which == "left":
        return (left, "*")
    if which == "right":
        return ("*", right)
    return (left, right)


def alias_ids():
    """Every `sound_alias` id in either game. An alias has no slash, so one hash serves both."""
    out = set()
    for name in ("blkops04", "blkopscw"):
        path = os.path.join(snapshot.ROOT, "snapshots", name + ".ids")
        if not os.path.exists(path):
            continue
        snap = snapshot.read(path)
        if "sound_alias" not in snap.pools:
            continue
        index = snap.pools.index("sound_alias")
        out |= {asset for asset, pool in snap.records if pool == index}
    return out


def known_aliases(ids):
    """Names from the tables and from everything confirmed that land on an alias id."""
    out = set()
    for name in list(snapshot.table_names(*TABLES)) + list(snapshot.confirmed_names("sound_alias")):
        name = name.strip().lower()
        if name and (snapshot.fnv1a(name) & snapshot.ID_MASK) in ids:
            out.add(name)
    return out


def main(argv):
    cap = option(argv, "--cap", 24)
    min_seen = option(argv, "--min-seen", 1)
    which = word(argv, "--context", "both")

    known = known_aliases(alias_ids())
    if not known:
        raise SystemExit("no known aliases found; are the tables fetched?")

    contexts = collections.defaultdict(collections.Counter)
    for name in known:
        tokens = name.split("_")
        for i, token in enumerate(tokens):
            contexts[context_of(tokens, i, which)][token] += 1

    if "--count" in argv:
        total = sum(
            min(cap, len(contexts[context_of(t, i, which)]))
            for t in (n.split("_") for n in known)
            for i in range(len(t))
        )
        print("%d known aliases, %d contexts, about %d candidates" % (len(known), len(contexts), total))
        return

    out = sys.stdout
    for name in known:
        tokens = name.split("_")
        for i, token in enumerate(tokens):
            for alt, seen in contexts[context_of(tokens, i, which)].most_common(cap):
                if alt == token or seen < min_seen:
                    continue
                out.write("_".join(tokens[:i] + [alt] + tokens[i + 1:]) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
