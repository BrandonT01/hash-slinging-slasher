"""What every submission in this repository was, what it cost, and what it returned.

    python scripts/methods_report.py               one line per submission, newest last
    python scripts/methods_report.py --by-method   what each method returned, ranked by yield
    python scripts/methods_report.py --families    the same with tuning variants folded together
    python scripts/methods_report.py --efficiency  every measured method, decay included
    python scripts/methods_report.py --unattributed  runs whose yield cannot be credited, and why
    python scripts/methods_report.py --registry    the computed method registry, as markdown
    python scripts/methods_report.py --duplicates  submissions that returned the same names

Run this before choosing what to grind. It is the only place that answers "has this already been
done, and did it pay?" -- and the answer is usually yes to the first half.

## Read this if you have seen an older ranking

Until 2026-08-22 `--by-method` credited **every method in a submission with that submission's
entire name count**. A submission holding nine runs and 9,034 names credited all nine methods with
9,034 each, so fifteen methods reported identical invented yields at the top of the ranking while
the best method actually measured -- image siblings, 1,514 names off 596,049 candidates -- sat
thirty rows down. Every agent that chose a method by reading that table was choosing from
fiction, and the error grew with how many methods a contributor bundled into one submission.

Names are now credited to the **run** that found them and to nothing else. A run that does not
record its own yield is counted as unattributed rather than being given the batch's total; see
`--unattributed`, which exists so the size of that gap stays visible instead of being quietly
absorbed into the ranking.

## The metric

A method's worth is what it returns **per candidate**, not what it returns in a pass. Names per
run rewards whatever ran longest, which is how a blind sweep testing 1.35 billion candidates for
402 names outranks a derivation testing 596,049 for 1,514. Both numbers are printed; the ranking
uses the first.

`submissions/` records more than names: each batch carries an `about_*.md` naming the method, how
long it ran, and (since the fingerprint was introduced) exactly what its inputs were. This reads
all of it. Nothing here needs the network; it is the merged history on disk, which is current as
long as `start` has run.
"""
import collections
import datetime
import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBMISSIONS = os.path.join(ROOT, "submissions")

# A run records how many names it found under one of three labels, because the vocabulary changed
# twice as the tools grew. In preference order: `confirm_list` writes `new`, the current general
# search writes `new here`, and two surviving runs from the first day write `names found`. Reading
# only the first would drop 70 runs on the floor; reading them in the wrong order would prefer a
# match count over a new-name count for the runs that carry both.
YIELD_LABELS = ("new", "new here", "names found")

# How much worse a method's latest run has to be than its best before it is worth warning somebody
# off. Ten is deliberately loose: these are noisy small samples, and the cost of calling a live
# method spent is somebody not running the best thing available.
#
# Compared against the method's *best* run rather than its lifetime average, because decay is the
# thing being detected and an average that already includes the decline hides it. A method whose
# first run returned 1 name per 400 and whose latest returns 1 per 40,000 has been ground out,
# even though its average over the two still reads healthy.
SPENT_FACTOR = 10.0
COOLING_FACTOR = 3.0


def parse_duration(text):
    """`1h 00m 53s`, `47m`, `9s` -> seconds. None when it does not parse."""
    if not text:
        return None
    seconds = 0
    found = False
    for value, unit in re.findall(r"(\d+)\s*([hms])", text):
        found = True
        seconds += int(value) * {"h": 3600, "m": 60, "s": 1}[unit]
    return seconds if found else None


def parse_int(text):
    """A recorded count. These are written plain, but tolerate separators rather than crash."""
    if text is None:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def parse_stamp(text):
    """`20260821-163108` -> a datetime, for ordering runs and reporting when one last ran."""
    match = re.search(r"(\d{8})-(\d{6})", text or "")
    if not match:
        return None
    try:
        return datetime.datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def fields(text):
    """The `- key: value` lines of one block, as a dict. Later wins, which no block relies on."""
    return {
        key.strip(): value.strip()
        for key, value in re.findall(r"^- ([a-z][a-z0-9 _-]*): (.*)$", text, re.M)
    }


