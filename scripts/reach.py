"""How much of the game the current lists can actually express, measured on names we already know.

    python scripts/reach.py            every pool, both list pairs
    python scripts/reach.py --missing  and the commonest beginnings/endings we do not carry

The general search builds a candidate as `beginning + stem + ending`, drawing the two ends from
`data/prefixes.txt` and `data/suffixes.txt`. Whatever those lists cannot express, no pass can find,
however long it runs -- and nothing in a run says so. A pass that reaches a tenth of the game looks
exactly like a pass that reaches all of it, only with fewer results, which is indistinguishable
from the game simply being nearly finished.

Two beginning columns, and the second is the one that notices damage. `reached` asks whether
*any* cut of a name is carried, which is the honest ceiling -- a candidate is `beginning + stem +
ending` and a long stem reaches a deep name from a short beginning. But `mc/` is a must-keep, so
every `mc/...` name stays "reached" after `mc/p9_`, `mc/ui_`, `mc/veh_` and fourteen more have
been evicted from the file. Both re-measures of the collapse were validated on that column and it
could not have shown the regression. `named` asks the stricter question -- whether the beginning
the measurement would have written for this name is actually carried -- and it falls the moment a
capped list starts displacing vocabulary.

So this measures the ceiling rather than the yield. It takes names cod-name-db already publishes,
which are real names of the kind we are hunting, and asks what share of them the lists could
reconstruct. The unnamed ones are the same shape as the named ones, so the share is a fair estimate
of the best a pass could possibly do.

**It is a floor to clear, not a score to maximise**, and the difference is the whole point of this
repository. Every name measured here is one cod-name-db already holds, so reconstructing it is by
definition not a find. A *low* share means a pass is losing names it should already be reaching,
and is worth acting on immediately. A *high* share means only that the lists are not the thing
standing in the way -- it does not predict that a pass will return anything, and it is blind to
any naming family with no published example at all, since such a family is absent from the very
corpus being measured.

So tuning lists until this number is high is not the work, and an assistant that spends its night
doing so has measured itself busy. The work is inventing a method that reaches ground the corpus
does not describe. `METHODS.md` methods 10 and 11 were both invented, written and submitted by a
contributor rather than shipped here, which is the intended shape of a contribution.

Reads the tables and `data/`. Needs no game, no network and no snapshot.
"""
import collections
import os
import re
import sys

import snapshot

# A mesh name: 26 base32 characters that are a hash of the mesh itself, so the tail cannot be
# predicted by anything and never will be. `AGENTS.md` lists `xmodelmesh` as unreachable for
# exactly this reason -- but 81,381 of `fnv1a_xmodels`' 286,501 names carry the same tail, because
# the published table holds mesh entries alongside model names.
#
# Counting them dragged the measured xmodel ending reach down to 64.3% when the reach over real
# model names is 89.9%. That is not a rounding difference, it is the difference between a ceiling
# worth a night of work and one that is not there at all -- and chasing a phantom ceiling is the
# precise failure this script exists to prevent, so it had better not cause one.
UNREACHABLE = re.compile(r"_[a-z0-9]{26}$")

