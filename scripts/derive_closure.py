"""Every name the names we already have imply, worked out until no more come.

    python scripts/derive_closure.py            derive, confirm, repeat until it stops paying
    python scripts/derive_closure.py --dry-run  say what it would run and how big each is
    python scripts/derive_closure.py --once     one round rather than to a fixpoint
    python scripts/derive_closure.py --game BLKOPS04    force a game for this run

## This is not the rotation AGENTS.md forbids, and the difference is the whole point

§2 removed a driver that ran every method in order, because every method in the library has been
ground repeatedly and running them again buys throughput on picked-over ground while the
inventing stops. That is a real rule and this does not break it.

A **derivation** is not a search. A search asks the game about candidates a rule invented and is
spent once its rule has been asked; a derivation says *this confirmed material implies this image
name*, and it is bounded not by how much ground it has covered but by **how many confirmed names
exist to derive from**. Confirm 400 new materials and the material→image derivation has 400 new
questions it has never asked. It refills as fast as the corpus grows, which is exactly the
snowball §7 describes.

Two consequences, and they are why this loops rather than being a list somebody runs:

  - **It terminates.** Each round derives only from what the round before confirmed. When a round
    adds nothing, the corpus is closed under every relation here and the loop stops. It cannot
    grind on bare ground, because bare ground produces no round.
  - **It is worth running after any pass at all.** `contrib/image_siblings.py` has said so in its
    own docstring since the day it was written -- *"worth re-running after any pass that gains
    materials"* -- and that instruction has only ever been carried out when somebody remembered.

## Why it is worth the machine time

These are the highest yield-per-candidate methods in the project by three orders of magnitude,
and it is not close. Measured from the run record on 2026-08-22:

    image siblings of confirmed materials     596,049 candidates ->  1,514 names   1 per 394
    image channel completion                2,352,722 candidates ->    456 names   1 per 5,160
    sibling token substitution          1,354,263,677 candidates ->    402 names   1 per 3,370,000

A round of this is seconds to minutes, not hours. Run it after every pass.

## What it derives from what

Each entry is a relation measured to hold, not a guess. `scripts/seams.py` is what measures them,
and anything it ranks strongly belongs in this list.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot

ROOT = snapshot.ROOT

# The derivations, in the order a round runs them.
#
# Ordering is not arbitrary and it is not a rotation's ordering either: a derivation that *feeds*
# another goes first, so a single round can carry a name two steps. Materials imply images, and
# images imply their other channels, so a material confirmed at the top of a round can reach a
# channel image by the bottom of the same one.
#
# `label` is what lands in the run notes and therefore in `methods_report.py`, so it must stay
# stable -- renaming one splits its history into two methods that each look half as good.
DERIVATIONS = [
    {
        "label": "image siblings of confirmed materials",
        "script": "contrib/image_siblings.py",
        "args": [],
        "why": "the strongest measured cross-type seam: 15,770 shared cores, 12.8% of image's",
    },
    {
        "label": "materials from image cores",
        "script": "scripts/materials_from_images.py",
        "args": [],
        "why": "the same seam walked the other way, so each side seeds the other",
    },
    {
        "label": "image channel completion",
        "script": "scripts/image_channels.py",
        "args": [],
        "why": "an image we hold one channel of implies the channels beside it",
    },
    {
        "label": "family gap filling",
        "script": "scripts/families.py",
        "args": ["--gaps"],
        "why": "holes between confirmed members of a numbered family",
    },
    {
        "label": "sound language and encoding variants",
        "script": "scripts/sound_languages.py",
        "args": [],
        "why": "the same sound in the other eleven languages; Black Ops 4 only",
    },
]

# A round that adds fewer than this is not worth another round: the next one derives from what
# this one added, so a round of one or two names produces a round of nearly nothing. Stopping is
# the correct outcome and gets reported as one.
WORTH_ANOTHER_ROUND = 1

# Rounds are bounded regardless. A derivation with a bug that emits its own input would otherwise
# loop until somebody noticed, and this runs unattended.
MOST_ROUNDS = 12


def binary(name):
    """Where this platform's copy of a tool is, preferring a build over the committed one."""
    if sys.platform.startswith("win"):
        built = os.path.join(ROOT, "target", "release", name + ".exe")
        shipped = os.path.join(ROOT, "bin", "windows", name + ".exe")
    elif sys.platform == "darwin":
        built = os.path.join(ROOT, "target", "release", name)
        shipped = os.path.join(ROOT, "bin", "macos", name)
    else:
        built = os.path.join(ROOT, "target", "release", name)
        shipped = os.path.join(ROOT, "bin", "linux", name)

    for path in (built, shipped):
        if os.path.exists(path):
            return path
    return None