def parse_about(path, folder_name):
    """One `about_*.md` split into its header and its runs.

    The header and the runs use overlapping key names -- both carry `game`, and the header's
    per-type counts (`- image: 4`) look exactly like a measurement -- so the two are parsed from
    separate slices of the file rather than from the file as a whole. Reading them together is how
    a submission's own total gets mistaken for a run's yield, which is the bug this file exists to
    have stopped doing.
    """
    text = open(path, encoding="utf-8", errors="replace").read()
    blocks = re.split(r"^### run_", text, flags=re.M)

    header = fields(blocks[0])
    runs = []

    for block in blocks[1:]:
        first, _, rest = block.partition("\n")
        recorded = fields(rest)

        found = None
        found_label = None
        for label in YIELD_LABELS:
            if label in recorded:
                found = parse_int(recorded[label])
                found_label = label
                break

        runs.append(
            {
                "id": "run_" + first.strip(),
                "when": parse_stamp(first) or parse_stamp(folder_name),
                "method": recorded.get("method", "not recorded"),
                "what": recorded.get("what it does", ""),
                "game": recorded.get("game", ""),
                "seconds": parse_duration(recorded.get("ran for")),
                "candidates": parse_int(recorded.get("candidates tested")),
                "matched": parse_int(recorded.get("matched")) or parse_int(recorded.get("matches")),
                "found": found,
                "found_label": found_label,
                "fingerprint": recorded.get("fingerprint"),
                "submission": folder_name,
            }
        )

    return header, runs


def read(folder):
    """One submission: who, when, how many names it sent, and every run inside it."""
    who = os.path.basename(folder)
    names = []
    kinds = collections.Counter()

    for path in sorted(glob.glob(os.path.join(folder, "*.txt"))):
        kind = re.sub(r"_\d{8}-\d{6}$", "", os.path.splitext(os.path.basename(path))[0])
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                _, _, name = line.partition(",")
                name = name.strip()
                if name:
                    names.append(name)
                    kinds[kind] += 1

    header, runs = {}, []
    for path in sorted(glob.glob(os.path.join(folder, "about_*.md"))):
        one_header, one_runs = parse_about(path, who)
        header.update(one_header)
        runs += one_runs

    return {
        "who": who,
        "when": parse_stamp(who),
        "names": names,
        "kinds": kinds,
        "runs": runs,
        "methods": [run["method"] for run in runs] or ["not recorded"],
        "sent": len(names),
        "digest": hashlib.sha1(",".join(sorted(names)).encode()).hexdigest()[:12],
    }


def thousands(value):
    return "-" if value is None else format(value, ",")


def per(candidates, found):
    """Candidates per name found. None when the run did not record enough to say."""
    if not candidates or not found:
        return None
    return candidates / found


# The parameter tail a contributor appends when they re-run a method tuned differently, and the
# game and timestamp `confirm_list` bakes into a generated label. None of these change what the
# method reaches, so all of them are stripped before a method is compared with another.
QUALIFIER = re.compile(
    r"""
      \s*\(.*?\)\s*$                      # a trailing (cap 64), (cap 200)
    | \s*,\s*(?:cap|depth|key|min-)\b.*$  # , cap 64  , depth 2 cap 24  , key 4
    | \s*,\s*(?:widened|loosened|deduplicated|interrupted|rare|wide|unique).*$
    | \s*--\s.*$                          # a trailing dash comment
    """,
    re.X,
)
GAME_PREFIX = re.compile(r"^(?:blkops04|blkopscw|bo4|cw)[_ -]+", re.I)
STAMP_SUFFIX = re.compile(r"[_ -]*\d{8}-\d{6}\s*$")
TOOL_SUFFIX = re.compile(r"\s*\((?:scripts/)?[\w./]+\.py\)\s*$")


def family(method):
    """The method a label names, with the game, the timestamp and the tuning taken off.

    `alias slot substitution`, `alias slot substitution, cap 64` and `alias slot substitution,
    left context only (cap 200)` are one method run three ways, and listing them as three is how
    somebody comes to invent a fourth. `blkops04_channels` and `blkopscw_channels` are one method
    run against two games. This is deliberately conservative -- it only removes what is known not
    to change what a method reaches -- so two labels for genuinely the same idea can still survive
    as two rows. It is a way to make the list shorter and truer, not a classifier.
    """
    name = method.strip()
    name = STAMP_SUFFIX.sub("", name)
    name = GAME_PREFIX.sub("", name)
    name = TOOL_SUFFIX.sub("", name)
    previous = None
    while previous != name:
        previous = name
        name = QUALIFIER.sub("", name).strip()
    return (name or method).replace("_", " ").strip().lower()


def collect(read_all, by_family=False):
    """Every run in the repository, grouped by the method that ran it."""
    grouped = collections.defaultdict(list)
    for entry in read_all:
        for run in entry["runs"]:
            grouped[family(run["method"]) if by_family else run["method"]].append(run)
    for runs in grouped.values():
        runs.sort(key=lambda run: run["when"] or datetime.datetime.min)
    return grouped


