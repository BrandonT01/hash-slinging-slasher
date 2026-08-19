"""One asset type's names, spelled the way another asset type spells them.

A method, and a measurement of whether the method is worth running. Pipe it into `confirm_list`.

    python scripts/cross_type.py --measure                  what the relationships actually are
    python scripts/cross_type.py --from xmodel --to material | confirm_list - --label "model->material"

## The idea

A weapon that has a model has a material, an image and usually an animation, and the four names
are the same idea under four spelling conventions. `images_from_materials` already exploits one
edge of that -- strip `mtl_`, add `i_` -- and it was hand-written for one pair out of twelve.

This measures every pair instead of assuming any of them. It reduces each known name to a **core**
by stripping the decorations its own type wears, counts which cores are shared across types, and
reports how strong each relationship is. Then it takes cores that exist in one type and are
missing in another, and spells them the way the target type spells things.

The measurement matters more than the generator. A pair with a strong shared core is a seam worth
mining for a night; a pair with a weak one is a night thrown away, and until now nobody could
tell which was which without spending the night.

## Options

    --measure            report the relationships and stop. Run this first.
    --from TYPE          xmodel | material | image | xanim
    --to TYPE            the same set
    --top N              how many of the target type's decorations to apply (default 12)
    --count              count candidates instead of writing them

Reads the tables, the merged submissions and this machine's findings.
"""
import collections
import sys

import snapshot

TABLES = {
    "xmodel": "fnv1a_xmodels",
    "material": "fnv1a_xmaterials",
    "image": "fnv1a_ximages",
    "xanim": "fnv1a_xanims",
}

# A leading directory is part of what the engine hashes, so it is a decoration rather than noise
# -- stripped to find the core, and put back to spell a name in the target type.
MAX_DIRECTORY = 6


def decompose(name):
    """(directory, leading token, core, trailing token) for one name.

    Deliberately shallow: one leading segment and one trailing segment. Deeper splits find more
    structure and also find it where there is none, and the point here is a measurement that can
    be trusted rather than the largest possible number.
    """
    name = name.strip().lower().replace("\\", "/")

    directory = ""
    head, sep, rest = name.partition("/")
    if sep and len(head) <= MAX_DIRECTORY and "_" not in head:
        directory, name = head + "/", rest

    parts = name.split("_")
    leading = parts[0] + "_" if len(parts) > 2 else ""
    trailing = "_" + parts[-1] if len(parts) > 2 else ""

    core = name
    if leading:
        core = core[len(leading):]
    if trailing:
        core = core[: -len(trailing)]

    return directory, leading, core, trailing


def load(kind):
    """Every known name of one type: published, submitted by anybody, and confirmed here."""
    names = set(snapshot.table_names(TABLES[kind]))
    names.update(snapshot.confirmed_names(kind))

    return {name.strip().lower().replace("\\", "/") for name in names if name.strip()}


def profile(names):
    """The decorations a type wears, and its cores."""
    directories = collections.Counter()
    leadings = collections.Counter()
    trailings = collections.Counter()
    cores = set()

    for name in names:
        directory, leading, core, trailing = decompose(name)
        if len(core) < 3:
            continue
        directories[directory] += 1
        leadings[leading] += 1
        trailings[trailing] += 1
        cores.add(core)

    return directories, leadings, trailings, cores


def main(argv):
    kinds = list(TABLES)
    print("reading the tables", file=sys.stderr)

    loaded = {kind: load(kind) for kind in kinds}
    profiles = {kind: profile(loaded[kind]) for kind in kinds}

    for kind in kinds:
        print("%-9s %8d names, %8d cores" % (kind, len(loaded[kind]), len(profiles[kind][3])),
              file=sys.stderr)

    if "--measure" in argv or ("--from" not in argv and "--to" not in argv):
        print("\nshared cores between types -- the higher the share, the better the seam\n")
        print("%-10s %-10s %10s %8s" % ("from", "to", "shared", "of from"))

        for source in kinds:
            for target in kinds:
                if source == target:
                    continue
                shared = profiles[source][3] & profiles[target][3]
                share = 100.0 * len(shared) / max(len(profiles[source][3]), 1)
                print("%-10s %-10s %10d %7.1f%%" % (source, target, len(shared), share))

        print("\nthe decorations each type wears (top 8)\n")
        for kind in kinds:
            directories, leadings, trailings, _ = profiles[kind]
            print("%s" % kind)
            print("  directories: %s" % ", ".join(
                "%s(%d)" % (d or "-", n) for d, n in directories.most_common(8)))
            print("  leading:     %s" % ", ".join(
                "%s(%d)" % (l or "-", n) for l, n in leadings.most_common(8)))
            print("  trailing:    %s" % ", ".join(
                "%s(%d)" % (t or "-", n) for t, n in trailings.most_common(8)))
        return

    source = argv[argv.index("--from") + 1]
    target = argv[argv.index("--to") + 1]
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 12
    counting = "--count" in argv

    if source not in TABLES or target not in TABLES:
        raise SystemExit("types are: %s" % ", ".join(TABLES))

    directories, leadings, trailings, target_cores = profiles[target]
    source_cores = profiles[source][3]

    # The interesting cores are the ones this type has and that one does not: a core both types
    # already carry is a name somebody has already published.
    missing = source_cores - target_cores
    print(
        "%d cores in %s that %s does not have" % (len(missing), source, target),
        file=sys.stderr,
    )

    picks = lambda counter: [value for value, _ in counter.most_common(top)]
    produced = 0

    for core in missing:
        for directory in picks(directories):
            for leading in picks(leadings):
                for trailing in picks(trailings):
                    produced += 1
                    if not counting:
                        sys.stdout.write(directory + leading + core + trailing + "\n")

    print("%d candidates" % produced, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
