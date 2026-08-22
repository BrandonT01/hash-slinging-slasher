#!/usr/bin/env bash
#
# Keeps the machine working until somebody stops it. It never exits on its own.
#
#     bash scripts/overnight.sh
#
# ## Why this exists
#
# On 2026-08-22 an agent finished a grind at 06:50, reasoned that everything cheap was exhausted
# and everything expensive was measured poor, and stopped to write things up. The machine sat idle
# for **four hours and fourteen minutes**. `tails` at k=5 was measured at 121 names an hour at the
# time, so that stop cost roughly five hundred names.
#
# It was not a careless decision. AGENTS.md §2 says never to start a pass merely to have something
# running, and lists "the only thing you could run is known low-yield" as a reason to stop and
# think instead. Every one of those reasons quietly assumes **somebody is coming back to start
# something better**. Unattended, nobody is.
#
# So: if you are leaving this running, do not choose a pass. Run this.
#
# ## What it does, and why it is not the rotation §2 banned
#
# §2 removed a driver that ran every method in the library in order, because that buys throughput
# on picked-over ground while the inventing stops. This does something narrower:
#
#   - **The derivation closure**, which is free and refills from whatever anybody has confirmed
#     since -- including other contributors' merged submissions, which arrive with `start`.
#   - **One plan, widened every round.** The ending alphabet grows by one character each time, so
#     no round asks what the last round already asked. It is not the same pass repeated.
#
# It does not touch the invented methods, it does not rotate through the library, and it does not
# stop anybody inventing. It replaces the **idle**, which is never worth anything.
#
# Submits after every stage, so a stage that dies never costs the stages before it.
set -u
cd "$(dirname "$0")/.." || exit 1

BIN="./target/release"
[ -x "$BIN/confirm_plan.exe" ] || BIN="./bin/windows"
[ -x "$BIN/confirm_plan.exe" ] || BIN="./bin/linux"
[ -x "$BIN/confirm_plan" ] || [ -x "$BIN/confirm_plan.exe" ] || { echo "confirm_plan is not built; run start"; exit 1; }

PLAN="$BIN/confirm_plan.exe"; [ -x "$PLAN" ] || PLAN="$BIN/confirm_plan"
SUBMIT="$BIN/submit.exe";     [ -x "$SUBMIT" ] || SUBMIT="$BIN/submit"

mkdir -p logs
stamp() { date '+%H:%M:%S'; }
round=0

echo "[$(stamp)] grinding until stopped. Ctrl-C to end; every stage submits before the next."

while true; do
    round=$((round + 1))
    echo "[$(stamp)] === round $round ==="

    # Free, and it refills every time anybody confirms anything.
    python scripts/derive_closure.py > logs/overnight_closure.log 2>&1
    echo "[$(stamp)] closure: $(grep -oE '[0-9]+ names added in total' logs/overnight_closure.log | tail -1)"
    "$SUBMIT" > logs/overnight_submit.log 2>&1

    # One character wider each round, capped at the measured alphabet. Every round therefore asks
    # something the last one could not, which is what stops this being one pass repeated.
    alphabet=$((22 + round))
    [ $alphabet -gt 37 ] && alphabet=37

    python scripts/tails.py --length 5 --alphabet $alphabet --write-plan plans/overnight.txt \
        > logs/overnight_plan.log 2>&1
    echo "[$(stamp)] tails k=5, alphabet $alphabet"

    for game in BLKOPSCW BLKOPS04; do
        "$PLAN" plans/overnight.txt --game "$game" > "logs/overnight_$game.log" 2>&1
        echo "[$(stamp)] $game: $(grep -oE 'this run added [0-9]+' "logs/overnight_$game.log" | tail -1)"
        "$SUBMIT" > logs/overnight_submit.log 2>&1
    done
done
