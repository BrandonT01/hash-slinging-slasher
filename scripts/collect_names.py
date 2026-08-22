"""The names this project has recovered, as one sorted file per game and asset type.

    python scripts/collect_names.py            rebuild all_names/ from submissions/
    python scripts/collect_names.py --check    say what would change, write nothing

Run by `.github/workflows/registry.yml` -- the `derived files` workflow -- whenever a submission
lands, so `all_names/` in the repository root is always current. Running it by hand is only useful
for checking it.

## What it is for

`submissions/` is the record of *who found what, when, and how* -- one folder per batch, and by
2026-08-22 there were 280 of them. That shape is right for provenance and wrong for every other
purpose. Anybody who wants "the names" -- to seed a generator, to hand a batch upstream, to check
whether something is already known -- has to walk several hundred folders and merge them, and
everybody has written that loop separately. So it is written once, here, and the answer committed.

## Only the five types worth searching

Submissions carry names for 105 asset types, because a general pass files whatever it lands on:
`craftbackground`, `uimodeldatastruct`, `winddef`, one row each. Those are real names and they
stay in `submissions/`, which is the record. They are not what anybody comes here for, and 99
files holding a hundred rows between them would bury the six that matter. See `WANTED`.

## Why it is split by game

`AGENTS.md` §4 is blunt about this and it is not tidiness. The two games number their asset types
differently -- `xmodel` is pool 6 in Cold War and 4 in Black Ops 4 -- so a file mixing them
mislabels every row in it. The evidence is in the submissions themselves: both `clipmap` and
`clip_map` appear, and both `localizeentry` and `localize_entry`, because those are the two games'
own names for one pool.

The same name appearing under both games is correct rather than duplication: Cold War carries a
great deal of Black Ops 4's content, so a name confirmed against both games' ids is a fact about
both.

## The submissions that never said which game they were

Twenty-three of them, from before the game went into the folder name, and they are not a rounding
error -- 19,286 of the rows in the five wanted types. There is exactly one way to place them, and
it is the way `games_holding` does it: **hash the name and ask each game's `.ids` snapshot whether
it holds an asset under it.** That is the same question that made the name a find in the first
place, asked again, so it is authoritative rather than a guess -- and a name both snapshots hold
is filed under both, because it is genuinely a fact about both.

`unplaced/` would hold anything neither snapshot carries. Nothing currently lands there.

## The format

`hash,name`, exactly as the submissions store it, sorted by name. Sorted for two reasons: it makes
each rebuild a diff git can delta down to the lines that changed rather than storing 4 MB again,
and it makes a name findable by eye.
"""
import argparse
import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT
FOLDER = "all_names"

# `Who_GAME_20260822-020208`, and the older `Who_20260819-022655` which predates the game going
# into the name.
STAMPED = re.compile(r"^(?P<who>.+?)_(?:(?P<game>[A-Z0-9]+)_)?(?P<when>\d{8}-\d{6})$")

# The only asset types worth publishing, and the same five `AGENTS.md` §5 says to search.
#
# An allowlist rather than a blocklist, deliberately. Submissions carry names for 105 different
# types -- `craftbackground`, `uimodeldatastruct`, `winddef`, one row each -- because a general
# pass files whatever it lands on. Those are real names and they stay in `submissions/`, which is
# the record; they are not what anybody comes here for, and a folder of 105 files where 99 hold
# fewer than a hundred rows between them buries the six that matter.
#
# Both spellings of each, because the two games name their pools differently: Cold War writes
# `localize_entry` where Black Ops 4 writes `localizeentry`, and the same split runs through the
# map pools. Where a type has one spelling in both, one entry covers it.
WANTED = (
    "xmodel",
    "material",
    "image",
    "xanim",
    "sound_asset",
    "sound_alias",
)


