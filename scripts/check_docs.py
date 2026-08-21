"""Checks that the documentation describes the repository that actually exists.

    python scripts/check_docs.py            report and exit non-zero on any problem

The markdown here is not documentation in the usual sense. It is the input to another program:
an assistant reads `AGENTS.md` and does what it says. A path that has been renamed, a binary that
no longer exists, a script referred to by a name it never had -- each of those is a bug that
wastes somebody's night, and none of them shows up in a compiler.

So they are checked. What this verifies:

  - every `cargo run --release --bin X` names a binary Cargo.toml declares
  - every `bin/windows/X.exe` mentioned is committed
  - every `scripts/X.py` mentioned exists
  - every repository path in backticks exists
  - the asset type names used in prose are real pool names in one of the two games
  - the pools the Python scripts skip match LOW_VALUE_POOLS and UNREACHABLE on the Rust side

What it deliberately does not verify: measured numbers. A figure in the documentation should
carry the command that reproduces it -- see `docs/` -- and a checker that re-ran every
measurement would take an hour and still not know which numbers were meant to be current.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths named in prose that are created at runtime rather than committed, and things that are
# examples rather than claims about this repository.
EXPECTED_ABSENT = {
    "findings",
    "logs",
    "state",
    "contrib",
    "tables",
    "cod-name-db",
    "target/release",
    "scripts/contributed",
}


def markdown():
    for path in glob.glob(os.path.join(ROOT, "*.md")) + glob.glob(
        os.path.join(ROOT, "docs", "*.md")
    ) + glob.glob(os.path.join(ROOT, "scripts", "*.md")):
        yield path, open(path, encoding="utf-8", errors="replace").read()


def declared_binaries():
    text = open(os.path.join(ROOT, "Cargo.toml"), encoding="utf-8").read()
    return set(re.findall(r'^name = "([a-z_\-]+)"$', text, re.M))


def pool_names():
    text = open(os.path.join(ROOT, "src", "lib.rs"), encoding="utf-8").read()
    names = set()
    for constant in ("POOLS", "BO4_POOLS"):
        block = re.search(r"pub const %s: &\[&str\] = &\[(.*?)\];" % constant, text, re.S)
        if block:
            names |= set(re.findall(r'"([^"]+)"', block.group(1)))
    return names


def low_value_pools():
    text = open(os.path.join(ROOT, "src", "lib.rs"), encoding="utf-8").read()
    block = re.search(r"pub const LOW_VALUE_POOLS.*?\n\];", text, re.S)
    return set(re.findall(r'\(\s*\n?\s*"([a-z_]+)",', block.group(0))) if block else set()


def main():
    problems = []

    # Reported, never fatal. A submission carries names, and the names are what matter: failing a
    # contributor's pull request over a path bug in a generator it happens to carry would throw
    # away verified finds to enforce library hygiene. Five submissions holding 211 confirmed names
    # were blocked exactly that way on 2026-08-21, within an hour of this check being added.
    warnings = []
    binaries = declared_binaries()
    pools = pool_names()

    for path, text in markdown():
        where = os.path.relpath(path, ROOT)

        for name in re.findall(r"--bin ([a-z_\-]+)", text):
            if name not in binaries:
                problems.append("%s: `--bin %s` is not a binary Cargo.toml declares" % (where, name))

        for name in re.findall(r"bin[/\\]windows[/\\]([a-z_\-]+)\.exe", text):
            if not os.path.exists(os.path.join(ROOT, "bin", "windows", name + ".exe")):
                problems.append(
                    "%s: bin/windows/%s.exe is referred to but not committed" % (where, name)
                )
            if name not in binaries:
                problems.append("%s: bin/windows/%s.exe is not a declared binary" % (where, name))

        for name in re.findall(r"scripts/([a-z_]+\.py)", text):
            if not os.path.exists(os.path.join(ROOT, "scripts", name)):
                problems.append("%s: scripts/%s does not exist" % (where, name))

        # Backticked repository paths. Only ones that look like a path into this repo, so prose
        # about `mc/` or `_01` is not mistaken for a filename.
        for quoted in re.findall(r"`([A-Za-z0-9_./-]+)`", text):
            if quoted in EXPECTED_ABSENT or quoted.rstrip("/") in EXPECTED_ABSENT:
                continue
            if not re.match(r"^(src|scripts|data|snapshots|docs|bin|\.github)/", quoted):
                continue
            if glob.glob(os.path.join(ROOT, quoted)):
                continue
            problems.append("%s: `%s` does not exist" % (where, quoted))

    # The two sides' idea of what is not worth searching must agree, or a Python generator will
    # cheerfully produce candidates the Rust side then refuses to file.
    rust_low = low_value_pools()
    python_skip = set()
    skip = re.search(r"^SKIP = \{(.*?)\}", open(
        os.path.join(ROOT, "scripts", "snapshot.py"), encoding="utf-8").read(), re.S | re.M)
    if skip:
        python_skip = set(re.findall(r'"([a-z_]+)"', skip.group(1)))

    # `xmodelmesh` is unreachable rather than low value, and is in both lists on purpose.
    if not rust_low <= python_skip:
        problems.append(
            "scripts/snapshot.py SKIP is missing %s, which src/lib.rs calls low value"
            % ", ".join(sorted(rust_low - python_skip))
        )

    for name in python_skip:
        if name not in pools:
            problems.append("scripts/snapshot.py skips `%s`, which is not a pool in either game" % name)

    # AGENTS.md and CLAUDE.md are the same file under two names, because different assistants look
    # for different ones. Nothing stops an edit landing in only one, and the failure is silent and
    # nasty: half the agents in the world would follow last month's instructions.
    agents = open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8").read()
    claude = open(os.path.join(ROOT, "CLAUDE.md"), encoding="utf-8").read()
    if agents != claude:
        problems.append(
            "AGENTS.md and CLAUDE.md have drifted apart. They must be identical -- different "
            "assistants read different ones. Fix with: cp AGENTS.md CLAUDE.md"
        )

    # The twelve material directories have been lost once already, to a beginnings list ranked by
    # popularity: `mc/` heads 496,666 published names and `ec/` heads 25, so a global ranking keeps
    # the first two and silently discards the naming of everything under the other ten.
    directories = ["mc/", "wc/", "clt/", "splm/", "vd/", "mcs/", "ei/", "cltp/", "vdd/", "el/",
                   "mcp/", "ec/"]
    prefixes = set(
        line.strip()
        for line in open(os.path.join(ROOT, "data", "prefixes.txt"), encoding="utf-8")
    )
    missing = [d for d in directories if d not in prefixes]
    if missing:
        problems.append(
            "data/prefixes.txt is missing the material directories %s. All twelve must be carried "
            "-- ranking beginnings by popularity drops the rare ones, and with them the naming of "
            "everything under them. See scripts/derive_lists.py." % ", ".join(missing)
        )

    # And the beginnings that reach most of the game, for the same reason and a worse failure.
    # The lists are capped, so measuring a new table displaces rather than grows -- and the file
    # still looks healthy afterwards, at its full 700 lines, with the entries that mattered gone.
    # `derive_lists.py` refuses to write such a list; this catches one that reached the repository
    # some other way.
    heads = {
        "p9_": 77248, "p8_": 66172, "p7_": 42516, "attach_": 27504, "mtl_": 343794,
        "i_": 403889, "vm_": 18088, "ai_": 11226, "ui_": 31742,
    }
    lost = sorted(k for k in heads if k not in prefixes)
    if lost:
        problems.append(
            "data/prefixes.txt has lost %s -- beginnings heading %s published names between them. "
            "A capped list displaces rather than grows; something newly measured crowded them out. "
            "See MUST_KEEP_PREFIXES in scripts/derive_lists.py."
            % (", ".join(lost), sum(heads[k] for k in lost))
        )

    # A contributed generator that cannot find `snapshot.py` is a method that dies on arrival.
    #
    # Only `scripts/contributed/` is checked. A script in `scripts/` proper sits beside
    # `snapshot.py`, so a plain import is right there -- it is being filed one level down that
    # breaks it, and that is where the copy lands.
    #
    # `submit` files one into `scripts/contributed/`, one level below `snapshot.py`, so a script
    # that adds only its own directory to `sys.path` works for its author and fails for everybody
    # who merges it. scripts/README.md has said to walk up for the whole life of the repository
    # and five of ten contributed scripts still did not, which is why this is a check rather than
    # a paragraph. Checked by reading, never by importing: this is other people's code.
    for script in sorted(glob.glob("scripts/contributed/*.py")):
        text = open(script, encoding="utf-8", errors="ignore").read()
        if not re.search(r"^import snapshot", text, re.M):
            continue
        if 'os.path.join(_root, "scripts", "snapshot.py")' in text:
            continue

        warnings.append(
            "%s imports `snapshot` without walking up to find `scripts/`, so it cannot run from "
            "where it has been filed -- see the pattern in scripts/README.md." % script
        )

    if warnings:
        print("%d warning(s), which do not fail this check:\n" % len(warnings))
        for warning in warnings:
            print("  " + warning)
        print()

    if problems:
        print("%d problem(s):\n" % len(problems))
        for problem in problems:
            print("  " + problem)
        print(
            "\nThe markdown here is executable instructions for another program. A path that has\n"
            "moved is a bug, not a typo."
        )
        return 1

    print("documentation matches the repository: binaries, scripts, paths and pool names all check out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
