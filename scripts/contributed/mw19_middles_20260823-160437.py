"""The middle of every Modern Warfare 2019 name, for re-decorating with Cold War's own affixes.

    python contrib/mw19_middles.py --reach      measure what it could reach, run nothing
    python contrib/mw19_middles.py              write the middles list
    python contrib/mw19_middles.py --strip 3    how many segments may come off each end

## The idea, and why the obvious tests missed it

Modern Warfare 2019's names were taken verbatim into the community tables about three years ago,
which is why 66,842 of them are already published and why feeding them to Cold War returns
nothing new. What that pass could not do by hand, over a million names, is the thing that was
actually needed: the same asset is often in both titles under *the same middle with different
decoration* -- a prefix or a suffix or both that one title adds and the other does not.

So the operation is not "does this name exist in Cold War" but "does this name's **middle**,
wearing **Cold War's** prefixes and suffixes, exist in Cold War".

Measured 2026-08-23, everything else about this corpus is spent:

    MW19 names verbatim, Cold War          0 in the five wanted types (2,027 localizeentry)
    MW19 names verbatim, Black Ops 4       0 in the five wanted types (1,049 localize_entry)
    MW19 all-boundary cores x endings      0 in 184 billion candidates

That last one failed for a reason worth keeping: a core is a *prefix* of a name, so it can only
ever put new material on the front. The endings that followed those cores in real Cold War names
turned out to be 3,886 near-unique tails, the commonest appearing three times, including
`otgun_leveraction` -- a cut through the middle of "shotgun". Coincidental character boundaries,
not shared vocabulary. Middles are cut at segment boundaries on *both* ends, which is what makes
them morphemes rather than substrings.

## What --reach measures

Whether a known Cold War name can be built as prefix + MW19 middle + suffix. That is the ceiling:
the method cannot find an unnamed name of a shape it cannot express, and a low ceiling means do
not spend the machine on it. Running this before the sweep is the whole lesson of 2026-08-23.
"""

import argparse
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent
while not (ROOT / "scripts" / "snapshot.py").exists() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "scripts"))

import snapshot

SEPS = "_/\\."


def boundaries(name):
    """Every index a segment may start or end at, including both ends of the name."""
    out = [0]
    for i, ch in enumerate(name):
        if ch in SEPS:
            out.append(i)          # before the separator
            out.append(i + 1)      # after it
    out.append(len(name))
    return sorted(set(out))


def middles_of(name, strip, min_len):
    """Every substring cut at segment boundaries, with at most `strip` segments off each end."""
    marks = boundaries(name)
    # Segment starts are the marks; taking at most `strip` off each end bounds the work.
    heads = marks[: strip * 2 + 1]
    tails = marks[-(strip * 2 + 1):]
    for i in heads:
        for j in tails:
            if j - i >= min_len and not (i == 0 and j == len(name)):
                yield name[i:j]


def load_names(t9_only=False):
    names, dropped = [], 0
    # Through the shared reader, so the gzipped corpus and the raw one both work: the committed
    # artefact is `modwar19.names.txt.gz` (7.3 MB against 54 MB) and a capture straight off the
    # loader is the plain file. Reading the path directly worked only on the machine that
    # captured it.
    for _pool, name in snapshot.name_corpus("modwar19"):
        # Packed-channel entries are several real names joined by `&`, not artefacts. Dropping
        # them cost 211,306 names that appear nowhere else in the corpus, 57,149 of them t9.
        for piece in snapshot.unpack(name):
            if t9_only and "t9" not in piece:
                continue
            names.append(piece.lower())
    return names, dropped


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reach", action="store_true",
                        help="measure the ceiling against known Cold War names and stop")
    parser.add_argument("--strip", type=int, default=2,
                        help="how many segments may be stripped from each end")
    parser.add_argument("--min-len", type=int, default=6)
    parser.add_argument("--t9", action="store_true")
    parser.add_argument("--sample", type=int, default=40000)
    parser.add_argument("--out", default="mw19_middles.txt")
    args = parser.parse_args()

    names, dropped = load_names(args.t9)
    print(f"{len(names)} MW19 names ({dropped} composites dropped)", file=sys.stderr)

    middles = set()
    for name in names:
        middles.update(middles_of(name, args.strip, args.min_len))
    print(f"{len(middles)} distinct middles", file=sys.stderr)

    if not args.reach:
        out = ROOT / "contrib" / args.out
        out.write_text("\n".join(sorted(middles)) + "\n", encoding="utf-8")
        print(f"-> contrib/{args.out}", file=sys.stderr)
        return

    # ---- the ceiling ----
    prefixes = [x.strip() for x in (ROOT / "data" / "prefixes.txt")
                .read_text(encoding="utf-8").splitlines() if x.strip()]
    suffixes = [x.strip() for x in (ROOT / "data" / "suffixes.txt")
                .read_text(encoding="utf-8").splitlines() if x.strip()]
    prefixes.append("")
    suffixes.append("")
    print(f"{len(prefixes)} beginnings, {len(suffixes)} endings", file=sys.stderr)

    known = [n.lower() for n in snapshot.table_names(
        "fnv1a_xmaterials", "fnv1a_xmaterials_v2", "fnv1a_ximages", "fnv1a_ximages_v2",
        "fnv1a_xmodels", "fnv1a_xanims", "fnv1a_xanims_v2")]
    known += [n.lower() for n in snapshot.confirmed_names()]
    known = list({n for n in known if n})
    random.seed(0)
    sample = random.sample(known, min(args.sample, len(known)))
    print(f"testing {len(sample)} known Cold War names\n", file=sys.stderr)

    by_prefix = sorted(set(prefixes), key=len, reverse=True)
    by_suffix = sorted(set(suffixes), key=len, reverse=True)

    buildable = 0
    middle_only = 0
    examples = []
    for name in sample:
        hit = False
        for p in by_prefix:
            if not name.startswith(p):
                continue
            rest = name[len(p):]
            for s in by_suffix:
                if s and not rest.endswith(s):
                    continue
                core = rest[: len(rest) - len(s)] if s else rest
                if core and core in middles:
                    hit = True
                    if len(examples) < 10:
                        examples.append((p, core, s))
                    break
            if hit:
                break
        if hit:
            buildable += 1
        elif any(name[i:j] in middles for i, j in ((0, len(name)),)):
            middle_only += 1

    n = len(sample)
    print(f"known Cold War names this method can express: {buildable} of {n} ({buildable/n:.2%})")
    if examples:
        print("\nhow they decompose (prefix | MW19 middle | suffix):")
        for p, c, s in examples:
            print(f"  {p!r:14} {c[:60]!r:64} {s!r}")
    print("\nCompare: MW19 all-boundary cores x uncarried endings reached 1.00% and returned 0.")


if __name__ == "__main__":
    main()
