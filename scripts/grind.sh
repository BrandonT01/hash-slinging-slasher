#!/usr/bin/env bash
#
# An overnight grind: every method this repository has, against both games, submitting as it goes.
#
#     bash scripts/grind.sh                 run the whole rotation once, then loop
#     bash scripts/grind.sh --once          one pass through the rotation and stop
#
# ## Why this exists
#
# A session ends unpredictably -- a usage limit, a closed laptop, a crash -- and an assistant
# driving the grind one command at a time takes the grind down with it. Everything here is CPU
# work that needs no decisions once it has started, so it should not need a decision-maker awake.
#
# The rotation is ordered by measured opportunity, biggest first: sound is the largest unnamed
# ground in either game (70,878 of Black Ops 4's 79,263 `sound_asset` ids, 43,603 of Cold War's
# 50,890 `sound_alias`), so it runs before anything else.
#
# ## What it does after every job
#
# Submits. That is not optional and it is not asked about -- a submitted find is worth more than a
# found one, because the next contributor's search excludes against it. `submit` keeps a ledger,
# refuses to send the same run twice, and drops anything already claimed, so calling it after every
# job is safe and cheap.
#
# Between rotations it re-measures the lists with `derive_lists.py`, which folds every name
# confirmed since into the beginnings and endings. That changes the general search's fingerprint
# and genuinely reopens methods that reported themselves exhausted.
#
# ## Reading the output
#
# Every job writes to `logs/`, and only its last lines matter. Nothing here prints progress to the
# terminal on purpose: a pass prints every thirty seconds for an hour, and pulling that into an
# assistant's context is the one reliable way to waste a usage limit on nothing.
set -u

cd "$(dirname "$0")/.." || exit 1
mkdir -p logs

WIN=bin/windows
EXE=".exe"
if [ ! -x "$WIN/confirm_cw$EXE" ]; then
    WIN=bin/linux
    EXE=""
fi

ONCE=0
[ "${1:-}" = "--once" ] && ONCE=1

say() { printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

# A search, then a submission. The submission is the point; the search is how it gets something to
# submit. A failure in either is logged and stepped over -- one bad job must not end the night.
job() {
    local name="$1"; shift
    local log="logs/grind_${name}.log"

    say "$name"
    if ! "$@" > "$log" 2>&1; then
        say "  $name exited non-zero -- see $log"
    fi

    # The line that says what it found, and nothing else.
    grep -E "^total:|this run found nothing new|already been run" "$log" | tail -2 | sed 's/^/  /'

    "$WIN/submit$EXE" > "logs/grind_${name}_submit.log" 2>&1
    grep -E "submitted:|nothing new to submit|names to send" "logs/grind_${name}_submit.log" \
        | tail -3 | sed 's/^/  /'
}

# A generator piped into confirm_list. Same contract, plus a timeout: a generator with no natural
# end streams for ever, and an overnight run must not spend all of it on one script.
generate() {
    local name="$1" game="$2" script="$3"; shift 3
    local log="logs/grind_${name}.log"

    say "$name"
    timeout 3600 python "$script" "$@" 2>/dev/null \
        | "$WIN/confirm_list$EXE" - --game "$game" --label "$name" --script "$script" \
        > "$log" 2>&1

    grep -E "^total:|this run found nothing new|already been run" "$log" | tail -2 | sed 's/^/  /'

    "$WIN/submit$EXE" > "logs/grind_${name}_submit.log" 2>&1
    grep -E "submitted:|nothing new to submit" "logs/grind_${name}_submit.log" | tail -2 | sed 's/^/  /'
}

rotation=0
while :; do
    rotation=$((rotation + 1))
    say "=== rotation $rotation ==="

    # 1. Sound first, both games. The largest unnamed ground there is, and the pass that needs a
    #    flag rather than happening by default -- which is exactly why it gets neglected.
    job "cw_sound"  "$WIN/confirm_cw$EXE" --game BLKOPSCW --sounds
    job "bo4_sound" "$WIN/confirm_cw$EXE" --game BLKOPS04 --sounds --no-fold

    # 2. The general search, both games.
    job "cw_general"  "$WIN/confirm_cw$EXE" --game BLKOPSCW
    job "bo4_general" "$WIN/confirm_cw$EXE" --game BLKOPS04

    # 3. Every generator, both games. Ordered by what each returned when it was measured.
    for game in BLKOPS04 BLKOPSCW; do
        short=$(echo "$game" | tr 'A-Z' 'a-z')

        for type in model material image anim; do
            generate "${short}_edits_${type}" "$game" scripts/token_edits.py --type "$type"
        done

        generate "${short}_channels"      "$game" scripts/image_channels.py
        generate "${short}_continuations" "$game" scripts/continuations.py --depth 2 --cap 24
        generate "${short}_gaps"          "$game" scripts/families.py --gaps

        for script in scripts/contributed/slotswap_*.py scripts/contributed/templates_*.py \
                      scripts/contributed/image_siblings_*.py; do
            [ -f "$script" ] || continue
            generate "${short}_$(basename "$script" .py)" "$game" "$script"
        done
    done

    # 4. Sound languages reaches Black Ops 4 only -- Cold War's twelve language tables are already
    #    complete, measured at 0 names returned. No point spending an hour proving it twice.
    say "bo4_languages"
    timeout 3600 python scripts/sound_languages.py 2>/dev/null \
        | "$WIN/confirm_list$EXE" - --game BLKOPS04 --no-fold \
          --label "sound language and encoding variants" --script scripts/sound_languages.py \
        > logs/grind_bo4_languages.log 2>&1
    grep -E "^total:" logs/grind_bo4_languages.log | tail -1 | sed 's/^/  /'
    "$WIN/submit$EXE" > logs/grind_bo4_languages_submit.log 2>&1

    # 5. The cross-type and variant binaries, which are their own methods.
    job "images_from_materials" "$WIN/images_from_materials$EXE"
    job "variants"              "$WIN/confirm_variants$EXE"
    job "swaps"                 "$WIN/confirm_variants$EXE" swaps

    # 6. Re-measure. Every name confirmed this rotation becomes a new beginning, a new ending and
    #    a new numbered family for the next one -- which is what makes the next rotation find
    #    things this one could not, rather than repeating it.
    say "re-measuring the lists"
    python scripts/derive_lists.py > logs/grind_derive.log 2>&1
    tail -3 logs/grind_derive.log | sed 's/^/  /'

    [ "$ONCE" = "1" ] && break
done

say "done"