def confirmed_total(game=None):
    """How many names this machine has confirmed, which is what a round is judged by.

    Counted from the findings files rather than from what `confirm_list` prints, because a round
    is several tools and the only figure that means the same thing across all of them is the one
    on disk.
    """
    folder = os.path.join(ROOT, "findings")
    if not os.path.isdir(folder):
        return 0

    total = 0
    for game_folder in sorted(os.listdir(folder)):
        if game and game_folder.lower() != game.lower():
            continue
        here = os.path.join(folder, game_folder)
        if not os.path.isdir(here):
            continue
        for name in sorted(os.listdir(here)):
            if name.endswith(".txt"):
                with open(os.path.join(here, name), encoding="utf-8", errors="replace") as handle:
                    total += sum(1 for line in handle if line.strip())
    return total


def run_derivation(entry, confirm, game, dry_run):
    """One derivation: generate candidates, hand them to `confirm_list`, report what it found."""
    script = os.path.join(ROOT, entry["script"])
    if not os.path.exists(script):
        print("  %-42s skipped: %s is not here" % (entry["label"], entry["script"]))
        return 0

    generate = [sys.executable, script] + entry["args"]

    if dry_run:
        try:
            produced = subprocess.run(
                generate, cwd=os.path.dirname(script), capture_output=True, text=True, timeout=900
            )
            count = sum(1 for line in produced.stdout.splitlines() if line.strip())
            print("  %-42s %12s candidates" % (entry["label"], format(count, ",")))
        except subprocess.SubprocessError as error:
            print("  %-42s would not run: %s" % (entry["label"], error))
        return 0

    before = confirmed_total(game)

    confirm_args = [
        confirm,
        "-",
        "--label",
        entry["label"],
        "--script",
        entry["script"].replace("\\", "/"),
    ]
    if game:
        confirm_args += ["--game", game]

    # The generator's own folder, because these scripts import `snapshot` as a sibling.
    producer = subprocess.Popen(
        generate, cwd=os.path.dirname(script), stdout=subprocess.PIPE
    )
    consumer = subprocess.Popen(confirm_args, stdin=producer.stdout, stdout=subprocess.DEVNULL)

    # So the generator is told when the confirmer goes away, rather than writing into a pipe
    # nobody is reading.
    producer.stdout.close()
    consumer.wait()
    producer.wait()

    if consumer.returncode != 0:
        print("  %-42s confirm_list exited %d" % (entry["label"], consumer.returncode))
        return 0

    gained = confirmed_total(game) - before
    print("  %-42s %+d" % (entry["label"], gained))
    return max(gained, 0)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="say what it would run, and stop")
    parser.add_argument("--once", action="store_true", help="one round rather than a fixpoint")
    parser.add_argument("--game", help="force a game for this run")
    parser.add_argument(
        "--rounds", type=int, default=MOST_ROUNDS, help="most rounds to run (default %d)" % MOST_ROUNDS
    )
    options = parser.parse_args(argv)

    confirm = binary("confirm_list")
    if not confirm and not options.dry_run:
        raise SystemExit(
            "confirm_list is not built and not committed for this platform.\n"
            "Run `start`, which builds what is missing, or `cargo build --release`."
        )

    if options.dry_run:
        print("the derivations a round would run, and how many candidates each would ask about:\n")
        for entry in DERIVATIONS:
            run_derivation(entry, confirm, options.game, True)
        print("\nNothing was confirmed and nothing was written.")
        return 0

    started = confirmed_total(options.game)
    print("closing the corpus under %d derivations, from %s confirmed names\n"
          % (len(DERIVATIONS), format(started, ",")))

    total = 0
    for round_number in range(1, max(options.rounds, 1) + 1):
        print("round %d" % round_number)
        gained = sum(
            run_derivation(entry, confirm, options.game, False) for entry in DERIVATIONS
        )
        total += gained
        print("  round %d added %d\n" % (round_number, gained))

        if options.once:
            break
        if gained < WORTH_ANOTHER_ROUND:
            print(
                "no derivation found anything new, so the corpus is closed under all of them.\n"
                "That is the correct end, not a failure: it means every name these relations can\n"
                "reach from what is confirmed has been reached. The next round comes free after\n"
                "the next pass that confirms anything."
            )
            break
    else:
        print("stopped at the round limit (%d) with names still arriving." % options.rounds)

    print("\n%d names added in total. Now run `submit`." % total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
