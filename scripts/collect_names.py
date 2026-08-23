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
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT
FOLDER = "all_names"

# The order asset types are listed in, everywhere they are listed: the README and the Discord
# announcement both take it from here, so the two cannot drift apart. Sorting by count instead
# reorders the rows whenever a pass lands, which makes two readings of the same page hard to
# compare -- and puts the same type in a different place for each game.
#
# Model, material, image, anim, then the two sound pools: roughly the order an asset is built in,
# and the order `AGENTS.md` §5 lists them. Anything not named here sorts after, alphabetically.
DISPLAY_ORDER = ["xmodel", "material", "image", "xanim", "sound_asset", "sound_alias"]


def in_display_order(pairs):
    """`[(kind, count)]` in DISPLAY_ORDER, with anything unrecognised after it."""
    rank = {kind: index for index, kind in enumerate(DISPLAY_ORDER)}
    return sorted(pairs, key=lambda pair: (rank.get(pair[0], len(rank)), pair[0]))

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


def pool_coverage(written):
    """{game: {asset type: (named, total)}} -- how much of each pool anybody can name.

    Read from `all_names/coverage.json`, which `scripts/measure_coverage.py` writes on a machine
    that has the published tables. They are 345 MB and live in `cod-name-db/`, which is gitignored
    and fetched by `start`, so nothing that runs in CI can see them -- and downloading them on
    every merged submission, forty-odd on a busy night, for a figure that moves slowly would be
    absurd.

    This project's own growth since that baseline is added here rather than re-measured, and that
    is exact rather than approximate: `submit` drops any name the tables already publish, so a
    name confirmed after the baseline cannot already be inside its `named` count.

    What the stored figure cannot see is names *somebody else* published upstream since. Those
    raise the true percentage without raising this one, so a stale baseline under-reports. Re-run
    `measure_coverage.py` and it corrects.

    Returns an empty mapping when there is no baseline, and the README then omits the column
    rather than printing a percentage of nothing.
    """
    path = os.path.join(ROOT, FOLDER, "coverage.json")
    if not os.path.exists(path):
        return {}

    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            baseline = json.load(handle)
    except (ValueError, OSError):
        return {}

    ours_now = collections.defaultdict(dict)
    for game, kind, count in written:
        ours_now[game][kind] = count

    out = {}
    for game, types in baseline.get("games", {}).items():
        counts = {}
        for kind, figures in types.items():
            total = figures.get("total", 0)
            named = figures.get("named", 0)
            # Anything this project has published since the baseline was taken.
            grown = ours_now.get(game, {}).get(kind, 0) - figures.get("ours_at_baseline", 0)
            named = min(total, named + max(0, grown))
            counts[kind] = (named, total)
        out[game] = counts
    return out


def game_table(game, rows, coverage):
    """One game's table as HTML, so two of them can sit side by side.

    Markdown cannot span a header across columns or place two tables next to each other, and
    stacked tables made this page mostly whitespace. GitHub renders HTML in markdown, so the
    tables are HTML and everything else on the page stays markdown.
    """
    total = sum(count for _, count in rows)
    counts = coverage.get(game, {})
    show_percent = any(kind in counts for kind, _ in rows)

    span = 3 if show_percent else 2
    out = [
        "<table>",
        "<tr>"
        '<th align="left"><code>%s/</code></th>' % game,
        '<th align="right" colspan="%d">%s names in %d file(s)</th>' % (span - 1, format(total, ","), len(rows)),
        "</tr>",
        "<tr>"
        '<th align="left">asset type</th>'
        '<th align="right">found here</th>'
        + ('<th align="right">named, of all in the game</th>' if show_percent else ""),
        "</tr>",
    ]

    for kind, count in rows:
        cells = [
            "<td><code>%s</code></td>" % kind,
            '<td align="right">%s</td>' % format(count, ","),
        ]
        if show_percent:
            named, pool_total = counts.get(kind, (0, 0))
            # The fraction, not just the percentage. Printing `8,423` beside `79.4%` reads as
            # though the one is the other's numerator, and it is not: the count is what this
            # project found, the percentage is what everybody together has named.
            cells.append(
                '<td align="right">%s</td>'
                % (
                    "%s / %s &nbsp;(%.1f%%)" % (format(named, ","), format(pool_total, ","), 100.0 * named / pool_total)
                    if pool_total
                    else "--"
                )
            )
        out.append("<tr>" + "".join(cells) + "</tr>")

    out.append("</table>")
    return out


