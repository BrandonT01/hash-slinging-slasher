"""Is anything grinding right now? Answers it, and shows how to stop it.

    python scripts/running.py          list every search this machine is running
    python scripts/running.py --stop   stop them

Ten seconds of reconnaissance that would have saved seven and a half hours.

## Why this exists

On 2026-08-22 a background loop was believed killed and was not. The `confirm_plan` **child** was
killed; the shell that would start the next one was not, so the loop carried on and ran for seven
and a half hours, competing for every core with each pass launched in that window and quietly
ruining their timings.

The kill had used `pkill -f forever.sh`, which under Git Bash on Windows matched nothing and
exited **0**. No error, so it was read as success -- and the only thing checked afterwards was
that the current pass had stopped, which says nothing about the loop that starts the next one.

So: check the **parent**, not the child, and check with something that can actually see it.

## Use it before

- **timing anything.** A figure measured while something else has the cores is not a figure.
- **assuming the machine is idle.** "Nothing is running" is a claim worth one command.
- **starting a long pass.** Two confirming tools both load `findings/` at start and rewrite it at
  the end, so running them together loses whichever finishes first from the aggregate.
"""
import argparse
import os
import subprocess
import sys

# The confirming tools, and the shells that drive them. A runner script is the thing that actually
# has to die: killing only what it is currently running just advances it to the next stage.
SEARCHES = ("confirm_plan", "confirm_list", "confirm_cw", "confirm_sounds", "confirm_variants",
            "images_from_materials", "confirm_localize")
DRIVERS = ("bash", "sh", "python")

# A driver is only interesting if it is driving one of ours.
OURS = ("confirm_", "derive_closure", "tails.py", "precedents.py", "final_byte", "cross_era",
        "sab_plan", "splice.py", "uncarried", "overnight", "forever", "night.sh", "queue.sh")


def windows():
    """[(pid, name, command line)] for everything that might be a grind, on Windows."""
    query = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine | "
        "ForEach-Object { \"$($_.ProcessId)`t$($_.Name)`t$($_.CommandLine)\" }"
    )
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command", query],
        capture_output=True, text=True, timeout=120,
    ).stdout

    found = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        pid, name = parts[0].strip(), parts[1].strip()
        command = parts[2] if len(parts) > 2 else ""
        found.append((pid, name, command))
    return found


def unix():
    out = subprocess.run(["ps", "-eo", "pid=,comm=,args="], capture_output=True, text=True).stdout
    found = []
    for line in out.splitlines():
        bits = line.strip().split(None, 2)
        if len(bits) >= 2:
            found.append((bits[0], bits[1], bits[2] if len(bits) > 2 else ""))
    return found


def grinding():
    """Everything running that is one of ours, as (pid, name, why it matched)."""
    listing = windows() if sys.platform.startswith("win") else unix()

    out = []
    for pid, name, command in listing:
        bare = name.lower().replace(".exe", "")

        if bare in SEARCHES:
            out.append((pid, name, "a search"))
            continue

        # A driver only counts if its command line names something of ours -- otherwise every
        # shell on the machine is reported and the output is useless.
        #
        # And never this check or the shell that launched it. A command line that *mentions* a
        # script matches as readily as one running it, so asking "is anything grinding?" from a
        # shell whose command line contains the question reports itself, three times over. Caught
        # by running it against a process it was supposed to find and reading what else came back.
        if bare in DRIVERS and any(mark in command for mark in OURS) and "running.py" not in command:
            out.append((pid, name, "a runner: " + command.strip()[:70]))

    return out


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stop", action="store_true", help="stop everything listed")
    options = parser.parse_args(argv)

    found = grinding()

    if not found:
        print("nothing is grinding. The machine is idle and a timing taken now is a real one.")
        return 0

    print("%d process(es) grinding:\n" % len(found))
    for pid, name, why in found:
        print("  %-8s %-22s %s" % (pid, name, why))

    if not options.stop:
        print(
            "\nRunners are listed as well as searches on purpose: killing a search that a runner\n"
            "started just advances the runner to its next stage. Stop the runner first.\n\n"
            "    python scripts/running.py --stop"
        )
        return 1

    # Runners first, so nothing starts a replacement for the search being killed.
    for pid, name, why in sorted(found, key=lambda row: 0 if "runner" in row[2] else 1):
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/PID", pid, "/F", "/T"], capture_output=True)
            else:
                os.kill(int(pid), 9)
            print("  stopped %s (%s)" % (pid, name))
        except (OSError, ValueError) as error:
            print("  could not stop %s: %s" % (pid, error))

    left = grinding()
    print("\n%s" % ("still running: %d -- check by hand" % len(left) if left
                    else "verified: nothing is grinding now."))
    return 1 if left else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
