"""What every submission in this repository was, what it cost, and what it returned.

    python scripts/methods_report.py              one line per submission, newest last
    python scripts/methods_report.py --by-method  totals per method, which is the useful view
    python scripts/methods_report.py --duplicates submissions that returned the same names

Run this before choosing what to grind. It is the only place that answers "has this already been
done, and did it pay?" -- and the answer is usually yes to the first half.

`submissions/` records more than names: each batch carries an `about_*.md` naming the method, how
long it ran, and (since the fingerprint was introduced) exactly what its inputs were. This reads
all of it. Nothing here needs the network; it is the merged history on disk, which is current as
long as `start` has run.
"""
import collections
import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBMISSIONS = os.path.join(ROOT, "submissions")


def read(folder):
    """One submission: who, when, how many names, which methods, and the names themselves."""
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

    methods, ran_for, fingerprints = [], [], []
    for path in glob.glob(os.path.join(folder, "about_*.md")):
        text = open(path, encoding="utf-8", errors="replace").read()
        methods += re.findall(r"^- method: (.+)$", text, re.M)
        ran_for += re.findall(r"^- ran for: (.+)$", text, re.M)
        fingerprints += re.findall(r"^- fingerprint: (.+)$", text, re.M)

    return {
        "who": who,
        "names": names,
        "kinds": kinds,
        "methods": methods or ["not recorded"],
        "ran_for": ran_for,
        "fingerprints": fingerprints,
        "digest": hashlib.sha1(",".join(sorted(names)).encode()).hexdigest()[:12],
    }


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

    if "--duplicates" in argv:
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
        return

    if "--by-method" in argv:
        totals = collections.Counter()
        runs = collections.Counter()
        for entry in read_all:
            for method in entry["methods"]:
                totals[method] += len(entry["names"])
                runs[method] += 1

        print("%-58s %6s %8s %8s" % ("method", "runs", "names", "per run"))
        for method, total in totals.most_common():
            print("%-58s %6d %8d %8d" % (method[:58], runs[method], total, total // runs[method]))
        return

    print("%-34s %7s  %-42s %s" % ("submission", "names", "method", "kinds"))
    for entry in read_all:
        print(
            "%-34s %7d  %-42s %s"
            % (
                entry["who"][:34],
                len(entry["names"]),
                (entry["methods"][0])[:42],
                " ".join("%s:%d" % pair for pair in entry["kinds"].most_common(4)),
            )
        )

    everything = set()
    for entry in read_all:
        everything |= set(entry["names"])

    total = sum(len(entry["names"]) for entry in read_all)
    print(
        "\n%d submissions, %d names sent, %d distinct -- %d were somebody else's already."
        % (len(read_all), total, len(everything), total - len(everything))
    )


if __name__ == "__main__":
    main(sys.argv[1:])