def game_of(folder, files):
    """Which game a submission was for: from its folder name, or from its own run notes."""
    match = STAMPED.match(os.path.basename(folder))
    if match and match.group("game"):
        return match.group("game").lower()

    for path in files:
        if os.path.basename(path).startswith("about_"):
            found = re.search(r"^- game: (\w+)$", open(path, encoding="utf-8", errors="replace").read(), re.M)
            if found:
                return found.group(1).lower()

    return None


def snapshots_by_game():
    """{game: {id}} for every snapshot the repository ships."""
    held = {}
    for path in snapshot.snapshots():
        shot = snapshot.read(path)
        held[shot.game.lower()] = {asset_id for asset_id, _ in shot.records}
    return held


def games_holding(row, held):
    """Which games actually hold an asset under this row's name.

    The fallback for the 23 submissions that predate the game going into the folder name -- 24,212
    names, a quarter of the corpus, which would otherwise sit in an `unknown/` bucket nobody can
    seed from. Filing them by *which game holds the id* is not a guess: it is the same question
    that made the name a find in the first place, asked again.

    A name can come back for both, and that is the right answer rather than a duplicate. Cold War
    carries a great deal of Black Ops 4's content, so a great many names are genuinely facts about
    both games.
    """
    _, _, name = row.partition(",")
    name = name.strip()
    if not name:
        return []

    value = snapshot.fnv1a(name)
    masked = value & snapshot.ID_MASK

    return [game for game, ids in held.items() if value in ids or masked in ids]


def collect():
    """{(game, type): {row}} across every submission on disk."""
    gathered = collections.defaultdict(set)
    skipped = collections.Counter()
    held = snapshots_by_game()
    resolved = unresolved = 0

    for folder in sorted(glob.glob(os.path.join(ROOT, "submissions", "*"))):
        if not os.path.isdir(folder):
            continue

        files = sorted(glob.glob(os.path.join(folder, "*")))
        game = game_of(folder, files)

        for path in files:
            if not path.endswith(".txt"):
                continue

            kind = re.sub(r"_\d{8}-\d{6}$", "", os.path.splitext(os.path.basename(path))[0])
            if kind not in WANTED:
                skipped[kind] += 1
                continue

            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue

                    if game:
                        gathered[(game, kind)].add(line)
                        continue

                    # No game recorded anywhere in this submission: ask the snapshots instead.
                    #
                    # Filed under **every** game that holds it, not the first. If Black Ops 4's
                    # snapshot holds an asset under this name's hash then the name is a fact about
                    # Black Ops 4, whoever happened to confirm it and against whichever game.
                    holders = games_holding(line, held)
                    for holder in holders:
                        gathered[(holder, kind)].add(line)

                    if holders:
                        resolved += 1
                    else:
                        # Neither snapshot holds it. Almost certainly a pool the snapshots do not
                        # carry rather than a bad name, so it is kept and labelled rather than
                        # dropped -- results only ever grow.
                        gathered[("unplaced", kind)].add(line)
                        unresolved += 1

    if skipped:
        print(
            "  %d file(s) across %d other asset type(s) left in submissions/ only; %s holds the "
            "five that matter." % (sum(skipped.values()), len(skipped), FOLDER)
        )

    if resolved or unresolved:
        print(
            "  %s name(s) from submissions with no game recorded were placed by snapshot; "
            "%s could not be." % (format(resolved, ","), format(unresolved, ","))
        )

    return gathered


def sort_key(row):
    """By name, then hash, then the row itself.

    The last term looks redundant and is not. The first two are lowercased and stripped, so two
    rows differing only in case tie -- and the rows arrive from a `set`, whose iteration order
    Python randomises per process. Ties therefore broke differently on every run, the file changed
    without its contents changing, and CI would have committed 5 MB of reordering on every
    submission for ever. Sorting on the raw row last makes the order total and the output
    reproducible.
    """
    key, _, name = row.partition(",")
    return (name.strip().lower(), key.strip(), row)


