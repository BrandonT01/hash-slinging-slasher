"""How much ground a plan shares with searches other people have already run.

    python scripts/overlap.py plans/mine.txt        before spending an hour on it
    python scripts/overlap.py --runs               what the record holds, and how it relates
    python scripts/overlap.py plans/mine.txt --worst 5

Reconnaissance. It prints numbers, never candidates, and it never blocks a run.

## The gap this fills

A run carries a **fingerprint**: a digest of everything that decides what it will find. It answers
one question perfectly -- is this the identical search somebody already ran -- and that is what
stopped five contributors submitting the same 430 names.

It is blind to the far commoner waste. A plan sharing nine tenths of its stems with one somebody
ran last night has a *different* fingerprint, so nothing warns anybody, and the second run spends
an hour to return the first one's names minus a handful. `state/swept.txt` holds 264 of those
opaque digests and cannot answer a single question about how any two of them relate. This is why
"re-measure the lists" looked like a remedy for an exhausted search: it reliably changes the
fingerprint without changing what the search can reach.

## How it answers

Every plan-shaped run now records a **sketch** of each of its three lists -- the thirty-two
smallest scattered hashes, which estimate how much two lists share without either side keeping
the lists. A cross product overlaps another cross product roughly as the product of its three
list overlaps, and that is what this reports.

Roughly. The estimate carries about a fifth either way, so it is worth reading as "broadly the
same ground" or "somewhere else", never as a number. **It is advice, not a gate:** the whole
lesson of §8 is that blocking on a coarse signal sends people to re-measure their lists instead of
inventing something, and that is how the yield here collapsed.

## What to do when it says you overlap

Not widen the plan -- a wider plan overlaps *more*. Aim it somewhere else: a different pool's
stems, a family nothing has covered, the beginnings `scripts/uncarried.py` measures as
unreachable. `scripts/seams.py` says which relations are worth aiming at.
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT

# Must match `Sketch` in src/fingerprint.rs. Recomputing a sketch here has to produce exactly what
# the Rust side would, or a plan would never match any run.
SKETCH = 32
MASK = (1 << 64) - 1

# Below this, two searches are looking at different things and saying so is noise.
WORTH_SAYING = 0.15


def scatter(value):
    """SplitMix64's finalizer, exactly as `Sketch::scatter` does it.

    Not decoration. FNV-1a barely avalanches on short strings sharing a prefix, so the thirty-two
    smallest raw hashes of a name list are thirty-two consecutive names rather than a sample of
    it -- two lists sharing half their entries measured as zero overlap until this went in.
    """
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & MASK
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def sketch_of(items):
    """The sketch of a list, as the same hex string the Rust side writes."""
    hashes = sorted({scatter(snapshot.fnv1a(item)) for item in items if item})
    return "".join("%016x" % value for value in hashes[:SKETCH])


def parse_sketch(text):
    text = (text or "").strip()
    return [
        int(text[at : at + 16], 16)
        for at in range(0, len(text) - 15, 16)
    ]


def overlap(left, right):
    """Roughly what share of two sketched lists is common, or None if either is unsketched."""
    left, right = parse_sketch(left), parse_sketch(right)
    if not left or not right:
        return None

    union = sorted(set(left) | set(right))[: min(SKETCH, len(left), len(right))]
    if not union:
        return None

    in_both = set(left) & set(right)
    return sum(1 for value in union if value in in_both) / len(union)


def recorded_runs():
    """Every run anywhere on disk that recorded sketches: this machine's, and everybody's."""
    runs = []
    sources = [
        os.path.join(ROOT, "submissions", "*", "about_*.md"),
        os.path.join(ROOT, "findings", "*", "run_*", "notes.md"),
    ]

    for pattern in sources:
        for path in glob.glob(pattern):
            text = open(path, encoding="utf-8", errors="replace").read()
            for block in re.split(r"^### run_", text, flags=re.M) or []:
                found = {
                    key: value.strip()
                    for key, value in re.findall(r"^- (sketch \w+|method|game): (.*)$", block, re.M)
                }
                if not any(key.startswith("sketch") for key in found):
                    continue
                runs.append(
                    {
                        "method": found.get("method", "not recorded"),
                        "game": found.get("game", ""),
                        "where": os.path.basename(os.path.dirname(path)),
                        "beginnings": found.get("sketch beginnings", ""),
                        "stems": found.get("sketch stems", ""),
                        "endings": found.get("sketch endings", ""),
                    }
                )
    return runs


def read_plan(path):
    """The three lists a plan names, resolved the way `confirm_plan` resolves them."""
    lists = {"begin": [], "stem": [], "end": []}
    game = None

    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()

        if key == "game":
            game = value.upper()
        if key not in lists or not value:
            continue

        if value.startswith("@"):
            listed = os.path.join(ROOT, value[1:].strip())
            try:
                with open(listed, encoding="utf-8", errors="replace") as handle:
                    for entry in handle:
                        entry = entry.strip()
                        if entry and not entry.startswith("#"):
                            lists[key].append(entry.split(",")[-1].strip())
            except OSError as error:
                raise SystemExit("%s names %s, which cannot be read: %s" % (path, listed, error))
        else:
            lists[key].append(value)

    return lists, game


def agrees_with_rust():
    """The sketch here must match `Sketch::of` in src/fingerprint.rs byte for byte.

    Two implementations of one format, and if they drift this tool reports "nothing on record
    looks like this plan" for every plan for ever -- the reassuring failure rather than the loud
    one. The same literal is pinned in `fingerprint.rs`, in
    `the_python_side_computes_the_same_sketch`.
    """
    pinned = "272847589166a63e81de050a13ba3960bbc39531c9277735d0b9e574cfee006adb07a4b5dba9ed84"
    mine = sketch_of(["mc/mtl_wpn_ak47", "i_wpn_ak47_c", "zmb/ai/nosferatu", "token_7", "_barrel_c"])
    return mine == pinned, mine, pinned


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plan", nargs="?", help="the plan to check before running it")
    parser.add_argument("--runs", action="store_true", help="list the runs that recorded sketches")
    parser.add_argument("--worst", type=int, default=8, help="how many overlaps to show")
    options = parser.parse_args(argv)

    agrees, mine, pinned = agrees_with_rust()
    if not agrees:
        raise SystemExit(
            "This sketch no longer matches the one src/fingerprint.rs writes, so nothing "
            "here could ever match a recorded run.\n\n"
            "  here: %s\n  rust: %s\n\n"
            "Both sides pin the same literal; whichever changed has to be put back, or "
            "both updated together." % (mine, pinned)
        )

    runs = recorded_runs()

    if options.runs or not options.plan:
        print("%d run(s) on disk recorded a sketch.\n" % len(runs))
        for run in runs[: options.worst]:
            print("  %-46s %-10s %s" % (run["method"][:46], run["game"], run["where"]))
        if not runs:
            print(
                "  None yet. Sketches are written by `confirm_plan` and `confirm_cw` from\n"
                "  2026-08-22 onward; runs recorded before that carry only a fingerprint, which\n"
                "  cannot be compared with anything but itself. This fills up as passes are run."
            )
        if not options.plan:
            print("\nGive a plan file to check it against these.")
        return 0

    lists, game = read_plan(options.plan)
    mine = {
        "beginnings": sketch_of(lists["begin"]),
        "stems": sketch_of(lists["stem"]),
        "endings": sketch_of(lists["end"]),
    }

    print(
        "%s: %s beginnings, %s stems, %s endings%s\n"
        % (
            os.path.basename(options.plan),
            format(len(lists["begin"]), ","),
            format(len(lists["stem"]), ","),
            format(len(lists["end"]), ","),
            " (%s)" % game if game else "",
        )
    )

    scored = []
    for run in runs:
        parts = []
        for which in ("beginnings", "stems", "endings"):
            shared = overlap(mine[which], run[which])
            # An unsketched or empty list on either side is not evidence of anything. Treated as
            # a full match it would invent overlap; as none, it would hide it. Left out, so the
            # estimate is over the lists both sides actually have.
            if shared is not None:
                parts.append(shared)

        if not parts:
            continue

        # A cross product overlaps another roughly as the product of its list overlaps: sharing
        # every stem but no ending is not the same ground at all.
        together = 1.0
        for part in parts:
            together *= part
        scored.append((together, parts, run))

    scored.sort(key=lambda row: row[0], reverse=True)
    close = [row for row in scored if row[0] >= WORTH_SAYING]

    if not close:
        print(
            "Nothing on record looks like this plan. Either it is new ground, or the runs that\n"
            "covered it predate sketches -- %d of the %d runs on disk recorded one."
            % (len(runs), len(runs))
        )
        return 0

    print("%-40s %-10s %8s   %s" % ("run", "game", "overlap", "begin / stem / end"))
    for together, parts, run in close[: options.worst]:
        print(
            "%-40s %-10s %7.0f%%   %s"
            % (
                run["method"][:40],
                run["game"],
                100.0 * together,
                " / ".join("%.0f%%" % (100.0 * part) for part in parts),
            )
        )

    print(
        "\nRoughly, to about a fifth either way. This is advice and it blocks nothing.\n\n"
        "If it looks like the same ground, do not widen the plan -- a wider plan overlaps more.\n"
        "Aim it somewhere else: another pool's stems, a family nothing covers, or the beginnings\n"
        "`scripts/uncarried.py` measures as unreachable. `scripts/seams.py` says what is worth\n"
        "aiming at."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
