#!/bin/sh
# The remaining three types of `typed_borrowed_endings`, both games, submitting after each.
#
# This is one invented method finishing its own types, not a rotation over the library -- the
# thing AGENTS.md §2 removed. It ends when the types run out.
cd "$(dirname "$0")/.." || exit 1

for kind in xmodel material image; do
  for game in BLKOPSCW BLKOPS04; do
    echo "=== $kind $game $(date +%H:%M:%S) ==="
    ./bin/windows/confirm_plan.exe "plans/tbe.$kind.txt" --game "$game" \
      --label "$kind cores under borrowed bo3 endings" \
      --script contrib/typed_borrowed_endings.py \
      > "logs/tbe_${kind}_${game}.log" 2>&1
    grep -E "this run added" "logs/tbe_${kind}_${game}.log" | tail -1
    ./bin/windows/submit.exe > "logs/submit_tbe_${kind}_${game}.log" 2>&1
    grep -E "submitted:|nothing new" "logs/submit_tbe_${kind}_${game}.log" | tail -2
  done
done
echo "=== all types done $(date +%H:%M:%S) ==="
