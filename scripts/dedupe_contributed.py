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
import hashlib
import os
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


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remove", action="store_true", help="delete the redundant copies")
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

    if not redundant:
        print("%d file(s), all distinct." % sum(len(v) for v in found.values()))
        return 0

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

    if not options.remove:
        print("\nNothing was removed. Pass --remove to do it.")
        return 0

    for name in redundant:
        os.remove(os.path.join(FOLDER, name))

    print("\n%d file(s) removed." % len(redundant))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
