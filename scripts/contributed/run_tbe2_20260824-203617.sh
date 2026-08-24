#!/bin/sh
# The second band of borrowed endings -- ranks 8,001+ -- which the first pass's cap could not
# express. xmodel is absent on purpose: it has 0 endings past the cap and is exhausted.
#
# `start` is re-run between stages because `readiness::require` refuses to search if it last
# passed more than twelve hours ago, and inside a multi-stage script that refusal does not read
# as one -- METHODS.md records a runner that carried on as though it had searched.
cd "$(dirname "$0")/.." || exit 1

for kind in material image; do
  for game in BLKOPSCW BLKOPS04; do
    echo "=== $kind $game $(date +%H:%M:%S) ==="

    ./bin/windows/start.exe > "logs/start_before_${kind}_${game}.log" 2>&1
    if [ $? -ne 0 ]; then
      echo "  start blocked -- stopping rather than pretending to search"
      tail -5 "logs/start_before_${kind}_${game}.log"
      exit 1
    fi

    ./bin/windows/confirm_plan.exe "plans/tbe2.$kind.txt" --game "$game" \
      --label "$kind cores under borrowed bo3 endings, band 2" \
      --script contrib/typed_borrowed_endings.py \
      > "logs/tbe2_${kind}_${game}.log" 2>&1

    # A stage that reported nothing is a stage that did not run. Say so rather than let it
    # look like an exhausted method.
    if ! grep -q "this run added" "logs/tbe2_${kind}_${game}.log"; then
      echo "  no result reported -- check the log"
      tail -5 "logs/tbe2_${kind}_${game}.log"
      continue
    fi
    grep -E "this run added" "logs/tbe2_${kind}_${game}.log" | tail -1

    ./bin/windows/submit.exe > "logs/submit_tbe2_${kind}_${game}.log" 2>&1
    grep -E "submitted:|nothing new" "logs/submit_tbe2_${kind}_${game}.log" | tail -2
  done
done
echo "=== band 2 done $(date +%H:%M:%S) ==="