def write(gathered, check):
    """Writes each list, and reports what changed. Returns how many files differ."""
    changed = 0
    written = []

    for (game, kind), rows in sorted(gathered.items()):
        body = "\n".join(sorted(rows, key=sort_key)) + "\n"
        path = os.path.join(ROOT, FOLDER, game, kind + ".txt")

        existing = ""
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as handle:
                existing = handle.read()

        if existing != body:
            changed += 1
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(body)

        written.append((game, kind, len(rows)))

    return changed, written


def write_index(written, check):
    """A README in the folder, so somebody who lands in it knows what they are looking at."""
    by_game = collections.defaultdict(list)
    for game, kind, count in written:
        by_game[game].append((kind, count))

    lines = [
        "# Every name this project has recovered",
        "",
        "**Generated. Do not edit anything here by hand** -- `scripts/collect_names.py` rewrites it",
        "whenever a submission lands, and an edit would be overwritten without warning. Corrections",
        "belong in a submission, which is the record these are built from.",
        "",
        "One file per game and asset type, `hash,name`, sorted by name. Together they are every name",
        "in every merged submission in `submissions/`, with duplicates removed.",
        "",
        "## Why you might want these rather than `submissions/`",
        "",
        "`submissions/` answers *who found what, when, and by which method* -- it is the provenance",
        "record and the input to `scripts/methods_report.py`. It is several hundred folders, and",
        "anybody who just wants the names has had to walk and merge them. That loop is written once,",
        "here, and the answer committed.",
        "",
        "These are **not** a substitute for the community tables in `cod-name-db`. Those are the",
        "published truth and are what every search excludes against. These are this project's own",
        "contribution to them, which is a different and smaller thing.",
        "",
        "## Why it is split by game",
        "",
        "The two games number their asset types differently -- `xmodel` is pool 6 in Cold War and 4 in",
        "Black Ops 4 -- so a file mixing them mislabels every row. You can see it in the type names",
        "themselves: both `clipmap` and `clip_map` appear, and both `localizeentry` and",
        "`localize_entry`, because those are the two games' own names for one pool.",
        "",
        "A name appearing under both games is not duplication. Cold War carries a great deal of Black",
        "Ops 4's content, and a name confirmed against both games' ids is a fact about both.",
        "",
        "Twenty-three submissions predate the game going into the folder name. They are placed by",
        "hashing each name and asking each game's `.ids` snapshot whether it holds an asset under it",
        "-- the same question that made the name a find. A name both snapshots hold is filed under",
        "both, because it is genuinely a fact about both.",
        "",
        "Only the five asset types worth searching are here. Submissions carry names for 105 types;",
        "the rest stay in `submissions/`, which is the record.",
        "",
        "## Contents",
        "",
    ]

    for game in sorted(by_game):
        rows = sorted(by_game[game], key=lambda pair: -pair[1])
        total = sum(count for _, count in rows)
        lines += [
            "### `%s/` -- %s names in %d file(s)" % (game, format(total, ","), len(rows)),
            "",
            "| asset type | names |",
            "|---|---:|",
        ]
        lines += ["| `%s` | %s |" % (kind, format(count, ",")) for kind, count in rows]
        lines.append("")

    body = "\n".join(lines)
    path = os.path.join(ROOT, FOLDER, "README.md")

    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            existing = handle.read()

    if existing == body:
        return 0

    if not check:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)

    return 1


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report what would change, write nothing")
    options = parser.parse_args(argv)

    gathered = collect()
    if not gathered:
        raise SystemExit(
            "no submissions on disk, so there is nothing to collect. Run `start` first -- the\n"
            "merged submissions arrive with it."
        )

    changed, written = write(gathered, options.check)
    changed += write_index(written, options.check)

    names = sum(count for _, _, count in written)
    games = len({game for game, _, _ in written})

    print(
        "%s names across %d file(s) in %d game(s); %d file(s) %s."
        % (
            format(names, ","),
            len(written),
            games,
            changed,
            "would change" if options.check else "written",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