def summarise(runs):
    """One method's record: totals, its recent form, and whether it still pays."""
    measured = [run for run in runs if run["candidates"] and run["found"] is not None]
    attributed = [run for run in runs if run["found"] is not None]

    names = sum(run["found"] for run in attributed)
    candidates = sum(run["candidates"] for run in measured)
    names_measured = sum(run["found"] for run in measured)

    lifetime = per(candidates, names_measured)

    # Each measured run's own rate, in the order they ran. `best` is the method at its best and
    # `latest` is the method as it now stands; the gap between them is the decay.
    rates = [per(run["candidates"], run["found"]) for run in measured]
    scored = [rate for rate in rates if rate]
    best = min(scored) if scored else None
    latest = next((rate for rate in reversed(rates) if rate), None)

    # A run that tested candidates and found nothing has no rate at all -- it cannot be divided --
    # but it is the single clearest signal in the record, and the old report threw every one of
    # them away. Two such in a row is spent whatever the average says.
    tail = [run["found"] for run in runs if run["found"] is not None][-2:]
    dead_tail = len(tail) == 2 and sum(tail) == 0

    if not measured:
        state = "unmeasured"
    elif dead_tail:
        state = "spent"
    elif best and latest and latest > best * SPENT_FACTOR:
        state = "spent"
    elif best and latest and latest > best * COOLING_FACTOR:
        state = "cooling"
    elif len(measured) < 2:
        # One data point is not a trend, and calling it live reads as a recommendation it has not
        # earned. Somebody should run it again; that is a different message from "this still pays".
        state = "untried"
    else:
        state = "live"

    when = [run["when"] for run in runs if run["when"]]

    return {
        "runs": len(runs),
        "attributed_runs": len(attributed),
        "names": names,
        "candidates": candidates,
        "names_measured": names_measured,
        "per": lifetime,
        "best_per": best,
        "recent_per": latest,
        "state": state,
        "first": min(when) if when else None,
        "last": max(when) if when else None,
        "what": next((run["what"] for run in runs if run["what"]), ""),
        "games": sorted({run["game"] for run in runs if run["game"]}),
        "labels": sorted({run["method"] for run in runs}),
        "contributors": sorted({run["submission"].split("_")[0] for run in runs}),
    }


def rank(by_method, key):
    """Methods worth ranking first, then everything that cannot be ranked, each best first."""
    summaries = {method: summarise(runs) for method, runs in by_method.items()}
    ranked = [m for m in summaries if summaries[m][key]]
    rest = [m for m in summaries if not summaries[m][key]]
    ranked.sort(key=lambda m: summaries[m][key])
    rest.sort(key=lambda m: summaries[m]["names"], reverse=True)
    return summaries, ranked + rest


def show_by_method(read_all):
    by_method = collect(read_all)
    if not by_method:
        print("no runs recorded in any submission.")
        return

    summaries, order = rank(by_method, "per")

    print(
        "%-46s %5s %9s %14s %12s %10s %s"
        % ("method", "runs", "names", "candidates", "1 name per", "last run", "state")
    )
    for method in order:
        s = summaries[method]
        print(
            "%-46s %5d %9s %14s %12s %10s %s"
            % (
                method[:46],
                s["runs"],
                thousands(s["names"]),
                thousands(s["candidates"]) if s["candidates"] else "-",
                format(int(s["per"]), ",") if s["per"] else "-",
                s["last"].strftime("%m-%d") if s["last"] else "-",
                s["state"],
            )
        )

    unattributed = sum(1 for entry in read_all for run in entry["runs"] if run["found"] is None)
    total_runs = sum(len(entry["runs"]) for entry in read_all)
    print(
        "\n%d runs across %d submissions. %d recorded what they found; %d did not and are counted\n"
        "in no method's names -- `--unattributed` says which."
        % (total_runs, len(read_all), total_runs - unattributed, unattributed)
    )
    print(
        "\nRanked by candidates per name, best first, because that is what predicts the next run.\n"
        "`names` is what the run found new to the machine that ran it, which is more than reached\n"
        "the community: %s were sent in total after `submit` dropped what was already published or\n"
        "claimed. `state` is spent when the last two runs found nothing or recent yield is %gx worse\n"
        "than lifetime, cooling at %gx, unmeasured when no run recorded its candidate count."
        % (
            thousands(sum(entry["sent"] for entry in read_all)),
            SPENT_FACTOR,
            COOLING_FACTOR,
        )
    )