# Which lists serve which tables, mirroring how the searches choose. A sound pass reads the sound
# pair, everything else reads the general pair -- see `paths::SOUND_SUFFIX_LIST`.
GROUPS = [
    (
        "general",
        "prefixes.txt",
        "suffixes.txt",
        ["fnv1a_xmodels", "fnv1a_xmaterials", "fnv1a_ximages", "fnv1a_xanims"],
    ),
    (
        "sound",
        "sound.prefixes.txt",
        "sound.suffixes.txt",
        ["fnv1a_soundbanks_aliases", "fnv1a_english_xsounds", "fnv1a_xsounds"],
    ),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    path = os.path.join(ROOT, "data", name)
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def endings_of(name):
    """The one, two and three trailing segments a name carries, as the measurement cuts them."""
    base = name.rpartition("/")[2]
    parts = base.split("_")
    out = []

    if len(parts) >= 2:
        out.append("_" + parts[-1])
        out.append("_" + "_".join(parts[-2:]))
    if len(parts) >= 4:
        out.append("_" + "_".join(parts[-3:]))

    return out


def canonical_beginnings_of(name):
    """The beginnings `derive_lists.measure` would write for this name, carrying a token.

    The strict half of the pair. A name whose own measured beginning is not carried is one the
    lists no longer describe, however reachable it remains through a shorter beginning and a
    longer stem.

    **The bare directory is deliberately not one of them**, though the measurement does count it.
    `mc/` is a must-keep and can never be evicted, so including it scored every `mc/...` name as
    named however many of `mc/p9_`, `mc/ui_` and `mc/veh_` had gone -- and this column measured
    byte-identical to `reached` across all four general tables, which is exactly the blindness it
    was added to cure.
    """
    head, separator, base = name.rpartition("/")
    directory = head + separator
    parts = base.split("_")

    if len(parts) < 2:
        return []

    return [directory + parts[0] + "_", directory + "_".join(parts[:2]) + "_"]


def beginnings_of(name):
    """Every beginning the search could actually build this name with.

    Not just the three cuts the measurement counts. A candidate is `beginning + stem + ending`
    and the stem is any piece cut at a mark, so a deep path can be reached by a *short* beginning
    with a long stem just as well as by its whole directory. Counting only the canonical cuts
    said Black Ops 4's sound table was 15.5% reachable when much of the rest is reachable another
    way -- which would have sent someone off to fix a ceiling that was not there.
    """
    out = []
    for index, character in enumerate(name):
        if character in "_/":
            out.append(name[: index + 1])

    return out


def main(argv):
    show_missing = "--missing" in argv

    for title, prefix_file, suffix_file, tables in GROUPS:
        prefixes = set(load(prefix_file))
        endings = set(load(suffix_file))

        print("\n=== %s lists: %d beginnings, %d endings ===" % (title, len(prefixes), len(endings)))
        print("%-28s %9s %9s %9s %9s %9s"
              % ("table", "names", "reached", "named", "ending", "skipped"))

        want_begin = collections.Counter()
        want_named = collections.Counter()
        want_end = collections.Counter()
        totals = [0, 0, 0, 0]

        for table in tables:
            names = snapshot.table_names(table)
            if not names:
                continue

            have_begin = have_named = have_end = 0
            counted = skipped = 0
            for name in names:
                name = name.strip().lower().replace("\\", "/")
                if not name:
                    continue

                # Never counted against the lists: no list can ever express it, so including it
                # would report a ceiling that no amount of work could raise.
                if UNREACHABLE.search(name):
                    skipped += 1
                    continue

                counted += 1
                bs = beginnings_of(name)
                es = endings_of(name)

                if any(b in prefixes for b in bs):
                    have_begin += 1
                elif bs:
                    want_begin[bs[-1]] += 1

                cs = canonical_beginnings_of(name)
                if any(c in prefixes for c in cs):
                    have_named += 1
                elif cs:
                    want_named[cs[0]] += 1

                if any(e in endings for e in es):
                    have_end += 1
                elif es:
                    want_end[es[0]] += 1

            total = max(counted, 1)
            print("%-28s %9d %8.1f%% %8.1f%% %8.1f%% %9d"
                  % (table.replace("fnv1a_", ""), counted,
                     100.0 * have_begin / total, 100.0 * have_named / total,
                     100.0 * have_end / total, skipped))

            totals[0] += counted
            totals[1] += have_begin
            totals[2] += have_named
            totals[3] += have_end

        if totals[0]:
            print("%-28s %9d %8.1f%% %8.1f%% %8.1f%%"
                  % ("all four" if title == "general" else "all three", totals[0],
                     100.0 * totals[1] / totals[0], 100.0 * totals[2] / totals[0],
                     100.0 * totals[3] / totals[0]))

        if show_missing:
            print("\n  commonest beginnings no cut of which is carried:")
            for key, count in want_begin.most_common(8):
                print("    %-42s %d names" % (key, count))
            print("  commonest names whose own measured beginning is not carried:")
            for key, count in want_named.most_common(8):
                print("    %-42s %d names" % (key, count))
            print("  commonest endings not carried:")
            for key, count in want_end.most_common(8):
                print("    %-42s %d names" % (key, count))

    print("\n`reached` is the ceiling: some cut of the name is carried, so a pass could build it.")
    print("`named` is the stricter one: the beginning the measurement itself would write for that")
    print("name is in the file. `reached` stays flat while a capped list displaces vocabulary --")
    print("`mc/` is a must-keep, so it covers every `mc/...` name after `mc/p9_` has been evicted.")
    print("A `named` share that has fallen since the last measurement is list damage, and")
    print("`derive_lists.py` now reports what its ceiling cut for the same reason.")

    print("\n`skipped` is names no list can ever express -- a mesh tail is 26 base32 characters")
    print("hashed from the mesh itself. They are left out of the shares rather than counted as")
    print("failures, because a ceiling nothing can raise is not a ceiling worth reporting.")

    print("\nA low share is a ceiling, not a yield: it is the most a pass could find even if it")
    print("ran for ever. Raise it by measuring more (`derive_lists.py`) or by a method that does")
    print("not build names end-first at all -- see METHODS.md.")
    print("\nA high share is not a result. Every name measured here is already published, so")
    print("rebuilding one finds nothing; a high share only says the lists are not what is in")
    print("the way. What finds names is a method that reaches ground this corpus cannot describe.")


if __name__ == "__main__":
    main(sys.argv[1:])