def write_index(written, check):
    """A README in the folder, so somebody who lands in it knows what they are looking at."""
    by_game = collections.defaultdict(list)
    for game, kind, count in written:
        by_game[game].append((kind, count))

    coverage = pool_coverage(written)
    games = sorted(by_game)

    lines = [
        "# Every name this project has recovered",
        "",
    ]

    # The tables first and side by side. They are the reason anybody opens this file, and stacked
    # they pushed every word of explanation below two screens of whitespace.
    lines += ["<table><tr>"]
    for game in games:
        rows = in_display_order(by_game[game])
        lines.append('<td valign="top">')
        lines.append("")
        lines += game_table(game, rows, coverage)
        lines.append("")
        lines.append("</td>")
    lines += ["</tr></table>", ""]

    if coverage:
        measured = ""
        try:
            with open(os.path.join(ROOT, FOLDER, "coverage.json"), encoding="utf-8") as handle:
                measured = json.load(handle).get("measured", "")
        except Exception:
            pass

        # A worked example and the emptiest pool, both computed. Written by hand they would be
        # wrong within a night, and a generated page carrying stale numbers is worse than one
        # carrying none.
        worked = emptiest = None
        for game in games:
            for kind, count in by_game[game]:
                named, total = coverage.get(game, {}).get(kind, (0, 0))
                if not total:
                    continue
                if worked is None and count and named > count:
                    worked = (game, kind, count, named, total)
                if emptiest is None or named / total < emptiest[3] / emptiest[4]:
                    emptiest = (game, kind, count, named, total)

        lines += [
            "**found here** is what this project has recovered and published in these files.",
            "**named, of all in the game** is the whole pool: those names plus every one already in",
            "the community tables, against every id the game holds.",
            "",
            "They are not the same measure, and the second is much the larger.",
            "",
        ]

        if worked:
            game, kind, count, named, total = worked
            lines += [
                "Where `%s` under `%s/` reads %s and %s / %s:"
                % (kind, game, format(count, ","), format(named, ","), format(total, ",")),
                "this project found %s of the %s names anybody has for that pool, and"
                % (format(count, ","), format(named, ",")),
                "%s of its ids are still nameless. The percentage is the fraction named,"
                % format(total - named, ","),
                "not the fraction found here.",
                "",
            ]

        if emptiest:
            game, kind, count, named, total = emptiest
            lines += [
                "The emptiest pool is `%s` under `%s/`: %s of %s named,"
                % (kind, game, format(named, ","), format(total, ",")),
                "so %s ids carry no name at all. That is the largest unworked ground"
                % format(total - named, ","),
                "here, and it is invisible from a count on its own.",
                "",
            ]

        lines += [
            "The community half of that is measured against `cod-name-db`%s and stored in"
            % (" on %s" % measured if measured else ""),
            "`coverage.json`, because the tables are 345 MB and are not in this repository. Names",
            "recovered here since are added on top, which is exact rather than approximate: `submit`",
            "drops anything the tables already publish, so a later find cannot already be counted.",
            "What a stale baseline misses is names *somebody else* published upstream, so it",
            "under-reports rather than over-reports. `scripts/measure_coverage.py` refreshes it.",
            "",
        ]

    lines += [
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
    ]

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


def write_summary(written, check):
    """The same figures as the README, as JSON, for anything that is not a person.

    The README is HTML so it can put two tables side by side, which is right for a reader and
    wrong for a program: scraping it would break the next time anybody touches the layout. So the
    numbers are written once more in a shape a bot can read, and the two never have to agree by
    hand because both come from this function's caller.

    `names` is what this project has published here. `named`/`total`/`found_pct` are about the
    game: every id in that pool, and how many of them *anybody* can name.
    """
    coverage = pool_coverage(written)
    by_game = collections.defaultdict(list)
    for game, kind, count in written:
        by_game[game].append((kind, count))

    out = {"games": {}, "totals": {}}
    grand = 0
    for game in sorted(by_game):
        counts = coverage.get(game, {})
        types = {}
        for kind, count in in_display_order(by_game[game]):
            named, total = counts.get(kind, (0, 0))
            types[kind] = {
                "names": count,
                "named": named,
                "total": total,
                "found_pct": round(100.0 * named / total, 1) if total else None,
            }
        game_total = sum(count for _, count in by_game[game])
        grand += game_total
        out["games"][game] = {"names": game_total, "files": len(by_game[game]), "types": types}

    out["totals"] = {"names": grand, "games": len(by_game)}
    # So anything reading this file lists the types the same way the README does.
    out["order"] = list(DISPLAY_ORDER)

    body = json.dumps(out, indent=2, sort_keys=True) + chr(10)
    path = os.path.join(ROOT, FOLDER, "summary.json")

    existing = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            existing = handle.read()

    if existing == body:
        return 0

    if not check:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline=chr(10)) as handle:
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
    changed += write_summary(written, options.check)

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