def show_efficiency(read_all):
    by_method = collect(read_all)
    summaries, order = rank(by_method, "per")
    order = [m for m in order if summaries[m]["per"]]

    if not order:
        print("no run has recorded both a candidate count and a yield.")
        return

    print(
        "%-42s %14s %9s %12s %12s %12s"
        % ("method", "candidates", "names", "lifetime", "at its best", "latest run")
    )
    for method in order:
        s = summaries[method]
        print(
            "%-42s %14s %9s %12s %12s %12s"
            % (
                method[:42],
                thousands(s["candidates"]),
                thousands(s["names_measured"]),
                format(int(s["per"]), ","),
                format(int(s["best_per"]), ",") if s["best_per"] else "-",
                format(int(s["recent_per"]), ",") if s["recent_per"] else "-",
            )
        )
    print(
        "\nAll three columns are candidates per name, so smaller is better. Where `latest run` is\n"
        "far worse than `at its best` the method has been ground out on the corpus it had, and the\n"
        "lifetime figure is being held up by the day it was new. That gap, not the lifetime column,\n"
        "is what says whether running it again would pay."
    )


def show_unattributed(read_all):
    """The runs the ranking cannot credit, so the gap is visible rather than absorbed."""
    missing = collections.Counter()
    examples = {}
    for entry in read_all:
        for run in entry["runs"]:
            if run["found"] is None:
                missing[run["method"]] += 1
                examples.setdefault(run["method"], run["submission"])

    if not missing:
        print("every run records what it found.")
        return

    print("%-58s %6s  %s" % ("method", "runs", "first seen in"))
    for method, count in missing.most_common():
        print("%-58s %6d  %s" % (method[:58], count, examples[method]))
    print(
        "\nThese runs name a method but not a yield, so they are credited with no names at all.\n"
        "Crediting them with their submission's total is what the old ranking did, and it invented\n"
        "the numbers that sat at the top of it. A run recorded before its tool wrote `new` cannot\n"
        "be recovered; what stops the list growing is every search recording its own yield."
    )


def show_families(read_all):
    """One row per method, with its tuning variants folded together."""
    grouped = collect(read_all, by_family=True)
    summaries, order = rank(grouped, "per")

    print(
        "%-40s %5s %5s %9s %12s %10s %s"
        % ("method", "ways", "runs", "names", "1 name per", "last run", "state")
    )
    for name in order:
        s = summaries[name]
        print(
            "%-40s %5d %5d %9s %12s %10s %s"
            % (
                name[:40],
                len(s["labels"]),
                s["runs"],
                thousands(s["names"]),
                format(int(s["per"]), ",") if s["per"] else "-",
                s["last"].strftime("%m-%d") if s["last"] else "-",
                s["state"],
            )
        )
    print(
        "\n%d methods, run %d ways between them. `ways` counts the distinct labels folded into one\n"
        "row -- a method run against both games, or re-run with a different cap, is one method. The\n"
        "unfolded list is `--by-method`; this is the one to read before inventing something, because\n"
        "a method already here under a name you would not have guessed is the thing you are about\n"
        "to build again." % (len(order), sum(len(summaries[n]["labels"]) for n in order))
    )


MARKER_BEGIN = "<!-- BEGIN GENERATED REGISTRY -->"
MARKER_END = "<!-- END GENERATED REGISTRY -->"
METHODS_MD = os.path.join(ROOT, "METHODS.md")


