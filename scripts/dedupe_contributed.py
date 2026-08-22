"""Removes byte-identical copies from `scripts/contributed/`, keeping the earliest of each.

    python scripts/dedupe_contributed.py           report what is redundant, remove nothing
    python scripts/dedupe_contributed.py --remove  actually remove it

Run by `.github/workflows/derived.yml` whenever a submission lands.

## Why this has to exist on the maintainer's side as well

`submit` decides whether it has already sent a script by looking for it in the library **on
disk** -- and a script only reaches disk once the pull request carrying it has merged *and* been
pulled back down, which is hours later. Somebody submitting four times in eight minutes therefore
stamps four copies of the same generator, under four timestamps, and every one of them lands.

That is fixed at the source: `submit` now keeps a local ledger of what it has already carried, by
content. But the fix only helps a client that *has* it, and clients update when their owner runs
`start`. In the hours between, the library keeps gaining copies -- measured on 2026-08-22, one
contributor's evening added 40 redundant files across eight groups, five and ten copies deep,
while their client was a few commits behind.

So the library is also swept from this side. Between them the two hold: the ledger stops it at
source for updated clients, and this cleans up after the rest without anybody having to notice.

## What it will not do

Compares **content**, never names. A stamp differs on every submission, so names cannot tell an
updated generator from a duplicate of an unchanged one -- and those two need opposite treatment.
Line endings are ignored, because git checks a file out with CRLF while a freshly written one has
LF, and a byte comparison would call the identical script two different scripts.

The **earliest** copy of each is kept, so the name other submissions and `METHODS.md` already
refer to keeps working. Anything with content nothing else shares is left alone, which includes
every genuinely edited version of an evolving generator.
"""
import argparse
import collections
import glob
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

FOLDER = os.path.join(snapshot.ROOT, "scripts", "contributed")


def groups():
    """{content digest: [path]} for everything in the contributed library."""
    found = collections.defaultdict(list)

    for name in sorted(os.listdir(FOLDER)) if os.path.isdir(FOLDER) else []:
        path = os.path.join(FOLDER, name)
        if not os.path.isfile(path) or name.startswith("."):
            continue

        with open(path, "rb") as handle:
            # Line endings out, for the same reason `same_text` in submit.rs takes them out.
            body = handle.read().replace(b"\r", b"")

        found[hashlib.sha1(body).hexdigest()].append(name)

    return found


def referenced():
    """Stamped filenames the documentation pins by name, which must never be removed.

    `check_docs.py` fails on a path the markdown mentions and the repository does not have, so
    removing one would break the build -- but relying on that means finding out afterwards. Two
    are pinned today: METHODS.md names `slotswap_20260819-225818.py` and
    `templates_20260819-220821.py` as the way to run methods 10 and 11.
    """
    pinned = set()
    roots = (
        glob.glob(os.path.join(snapshot.ROOT, "*.md"))
        + glob.glob(os.path.join(snapshot.ROOT, "docs", "*.md"))
        + glob.glob(os.path.join(snapshot.ROOT, "scripts", "*.py"))
    )
    for path in roots:
        with open(path, encoding="utf-8", errors="replace") as handle:
            pinned.update(re.findall(r"scripts/contributed/([A-Za-z0-9_.-]+)", handle.read()))
    return pinned


def base_of(name):
    """`aliasswap_20260821-085126.py` -> `aliasswap.py`, so versions of one script group."""
    return re.sub(r"_\d{8}-\d{6}(?=\.)", "", name)


def superseded(pinned):
    """Copies worth removing that are not byte-identical to anything.

    Two kinds, both of which leave somebody holding several files and no way to tell which to run:

      - **Promoted.** A generator that earns its place moves into `scripts/` proper. The copy left
        behind in `contributed/` is then the same method twice.
      - **Outgrown.** Several stamped versions of one generator. Git holds every version; the
        library only needs the one somebody should actually run, which is the newest.

    Anything the documentation pins by name is kept regardless -- see `referenced`.
    """
    promoted = {
        name
        for name in os.listdir(os.path.join(snapshot.ROOT, "scripts"))
        if os.path.isfile(os.path.join(snapshot.ROOT, "scripts", name))
    }

    versions = collections.defaultdict(list)
    if os.path.isdir(FOLDER):
        for name in sorted(os.listdir(FOLDER)):
            if os.path.isfile(os.path.join(FOLDER, name)) and not name.startswith("."):
                versions[base_of(name)].append(name)

    stale = []
    for base, names in versions.items():
        names = sorted(names)
        if base in promoted:
            stale += [n for n in names if n not in pinned]
            continue
        # Newest last, so everything before it is an outgrown version.
        stale += [n for n in names[:-1] if n not in pinned]

    return stale


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remove", action="store_true", help="delete the redundant copies")
    parser.add_argument(
        "--versions",
        action="store_true",
        help="also drop outgrown versions and copies of scripts since promoted",
    )
    options = parser.parse_args(argv)

    found = groups()
    if not found:
        print("nothing in scripts/contributed/.")
        return 0

    redundant = []
    for names in found.values():
        # Sorted, so the earliest stamp is the one kept and the name anything already refers to
        # keeps working.
        redundant += sorted(names)[1:]

    print(
        "%d file(s) in the library are %d distinct scripts; %d are byte-identical copies.\n"
        % (sum(len(v) for v in found.values()), len(found), len(redundant))
    )
    for names in sorted(found.values(), key=len, reverse=True):
        if len(names) > 1:
            kept = sorted(names)[0]
            print("  keeping %s" % kept)
            for name in sorted(names)[1:]:
                print("     removing %s" % name)

    if options.versions:
        pinned = referenced()
        outgrown = [name for name in superseded(pinned) if name not in redundant]
        if outgrown:
            print("\nOutgrown -- a newer version or a promoted copy exists:")
            for name in outgrown:
                print("     removing %s" % name)
            redundant += outgrown
        if pinned:
            print("\nKept, because the documentation names them:")
            for name in sorted(pinned):
                print("     %s" % name)

    if not redundant:
        print("nothing redundant.")
        return 0

    if not options.remove:
        print("\nNothing was removed. Pass --remove to do it.")
        return 0

    for name in redundant:
        os.remove(os.path.join(FOLDER, name))

    print("\n%d file(s) removed." % len(redundant))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