def write_registry(text):
    """Replaces the generated block in METHODS.md, leaving everything a person wrote alone.

    The registry in METHODS.md above this block is hand-written and stays that way: it says what a
    method *reaches* and when it is spent, which is judgement and cannot be computed. This block
    is the other half -- every method that has actually been run, with what it returned -- and
    keeping it by hand is why it held 10 of the 104 methods that existed.
    """
    if not os.path.exists(METHODS_MD):
        raise SystemExit("METHODS.md is not where it should be; nothing was written.")

    document = open(METHODS_MD, encoding="utf-8").read()
    if MARKER_BEGIN not in document or MARKER_END not in document:
        raise SystemExit(
            "METHODS.md has no generated-registry markers, so there is nowhere to write.\n"
            "Add these two lines where the table belongs and run this again:\n\n"
            "    %s\n    %s" % (MARKER_BEGIN, MARKER_END)
        )

    head, _, rest = document.partition(MARKER_BEGIN)
    _, _, tail = rest.partition(MARKER_END)

    with open(METHODS_MD, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(head + MARKER_BEGIN + "\n" + text.rstrip() + "\n" + MARKER_END + tail)

    print("METHODS.md registry updated.")


def show_registry(read_all, write=False):
    """The method registry, computed. See METHODS.md, which holds what a machine cannot derive."""
    grouped = collect(read_all, by_family=True)
    summaries, order = rank(grouped, "per")

    lines = []
    print = lines.append  # noqa: A001 -- collected so the same body can print or write

    print("<!-- generated by scripts/methods_report.py --registry --write; do not edit by hand -->")
    print(
        "\nEvery method ever run here, computed from the run record in `submissions/`. Ranked by\n"
        "candidates per name, best first. `ways` is how many distinct labels this one method has\n"
        "been run under -- check it before inventing anything, because a method already in this\n"
        "table under a name you would not have guessed is the thing you are about to rebuild.\n"
    )
    print("| method | ways | runs | names | candidates | 1 name per | best | latest | first | last | state |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|")
    for name in order:
        s = summaries[name]
        print(
            "| %s | %d | %d | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                name.replace("|", "\\|"),
                len(s["labels"]),
                s["runs"],
                thousands(s["names"]),
                thousands(s["candidates"]) if s["candidates"] else "-",
                format(int(s["per"]), ",") if s["per"] else "-",
                format(int(s["best_per"]), ",") if s["best_per"] else "-",
                format(int(s["recent_per"]), ",") if s["recent_per"] else "-",
                s["first"].strftime("%Y-%m-%d") if s["first"] else "-",
                s["last"].strftime("%Y-%m-%d") if s["last"] else "-",
                s["state"],
            )
        )
    print(
        "\n%d distinct methods, run %d ways between them, across %d runs. `names` is what each run\n"
        "found new to the machine that ran it. A blank candidate count means no run of that method\n"
        "recorded one, so it cannot be ranked -- see `--unattributed`."
        % (
            len(order),
            sum(len(summaries[n]["labels"]) for n in order),
            sum(summaries[n]["runs"] for n in order),
        )
    )

    text = "\n".join(lines)
    if write:
        write_registry(text)
    else:
        sys.stdout.write(text + "\n")


def show_duplicates(read_all):
    by_digest = collections.defaultdict(list)
    for entry in read_all:
        by_digest[entry["digest"]].append(entry["who"])

    repeated = {d: w for d, w in by_digest.items() if len(w) > 1}
    if not repeated:
        print("no two submissions hold exactly the same set of names.")
        return

    print("submissions that returned identical name sets:\n")
    for digest, who in repeated.items():
        print("  %s" % digest)
        for name in who:
            print("     %s" % name)
    print(
        "\nThis is what a deterministic method looks like from the outside: the same search\n"
        "over the same inputs returns the same answer to everybody who runs it. The run\n"
        "fingerprint exists to warn the second person before they spend the night, and\n"
        "`submit` now drops names an open pull request already claims."
    )


def main(argv):
    folders = sorted(
        path for path in glob.glob(os.path.join(SUBMISSIONS, "*")) if os.path.isdir(path)
    )

    if not folders:
        raise SystemExit(
            "no submissions on disk. Run `start` first -- it updates the clone, and the merged\n"
            "submissions arrive with it."
        )

    read_all = [read(folder) for folder in folders]

    for flag, view in (
        ("--duplicates", show_duplicates),
        ("--by-method", show_by_method),
        ("--families", show_families),
        ("--efficiency", show_efficiency),
        ("--unattributed", show_unattributed),
    ):
        if flag in argv:
            view(read_all)
            return

    if "--registry" in argv:
        show_registry(read_all, write="--write" in argv)
        return

    print("%-34s %7s  %-42s %s" % ("submission", "names", "method", "kinds"))
    for entry in read_all:
        print(
            "%-34s %7d  %-42s %s"
            % (
                entry["who"][:34],
                entry["sent"],
                (entry["methods"][0])[:42],
                " ".join("%s:%d" % pair for pair in entry["kinds"].most_common(4)),
            )
        )

    everything = set()
    for entry in read_all:
        everything |= set(entry["names"])

    total = sum(entry["sent"] for entry in read_all)
    print(
        "\n%d submissions, %d names sent, %d distinct -- %d were somebody else's already."
        % (len(read_all), total, len(everything), total - len(everything))
    )


if __name__ == "__main__":
    main(sys.argv[1:])
